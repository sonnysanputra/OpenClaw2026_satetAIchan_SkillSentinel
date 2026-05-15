"""POST /api/files/preview — stateless render of workspace files for step 9."""
from __future__ import annotations

from fastapi import APIRouter

from schemas.models import DeployRequest, FilePreviewResponse
from services.file_generator import (
    generate_agents_md,
    generate_identity_md,
    generate_soul_md,
    generate_user_md,
)

router = APIRouter()


@router.post("/files/preview", response_model=FilePreviewResponse)
async def preview_files(req: DeployRequest) -> FilePreviewResponse:
    return FilePreviewResponse(
        soul_md=generate_soul_md(req.identity, req.persona),
        user_md=generate_user_md(req.user_context),
        agents_md=generate_agents_md(req.instructions),
        identity_md=generate_identity_md(req.identity),
    )
