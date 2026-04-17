"""Pydantic schemas for Memory service."""
from pydantic import BaseModel, Field


class CreateAssetRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=1000)
    content: str = Field(default="", max_length=10_000_000)
    content_type: str = Field(default="text/plain", max_length=100)


class ListAssetsQuery(BaseModel):
    path: str | None = Field(default=None, max_length=1000)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
