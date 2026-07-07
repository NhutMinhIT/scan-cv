import re
from collections import defaultdict
from datetime import datetime
from typing import Any


def normalize_ai_response(data: dict[str, Any]) -> dict[str, Any]:
    """Chuyển JSON snake_case từ AI sang schema nội bộ camelCase."""
    if not data:
        return {}

    exp = data.get("experience") or {}
    if isinstance(exp, dict):
        exp_years = exp.get("total_years", 0)
        exp_months = exp.get("total_months", 0)
    else:
        exp_years = data.get("experienceYears") or data.get("experience_years") or 0
        exp_months = data.get("experienceMonths") or data.get("experience_months") or 0

    work_raw = data.get("work_history") or data.get("workHistory") or []
    education_raw = data.get("education") or []

    birth_year = _str_or_empty(data.get("birth_year") or data.get("birthYear"))
    age_source = data.get("age_source") or data.get("ageSource") or ""

    if not birth_year:
        estimated = _estimate_birth_year(education_raw)
        if estimated:
            birth_year = estimated
            age_source = "estimated_from_education"

    age_source_map = {
        "birth_date": "birthYear",
        "birthYear": "birthYear",
        "estimated_from_education": "estimated",
        "estimated": "estimated",
        "stated": "stated",
    }

    return {
        "name": _str(data.get("full_name") or data.get("name")),
        "email": _str(data.get("email")),
        "phone": _str(data.get("phone")),
        "location": _str(data.get("address") or data.get("location")),
        "title": _str(data.get("title")),
        "currentCompany": _str(
            data.get("current_company") or data.get("currentCompany")
        ) or _company_from_work(work_raw),
        "birthYear": birth_year,
        "estimatedAge": "",
        "age": data.get("age"),
        "ageSource": age_source_map.get(str(age_source), str(age_source) if age_source else ""),
        "skills": _list(data.get("skills")),
        "keywords": _list(data.get("keywords")),
        "languages": _list(data.get("languages")),
        "certifications": _list(data.get("certifications")),
        "awards": _list(data.get("awards")),
        "facebook": _str(data.get("facebook")),
        "linkedin": _str(data.get("linkedin")),
        "github": _str(data.get("github")),
        "summary": _str(data.get("summary")),
        "experienceYears": exp_years or 0,
        "experienceMonths": exp_months or 0,
        "education": [_normalize_education(e) for e in education_raw if isinstance(e, dict)],
        "workHistory": _build_work_history(work_raw),
        "hrInsights": _normalize_hr_insights(data.get("hr_insights") or data.get("hrInsights")),
    }


def _normalize_education(item: dict[str, Any]) -> dict[str, str]:
    return {
        "school": _str(item.get("school")),
        "degree": _str(item.get("degree")),
        "major": _str(item.get("major")),
        "startYear": _str_or_empty(item.get("start_year") or item.get("startYear")),
        "endYear": _str_or_empty(item.get("end_year") or item.get("endYear")),
        "startDate": _str(item.get("start_date") or item.get("startDate")),
        "endDate": _str(item.get("end_date") or item.get("endDate")),
    }


def _normalize_work(item: dict[str, Any]) -> dict[str, str]:
    months = item.get("duration_months")
    duration = ""
    if months:
        y, m = divmod(int(months), 12)
        parts = []
        if y:
            parts.append(f"{y} năm")
        if m:
            parts.append(f"{m} tháng")
        duration = " ".join(parts)

    return {
        "company": _str(item.get("company")),
        "position": _str(item.get("position")),
        "startDate": _str(item.get("start_date") or item.get("startDate")),
        "endDate": _str(item.get("end_date") or item.get("endDate")),
        "duration": duration or _str(item.get("duration")),
        "description": _str(item.get("description")),
        "achievement": _str(item.get("achievement")),
        "project": _str(item.get("project")),
    }


def _company_from_work(work: list) -> str:
    if not work or not isinstance(work[0], dict):
        return ""
    return _str(work[0].get("company"))


def _str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _str_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


# ─── Date parsing & duration helpers ──────────────────────────────────────────
_MON = {
    'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
    'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12,
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
    # Vietnamese
    'tháng 1':1,'tháng 2':2,'tháng 3':3,'tháng 4':4,'tháng 5':5,'tháng 6':6,
    'tháng 7':7,'tháng 8':8,'tháng 9':9,'tháng 10':10,'tháng 11':11,'tháng 12':12,
}


def _parse_ym(s: str) -> tuple[int, int] | None:
    """Parse 'Feb 2025', '2025-02', '01/2025', 'Present', '2025' → (year, month) or None."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    low = s.lower()
    # Various "present" keywords
    _PRESENT = {
        'present','now','current','ongoing','till date','to date','today',
        'hiện tại','nay','hôm nay','hiện nay','hiện',
    }
    if low in _PRESENT or low.startswith('present') or low.startswith('current'):
        n = datetime.now()
        return (n.year, n.month)
    # Remove extra chars: commas, dots after month abbreviation, trailing text
    s_clean = re.sub(r'[,.]', ' ', s).strip()
    # "Feb 2025" or "February 2025" (allow optional dot/comma)
    m = re.match(r'([a-zA-Z]+)\s+(\d{4})', s_clean)
    if m:
        mon = _MON.get(m.group(1).lower()) or _MON.get(m.group(1).lower()[:3])
        if mon:
            return (int(m.group(2)), mon)
    # "MM/YYYY" or "MM-YYYY" or "MM.YYYY"
    m = re.match(r'(\d{1,2})[/\-.](\d{4})', s)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            return (int(m.group(2)), month)
    # "YYYY/MM" or "YYYY-MM" or "YYYY.MM"
    m = re.match(r'(\d{4})[/\-.](\d{1,2})', s)
    if m:
        month = int(m.group(2))
        if 1 <= month <= 12:
            return (int(m.group(1)), month)
    # Just year like "2025"
    m = re.match(r'^(\d{4})$', s.strip())
    if m:
        return (int(m.group(1)), 6)  # assume mid-year
    return None


def _estimate_birth_year(education_raw: list) -> str | None:
    earliest_start = None
    earliest_end = None
    
    for item in education_raw:
        if not isinstance(item, dict):
            continue
            
        sy = item.get("start_year") or item.get("startYear")
        if sy:
            try:
                val = int(str(sy).strip())
                if earliest_start is None or val < earliest_start:
                    earliest_start = val
            except ValueError:
                pass
                
        if not sy:
            sd = item.get("start_date") or item.get("startDate")
            if sd:
                ym = _parse_ym(str(sd))
                if ym:
                    val = ym[0]
                    if earliest_start is None or val < earliest_start:
                        earliest_start = val
                        
        ey = item.get("end_year") or item.get("endYear")
        if ey:
            try:
                val = int(str(ey).strip())
                if earliest_end is None or val < earliest_end:
                    earliest_end = val
            except ValueError:
                pass
                
        if not ey:
            ed = item.get("end_date") or item.get("endDate")
            if ed:
                ym = _parse_ym(str(ed))
                if ym:
                    val = ym[0]
                    if earliest_end is None or val < earliest_end:
                        earliest_end = val

    if earliest_start:
        return str(earliest_start - 18)
    if earliest_end:
        return str(earliest_end - 22)
    return None


def _ym_to_idx(year: int, month: int) -> int:
    return year * 12 + month


def _idx_to_label(months: int) -> str:
    y, m = divmod(months, 12)
    parts = []
    if y:
        parts.append(f"{y} năm")
    if m:
        parts.append(f"{m} tháng")
    return " ".join(parts) if parts else "< 1 tháng"


def _company_key(name: str) -> str:
    """Normalize company name for grouping (case-insensitive, strip spaces)."""
    return re.sub(r'\s+', ' ', name.strip().lower())


def _compute_company_durations(work_raw: list) -> dict[str, int]:
    """
    Group work entries by company, merge overlapping date intervals,
    return {company_key: total_non_overlapping_months}.
    """
    intervals: dict[str, list] = defaultdict(list)
    now = datetime.now()

    for w in work_raw:
        if not isinstance(w, dict):
            continue
        company = _str(w.get('company'))
        if not company:
            continue
        start_str = _str(w.get('start_date') or w.get('startDate'))
        end_str   = _str(w.get('end_date')   or w.get('endDate'))
        s = _parse_ym(start_str)
        e = _parse_ym(end_str) if end_str else (now.year, now.month)
        if not e:
            e = (now.year, now.month)
        if s:
            si, ei = _ym_to_idx(*s), _ym_to_idx(*e)
            if ei >= si:
                intervals[_company_key(company)].append((si, ei))

    result: dict[str, int] = {}
    for key, ivs in intervals.items():
        ivs.sort()
        merged: list[list[int]] = []
        for s, e in ivs:
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        result[key] = sum(e - s + 1 for s, e in merged)  # +1: inclusive (both start and end month counted)
    return result


def _build_work_history(work_raw: list) -> list:
    """Build normalized workHistory with companyTotalDuration added per entry."""
    durations = _compute_company_durations(work_raw)
    result = []
    for w in work_raw:
        if not isinstance(w, dict):
            continue
        item = _normalize_work(w)
        key = _company_key(item.get('company', ''))
        computed = durations.get(key, 0)

        # Also get AI's reported duration_months as cross-check
        ai_months = 0
        try:
            ai_months = int(w.get('duration_months') or 0)
        except (ValueError, TypeError):
            ai_months = 0

        # Use max of computed vs AI-reported (AI may have correct value if date parsing fails)
        total = max(computed, ai_months)
        item['companyTotalDuration'] = _idx_to_label(total) if total > 0 else item.get('duration', '')
        result.append(item)
    return result


def _normalize_hr_insights(data: Any) -> dict:
    if not data or not isinstance(data, dict):
        return {
            "level": "",
            "strengths": [],
            "concerns": [],
            "interviewFocus": [],
            "domainExpertise": "",
            "careerTrajectory": "",
            "salaryExpectation": "",
            "noticePeriod": "",
        }
    return {
        "level": _str(data.get("level")),
        "strengths": _list(data.get("strengths")),
        "concerns": _list(data.get("concerns")),
        "interviewFocus": _list(data.get("interview_focus") or data.get("interviewFocus")),
        "domainExpertise": _str(data.get("domain_expertise") or data.get("domainExpertise")),
        "careerTrajectory": _str(data.get("career_trajectory") or data.get("careerTrajectory")),
        "salaryExpectation": _str(data.get("salary_expectation") or data.get("salaryExpectation")),
        "noticePeriod": _str(data.get("notice_period") or data.get("noticePeriod")),
    }

