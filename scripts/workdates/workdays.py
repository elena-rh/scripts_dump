#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
workdays.py
Small script that returns the number of elapsed work days between two dates,
START and END **included**, using the already implemented holidays_provider.py.

Example:
  python workdays.py 2025-10-07 2025-10-23
  python workdays.py 07/10/2025 23/10/2025 --closures-dir ./ferie
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, date, timedelta
import argparse
import numpy as np

# Import your provider (must be in the same directory or on PYTHONPATH)
from utils.holidays_provider import get_busday_holidays

# ---- Configurable default: where ferie_<YYYY>.txt live (can be overridden via --closures-dir)
DEFAULT_CLOSURES_DIR: Path = (Path(__file__).parent / "chiusure_aziendali").resolve()


def parse_date_any(s: str) -> date:
    """Parse a date in several common formats and return a datetime.date."""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(f"Cannot parse date: {s!r}. "
                                     f"Supported formats: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, MM/DD/YYYY")


def _years_between_inclusive(a: date, b: date) -> set[int]:
    """Return all calendar years touched by [a, b] inclusive."""
    y0, y1 = a.year, b.year
    if y0 <= y1:
        return set(range(y0, y1 + 1))
    return set(range(y1, y0 + 1))


def count_workdays_inclusive(
    start: date,
    end: date,
    *,
    closures_dir: Path = DEFAULT_CLOSURES_DIR,
    include_neighbor_years: bool = True,
) -> int:
    """
    Count working days between start and end, **including** both boundaries.
    - Weekends excluded by default (Mon-Fri weekmask).
    - National holidays + company closures excluded via holidays_provider.get_busday_holidays(...).

    If end < start, returns the **negative** of the count for [end, start].
    """
    if start == end:
        # one-day interval, included if it's a working day after exclusions
        years = {start.year}
        hol = get_busday_holidays(years, base_dir=closures_dir, include_neighbor_years=include_neighbor_years)
        s = np.datetime64(start.isoformat())
        # include the same day -> end exclusive trick: end = start + 1 day
        e = np.datetime64((start + timedelta(days=1)).isoformat())
        return int(np.busday_count(s, e, holidays=hol))

    # Handle reversed intervals by symmetry (return negative)
    if end < start:
        return -count_workdays_inclusive(end, start, closures_dir=closures_dir,
                                         include_neighbor_years=include_neighbor_years)

    # Normal forward interval
    years = _years_between_inclusive(start, end)
    hol = get_busday_holidays(years, base_dir=closures_dir, include_neighbor_years=include_neighbor_years)

    s = np.datetime64(start.isoformat())
    # Make end inclusive by adding 1 day (end is exclusive in busday_count)
    e = np.datetime64((end + timedelta(days=1)).isoformat())
    return int(np.busday_count(s, e, holidays=hol))


def main():
    ap = argparse.ArgumentParser(
        description="Return the number of elapsed work days between START and END (both included)."
    )
    ap.add_argument("start", type=parse_date_any, help="Start date (YYYY-MM-DD or DD/MM/YYYY, etc.)")
    ap.add_argument("end",   type=parse_date_any, help="End date (inclusive)")
    ap.add_argument(
        "--closures-dir",
        type=lambda p: Path(p).resolve(),
        default=DEFAULT_CLOSURES_DIR,
        help=f"Folder containing ferie_<YYYY>.txt files (default: {DEFAULT_CLOSURES_DIR})"
    )
    ap.add_argument(
        "--no-neighbors",
        action="store_true",
        help="Do not load neighbor years (min-1, max+1) when building holidays (default: load them)."
    )
    args = ap.parse_args()

    days = count_workdays_inclusive(
        start=args.start,
        end=args.end,
        closures_dir=args.closures_dir,
        include_neighbor_years=not args.no_neighbors,
    )
    # Print just the integer (easy to consume in scripts)
    print(days)


if __name__ == "__main__":
    main()