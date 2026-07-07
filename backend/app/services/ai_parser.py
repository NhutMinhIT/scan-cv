import json
import os
from typing import Any

from openai import APIConnectionError, APITimeoutError, AuthenticationError, OpenAI

from app.services.ai_normalizer import normalize_ai_response

CV_SCHEMA_PROMPT = """Bạn là chuyên gia phân tích CV tuyển dụng.

Nhiệm vụ:
Đọc toàn bộ nội dung CV và trích xuất ĐẦY ĐỦ thông tin vào JSON schema bên dưới.
Bạn là nguồn duy nhất — mọi field phải được điền từ CV (hoặc null/mảng rỗng nếu không có).

QUY TẮC CHUNG:
1. Chỉ trả về JSON hợp lệ. Không giải thích. Không markdown.
2. Không bịa thông tin. Không có trong CV thì null hoặc [].
3. Đọc TẤT CẢ section: Experience, Project Experience, Education, Skills, Languages, Certifications, Awards.
4. Chuẩn hóa SĐT VN: 10 số bắt đầu 0. 9 số thiếu số 0 đầu (3/5/7/8/9) → thêm 0. 9 số đã có 0 đầu → phone = "".

QUY TẮC WORK HISTORY:
- Lấy TẤT CẢ công việc và dự án (kể cả intern), sắp xếp mới nhất trước.
- Gom nhận biết dự án cùng công ty (project field).
- company: chỉ tên công ty, không gộp ngày tháng.
- description: phạm vi công việc / dự án đã làm.
- achievement: thành tựu nếu CV có ghi.
- KHÔNG lấy bullet mô tả làm tên công ty.

QUY TẮC SUMMARY (field summary):
- Hãy viết summary như một nhà tuyển dụng nhiều năm kinh nghiệm đang đọc CV và cần nắm nhanh toàn bộ quá trình làm việc.
- Gom theo CÔNG TY — nhiều dự án/vị trí cùng công ty → 1 dòng.
- Với mỗi công ty, phải làm rõ:
  1. Tổng thời gian làm tại công ty đó (cộng tất cả giai đoạn làm việc tại cùng công ty).
  2. Vị trí/chức danh đã đảm nhiệm.
  3. Đã làm gì: dự án, phạm vi công việc, trách nhiệm chính.
  4. Liên quan tới gì: domain, sản phẩm, công nghệ, nghiệp vụ.
- Format mỗi dòng:
  Company (mm/yyyy - mm/yyyy, tổng X năm Y tháng) - Vị trí - Công việc/dự án - Liên quan: domain/công nghệ
- Nếu cùng công ty nhưng nhiều dự án hoặc nhiều giai đoạn, vẫn gộp chung 1 dòng và nêu rõ các dự án chính.
- Nếu CV scan/OCR lỗi ngắt dòng, ký tự dính nhau hoặc thiếu dấu, hãy suy luận theo ngữ cảnh để giữ đúng công ty, project, position và thời gian.
- Không giới hạn ký tự. Đây là field quan trọng nhất mô tả career path.

QUY TẮC KINH NGHIỆM (experience):
- total_years + total_months = tổng thời gian làm việc thực tế.
- Gap giữa các công ty KHÔNG tính. Overlap (làm song song) không cộng đôi.

QUY TẮC NĂM SINH:
- Có ngày/năm sinh → birth_year, age_source = "birth_date"
- Không có → suy từ năm vào ĐH/CĐ đầu tiên (vào học 18 tuổi), age_source = "estimated_from_education"
- Không suy được → birth_year = null, age_source = null
- age luôn null

QUY TẮC KHÁC:
- skills: kỹ năng chuyên môn.
- keywords: từ khóa ngắn để HR tìm kiếm.
- languages: chỉ ngôn ngữ (không ghi award/contest).
- certifications: chỉ chứng chỉ chuyên môn (không ghi giải thưởng/học bổng).
- awards: tất cả giải thưởng, danh hiệu, học bổng, thành tích thi đấu, giải cuộc thi lập trình, hackathon, giải học tập. Mỗi giải là 1 string ngắn gọn (tên giải + năm nếu có).
- current_company: công ty đang làm (job mới nhất hoặc đang Present).

QUY TẮC HR INSIGHTS (field hr_insights):
Bạn đóng vai HR senior có 10+ năm kinh nghiệm. Phân tích CV để giúp người dùng ra quyết định nhanh:
- level: đánh giá "junior" (<2năm), "mid" (2-4năm), "senior" (4-8năm), "lead" (>8năm hoặc quản lý team), "principal" (architect/director) dựa vào KN thực tế + chuyên môn + scope.
- strengths: 3-4 điểm mạnh NỔI BẬT, CỤ THỂ từ CV (không chung chung). VD: "Đã làm tổng 4 công ty trong 3 năm, tất cả đều là enterprise product", "Có kinh nghiệm cả frontend lẫn product ownership".
- concerns: CHỈ ghi nếu có thật. VD: gap việc >6 tháng, tenure <6 tháng, career lùi vị trí, không rõ output. Nếu không có gì bất thường → mảng rỗng [].
- interview_focus: 3-5 câu hỏi/vùng cần khai thác sâu khi PV. Phải cụ thể và actionable, không chung chung.
- domain_expertise: Domain chính ('Logistics E-commerce', 'HR Tech', 'Fintech', 'Enterprise SaaS'...).
- career_trajectory: 'growing' (thăng tiến rõ), 'stable' (ổn định cùng level), 'mixed' (lên xuống), 'declining' (có dấu hiệu lùi).
- salary_expectation: Lương kỳ vọng nếu CV có ghi, không có → "".
- notice_period: Thời gian báo trước nếu CV có ghi, không có → "".

TRẢ VỀ JSON:
{
  "full_name": "",
  "email": "",
  "phone": "",
  "title": "",
  "address": "",
  "linkedin": "",
  "github": "",
  "facebook": "",
  "current_company": "",
  "birth_year": null,
  "age": null,
  "age_source": null,
  "skills": [],
  "keywords": [],
  "languages": [],
  "certifications": [],
  "awards": [],
  "summary": "",
  "experience": {
    "total_years": 0,
    "total_months": 0
  },
  "education": [
    {
      "school": "",
      "degree": "",
      "major": "",
      "start_year": null,
      "end_year": null
    }
  ],
  "work_history": [
    {
      "company": "",
      "project": "",
      "position": "",
      "start_date": "",
      "end_date": "",
      "duration_months": 0,
      "description": "",
      "achievement": ""
    }
  ],
  "hr_insights": {
    "level": "",
    "strengths": [],
    "concerns": [],
    "interview_focus": [],
    "domain_expertise": "",
    "career_trajectory": "",
    "salary_expectation": "",
    "notice_period": ""
  }
}
"""

PLACEHOLDER_KEYS = {
    "sk-your-openai-api-key-here",
    "xai-your-grok-api-key-here",
    "gsk-your-groq-api-key-here",
}


class AIParseError(Exception):
    """Lỗi khi AI không phân tích được CV."""


def parse_cv_with_ai(raw_text: str) -> dict[str, Any]:
    config = _get_llm_config()
    if not config:
        raise AIParseError(
            "Chưa cấu hình API key AI. Thêm OPENAI_API_KEY vào file .env"
        )

    try:
        raw = _parse_with_llm(raw_text, config)
        normalized = normalize_ai_response(raw)
        if not normalized.get("name") and not normalized.get("email") and not normalized.get("workHistory"):
            raise AIParseError("AI trả về dữ liệu rỗng — kiểm tra API key hoặc thử lại")
        return normalized
    except (AuthenticationError, APIConnectionError, APITimeoutError) as exc:
        raise AIParseError(
            "Không kết nối được tới AI provider. Kiểm tra API key, mạng, base URL, và model đang dùng."
        ) from exc
    except AIParseError:
        raise
    except Exception as exc:
        raise AIParseError(f"AI không phân tích được CV: {exc}") from exc


def _get_llm_config() -> dict[str, str] | None:
    provider = os.getenv("AI_PROVIDER", "openai").strip().lower()

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if api_key and api_key not in PLACEHOLDER_KEYS:
            return {
                "api_key": api_key,
                "base_url": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip() or None,
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            }
        return None

    if provider == "grok":
        api_key = os.getenv("GROK_API_KEY", "").strip()
        if api_key and api_key not in PLACEHOLDER_KEYS:
            return {
                "api_key": api_key,
                "base_url": os.getenv("GROK_BASE_URL", "https://api.x.ai/v1").strip() or None,
                "model": os.getenv("GROK_MODEL", "grok-2-latest"),
            }
        return None

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key and api_key not in PLACEHOLDER_KEYS:
        return {
            "api_key": api_key,
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip() or None,
            "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        }
    return None


def _parse_with_llm(raw_text: str, config: dict[str, str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"api_key": config["api_key"]}
    if config.get("base_url"):
        kwargs["base_url"] = config["base_url"]

    client = OpenAI(**kwargs)
    messages = [
        {"role": "system", "content": CV_SCHEMA_PROMPT},
        {"role": "user", "content": f"NỘI DUNG CV:\n\n{raw_text[:20000]}"},
    ]
    try:
        response = client.chat.completions.create(
            model=config["model"],
            temperature=0.1,
            messages=messages,
            response_format={"type": "json_object"},
        )
    except TypeError:
        response = client.chat.completions.create(
            model=config["model"],
            temperature=0.1,
            messages=messages,
        )

    content = response.choices[0].message.content or "{}"
    return json.loads(content)
