"""Pydantic schemas for auth requests/responses."""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    api_key: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    expires_at: str
    user: dict
