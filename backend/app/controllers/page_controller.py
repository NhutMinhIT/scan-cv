from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import VIEWS_DIR

router = APIRouter(tags=["pages"])


@router.get("/")
def index() -> FileResponse:
    return FileResponse(Path(VIEWS_DIR) / "index.html")
