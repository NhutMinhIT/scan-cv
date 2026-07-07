import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook


class LocalStorage:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = Path(data_dir)
        self.cv_dir = self.data_dir / "cvs"
        self.db_file = self.data_dir / "candidates.json"
        self.cv_dir.mkdir(parents=True, exist_ok=True)
        if not self.db_file.exists():
            self.db_file.write_text("[]", encoding="utf-8")

    def save_candidate(
        self,
        candidate: dict[str, Any],
        note: str,
        file_bytes: bytes | None,
        original_filename: str | None,
    ) -> dict[str, Any]:
        now = datetime.now()
        scan_date = now.strftime("%Y-%m-%d")
        name = candidate.get("name") or "Unknown"
        safe_name = re.sub(r"[^\w]+", "", name, flags=re.UNICODE)
        ext = Path(original_filename or "cv.pdf").suffix or ".pdf"
        filename = f"{now.strftime('%Y%m%d')}_{safe_name}{ext}"

        year_dir = self.cv_dir / str(now.year) / f"{now.month:02d}"
        year_dir.mkdir(parents=True, exist_ok=True)
        cv_path = year_dir / filename
        cv_url = ""

        if file_bytes:
            cv_path.write_bytes(file_bytes)
            cv_url = str(cv_path.relative_to(self.data_dir))

        experience = _format_experience(candidate)
        education = _format_education(candidate)
        record = {
            "id": f"{now.timestamp():.0f}",
            "scanDate": scan_date,
            "name": candidate.get("name", ""),
            "email": candidate.get("email", ""),
            "phone": candidate.get("phone", ""),
            "location": candidate.get("location", ""),
            "title": candidate.get("title", ""),
            "currentCompany": candidate.get("currentCompany", ""),
            "birthYear": candidate.get("birthYear", ""),
            "age": candidate.get("age"),
            "experience": experience,
            "skills": ", ".join(candidate.get("skills") or []),
            "keywords": ", ".join(candidate.get("keywords") or []),
            "languages": ", ".join(candidate.get("languages") or []),
            "certifications": ", ".join(candidate.get("certifications") or []),
            "awards": ", ".join(candidate.get("awards") or []),
            "facebook": candidate.get("facebook", ""),
            "linkedin": candidate.get("linkedin", ""),
            "github": candidate.get("github", ""),
            "education": education,
            "summary": candidate.get("summary", ""),
            "hrNote": note,
            "status": "New",
            "cvUrl": cv_url,
            # HR Insights
            "hrLevel": (candidate.get("hrInsights") or {}).get("level", ""),
            "hrStrengths": " | ".join((candidate.get("hrInsights") or {}).get("strengths") or []),
            "hrConcerns": " | ".join((candidate.get("hrInsights") or {}).get("concerns") or []),
            "hrInterviewFocus": " | ".join((candidate.get("hrInsights") or {}).get("interviewFocus") or []),
            "hrDomain": (candidate.get("hrInsights") or {}).get("domainExpertise", ""),
            "hrTrajectory": (candidate.get("hrInsights") or {}).get("careerTrajectory", ""),
            "hrSalary": (candidate.get("hrInsights") or {}).get("salaryExpectation", ""),
            "hrNotice": (candidate.get("hrInsights") or {}).get("noticePeriod", ""),
            # Interview tracking
            "interviewRound": candidate.get("interviewRound", ""),
            "interviewDate": candidate.get("interviewDate", ""),
            "interviewResult": candidate.get("interviewResult", ""),
            "rating": candidate.get("rating", ""),
        }

        records = self._load_records()
        records.append(record)
        self.db_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def export_excel(self, output_path: Path) -> Path:
        records = self._load_records()
        if not records:
            raise ValueError("Chưa có ứng viên nào. Hãy bấm 'Lưu ứng viên' trước khi xuất Excel.")
        wb = Workbook()
        ws = wb.active
        ws.title = "Candidates"
        headers = [
            "Scan Date", "Name", "Email", "Phone", "Location", "Title",
            "Current Company", "Birth Year", "Age", "Experience", "Facebook", "LinkedIn", "GitHub",
            "Skills", "Keywords", "Languages", "Certifications", "Awards", "Education", "Summary",
            "HR Level", "HR Domain", "HR Trajectory", "Strengths", "Concerns", "Interview Focus",
            "Salary Expectation", "Notice Period",
            "Interview Round", "Interview Date", "Interview Result", "Rating",
            "HR Note", "Status", "CV URL",
        ]
        ws.append(headers)
        for row in records:
            ws.append([
                row.get("scanDate"), row.get("name"), row.get("email"), row.get("phone"),
                row.get("location"), row.get("title"), row.get("currentCompany"),
                row.get("birthYear"), row.get("age"), row.get("experience"),
                row.get("facebook"), row.get("linkedin"), row.get("github"),
                row.get("skills"), row.get("keywords"), row.get("languages"),
                row.get("certifications"), row.get("awards"), row.get("education"), row.get("summary"),
                row.get("hrLevel"), row.get("hrDomain"), row.get("hrTrajectory"),
                row.get("hrStrengths"), row.get("hrConcerns"), row.get("hrInterviewFocus"),
                row.get("hrSalary"), row.get("hrNotice"),
                row.get("interviewRound"), row.get("interviewDate"), row.get("interviewResult"), row.get("rating"),
                row.get("hrNote"), row.get("status"), row.get("cvUrl"),
            ])
        wb.save(output_path)
        return output_path

    def _load_records(self) -> list[dict[str, Any]]:
        return json.loads(self.db_file.read_text(encoding="utf-8"))


def _format_education(candidate: dict[str, Any]) -> str:
    items = candidate.get("education") or []
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        school = item.get("school", "")
        degree = item.get("degree", "")
        years = ""
        if item.get("startYear") or item.get("endYear"):
            years = f" ({item.get('startYear', '')}-{item.get('endYear', '')})"
        label = " - ".join(p for p in [degree, school] if p)
        if label:
            parts.append(f"{label}{years}")
    return "; ".join(parts)


def _format_experience(candidate: dict[str, Any]) -> str:
    years = candidate.get("experienceYears")
    months = candidate.get("experienceMonths")
    if years or months:
        parts = []
        if years:
            parts.append(f"{years} năm")
        if months:
            parts.append(f"{months} tháng")
        return " ".join(parts)
    return ""


def get_storage() -> LocalStorage:
    data_dir = os.getenv("DATA_DIR", "./data")
    return LocalStorage(data_dir)
