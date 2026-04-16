"""In-memory Market data store (skeleton stage)."""
from __future__ import annotations

from typing import Any


class MarketService:
    def __init__(self) -> None:
        self._templates: list[dict[str, Any]] = []
        self._skills: list[dict[str, Any]] = []
        self._mcps: list[dict[str, Any]] = []
        self._seed()

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    def list_templates(
        self,
        category: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        items = list(self._templates)
        if category:
            items = [t for t in items if t["category"] == category]
        if keyword:
            kw = keyword.lower()
            items = [
                t for t in items
                if kw in t["name"].lower() or kw in t["description"].lower()
            ]
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paged = items[start:end]
        return list_response(paged, total, page, page_size)

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        for tpl in self._templates:
            if tpl["id"] == template_id:
                return dict(tpl)
        return None

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def list_skills(
        self,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        items = list(self._skills)
        if keyword:
            kw = keyword.lower()
            items = [
                s for s in items
                if kw in s["name"].lower() or kw in s["description"].lower()
            ]
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paged = items[start:end]
        return list_response(paged, total, page, page_size)

    # ------------------------------------------------------------------
    # MCP servers
    # ------------------------------------------------------------------

    def list_mcps(
        self,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        items = list(self._mcps)
        if keyword:
            kw = keyword.lower()
            items = [
                m for m in items
                if kw in m["name"].lower() or kw in m["description"].lower()
            ]
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paged = items[start:end]
        return list_response(paged, total, page, page_size)

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        self._templates = [
            {
                "id": "tpl-001",
                "name": "Code Assistant",
                "description": "A general-purpose coding assistant template",
                "category": "coding",
                "scenario": "Software development with code generation and review",
                "skills": ["skill-001"],
                "mcp": ["mcp-001"],
                "resource_spec": {"cpu": "2", "memory": "4Gi"},
                "usage_count": 120,
            },
            {
                "id": "tpl-002",
                "name": "Research Agent",
                "description": "Deep research and analysis template for information gathering",
                "category": "research",
                "scenario": "Academic and market research tasks",
                "skills": ["skill-001", "skill-002"],
                "mcp": [],
                "resource_spec": {"cpu": "1", "memory": "2Gi"},
                "usage_count": 85,
            },
            {
                "id": "tpl-003",
                "name": "General Helper",
                "description": "A versatile general-purpose agent template",
                "category": "general",
                "scenario": "Everyday tasks and Q&A",
                "skills": [],
                "mcp": [],
                "resource_spec": {"cpu": "1", "memory": "1Gi"},
                "usage_count": 42,
            },
        ]
        self._skills = [
            {
                "id": "skill-001",
                "name": "Web Search",
                "description": "Search the web for up-to-date information",
                "author": "open",
                "version": "1.0.0",
            },
            {
                "id": "skill-002",
                "name": "Code Review",
                "description": "Review code for quality, bugs, and best practices",
                "author": "open",
                "version": "1.0.0",
            },
        ]
        self._mcps = [
            {
                "id": "mcp-001",
                "name": "filesystem",
                "transport": "stdio",
                "description": "Local filesystem access for reading and writing files",
            },
        ]


def list_response(items: list, total: int, page: int, page_size: int) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
