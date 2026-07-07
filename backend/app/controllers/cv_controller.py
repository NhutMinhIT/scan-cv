from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import ParsedCandidate, UploadResponse
from app.services.ai_parser import AIParseError, parse_cv_with_ai
from app.services.cv_enricher import enrich_parsed_cv
from app.services.cv_extractor import extract_text_from_cv

router = APIRouter(prefix="/api/cv", tags=["cv"])


@router.post("/upload", response_model=UploadResponse)
async def upload_cv(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Thiếu tên file")

    ext = file.filename.lower()
    if not (ext.endswith(".pdf") or ext.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ PDF hoặc DOCX")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng")

    try:
        raw_text = extract_text_from_cv(content, file.filename)
        parsed = parse_cv_with_ai(raw_text)
        enriched = enrich_parsed_cv(parsed, raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIParseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích CV: {exc}") from exc

    return UploadResponse(parsedData=ParsedCandidate(**enriched))
