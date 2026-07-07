import re
from typing import Any

from app.services.cv_text_parser import extract_education, extract_stated_experience_years
from app.services.date_parser import (
    CURRENT_MONTH,
    CURRENT_YEAR,
    merge_intervals,
    months_between,
    parse_date_to_month,
    parse_year,
    total_months_from_ranges,
    find_date_ranges,
    intervals_from_ranges,
)
from app.services.cv_text_parser import extract_work_history, EDUCATION_KW

MIN_BIRTH_YEAR = 1960
MAX_BIRTH_YEAR = CURRENT_YEAR - 18


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip().split(".")[0])
    except ValueError:
        return None


def _is_education_entry(item: dict[str, Any]) -> bool:
    text = f"{item.get('company', '')} {item.get('position', '')}"
    return bool(EDUCATION_KW.search(text))


def calculate_experience_months(
    raw_text: str,
    work_history: list[dict[str, Any]] | None = None,
) -> int:
    history = work_history or []
    job_items = [i for i in history if isinstance(i, dict) and not _is_education_entry(i)]

    intervals = []
    for item in job_items:
        start = parse_date_to_month(item.get("startDate", ""), end=False)
        end = parse_date_to_month(item.get("endDate", ""), end=True)
        if start and end and end >= start:
            intervals.append((start, end))

    if not intervals:
        parsed_jobs = extract_work_history(raw_text)
        for item in parsed_jobs:
            start = parse_date_to_month(item.get("startDate", ""), end=False)
            end = parse_date_to_month(item.get("endDate", ""), end=True)
            if start and end:
                intervals.append((start, end))

    if intervals:
        merged = merge_intervals(intervals)
        total = sum(months_between(s, e) for s, e in merged)
        if total > 0:
            calculated = min(total, 40 * 12)
            stated = extract_stated_experience_years(raw_text)
            if stated and stated * 12 > calculated:
                return stated * 12
            return calculated

    stated = extract_stated_experience_years(raw_text)
    if stated:
        return stated * 12

    return 0


def calculate_age(
    raw_text: str,
    ai_birth_year: Any = None,
    ai_estimated_age: Any = None,
    education: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    edu_list = education or []
    if not edu_list:
        edu_list = extract_education(raw_text)

    excluded = _collect_non_birth_years(raw_text, edu_list)

    birth_year = _find_birth_year_in_text(raw_text, excluded)
    if birth_year:
        return _age_result(birth_year, "birthYear")

    ai_year = _to_int(ai_birth_year)
    if ai_year and _is_plausible_birth_year(ai_year) and ai_year not in excluded:
        if _birth_year_confirmed_in_text(raw_text, ai_year):
            return _age_result(ai_year, "birthYear")

    stated_age = _find_stated_age(raw_text)
    if stated_age:
        return {"birthYear": "", "age": stated_age, "ageSource": "stated"}

    inferred = _infer_birth_from_education(edu_list, excluded, raw_text)
    if inferred:
        return _age_result(inferred, "estimated")

    return {"birthYear": "", "age": None, "ageSource": "unknown"}


def _age_result(birth_year: int, source: str) -> dict[str, Any]:
    age = CURRENT_YEAR - birth_year
    if not (17 <= age <= 70):
        return {"birthYear": "", "age": None, "ageSource": "unknown"}
    return {"birthYear": str(birth_year), "age": age, "ageSource": source}


def _is_plausible_birth_year(year: int) -> bool:
    return MIN_BIRTH_YEAR <= year <= MAX_BIRTH_YEAR


def _collect_non_birth_years(raw_text: str, education: list[dict[str, Any]]) -> set[int]:
    excluded: set[int] = {CURRENT_YEAR, CURRENT_YEAR + 1}
    for item in education:
        if not isinstance(item, dict):
            continue
        for key in ("startYear", "endYear"):
            year = _to_int(item.get(key))
            if year:
                excluded.add(year)
        for key in ("startDate", "endDate"):
            year = parse_year(str(item.get(key, "")))
            if year:
                excluded.add(year)
    return excluded


def _find_birth_year_in_text(raw_text: str, excluded: set[int]) -> int | None:
    patterns = [
        r"(?:sinh|born|ngày\s*sinh|date\s*of\s*birth|dob|birthday)[:\s]*\d{1,2}[/.\-]\d{1,2}[/.\-](\d{4})",
        r"(?:sinh|born|ngày\s*sinh|date\s*of\s*birth|dob|birthday)[:\s]*(\d{4})",
        r"(?:sinh|born)\s*(\d{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            year = int(match.group(1))
            if _is_plausible_birth_year(year) and year not in excluded:
                return year

    linkedin = re.search(r"linkedin\.com/in/[^/\s]*?(\d{4})", raw_text, re.I)
    if linkedin:
        year = int(linkedin.group(1))
        if _is_plausible_birth_year(year) and year not in excluded:
            return year
    return None


def _birth_year_confirmed_in_text(raw_text: str, year: int) -> bool:
    return bool(re.search(
        rf"(?:sinh|born|dob|ngày\s*sinh).*{year}|{year}.*(?:sinh|born)",
        raw_text,
        re.IGNORECASE,
    ))


def _find_stated_age(raw_text: str) -> int | None:
    patterns = [
        r"(?:tuổi|age)[:\s]*(\d{1,2})\b",
        r"\b(\d{1,2})\s*(?:tuổi|years?\s*old)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            age = int(match.group(1))
            if 17 <= age <= 65:
                return age
    return None


def _infer_birth_from_education(
    education: list[dict[str, Any]],
    excluded: set[int],
    raw_text: str = "",
) -> int | None:
    start_years: list[int] = []

    for item in education:
        if not isinstance(item, dict):
            continue
        start = _to_int(item.get("startYear")) or parse_year(str(item.get("startDate", "")))
        if start and 1985 <= start <= CURRENT_YEAR:
            start_years.append(start)

    if not start_years and raw_text:
        for item in extract_education(raw_text):
            start = _to_int(item.get("startYear")) or parse_year(str(item.get("startDate", "")))
            if start:
                start_years.append(start)

    if not start_years:
        return None

    birth_year = min(start_years) - 18
    if _is_plausible_birth_year(birth_year) and birth_year not in excluded:
        return birth_year
    return None
