from models import RaceResult

SEX_ABBREV = {
    "colt": "colt",
    "filly": "filly",
    "gelding": "gelding",
    "mare": "mare",
    "horse": "horse",
}


def _sex_abbrev(sex: str) -> str:
    """Return lowercase sex abbreviation."""
    return SEX_ABBREV.get(sex.lower(), sex.lower())


def format_alert(result: RaceResult) -> str:
    """Format a winning RaceResult into a 1- or 2-line alert string."""
    # --- Line 1 ---
    race_label = f"Race {result.race_number}"
    if result.race_name:
        race_label = f"Race {result.race_number} ({result.race_name})"

    if result.distance_m is not None:
        distance_str = f" over {result.distance_m:,}m"
    else:
        distance_str = ""

    line1 = (
        f"{result.horse} ({result.sire}) won {race_label} "
        f"at {result.track}{distance_str}."
    )

    # --- Line 2 ---
    parts = []

    # Age and sex prefix
    age_sex_parts = []
    if result.age is not None:
        age_sex_parts.append(f"{result.age}yo")
    if result.sex:
        age_sex_parts.append(_sex_abbrev(result.sex))
    if age_sex_parts:
        parts.append(" ".join(age_sex_parts))

    # Trainer
    if result.trainer:
        parts.append(f"trained by {result.trainer}")

    # Sales info
    if result.sale_price is not None:
        sale_str = f"${result.sale_price:,}"
        if result.sale_name:
            sale_str += f" {result.sale_name}"
        provenance_parts = []
        if result.vendor:
            provenance_parts.append(result.vendor)
        if result.buyer:
            provenance_parts.append(result.buyer)
        if provenance_parts:
            sale_str += f" ({' → '.join(provenance_parts)})"
        parts.append(sale_str)

    if not parts:
        return line1

    line2 = ", ".join(parts) + "."
    return f"{line1}\n{line2}"
