import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.models.schemas import ApiResponse, SaveCandidateRequest
from app.services.storage import get_storage

router = APIRouter(prefix="/api/candidate", tags=["candidate"])


@router.post("/save", response_model=ApiResponse)
async def save_candidate(
    candidateData: str = Form(...),
    note: str = Form(""),
    file: UploadFile | None = File(None),
) -> ApiResponse:
    try:
        data = json.loads(candidateData)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="candidateData không hợp lệ") from exc

    file_bytes: bytes | None = None
    filename: str | None = None
    if file and file.filename:
        file_bytes = await file.read()
        filename = file.filename

    storage = get_storage()
    storage.save_candidate(data, note, file_bytes, filename)
    return ApiResponse(success=True, message="Đã lưu thành công")


@router.post("/save-json", response_model=ApiResponse)
async def save_candidate_json(body: SaveCandidateRequest) -> ApiResponse:
    storage = get_storage()
    storage.save_candidate(body.candidateData, body.note, None, None)
    return ApiResponse(success=True, message="Đã lưu thành công")


@router.get("/export")
def export_candidates() -> FileResponse:
    storage = get_storage()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        output = Path(tmp.name)

    try:
        storage.export_excel(output)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(
        path=output,
        filename="candidate.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
