"""Pydantic schemas for auth requests/responses."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    api_key: str = Field(
        min_length=1,
        max_length=256,
        pattern=r'^[a-zA-Z0-9\-_.]+$',
        description="API key (alphanumeric, hyphens, underscores, dots only)"
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(
        min_length=1,
        max_length=4096,
        description="JWT refresh token"
    )


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    expires_at: str
    user: dict
