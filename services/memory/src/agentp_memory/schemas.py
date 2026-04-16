"""Pydantic schemas for Memory service."""
from pydantic import BaseModel


class CreateAssetRequest(BaseModel):
    path: str
    content: str = ""
    content_type: str = "text/plain"
