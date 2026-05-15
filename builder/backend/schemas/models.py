"""All request/response shapes for the OpenClaw Agent Builder API.

The DeployRequest tree mirrors PRD §8.3 verbatim so the frontend and backend
share a single source of truth.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------------
# Deploy request tree
# ----------------------------------------------------------------------------
class VpsConfig(BaseModel):
    host: str
    user: str = "root"
    port: int = 22
    auth_method: Literal["key", "password"]
    ssh_private_key: str | None = None
    ssh_password: str | None = None


class IdentityConfig(BaseModel):
    agent_name: str
    agent_id: str
    emoji: str = "🦞"
    theme: str = ""
    workspace_path: str


class PersonaConfig(BaseModel):
    tone: str = "friendly"
    traits: list[str] = Field(default_factory=list)
    avoid: str = ""


class UserContextConfig(BaseModel):
    user_name: str = ""
    user_role: str = ""
    user_location: str = ""
    user_prefs: str = ""
    user_extra: str = ""


class InstructionsConfig(BaseModel):
    responsibilities: str
    memory_rules: str = ""
    group_chat: Literal["mention", "all", "silent"] = "mention"
    security_rules: bool = True


class ModelConfig(BaseModel):
    provider: str
    model: str
    heartbeat_model: str = ""


class ChannelsConfig(BaseModel):
    selected: list[str] = Field(default_factory=list)
    account_ids: dict[str, str] = Field(default_factory=dict)


class DeploySkillItem(BaseModel):
    """A skill cleared for deployment — must be approved or overridden."""

    id: str
    name: str
    raw_url: str
    security_status: Literal["approved", "overridden"]
    security_reason: str | None = None


class DeployRequest(BaseModel):
    vps: VpsConfig
    identity: IdentityConfig
    persona: PersonaConfig
    user_context: UserContextConfig
    instructions: InstructionsConfig
    model: ModelConfig
    channels: ChannelsConfig
    skills: list[DeploySkillItem] = Field(default_factory=list)


# ----------------------------------------------------------------------------
# SSH test
# ----------------------------------------------------------------------------
class SshTestRequest(BaseModel):
    host: str
    user: str = "root"
    port: int = 22
    auth_method: Literal["key", "password"]
    ssh_private_key: str | None = None
    ssh_password: str | None = None


class SshTestResponse(BaseModel):
    success: bool
    os: str | None = None
    openclaw_installed: bool | None = None
    error: str | None = None


# ----------------------------------------------------------------------------
# SkillsHub catalogue
# ----------------------------------------------------------------------------
class SkillCatalogItem(BaseModel):
    id: str
    name: str
    description: str
    author: str
    category: str = "community"
    install_count: int = 0
    raw_url: str


class SkillsListResponse(BaseModel):
    skills: list[SkillCatalogItem]
    total: int
    page: int
    page_size: int


# ----------------------------------------------------------------------------
# Skill security review
# ----------------------------------------------------------------------------
class SkillReviewItem(BaseModel):
    id: str
    name: str
    raw_url: str


class SkillReviewRequest(BaseModel):
    skills: list[SkillReviewItem]


class SkillReviewResult(BaseModel):
    id: str
    status: Literal["approved", "blocked"]
    reason: str | None = None


class SkillReviewResponse(BaseModel):
    results: list[SkillReviewResult]


# ----------------------------------------------------------------------------
# Deploy + file preview
# ----------------------------------------------------------------------------
class DeployResponse(BaseModel):
    session_id: str


class FilePreviewResponse(BaseModel):
    soul_md: str
    user_md: str
    agents_md: str
    identity_md: str


# ----------------------------------------------------------------------------
# WebSocket messages
# ----------------------------------------------------------------------------
class LogMessage(BaseModel):
    type: Literal["log"] = "log"
    level: Literal["info", "success", "warning", "error"]
    message: str


class StatusMessage(BaseModel):
    type: Literal["status"] = "status"
    status: Literal["deploying", "completed", "failed"]
    error: str | None = None
