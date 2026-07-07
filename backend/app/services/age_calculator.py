from datetime import datetime
from typing import Any


CURRENT_YEAR = datetime.now().year


def enrich_with_age(parsed: dict[str, Any]) -> dict[str, Any]:
    result = dict(parsed)
    birth_year = _to_int(result.get("birthYear"))

    if birth_year:
        result["age"] = CURRENT_YEAR - birth_year
        result["ageSource"] = "birthYear"
        return result

    estimated = _to_int(result.get("estimatedAge"))
    if estimated:
        result["age"] = estimated
        result["ageSource"] = "estimated"
        return result

    education = result.get("education") or []
    start_years = [_to_int(item.get("startYear")) for item in education if isinstance(item, dict)]
    start_years = [y for y in start_years if y]
    if start_years:
        inferred_birth = min(start_years) - 18
        result["age"] = CURRENT_YEAR - inferred_birth
        result["ageSource"] = "estimated"
        result["birthYear"] = str(inferred_birth)
        return result

    result["age"] = None
    result["ageSource"] = "unknown"
    return result


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip()[:4])
    except ValueError:
        return None
