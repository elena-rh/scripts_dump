import re
from typing import Optional, Tuple

class DateInvalidError(ValueError):
    """Raised when a date is invalid (es. 40/12/2025)."""
    pass

def extract_date_token(date_string: Optional[str]) -> Optional[Tuple[int, int, int]]:
    """Return (a, b, y) as ints if a valid date token is found at start of date_string; else None."""
    if not date_string:
        return None
    
    # Accept '/', '-', '.' as separators and allow 2 or 4 digit years
    _date_token_re = re.compile(r"^\s*(\d{1,2})[\/\-.](\d{1,2})\/\-.")# (r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})") # (r"^\s*(\d{1,2})\/\-.\/\-.")
    m = _date_token_re.match(date_string.strip())
    if not m:
        return None
    a, b, y = map(int, m.groups())

    # Normalize two-digit years (assume 2000+ for simplicity)
    if y < 100:
        y += 2000

    if not is_valid_date(a, b, y):
        raise DateInvalidError(f"Found invalid date: '{date_string}'")

    return (a, b, y)


def is_valid_date(a: int, b: int, y: int) -> bool:
    """
    Simple validation: day and month ranges only + year between 1900 and 2100.
    Does NOT check leap years or actual calendar correctness.
    """
    return 1 <= a <= 31 and 1 <= b <= 12 and 1900 <= y <= 2100


def detect_date_order(dates: list[str]) -> Optional[str]:
        """
        Heuristic:
        - if we see left > 12 at least once => left cannot be month => DMY
        - if we see middle > 12 at least once => middle cannot be month  => MDY
        - first decisive signal wins; if none found in the sample, return None

        Arguments:
            dates: (list[str]): a list of dates

        Returns: a string that is either "DMY" or "MDY" or None if ambiguous
        """
        # Loop over each target column and a limited number of rows to find a decisive token quickly
        for date in dates:
            tok = extract_date_token(date)
            if not tok:
                continue
            a, b, _y = tok
            if a > 12:
                return "DMY"
            if b > 12:
                return "MDY"
        print("[WARN] Date order ambiguous in sample: defaulting to DMY (day/month/year)")
        return "DMY"