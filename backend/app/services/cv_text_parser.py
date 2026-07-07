import re
from typing import Any

from app.services.date_parser import (
    DATE_RANGE_RE,
    find_date_ranges,
    format_date_mm_yyyy,
    format_duration,
    parse_date_to_month,
    parse_year,
    total_months_from_ranges,
)

EXPERIENCE_SECTION = re.compile(
    r"(?:^|\n)\s*(?:experience|work\s*experience|employment|professional\s*experience|"
    r"kinh\s*nghiệm)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

PROJECT_SECTION = re.compile(
    r"(?:^|\n)\s*(?:project\s*experience|projects?|dự\s*án)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

EDUCATION_SECTION = re.compile(
    r"(?:^|\n)\s*(?:education|học\s*vấn|qualification|academic)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

SKILLS_SECTION = re.compile(
    r"(?:^|\n)\s*(?:skills|kỹ\s*năng|technical\s*skills)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

LANGUAGE_SECTION = re.compile(
    r"(?:^|\n)\s*(?:languages?|ngôn\s*ngữ)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

AWARDS_SECTION = re.compile(
    r"(?:^|\n)\s*(?:awards?|giải\s*thưởng|honors?)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

CERT_SECTION_HEADER = re.compile(
    r"(?:^|\n)\s*(?:certifications?|certificate|chứng\s*chỉ)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

EDUCATION_KW = re.compile(
    r"university|đại\s*học|college|học\s*viện|institute|school|academy|bachelor|master|phd",
    re.IGNORECASE,
)

JOB_TITLE_KW = re.compile(
    r"engineer|developer|intern|manager|analyst|lead|architect|consultant|specialist",
    re.IGNORECASE,
)


def extract_section(text: str, header: re.Pattern[str]) -> str:
    match = header.search(text)
    if not match:
        return ""
    start = match.end()
    end = len(text)
    for stop in (
        EDUCATION_SECTION, SKILLS_SECTION, LANGUAGE_SECTION, PROJECT_SECTION,
        EXPERIENCE_SECTION, AWARDS_SECTION, CERT_SECTION_HEADER,
    ):
        if stop.pattern == header.pattern:
            continue
        stop_match = stop.search(text, start)
        if stop_match:
            end = min(end, stop_match.start())
    return text[start:end].strip()


def extract_location(text: str) -> str:
    patterns = [
        r"(Ho\s*Chi\s*Minh\s*City|Hà\s*Nội|Hanoi|Da\s*Nang|Đà\s*Nẵng)[,\s]*(?:Viet\s*Nam|Vietnam)?",
        r"([A-Z][a-zA-Z\s]+),\s*(?:Viet\s*Nam|Vietnam|USA|Singapore|Japan)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip().rstrip(",")
    return ""


def extract_languages(text: str) -> list[str]:
    section = extract_section(text, LANGUAGE_SECTION)
    if not section:
        return []

    results: list[str] = []
    for line in section.splitlines():
        line = line.strip().lstrip("•-* ")
        if not line or len(line) > 120:
            continue
        if re.search(
            r"\benglish\b|\btiếng\s*anh\b|\bvietnamese\b|\btiếng\s*việt\b|"
            r"\bjapanese\b|\bchinese\b|\btoeic\b|\bielts\b",
            line,
            re.I,
        ):
            results.append(line)
    return results[:6]


def extract_education(text: str) -> list[dict[str, str]]:
    section = extract_section(text, EDUCATION_SECTION)
    if not section:
        return []

    items: list[dict[str, str]] = []
    lines = [ln.strip() for ln in section.splitlines() if ln.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        if DATE_RANGE_RE.search(line):
            i += 1
            continue

        if i + 1 < len(lines):
            next_line = lines[i + 1]
            date_match = DATE_RANGE_RE.search(next_line)
            if date_match:
                school = line
                degree = ""
                if re.search(r"\s[–\-]\s", line):
                    parts = re.split(r"\s*[–\-]\s*", line, maxsplit=1)
                    if len(parts) == 2:
                        degree, school = parts[0].strip(), parts[1].strip()
                if EDUCATION_KW.search(line) or EDUCATION_KW.search(school):
                    start, end = date_match.group(1), date_match.group(2)
                    items.append({
                        "school": school,
                        "degree": degree,
                        "major": "",
                        "startYear": str(parse_year(start) or ""),
                        "endYear": str(parse_year(end) or ""),
                        "startDate": start.strip(),
                        "endDate": end.strip(),
                    })
                i += 2
                continue
        i += 1

    return items[:6]


def extract_work_history(text: str) -> list[dict[str, str]]:
    exp_section = extract_section(text, EXPERIENCE_SECTION)
    items: list[dict[str, str]] = []

    if exp_section:
        items.extend(_parse_jobs_from_section(exp_section))

    if not items:
        full = text
        items.extend(_parse_jobs_from_section(full))

    return _dedupe_jobs(items)[:12]


ACHIEVEMENT_KW = re.compile(
    r"\b(achiev|award|prize|increased|reduced|improved|delivered|saved|won|top\s+\d)",
    re.IGNORECASE,
)

BULLET_START = re.compile(
    r"^(?:•|\-|\*|developed|led|contributed|built|worked|responsible|managed|"
    r"designed|implemented|created|maintained|supported|collaborated)",
    re.IGNORECASE,
)


def _normalize_experience_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        while i + 1 < len(lines):
            nxt = lines[i + 1]
            if DATE_RANGE_RE.search(nxt) and not DATE_RANGE_RE.search(line):
                line = f"{line} {nxt}".strip()
                i += 1
                continue
            if (
                not DATE_RANGE_RE.search(line)
                and not DATE_RANGE_RE.search(nxt)
                and re.match(r"^[a-z]", nxt)
            ):
                line = f"{line}{nxt}"
                i += 1
                continue
            break
        merged.append(line)
        i += 1
    return merged


def _parse_jobs_from_section(section: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    lines = _normalize_experience_lines(
        [ln.strip() for ln in section.splitlines() if ln.strip()]
    )

    i = 0
    while i < len(lines):
        line = lines[i]
        date_match = DATE_RANGE_RE.search(line)

        if date_match:
            start, end = date_match.group(1).strip(), date_match.group(2).strip()
            position, company = "", ""

            prefix = line[: date_match.start()].strip(" ,–-")
            if prefix:
                job_match = re.match(r"^(.+?),\s*(.+)$", prefix)
                if job_match and JOB_TITLE_KW.search(job_match.group(1)):
                    position, company = job_match.group(1).strip(), job_match.group(2).strip()
                elif JOB_TITLE_KW.search(prefix):
                    position = prefix
                else:
                    company = prefix

            if i > 0 and (not company or not position):
                prev = lines[i - 1]
                if not DATE_RANGE_RE.search(prev) and not prev.lower().startswith(("key ", "•", "-")):
                    job_match = re.match(r"^(.+?),\s*(.+)$", prev)
                    if job_match and JOB_TITLE_KW.search(job_match.group(1)):
                        if not position:
                            position = job_match.group(1).strip()
                        if not company:
                            company = job_match.group(2).strip()
                    elif JOB_TITLE_KW.search(prev) and not position:
                        position = prev
                        if i > 1 and not company:
                            company = lines[i - 2]
                    elif not company:
                        company = prev

            if i + 1 < len(lines) and not position:
                nxt = lines[i + 1]
                if JOB_TITLE_KW.search(nxt) and not DATE_RANGE_RE.search(nxt) and len(nxt) < 80:
                    position = nxt
                    i += 1

            if company or position:
                description, achievement = _collect_job_details(lines, i + 1)
                items.append({
                    "company": company or "N/A",
                    "project": "",
                    "position": position or "N/A",
                    "startDate": start,
                    "endDate": end,
                    "duration": format_duration(start, end),
                    "description": description,
                    "achievement": achievement,
                })
        i += 1

    return items


def _collect_job_details(lines: list[str], start_idx: int) -> tuple[str, str]:
    scope_parts: list[str] = []
    achievement_parts: list[str] = []

    for j in range(start_idx, min(start_idx + 8, len(lines))):
        line = lines[j].strip().lstrip("•-* ")
        if not line:
            continue
        if DATE_RANGE_RE.search(line):
            break
        if (
            not BULLET_START.match(line)
            and j + 1 < len(lines)
            and JOB_TITLE_KW.search(lines[j + 1])
            and not DATE_RANGE_RE.search(lines[j + 1])
            and len(lines[j + 1]) < 80
        ):
            break
        if (
            JOB_TITLE_KW.search(line)
            and not BULLET_START.match(line)
            and len(line) < 80
            and not scope_parts
        ):
            break
        if len(line) < 12:
            continue
        is_scope_line = bool(
            BULLET_START.match(line)
            or re.match(r"^[a-z]", line)
            or re.search(r"\b(project|system|platform|module|application|app|dashboard)\b", line, re.I)
        )
        if not is_scope_line:
            if (
                j + 1 < len(lines)
                and JOB_TITLE_KW.search(lines[j + 1])
                and not DATE_RANGE_RE.search(lines[j + 1])
            ):
                break
            continue
        if ACHIEVEMENT_KW.search(line):
            achievement_parts.append(line)
        else:
            scope_parts.append(line)

    return "; ".join(scope_parts[:3]), "; ".join(achievement_parts[:2])


def _dedupe_jobs(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = f"{item.get('company','')}|{item.get('position','')}|{item.get('startDate','')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def extract_stated_experience_years(text: str) -> int | None:
    patterns = [
        r"(\d+)\+?\s*years?\s+of\s+experience",
        r"(\d+)\+?\s*years?\s+experience",
        r"experience[:\s]+(\d+)\+?\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            years = int(match.group(1))
            if 0 < years <= 40:
                return years
    return None


def build_work_summary(work_history: list[dict[str, Any]]) -> str:
    from app.services.career_summary import build_work_summary as _build
    return _build(work_history)
