"""Pydantic schemas for auth requests/responses."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=256, description="API key for authentication")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=4096, description="JWT refresh token")


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    expires_at: str
    user: dict


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    parent_id: str | None = None
    plan: str = Field(default="free", pattern=r"^(free|basic|pro|enterprise)$")


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    permissions: list[str] | None = None
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "member"


class UpdateMemberRoleRequest(BaseModel):
    role: str


class RenewApiKeyRequest(BaseModel):
    expires_in_days: int = Field(default=30, ge=1)
