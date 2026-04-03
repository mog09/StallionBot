import re
import difflib
from models import RaceResult

FUZZY_THRESHOLD = 0.82


def _strip_suffix(s: str) -> str:
    """Remove parenthetical country/origin suffixes like (GB), (AUS)."""
    return re.sub(r'\s*\([^)]+\)\s*$', '', s).strip()


def fuzzy_match(a: str, b: str) -> bool:
    """Case-insensitive fuzzy match, stripping parenthetical suffixes."""
    a_clean = _strip_suffix(a.lower())
    b_clean = _strip_suffix(b.lower())
    ratio = difflib.SequenceMatcher(None, a_clean, b_clean).ratio()
    return ratio >= FUZZY_THRESHOLD


def evaluate_filter(f: dict, result: RaceResult) -> bool:
    """Evaluate a single filter against a RaceResult."""
    field = f.get("field")
    op = f.get("op", "eq")
    value = f.get("value")

    result_value = getattr(result, field, None)

    if result_value is None:
        return False

    if op == "eq":
        if isinstance(result_value, str) and isinstance(value, str):
            return fuzzy_match(result_value, value)
        return result_value == value
    elif op == "ne":
        if isinstance(result_value, str) and isinstance(value, str):
            return not fuzzy_match(result_value, value)
        return result_value != value
    elif op == "gt":
        return result_value > value
    elif op == "gte":
        return result_value >= value
    elif op == "lt":
        return result_value < value
    elif op == "lte":
        return result_value <= value
    elif op == "contains":
        if isinstance(result_value, str) and isinstance(value, str):
            return value.lower() in result_value.lower()
        return False
    else:
        raise ValueError(f"Unknown operator: {op}")


def evaluate_group(group: dict, result: RaceResult) -> bool:
    """Evaluate a FilterGroup (AND/OR/NOT) against a RaceResult."""
    logic = group.get("logic", "AND")
    filters = group.get("filters", [])

    if logic == "NOT":
        # Negate a sub-group or single filter
        if not filters:
            return True
        # Treat the contents as an AND group and negate
        sub = {"logic": "AND", "filters": filters}
        return not evaluate_group(sub, result)
    elif logic == "AND":
        return all(_evaluate_item(f, result) for f in filters)
    elif logic == "OR":
        return any(_evaluate_item(f, result) for f in filters)
    else:
        raise ValueError(f"Unknown logic operator: {logic}")


def _evaluate_item(item: dict, result: RaceResult) -> bool:
    """Dispatch to evaluate_filter or evaluate_group depending on item shape."""
    if "logic" in item:
        return evaluate_group(item, result)
    return evaluate_filter(item, result)


def matches(filter_config: dict | None, result: RaceResult) -> bool:
    """Returns True if result matches filter_config. Returns True if no filter_config."""
    if filter_config is None:
        return True
    return evaluate_group(filter_config, result)
