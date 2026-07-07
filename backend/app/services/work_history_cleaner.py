"""Lọc và chuẩn hóa work_history — loại bỏ dòng mô tả công việc bị nhận nhầm."""

import re
from typing import Any

from app.services.cv_text_parser import JOB_TITLE_KW, EDUCATION_KW
from app.services.date_parser import DATE_RANGE_RE, parse_date_to_month

BULLET_START = re.compile(
    r"^(\.\s*)?(developed|led|contributed|built|worked|responsible|managed|"
    r"designed|implemented|created|maintained|supported|collaborated|onboarding)",
    re.IGNORECASE,
)

MONTH_PATTERN = (
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
)


def clean_company_name(company: str) -> str:
    value = str(company or "").strip()
    if not value:
        return ""

    value = DATE_RANGE_RE.sub("", value).strip(" ,–-")
    value = re.sub(rf"({MONTH_PATTERN})\s*$", "", value, flags=re.IGNORECASE).strip(" ,–-")
    value = re.sub(r"\s+", " ", value)
    return value


def clean_position_name(position: str) -> str:
    value = str(position or "").strip()
    if value.upper() == "N/A":
        return ""
    if len(value) > 80 or BULLET_START.match(value):
        return ""
    return value


def is_valid_work_entry(item: dict[str, Any]) -> bool:
    company = clean_company_name(item.get("company", ""))
    position = clean_position_name(item.get("position", ""))
    start = str(item.get("startDate") or "").strip()
    end = str(item.get("endDate") or "").strip()

    if not start or start.upper() == "N/A":
        return False
    if not parse_date_to_month(start, end=False):
        return False
    if not company and not position:
        return False
    if company and EDUCATION_KW.search(company) and not JOB_TITLE_KW.search(position):
        return False
    if company and company.upper() == "N/A" and not position:
        return False
    if position and not company and not JOB_TITLE_KW.search(position):
        return False
    if end and end.upper() not in ("N/A", "") and not parse_date_to_month(end, end=True):
        if not re.search(r"present|now|current|hiện", end, re.I):
            return False
    return bool(company or position)


def sanitize_work_entry(item: dict[str, Any]) -> dict[str, str]:
    company = clean_company_name(item.get("company", ""))
    position = clean_position_name(item.get("position", ""))
    start = str(item.get("startDate") or "").strip()
    end = str(item.get("endDate") or "").strip()

    if DATE_RANGE_RE.search(company):
        match = DATE_RANGE_RE.search(company)
        if match and not start:
            start, end = match.group(1).strip(), match.group(2).strip()
        company = clean_company_name(company)

    if not position and company:
        job_match = re.match(r"^(.+?),\s*(.+)$", company)
        if job_match and JOB_TITLE_KW.search(job_match.group(1)):
            position, company = job_match.group(1).strip(), job_match.group(2).strip()
            company = clean_company_name(company)

    return {
        "company": company or "N/A",
        "project": str(item.get("project") or "").strip(),
        "position": position or "N/A",
        "startDate": start,
        "endDate": end,
        "duration": str(item.get("duration") or "").strip(),
        "description": str(item.get("description") or "").strip(),
        "project": str(item.get("project") or "").strip(),
        "achievement": str(item.get("achievement") or "").strip(),
    }


def clean_work_history(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if not items:
        return []

    cleaned: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw in items:
        if not isinstance(raw, dict):
            continue
        entry = sanitize_work_entry(raw)
        if not is_valid_work_entry(entry):
            continue
        key = (
            f"{entry['company']}|{entry['position']}|{entry['startDate']}"
        ).lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(entry)

    return cleaned
