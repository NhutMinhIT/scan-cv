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

MONTH_NAMES: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

DATE_TOKEN = (
    r"(?:"
    rf"(?<![a-zA-Z])(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{{4}}"
    r"|\d{1,2}[/.\-]\d{4}"
    r"|\d{4}"
    r")"
)

DATE_RANGE_RE = re.compile(
    rf"({DATE_TOKEN})\s*[-–—~]\s*({DATE_TOKEN}|{PRESENT_PATTERN.pattern})",
    re.IGNORECASE,
)


def parse_date_to_month(value: str, end: bool = False) -> int | None:
    value = str(value or "").strip()
    if not value:
        return None
    if PRESENT_PATTERN.search(value):
        return _month_index(CURRENT_YEAR, CURRENT_MONTH)

    month_year = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if month_year:
        month = MONTH_NAMES[month_year.group(1).lower()[:4].rstrip(".")]
        year = int(month_year.group(2))
        if _is_valid_year(year):
            return _month_index(year, month)

    mm_yyyy = re.match(r"(\d{1,2})[/.\-](\d{4})", value)
    if mm_yyyy:
        month, year = int(mm_yyyy.group(1)), int(mm_yyyy.group(2))
        if _is_valid_year(year):
            return _month_index(year, month)

    yyyy = re.match(r"(\d{4})", value)
    if yyyy:
        year = int(yyyy.group(1))
        if _is_valid_year(year):
            return _month_index(year, 12 if end else 1)
    return None


def parse_year(value: str) -> int | None:
    value = str(value or "").strip()
    if PRESENT_PATTERN.search(value):
        return CURRENT_YEAR

    month_year = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if month_year:
        return int(month_year.group(2))

    mm_yyyy = re.match(r"(\d{1,2})[/.\-](\d{4})", value)
    if mm_yyyy:
        return int(mm_yyyy.group(2))

    yyyy = re.match(r"(\d{4})", value)
    if yyyy:
        return int(yyyy.group(1))
    return None


def find_date_ranges(text: str) -> list[tuple[str, str]]:
    return [(m.group(1).strip(), m.group(2).strip()) for m in DATE_RANGE_RE.finditer(text)]


def _month_index(year: int, month: int) -> int:
    return year * 12 + max(1, min(12, month))


def _is_valid_year(year: int) -> bool:
    return 1980 <= year <= CURRENT_YEAR + 1


def months_between(start: int, end: int) -> int:
    return max(0, end - start + 1)


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []
    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        ls, le = merged[-1]
        if start <= le + 1:
            merged[-1] = (ls, max(le, end))
        else:
            merged.append((start, end))
    return merged


def intervals_from_ranges(ranges: list[tuple[str, str]]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for start_s, end_s in ranges:
        start = parse_date_to_month(start_s, end=False)
        end = parse_date_to_month(end_s, end=True)
        if start and end and end >= start:
            intervals.append((start, end))
    return intervals


def total_months_from_ranges(ranges: list[tuple[str, str]]) -> int:
    intervals = intervals_from_ranges(ranges)
    if not intervals:
        return 0
    merged = merge_intervals(intervals)
    return sum(months_between(s, e) for s, e in merged)


def format_date_mm_yyyy(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return "?"
    if PRESENT_PATTERN.search(value):
        return "hiện tại"

    mm_yyyy = re.match(r"(\d{1,2})[/.\-](\d{4})", value)
    if mm_yyyy:
        return f"{int(mm_yyyy.group(1)):02d}/{mm_yyyy.group(2)}"

    month_year = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(\d{4})",
        value,
        re.IGNORECASE,
    )
    if month_year:
        month = MONTH_NAMES[month_year.group(1).lower()[:4].rstrip(".")]
        return f"{month:02d}/{month_year.group(2)}"

    yyyy = re.match(r"(\d{4})", value)
    if yyyy:
        return f"01/{yyyy.group(1)}"
    return value


def format_duration(start: str, end: str) -> str:
    start_m = parse_date_to_month(start, end=False)
    end_m = parse_date_to_month(end, end=True)
    if not start_m or not end_m or end_m < start_m:
        return ""
    total = months_between(start_m, end_m)
    years, months = divmod(total, 12)
    parts = []
    if years:
        parts.append(f"{years} năm")
    if months:
        parts.append(f"{months} tháng")
    return " ".join(parts)
