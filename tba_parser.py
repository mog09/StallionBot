"""Parser for TBA (Thoroughbred Breeders Australia) black-type results CSV export.

Expected columns (tab-separated):
    Race ID, Meet date, Group, State, Club, Venue, Current Race Name, Sponsor,
    Distance, Prize, Age Criteria, Sex, Condition, Registered Race Name,
    Dead Heat, 1st Place Name, 1st Place Born, 1st Place Colour,
    1st Place Country, 1st Place Sex, 1st Place Sire, 1st Place Dam,
    1st Place Dam Sire, 1st Place Breeder, 1st Place Breeder State,
    1st Place Trainer, 1st Place Jockey, 1st Place Owner,
    2nd Place Name, 2nd Place Born, 2nd Place Country, 2nd Place Sex,
    3rd Place Name, 3rd Place Born, 3rd Place Country, 3rd Place Sex
"""

import csv
import re
from datetime import datetime
from typing import Optional

from models import RaceResult

# TBA State codes → country string
_STATE_TO_COUNTRY = {
    "NSW": "AUS", "VIC": "AUS", "QLD": "AUS", "SA": "AUS",
    "WA": "AUS", "TAS": "AUS", "ACT": "AUS", "NT": "AUS",
    "NZ": "NZ", "HK": "HK",
}

# TBA sex codes → standard sex strings
_SEX_MAP = {
    "C": "Colt",
    "F": "Filly",
    "G": "Gelding",
    "M": "Mare",
    "H": "Horse",
    "R": "Rig",
}

# TBA Group codes → race_class strings
_GROUP_MAP = {
    "G1": "G1", "GROUP 1": "G1",
    "G2": "G2", "GROUP 2": "G2",
    "G3": "G3", "GROUP 3": "G3",
    "LR": "LR", "LISTED": "LR",
}


def _parse_distance(raw: str) -> Optional[int]:
    """Extract integer metres from strings like '1200', '1200m', '1m200'."""
    if not raw:
        return None
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


def _parse_age(meet_date_str: str, born_str: str) -> Optional[int]:
    """Calculate age in years from meet date and birth year.

    TBA 'Meet date' is typically DD/MM/YYYY or YYYY-MM-DD.
    'Born' is typically a 4-digit year.
    """
    if not meet_date_str or not born_str:
        return None
    try:
        born_year = int(re.sub(r"[^\d]", "", born_str))
    except ValueError:
        return None

    # Try common date formats
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            meet_date = datetime.strptime(meet_date_str.strip(), fmt)
            return meet_date.year - born_year
        except ValueError:
            continue
    return None


def _normalise_sex(raw: str) -> Optional[str]:
    if not raw:
        return None
    return _SEX_MAP.get(raw.strip().upper(), raw.strip().capitalize())


def _normalise_group(raw: str) -> Optional[str]:
    if not raw:
        return None
    return _GROUP_MAP.get(raw.strip().upper(), raw.strip())


def _normalise_country(state: str, horse_country: str) -> Optional[str]:
    """Prefer explicit horse country field; fall back to state mapping."""
    if horse_country:
        c = horse_country.strip().upper()
        if c in ("AUS", "AUSTRALIA"):
            return "AUS"
        if c in ("NZ", "NEW ZEALAND"):
            return "NZ"
        if c in ("HK", "HONG KONG"):
            return "HK"
    if state:
        return _STATE_TO_COUNTRY.get(state.strip().upper())
    return None


def parse_tba_csv(filepath: str) -> list[RaceResult]:
    """Parse a TBA results CSV export and return a list of RaceResult objects.

    Only rows with a valid 1st place horse and sire are included.
    """
    results = []

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        # Auto-detect delimiter (tab or comma)
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        reader = csv.DictReader(f, dialect=dialect)

        for row in reader:
            horse = (row.get("1st Place Name") or "").strip()
            sire = (row.get("1st Place Sire") or "").strip()

            if not horse or not sire:
                continue  # skip incomplete rows

            track = (row.get("Venue") or "").strip()
            meet_date = (row.get("Meet date") or "").strip()
            born = (row.get("1st Place Born") or "").strip()
            state = (row.get("State") or "").strip()
            horse_country = (row.get("1st Place Country") or "").strip()
            trainer_raw = (row.get("1st Place Trainer") or "").strip()

            results.append(RaceResult(
                track=track or "Unknown",
                horse=horse,
                sire=sire,
                result="1st",
                race_name=(row.get("Current Race Name") or "").strip() or None,
                distance_m=_parse_distance(row.get("Distance") or ""),
                age=_parse_age(meet_date, born),
                sex=_normalise_sex(row.get("1st Place Sex") or ""),
                trainer=trainer_raw or None,
                race_class=_normalise_group(row.get("Group") or ""),
                country=_normalise_country(state, horse_country),
                # Sales info not in TBA export — omitted
            ))

    return results
