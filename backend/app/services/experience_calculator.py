import re
from datetime import datetime
from typing import Any

NOW = datetime.now()
CURRENT_YEAR = NOW.year
CURRENT_MONTH = NOW.month

PRESENT_PATTERN = re.compile(
    r"present|hiện\s*tại|hiện\s*nay|đến\s*nay|nay|now|current|ongoing",
    re.IGNORECASE,
)


def enrich_with_experience(parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
    result = dict(parsed)
    years = _to_int(result.get("experienceYears"))
    months = _to_int(result.get("experienceMonths"))

    if years is not None or months is not None:
        result["experienceYears"] = years or 0
        result["experienceMonths"] = months or 0
        return result

    total_months = _calculate_experience_months(raw_text)
    if total_months > 0:
        result["experienceYears"] = total_months // 12
        result["experienceMonths"] = total_months % 12
        result["experienceSource"] = "calculated"
    return result


def enrich_with_phone(parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
    result = dict(parsed)
    phone = str(result.get("phone") or "").strip()
    if _normalize_phone(phone):
        result["phone"] = _normalize_phone(phone)
        return result

    extracted = _extract_phone(raw_text)
    if extracted:
        result["phone"] = extracted
    return result


def _calculate_experience_months(text: str) -> int:
    intervals: list[tuple[int, int]] = []

    for match in re.finditer(
        r"(\d{1,2})[/.\-](\d{4})\s*[-–—~]\s*(\d{1,2})[/.\-](\d{4})",
        text,
    ):
        start = _to_month_index(int(match.group(2)), int(match.group(1)))
        end = _to_month_index(int(match.group(4)), int(match.group(3)))
        intervals.append(_clamp_interval(start, end))

    for match in re.finditer(
        r"(\d{1,2})[/.\-](\d{4})\s*[-–—~]\s*(" + PRESENT_PATTERN.pattern + r")",
        text,
        re.IGNORECASE,
    ):
        start = _to_month_index(int(match.group(2)), int(match.group(1)))
        end = _to_month_index(CURRENT_YEAR, CURRENT_MONTH)
        intervals.append(_clamp_interval(start, end))

    for match in re.finditer(
        r"(\d{4})\s*[-–—~]\s*(\d{4}|" + PRESENT_PATTERN.pattern + r")",
        text,
        re.IGNORECASE,
    ):
        start = _to_month_index(int(match.group(1)), 1)
        end_str = match.group(2)
        if PRESENT_PATTERN.search(end_str):
            end = _to_month_index(CURRENT_YEAR, CURRENT_MONTH)
        else:
            end = _to_month_index(int(end_str), 12)
        intervals.append(_clamp_interval(start, end))

    explicit = re.search(
        r"(\d+)\+?\s*(?:năm|years?)\s*(?:(\d+)\s*(?:tháng|months?))?",
        text,
        re.IGNORECASE,
    )
    if explicit and not intervals:
        years = int(explicit.group(1))
        months = int(explicit.group(2) or 0)
        return years * 12 + months

    merged = _merge_intervals(intervals)
    return sum(end - start + 1 for start, end in merged)


def _extract_phone(text: str) -> str:
    labeled = re.search(
        r"(?:phone|tel|mobile|điện\s*thoại|sđt|sdt|liên\s*hệ)[:\s]*([+\d\s.\-()]{8,24})",
        text,
        re.IGNORECASE,
    )
    if labeled:
        normalized = _normalize_phone(labeled.group(1))
        if normalized:
            return normalized

    patterns = [
        r"\(\s*\+?\s*84\s*\)\s*(\d{3})\s*(\d{3})\s*(\d{3,4})",
        r"\+84[\s.\-()]*(\d{2,3})[\s.\-()]*(\d{3})[\s.\-()]*(\d{3,4})",
        r"(?<!\d)0\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3,4}(?!\d)",
        r"(?<!\d)0\d{9}(?!\d)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        raw = match.group(0) if match.lastindex is None else "".join(g for g in match.groups() if g)
        normalized = _normalize_phone(raw)
        if normalized:
            return normalized
    return ""


def _normalize_phone(value: str) -> str:
    """
    Chuẩn hóa SĐT Việt Nam.
    - 10 số, bắt đầu 0 → giữ nguyên
    - 9 số, bắt đầu 3/5/7/8/9 → thêm 0 đầu (UV bỏ số 0)
    - 9 số đã có 0 đầu nhưng thiếu 1 số → không đoán, trả ""
    - Các trường hợp khác → ""
    """
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("84") and len(digits) >= 11:
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        return digits
    if len(digits) == 9 and digits[0] in "35789":
        return "0" + digits
    return ""


def _to_month_index(year: int, month: int) -> int:
    return year * 12 + max(1, min(12, month))


def _clamp_interval(start: int, end: int) -> tuple[int, int]:
    if end < start:
        start, end = end, start
    return start, end


def _merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip().split(".")[0])
    except ValueError:
        return None
