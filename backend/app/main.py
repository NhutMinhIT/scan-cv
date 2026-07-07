from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import candidate_router, cv_router, page_router

app = FastAPI(title="CV Scanner HR", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(page_router)
app.include_router(cv_router)
app.include_router(candidate_router)
