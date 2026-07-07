from typing import Any

from pydantic import BaseModel, Field


class WorkHistoryItem(BaseModel):
    company: str = ""
    position: str = ""
    startDate: str = ""
    endDate: str = ""
    duration: str = ""
    description: str = ""


class EducationItem(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    startYear: str = ""
    endYear: str = ""


class ParsedCandidate(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    title: str = ""
    currentCompany: str = ""
    birthYear: str = ""
    estimatedAge: str | int | None = ""
    age: int | None = None
    ageSource: str = ""
    skills: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    facebook: str = ""
    linkedin: str = ""
    github: str = ""
    summary: str = ""
    experienceYears: str | int = ""
    experienceMonths: str | int = ""
    experienceSource: str = ""
    education: list[dict[str, Any]] = Field(default_factory=list)
    workHistory: list[dict[str, Any]] = Field(default_factory=list)


class UploadResponse(BaseModel):
    parsedData: ParsedCandidate


class SaveCandidateRequest(BaseModel):
    candidateData: dict[str, Any]
    note: str = ""


class ApiResponse(BaseModel):
    success: bool
    message: str = ""
