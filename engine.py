import hashlib
import json
from dataclasses import asdict

from models import RaceResult
from filters import matches
from formatter import format_alert


def _result_hash(result: RaceResult) -> str:
    """Compute an MD5 hash of the full result dict (sorted keys)."""
    data = json.dumps(asdict(result), sort_keys=True, default=str)
    return hashlib.md5(data.encode()).hexdigest()


def _result_id(result: RaceResult) -> str:
    """Stable identity key for a result (track + race + horse)."""
    return f"{result.track}|{result.race_number}|{result.horse}"


class NotificationEngine:
    def __init__(self, filter_config: dict | None = None):
        self.filter_config = filter_config
        # Maps result_id -> last hash that was sent
        self.sent: dict[str, str] = {}

    def process(self, result: RaceResult) -> str | None:
        """Return formatted alert string if result is a match, else None.

        Resends if the result data has changed since the last alert.
        """
        if result.result != "1st":
            return None

        if not matches(self.filter_config, result):
            return None

        result_id = _result_id(result)
        current_hash = _result_hash(result)

        if self.sent.get(result_id) == current_hash:
            # Already sent this exact data; no resend needed
            return None

        self.sent[result_id] = current_hash
        return format_alert(result)

    def process_batch(self, results: list[RaceResult]) -> list[str]:
        """Process multiple results and return all generated alerts."""
        alerts = []
        for result in results:
            alert = self.process(result)
            if alert is not None:
                alerts.append(alert)
        return alerts
