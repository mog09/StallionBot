"""Client for The Racing API (theracingapi.com).

Fetches race results and maps them to RaceResult objects.
Authentication: HTTP Basic Auth (username=api_key, password=api_secret).
"""

import re
import time
import requests
from datetime import date, timedelta
from typing import Optional

from models import RaceResult

BASE_URL = "https://api.theracingapi.com/v1"

# Single-letter sex codes used by the Racing API
_SEX_MAP = {
    "G": "Gelding",
    "C": "Colt",
    "F": "Filly",
    "M": "Mare",
    "H": "Horse",
    "R": "Rig",
}

# Pattern field values → race_class strings
_PATTERN_MAP = {
    "group 1": "G1",
    "group 2": "G2",
    "group 3": "G3",
    "listed": "LR",
    "g1": "G1",
    "g2": "G2",
    "g3": "G3",
    "lr": "LR",
}


def _strip_country(course: str) -> str:
    """Strip trailing country suffix from course name.

    'Ballinrobe (IRE)' -> 'Ballinrobe'
    'Ascot (GB)'       -> 'Ascot'
    """
    return re.sub(r"\s*\([^)]+\)\s*$", "", course).strip()


def _race_class(pattern: str, cls: str) -> Optional[str]:
    """Resolve race class from pattern and class fields."""
    for val in (pattern, cls):
        if val:
            mapped = _PATTERN_MAP.get(val.strip().lower())
            if mapped:
                return mapped
            if val.strip():
                return val.strip()
    return None


def _map_runner(runner: dict, race: dict) -> Optional[RaceResult]:
    """Map a single runner dict + race dict to a RaceResult. Returns None if not a winner."""
    if str(runner.get("position", "")).strip() != "1":
        return None

    horse = (runner.get("horse") or "").strip()
    sire = (runner.get("sire") or "").strip()
    if not horse or not sire:
        return None

    dist_raw = race.get("dist_m") or ""
    try:
        distance_m = int(re.sub(r"[^\d]", "", str(dist_raw))) if dist_raw else None
    except ValueError:
        distance_m = None

    try:
        age = int(runner["age"]) if runner.get("age") else None
    except (ValueError, TypeError):
        age = None

    sex_code = (runner.get("sex") or "").strip().upper()
    sex = _SEX_MAP.get(sex_code)

    return RaceResult(
        track=_strip_country(race.get("course") or "Unknown"),
        horse=horse,
        sire=sire,
        result="1st",
        race_name=(race.get("race_name") or "").strip() or None,
        distance_m=distance_m,
        age=age,
        sex=sex,
        trainer=(runner.get("trainer") or "").strip() or None,
        race_class=_race_class(race.get("pattern") or "", race.get("class") or ""),
        country=(race.get("region") or "").strip() or None,
    )


class RacingAPIClient:
    def __init__(self, username: str, password: str, timeout: int = 30):
        self.auth = (username, password)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = self.auth

    def get_results(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[RaceResult]:
        """Fetch race results and return winning RaceResult objects.

        Args:
            start_date: 'YYYY-MM-DD' (defaults to today)
            end_date:   'YYYY-MM-DD' (defaults to start_date)
            region:     Filter by region e.g. 'GB', 'IRE' (optional)
            limit:      Results per page (max 50)
            skip:       Pagination offset
        """
        if start_date is None:
            start_date = date.today().isoformat()
        if end_date is None:
            end_date = start_date

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit,
            "skip": skip,
        }
        if region:
            params["region"] = region

        response = self.session.get(
            f"{BASE_URL}/results",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        winners = []
        for race in data.get("results", []):
            for runner in race.get("runners", []):
                result = _map_runner(runner, race)
                if result is not None:
                    winners.append(result)
        return winners

    def get_all_results(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[RaceResult]:
        """Fetch all pages of results for the given date range."""
        all_winners = []
        skip = 0
        limit = 50

        while True:
            batch = self.get_results(
                start_date=start_date,
                end_date=end_date,
                region=region,
                limit=limit,
                skip=skip,
            )
            all_winners.extend(batch)
            if len(batch) < limit:
                break
            skip += limit

        return all_winners
