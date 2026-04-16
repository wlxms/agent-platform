"""Common Pydantic models."""
from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    user_id: str
    org_id: str = ""
    role: str = "user"
    permissions: list[str] = Field(default_factory=list)
    request_id: str = ""


class PaginatedQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class UserInfo(BaseModel):
    id: str
    name: str
    role: str = "user"
    org_id: str = ""
    permissions: list[str] = Field(default_factory=list)
