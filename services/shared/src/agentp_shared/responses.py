"""Unified response wrappers."""
from __future__ import annotations
from typing import Any


def ok_response(task_id: str | None = None) -> dict:
    result: dict[str, Any] = {"ok": True}
    if task_id:
        result["task_id"] = task_id
    return result


def data_response(data: Any) -> dict:
    return {"data": data}


def list_response(items: list, total: int, page: int = 1, page_size: int = 20) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
