from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Iterable, Set, Dict
import numpy as np
from workalendar.europe import Italy  # pip install workalendar

# Simple cache
__CLOSURES_CACHE: dict[tuple[int, Path], Set[date]] = {}
__ITALY_CACHE: dict[int, Set[date]] = {}

def _parse_any_date(s: str) -> date | None:
    """Parsa una stringa data (varie forme) -> date | None."""
    if not s:
        return None
    s = s.strip()
    if not s or s.startswith("#"):
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def _load_closures_file(txt_path: Path) -> Set[date]:
    """Legge un file .txt con una data per riga OPPURE un range 'data1:data2' (inclusivo)."""
    dates: Set[date] = set()
    if not txt_path.exists():
        return dates
    for raw in txt_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            a, b = [t.strip() for t in line.split(":", 1)]
            d1, d2 = _parse_any_date(a), _parse_any_date(b)
            if d1 and d2:
                if d1 > d2:
                    d1, d2 = d2, d1
                d = d1
                while d <= d2:
                    dates.add(d)
                    d += timedelta(days=1)
            continue
        d = _parse_any_date(line)
        if d:
            dates.add(d)
    return dates

def load_closures_for_year(year: int, base_dir: Path) -> Set[date]:
    """Carica le chiusure aziendali dal file 'ferie_<year>.txt' nella cartella base_dir."""
    key = (year, base_dir.resolve())
    if key in __CLOSURES_CACHE:
        return __CLOSURES_CACHE[key].copy()
    file = base_dir / f"ferie_{year}.txt"
    dates = _load_closures_file(file)
    __CLOSURES_CACHE[key] = dates.copy()
    return dates

def italy_holidays_for_year(year: int) -> Set[date]:
    """Festività nazionali italiane per l'anno (via workalendar, include Pasquetta)."""
    if year in __ITALY_CACHE:
        return __ITALY_CACHE[year].copy()
    cal = Italy()
    # cal.holidays(year) -> List[Tuple[date, 'label']]
    dates = {d for (d, _label) in cal.holidays(year)}
    __ITALY_CACHE[year] = dates.copy()
    return dates

def get_busday_holidays(
    years: Iterable[int],
    base_dir: Path,
    include_neighbor_years: bool = True,
) -> np.ndarray:
    """
    Costruisce l'array di giorni NON lavorativi (da passare a numpy.busday_count come 'holidays'):
    - weekend esclusi automaticamente da busday_count;
    - restituisce un np.ndarray dtype=datetime64[D] con FESTIVITÀ NAZIONALI + CHIUSURE AZIENDALI.
    - Se include_neighbor_years=True carica anche ferie_<minY-1>.txt e ferie_<maxY+1>.txt
      per catturare range a cavallo d'anno presenti nei file "adiacenti".
    """
    years = sorted(set(int(y) for y in years))
    if not years:
        return np.array([], dtype="datetime64[D]")  # nessuna restrizione extra

    all_years: list[int] = list(years)
    if include_neighbor_years:
        all_years = [years[0] - 1] + all_years + [years[-1] + 1]

    blocked: Set[date] = set()
    # Festività nazionali per tutti gli anni
    for y in all_years:
        if y > 0:  # sicurezza
            blocked |= italy_holidays_for_year(y)

    # Chiusure aziendali per tutti gli anni (se il file non esiste, viene ignorato)
    for y in all_years:
        if y > 0:
            blocked |= load_closures_for_year(y, base_dir=base_dir)

    if not blocked:
        return np.array([], dtype="datetime64[D]")

    # np.busday_count si aspetta un array ordinato e unico di datetime64[D]
    arr = np.array(sorted({d.isoformat() for d in blocked}), dtype="datetime64[D]")
    return arr



# ----------------------------------------------------------
# ------------------STAMPA DI DEBUG-------------------------
# ----------------------------------------------------------

def _parse_as_of(d: object) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        s = d.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
    raise ValueError(f"Impossibile interpretare la data: {d!r}")

def check_holidays(
    as_of_date: object,
    base_dir: Path,
    *,
    lookbehind_years: int = 0,
    lookahead_years: int = 0,
    include_neighbor_years: bool = True,
    sample: int = 10,
    echo: bool = True,
) -> Dict[str, object]:
    """
    Autoverifica dei giorni NON lavorativi usati da np.busday_count.
    - as_of_date: data di riferimento (str/date/datetime)
    - base_dir: cartella dove si trovano i file ferie_<YYYY>.txt
    - lookbehind/lookahead: anni extra da includere oltre ad as_of.year
    - include_neighbor_years: carica anche ferie_<minY-1> e ferie_<maxY+1> (per range a cavallo d'anno)
    - sample: quante date mostrare in testa/coda
    - echo: se True stampa un riepilogo leggibile su stdout

    Ritorna un dict con breakdown dettagliato (utile per test).
    """
    ref = _parse_as_of(as_of_date)
    years_req = sorted({y for y in range(ref.year - lookbehind_years, ref.year + lookahead_years + 1) if y > 0})
    if not years_req:
        years_req = [ref.year]

    # Anni realmente usati (aggiungo vicini se richiesto)
    years_used = list(years_req)
    if include_neighbor_years:
        years_used = [years_req[0] - 1] + years_used + [years_req[-1] + 1]
        years_used = [y for y in years_used if y > 0]

    # Festività nazionali per anno (via workalendar, con cache del modulo)
    national_by_year: Dict[int, int] = {}
    national_all = set()
    for y in years_used:
        ds = italy_holidays_for_year(y)
        national_by_year[y] = len(ds)
        national_all |= ds

    # Chiusure aziendali per anno e file trovati
    closures_by_year: Dict[int, int] = {}
    files_found: Dict[int, str] = {}
    closures_all = set()
    for y in years_used:
        p = base_dir / f"ferie_{y}.txt"
        if p.exists():
            files_found[y] = str(p.resolve())
        ds = load_closures_for_year(y, base_dir=base_dir)
        closures_by_year[y] = len(ds)
        closures_all |= ds

    # Array finale per np.busday_count (può essere vuoto)
    arr = np.array(sorted({d.isoformat() for d in (national_all | closures_all)}), dtype="datetime64[D]")
    total_nat = len(national_all)
    total_clo = len(closures_all)
    total_blk = len(arr)

    # Stampa un riepilogo (se richiesto)
    if echo:
        head = [str(x) for x in arr[:sample]]
        tail = [str(x) for x in arr[-sample:]] if total_blk > sample else []
        print("== Autoverifica giorni NON lavorativi ==")
        print(f"Riferimento: {ref.isoformat()}")
        print(f"Anni richiesti: {years_req}")
        print(f"Anni effettivamente usati (con adiacenti={include_neighbor_years}): {years_used}")
        print("\n-- Festività nazionali (workalendar) --")
        for y in sorted(national_by_year):
            print(f"  {y}: {national_by_year[y]} date")
        print(f"Totale festività nazionali uniche: {total_nat}")

        print("\n-- Chiusure aziendali (ferie_<YYYY>.txt) --")
        for y in sorted(closures_by_year):
            mark = " (file presente)" if y in files_found else ""
            print(f"  {y}: {closures_by_year[y]} date{mark}")
        if files_found:
            print("File trovati:")
            for y in sorted(files_found):
                print(f"  {y}: {files_found[y]}")
        print(f"Totale chiusure aziendali uniche: {total_clo}")

        print("\n-- Unione (festività + chiusure) --")
        print(f"Totale giorni NON lavorativi unici: {total_blk}")
        if head:
            print(f"Prime {len(head)}: {', '.join(head)}")
        if tail:
            print(f"Ultime {len(tail)}: {', '.join(tail)}")
        print("== Fine autoverifica ==\n")

    return {
        "reference_date": ref,
        "years_requested": years_req,
        "years_used": years_used,
        "files_found": files_found,
        "national_by_year": national_by_year,
        "closures_by_year": closures_by_year,
        "total_national": total_nat,
        "total_closures": total_clo,
        "total_blocked": total_blk,
        "blocked_preview_head": [str(x) for x in arr[:sample]],
        "blocked_preview_tail": [str(x) for x in arr[-sample:]] if total_blk > sample else [],
        "holidays_array_dtype": str(arr.dtype),
    }
