"""Session state: token, response cache, undo/redo."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from cli_anything.figma.utils.config import get_token

_CACHE_MAX = 100
_UNDO_MAX = 50


class Session:
    def __init__(self) -> None:
        self.token: str | None = get_token()
        self._cache: dict[str, Any] = {}
        self._cache_keys: list[str] = []  # insertion order for LRU eviction
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._last_call: datetime | None = None
        self._history: list[str] = []

    # ── token ────────────────────────────────────────────────────────────────

    def token_header(self) -> dict:
        if not self.token:
            raise ValueError(
                "No Figma token set. Run: cli-anything-figma config set-token TOKEN\n"
                "Or set the FIGMA_TOKEN environment variable."
            )
        return {"X-Figma-Token": self.token}

    # ── cache ─────────────────────────────────────────────────────────────────

    def _cache_key(self, method: str, path: str, params: dict | None) -> str:
        p = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        return f"{method}:{path}:{p}"

    def get_cached(self, method: str, path: str, params: dict | None = None) -> Any | None:
        return self._cache.get(self._cache_key(method, path, params))

    def set_cached(self, method: str, path: str, params: dict | None, value: Any) -> None:
        key = self._cache_key(method, path, params)
        if key not in self._cache:
            if len(self._cache_keys) >= _CACHE_MAX:
                evict = self._cache_keys.pop(0)
                self._cache.pop(evict, None)
            self._cache_keys.append(key)
        self._cache[key] = value

    def invalidate_cache_prefix(self, prefix: str) -> None:
        to_remove = [k for k in self._cache if prefix in k]
        for k in to_remove:
            self._cache.pop(k, None)
            if k in self._cache_keys:
                self._cache_keys.remove(k)

    def clear_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        self._cache_keys.clear()
        return count

    # ── undo/redo ─────────────────────────────────────────────────────────────

    def snapshot(self, description: str) -> None:
        snap = {"description": description, "token": self.token}
        self._undo_stack.append(snap)
        if len(self._undo_stack) > _UNDO_MAX:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._history.append(description)

    def undo(self) -> str:
        if not self._undo_stack:
            raise ValueError("Nothing to undo.")
        snap = self._undo_stack.pop()
        self._redo_stack.append({"description": snap["description"], "token": self.token})
        self.token = snap["token"]
        return f"Undid: {snap['description']}"

    def redo(self) -> str:
        if not self._redo_stack:
            raise ValueError("Nothing to redo.")
        snap = self._redo_stack.pop()
        self._undo_stack.append({"description": snap["description"], "token": self.token})
        self.token = snap["token"]
        return f"Redid: {snap['description']}"

    def list_history(self) -> list[str]:
        return list(self._history)

    # ── status ────────────────────────────────────────────────────────────────

    def touch(self) -> None:
        self._last_call = datetime.now()

    def status(self) -> dict:
        from cli_anything.figma.utils.config import mask_token
        return {
            "token_set": self.token is not None,
            "token_preview": mask_token(self.token) if self.token else None,
            "cache_entries": len(self._cache),
            "undo_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
            "last_api_call": self._last_call.isoformat() if self._last_call else None,
        }
