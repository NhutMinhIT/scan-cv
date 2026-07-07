"""Trích xuất toàn bộ field từ raw text CV — hoạt động với mọi format."""

import re
from typing import Any

from app.services.cv_text_parser import (
    EDUCATION_KW,
    JOB_TITLE_KW,
    SKILLS_SECTION,
    extract_education,
    extract_languages,
    extract_location,
    extract_section,
    extract_work_history,
    build_work_summary,
)
from app.services.date_parser import DATE_RANGE_RE, format_duration, parse_date_to_month
from app.services.experience_calculator import _extract_phone, _normalize_phone
from app.services.work_history_cleaner import clean_company_name, clean_work_history

CERT_SECTION = re.compile(
    r"(?:^|\n)\s*(?:certifications?|certificate|chứng\s*chỉ)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

AWARDS_SECTION = re.compile(
    r"(?:^|\n)\s*(?:awards?|giải\s*thưởng|honors?)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

KNOWN_SKILLS = [
    "React", "React.js", "Next.js", "Node.js", "Python", "Java", "TypeScript",
    "JavaScript", "SQL", "MongoDB", "PostgreSQL", "AWS", "Docker", "Kubernetes",
    "Vue", "Vue.js", "Angular", "FastAPI", "NestJS", "Express", "Git", "Figma",
    "React Native", "Redis", "GraphQL", "CI/CD", "Agile", "Tailwind", "Redux",
    "Nuxt.js", "MS SQL", "RabbitMQ", "Microservices", "Cypress", "Storybook",
]

TITLE_KW = (
    "developer", "engineer", "manager", "designer", "intern", "analyst",
    "architect", "lead", "senior", "junior", "software", "frontend", "backend",
    "fullstack", "full-stack", "kỹ sư", "lập trình", "devops",
)


def extract_all_fields(raw_text: str) -> dict[str, Any]:
    """Trích xuất mọi field có thể từ text — dùng làm nguồn dự phòng khi AI thiếu."""
    skills = extract_skills(raw_text)
    work = _merge_work_history(extract_work_history(raw_text), _extract_jobs_from_projects(raw_text))

    return {
        "name": extract_name(raw_text),
        "email": extract_email(raw_text),
        "phone": _extract_phone(raw_text),
        "location": extract_location(raw_text),
        "title": extract_title(raw_text),
        "currentCompany": work[0].get("company", "") if work else "",
        "facebook": _extract_url(raw_text, "facebook"),
        "linkedin": _extract_url(raw_text, "linkedin"),
        "github": _extract_url(raw_text, "github"),
        "skills": skills,
        "keywords": skills[:10],
        "languages": extract_languages(raw_text),
        "certifications": extract_certifications(raw_text),
        "education": extract_education(raw_text),
        "workHistory": work,
        "birthYear": "",
        "estimatedAge": "",
        "experienceYears": "",
        "experienceMonths": "",
        "summary": build_work_summary(work) if work else "",
    }


def extract_name(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:8]:
        if "@" in line or re.search(r"https?://|linkedin|github|phone|tel:", line, re.I):
            continue
        if re.match(r"^[\d\s()+\-./]+$", line):
            continue
        if DATE_RANGE_RE.search(line):
            continue
        if len(line) > 60:
            continue
        if re.match(r"^[A-ZÀ-Ỹ][A-ZÀ-Ỹ\s'.-]{2,}$", line):
            return line.title() if line.isupper() else line
        if re.match(r"^[A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,4}$", line):
            return line
    return lines[0] if lines else ""


def extract_email(text: str) -> str:
    match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    return match.group(0) if match else ""


def extract_title(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[1:12]:
        lower = line.lower()
        if any(k in lower for k in TITLE_KW) and len(line) < 80:
            if not DATE_RANGE_RE.search(line) and "@" not in line:
                return line
    return ""


def extract_skills(text: str) -> list[str]:
    found: list[str] = []
    section = extract_section(text, SKILLS_SECTION)
    source = section or text

    for skill in KNOWN_SKILLS:
        if re.search(rf"\b{re.escape(skill)}\b", source, re.IGNORECASE):
            found.append(skill)

    for line in source.splitlines():
        line = line.strip().lstrip("•-* ")
        if not line or len(line) > 50:
            continue
        if ":" in line:
            _, items = line.split(":", 1)
            for part in re.split(r"[,;|/]", items):
                part = part.strip()
                if 2 < len(part) < 30:
                    found.append(part)

    seen: set[str] = set()
    result: list[str] = []
    for s in found:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            result.append(s)
    return result[:25]


def extract_certifications(text: str) -> list[str]:
    section = extract_section(text, CERT_SECTION)
    if not section:
        return []

    results: list[str] = []
    for line in section.splitlines():
        line = line.strip().lstrip("•-* ")
        if not line or len(line) < 5 or len(line) > 150:
            continue
        if re.match(r"^(?:certifications?|certificate|chứng\s*chỉ|awards?)$", line, re.I):
            continue
        if re.search(r"prize|scholarship|contest|giải\s*thưởng|award", line, re.I):
            continue
        if re.search(r"certificate|certification|chứng|google|coursera|udemy|aws|azure", line, re.I):
            results.append(line)
    return results[:10]


def _extract_url(text: str, platform: str) -> str:
    patterns = {
        "facebook": r"(?:https?://)?(?:www\.)?(?:facebook|fb)\.com/[\w.\-/?=&%]+",
        "linkedin": r"(?:https?://)?(?:www\.)?linkedin\.com/[\w.\-/?=&%]+",
        "github": r"(?:https?://)?(?:www\.)?github\.com/[\w.\-]+",
    }
    match = re.search(patterns[platform], text, re.IGNORECASE)
    if not match:
        return ""
    url = match.group(0).rstrip(".,;)")
    return url if url.startswith("http") else f"https://{url}"


def _extract_jobs_from_projects(text: str) -> list[dict[str, str]]:
    from app.services.cv_text_parser import PROJECT_SECTION

    section = extract_section(text, PROJECT_SECTION)
    if not section:
        return []

    items: list[dict[str, str]] = []
    blocks = re.split(r"\n{2,}", section)

    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        date_match = DATE_RANGE_RE.search(block)
        if not date_match or not lines:
            continue

        start, end = date_match.group(1).strip(), date_match.group(2).strip()
        company, position, project = "", "", ""

        header = lines[0]
        if re.search(r"\s[–\-]\s", header):
            parts = re.split(r"\s*[–\-]\s*", header, maxsplit=1)
            left, right = parts[0].strip(), parts[1].strip()
            if JOB_TITLE_KW.search(left) and not JOB_TITLE_KW.search(right):
                position, company = left, right
            elif not JOB_TITLE_KW.search(left) and JOB_TITLE_KW.search(right):
                project, position = left, right
            else:
                project, company = left, right
        else:
            project = header

        for line in lines[1:6]:
            if re.match(r"^(?:position|vị trí)\s*:", line, re.I):
                position = line.split(":", 1)[1].strip()
            elif re.match(r"^(?:company|công ty)\s*:", line, re.I):
                company = line.split(":", 1)[1].strip()
            elif re.match(r"^(?:project|dự án)\s*:", line, re.I):
                project = line.split(":", 1)[1].strip()
            elif JOB_TITLE_KW.search(line) and not DATE_RANGE_RE.search(line) and len(line) < 80:
                if not position:
                    position = line
                elif not company and not project:
                    company = line

        if company or project:
            desc_lines = [
                ln.strip().lstrip("•-* ")
                for ln in lines[1:]
                if ln.strip() and not DATE_RANGE_RE.search(ln)
                and not re.match(r"^(?:position|vị trí|company|công ty|project|dự án)\s*:", ln, re.I)
                and len(ln.strip()) > 15
            ]
            description = "; ".join(desc_lines[:3])
            items.append({
                "company": company or project or "N/A",
                "project": project if company else "",
                "position": position or "N/A",
                "startDate": start,
                "endDate": end,
                "duration": format_duration(start, end),
                "description": description,
                "achievement": "",
            })

    return items[:12]


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _merge_scalar(ai_val: Any, text_val: Any) -> Any:
    ai_ok = not _is_empty(ai_val)
    text_ok = not _is_empty(text_val)
    if ai_ok and text_ok:
        ai_s, text_s = str(ai_val).strip(), str(text_val).strip()
        if len(text_s) > len(ai_s) * 1.5:
            return text_val
        return ai_val
    return ai_val if ai_ok else text_val


def _filter_languages(items: list) -> list:
    results: list = []
    for item in items:
        line = str(item).strip()
        if not line:
            continue
        if re.search(r"prize|scholarship|contest|award|giải\s*thưởng", line, re.I):
            continue
        if re.search(
            r"\benglish\b|\btiếng\s*anh\b|\bvietnamese\b|\btiếng\s*việt\b|"
            r"\btoeic\b|\bielts\b|\bjapanese\b|\bchinese\b",
            line,
            re.I,
        ):
            results.append(line)
    return results


def _filter_certifications(items: list) -> list:
    results: list = []
    for item in items:
        line = str(item).strip()
        if not line:
            continue
        if re.search(r"prize|scholarship|contest|giải\s*thưởng|award", line, re.I):
            continue
        if re.search(r"certificate|certification|chứng|google|coursera|udemy|aws|azure", line, re.I):
            results.append(line)
    return results


def _merge_filtered_list(text_list: Any, ai_list: Any, filter_fn) -> list:
    text_items = filter_fn(text_list if isinstance(text_list, list) else [])
    if text_items:
        return text_items
    return filter_fn(ai_list if isinstance(ai_list, list) else [])


def _merge_list(ai_list: Any, text_list: Any) -> list:
    ai_items = ai_list if isinstance(ai_list, list) else []
    text_items = text_list if isinstance(text_list, list) else []
    seen: set[str] = set()
    merged: list = []
    for item in ai_items + text_items:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def _job_key(item: dict) -> str:
    return f"{item.get('company','')}|{item.get('position','')}|{item.get('startDate','')}".lower()


def _merge_work_history(ai_list: Any, text_list: Any) -> list[dict[str, Any]]:
    text_items = clean_work_history([i for i in (text_list or []) if isinstance(i, dict)])
    ai_items = clean_work_history([i for i in (ai_list or []) if isinstance(i, dict)])

    if len(text_items) >= max(1, len(ai_items)):
        primary, secondary = text_items, ai_items
    else:
        primary, secondary = ai_items, text_items

    by_key: dict[str, dict[str, Any]] = {}
    for item in primary + secondary:
        key = _job_key(item)
        if key not in by_key or _job_score(item) > _job_score(by_key[key]):
            by_key[key] = item

    result = list(by_key.values())
    result.sort(
        key=lambda x: parse_date_to_month(x.get("startDate", ""), end=False) or 0,
        reverse=True,
    )
    return clean_work_history(result)[:15]


def _job_score(item: dict) -> int:
    score = 0
    if item.get("company"):
        score += 2
    if item.get("position"):
        score += 2
    if item.get("startDate"):
        score += 3
    if item.get("endDate"):
        score += 2
    return score


def _merge_education(ai_list: Any, text_list: Any) -> list[dict[str, Any]]:
    ai_items = [i for i in (ai_list or []) if isinstance(i, dict) and i.get("school")]
    text_items = [i for i in (text_list or []) if isinstance(i, dict) and i.get("school")]
    if len(text_items) >= len(ai_items):
        return text_items or ai_items
    return ai_items or text_items


def _merge_company(ai_val: Any, text_val: Any) -> str:
    ai_raw = str(ai_val or "").strip()
    text_raw = str(text_val or "").strip()
    ai_clean = clean_company_name(ai_raw)
    text_clean = clean_company_name(text_raw)
    if text_clean and (not ai_clean or DATE_RANGE_RE.search(ai_raw)):
        return text_clean
    return ai_clean or text_clean


def merge_ai_and_text(ai: dict[str, Any], text: dict[str, Any]) -> dict[str, Any]:
    """Gộp kết quả AI + parser text — ưu tiên dữ liệu đầy đủ nhất."""
    scalar_keys = [
        "name", "email", "phone", "location", "title",
        "facebook", "linkedin", "github", "birthYear", "estimatedAge",
    ]
    result: dict[str, Any] = {}
    for key in scalar_keys:
        result[key] = _merge_scalar(ai.get(key), text.get(key))

    result["currentCompany"] = _merge_company(ai.get("currentCompany"), text.get("currentCompany"))

    phone = _normalize_phone(str(result.get("phone") or ""))
    if not phone:
        phone = _normalize_phone(str(text.get("phone") or ""))
    result["phone"] = phone

    result["skills"] = _merge_list(ai.get("skills"), text.get("skills"))
    result["keywords"] = _merge_list(ai.get("keywords"), text.get("keywords")) or result["skills"][:10]
    result["languages"] = _merge_filtered_list(text.get("languages"), ai.get("languages"), _filter_languages)
    result["certifications"] = _merge_filtered_list(
        text.get("certifications"), ai.get("certifications"), _filter_certifications
    )
    result["education"] = _merge_education(ai.get("education"), text.get("education"))
    result["workHistory"] = _merge_work_history(ai.get("workHistory"), text.get("workHistory"))

    for item in result["workHistory"]:
        if not item.get("duration"):
            item["duration"] = format_duration(item.get("startDate", ""), item.get("endDate", ""))

    if not result.get("currentCompany") and result["workHistory"]:
        result["currentCompany"] = clean_company_name(
            str(result["workHistory"][0].get("company", ""))
        )

    result["experienceYears"] = ai.get("experienceYears") or text.get("experienceYears") or ""
    result["experienceMonths"] = ai.get("experienceMonths") or text.get("experienceMonths") or ""
    result["summary"] = ""
    return result
