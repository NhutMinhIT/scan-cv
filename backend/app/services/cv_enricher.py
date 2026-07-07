from typing import Any

from app.services.career_summary import build_work_summary
from app.services.experience_calculator import _extract_phone, _normalize_phone
from app.services.work_history_cleaner import clean_company_name, clean_work_history


def enrich_parsed_cv(parsed: dict[str, Any], raw_text: str) -> dict[str, Any]:
    """
    AI-first: dữ liệu field lấy từ AI, chỉ post-process nhẹ (SĐT, làm sạch work history).
  Không ghi đè bằng text parser.
    """
    result = dict(parsed or {})

    phone = _normalize_phone(str(result.get("phone") or ""))
    if not phone:
        phone = _extract_phone(raw_text)
    result["phone"] = phone

    history = clean_work_history(result.get("workHistory") or [])
    result["workHistory"] = history

    current = clean_company_name(str(result.get("currentCompany") or ""))
    if not current and history:
        current = clean_company_name(history[0].get("company", ""))
    result["currentCompany"] = current

    if not str(result.get("summary") or "").strip() and history:
        result["summary"] = build_work_summary(history)

    result["age"] = None
    result["experienceSource"] = "ai"
    return result
