"""Skill catalogue + security review endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from schemas.models import (
    SkillReviewRequest,
    SkillReviewResponse,
    SkillReviewResult,
    SkillsListResponse,
)
from services.security_gateway import review_skills_batch
from services.skillshub import fetch_skills

router = APIRouter()


@router.get("/skills", response_model=SkillsListResponse)
async def list_skills(
    search: str = Query("", description="Substring filter on name/description/author"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SkillsListResponse:
    skills = await fetch_skills(search)
    total = len(skills)
    start = (page - 1) * page_size
    end = start + page_size
    return SkillsListResponse(
        skills=skills[start:end],  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/skills/review", response_model=SkillReviewResponse)
async def review_skills(req: SkillReviewRequest) -> SkillReviewResponse:
    payload = [s.model_dump() for s in req.skills]
    results = await review_skills_batch(payload)
    return SkillReviewResponse(
        results=[SkillReviewResult(**r) for r in results]
    )
