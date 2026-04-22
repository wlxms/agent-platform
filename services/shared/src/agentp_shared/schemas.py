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


class AgentConfigCreate(BaseModel):
    name: str
    model: dict = Field(default_factory=dict)
    prompt_template: dict = Field(default_factory=dict)
    tools: list = Field(default_factory=list)
    skills: list = Field(default_factory=list)
    mcp_servers: list = Field(default_factory=list)
    visibility: str = "private"
    tags: list[str] = Field(default_factory=list)


class AgentConfigResponse(BaseModel):
    id: str
    name: str
    author_id: str
    org_id: str
    version: str = "1.0.0"
    visibility: str = "private"
    status: str = "draft"
    model: dict = Field(default_factory=dict)
    personality: dict = Field(default_factory=dict)
    tags: list = Field(default_factory=list)
    created_at: str | None = None


class AgentConfigUpdate(BaseModel):
    name: str | None = None
    model: dict | None = None
    prompt_template: dict | None = None
    tools: list | None = None
    skills: list | None = None
    visibility: str | None = None
    tags: list[str] | None = None


class ApprovalCreate(BaseModel):
    applicant_id: str
    template_name: str = ""
    config_snapshot: dict = Field(default_factory=dict)


class ApprovalResponse(BaseModel):
    id: str
    org_id: str
    applicant_id: str
    status: str
    template_name: str = ""
    reviewer_id: str | None = None
    review_comment: str = ""
    created_at: str | None = None


class ApprovalReview(BaseModel):
    status: str  # "approved" | "rejected"
    comment: str = ""


class BudgetCreate(BaseModel):
    org_id: str
    threshold: float
    alert_rules: dict = Field(default_factory=dict)


class BudgetResponse(BaseModel):
    id: str
    org_id: str
    threshold: float
    alert_rules: dict = Field(default_factory=dict)
    created_at: str | None = None


class BudgetUpdate(BaseModel):
    threshold: float | None = None
    alert_rules: dict | None = None


class TemplateCreate(BaseModel):
    name: str
    category: str = "general"
    visibility: str = "private"
    config_snapshot: dict
    tags: list[str] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    id: str
    name: str
    category: str
    visibility: str
    author_id: str
    version: str = "1.0.0"
    usage_count: int = 0
    created_at: str | None = None


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    package_url: str = ""
    category: str = ""


class McpServerResponse(BaseModel):
    id: str
    name: str
    transport: str = "stdio"
    description: str = ""
    config_template: dict = Field(default_factory=dict)
    category: str = ""


class CategoryResponse(BaseModel):
    id: str
    name: str
    icon: str = ""
    display_order: int = 0
