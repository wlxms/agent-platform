"""In-memory KV storage for Memory service (skeleton stage)."""
from __future__ import annotations

import time
from typing import Any


class MemoryService:
    def __init__(self) -> None:
        self._assets: dict[str, dict[str, Any]] = {}
        self._seed()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_asset(self, path: str, content: str, content_type: str = "text/plain") -> dict:
        now = time.time()
        if path in self._assets:
            # Update existing asset
            asset = self._assets[path]
            asset["content"] = content
            asset["content_type"] = content_type
            asset["updated_at"] = now
        else:
            asset = {
                "path": path,
                "content": content,
                "content_type": content_type,
                "created_at": now,
                "updated_at": now,
            }
            self._assets[path] = asset
        return {
            "path": asset["path"],
            "content_type": asset["content_type"],
            "created_at": asset["created_at"],
            "updated_at": asset["updated_at"],
        }

    def get_asset(self, path: str) -> dict | None:
        asset = self._assets.get(path)
        if asset is None:
            return None
        return dict(asset)

    def list_assets(self, path_prefix: str | None = None) -> list[dict]:
        result: list[dict] = []
        for path, asset in self._assets.items():
            if path_prefix and not path.startswith(path_prefix):
                continue
            name = path.rsplit("/", 1)[-1] if "/" in path else path
            result.append({
                "path": path,
                "name": name,
                "type": "file",
                "size": len(asset["content"]),
                "updated_at": asset["updated_at"],
            })
        return result

    def delete_asset(self, path: str) -> bool:
        if path in self._assets:
            del self._assets[path]
            return True
        return False

    # ------------------------------------------------------------------
    # Seed sample data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        self.create_asset("system/prompt.txt", "You are a helpful assistant.", "text/plain")
        self.create_asset("system/config.json", '{"model": "gpt-4"}', "application/json")
        self.create_asset("workspace/notes.md", "# Notes\n\nSome notes here.", "text/markdown")
