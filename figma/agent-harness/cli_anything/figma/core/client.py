"""HTTP client for the Figma REST API."""
from __future__ import annotations

from typing import Any

import requests

from cli_anything.figma.core.session import Session

BASE = "https://api.figma.com"


class FigmaClient:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── private HTTP helpers ──────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        cached = self._session.get_cached("GET", path, params)
        if cached is not None:
            return cached
        resp = requests.get(
            BASE + path,
            headers=self._session.token_header(),
            params=params or {},
            timeout=30,
        )
        self._session.touch()
        self._raise_for_status(resp)
        data = resp.json()
        self._session.set_cached("GET", path, params, data)
        return data

    def _post(self, path: str, body: dict) -> dict:
        resp = requests.post(
            BASE + path,
            headers={**self._session.token_header(), "Content-Type": "application/json"},
            json=body,
            timeout=30,
        )
        self._session.touch()
        self._raise_for_status(resp)
        self._session.invalidate_cache_prefix(path)
        return resp.json()

    def _delete(self, path: str) -> dict:
        resp = requests.delete(
            BASE + path,
            headers=self._session.token_header(),
            timeout=30,
        )
        self._session.touch()
        self._raise_for_status(resp)
        self._session.invalidate_cache_prefix(path.rsplit("/", 1)[0])
        try:
            return resp.json()
        except Exception:
            return {"status": 200}

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.status_code == 403:
            raise requests.HTTPError(
                "403 Forbidden — invalid token or insufficient permissions.",
                response=resp,
            )
        if resp.status_code == 404:
            raise requests.HTTPError(
                f"404 Not Found — resource does not exist: {resp.url}",
                response=resp,
            )
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            try:
                msg = resp.json().get("err") or resp.json().get("message") or resp.text
            except Exception:
                msg = resp.text
            raise requests.HTTPError(f"{resp.status_code}: {msg}", response=resp)

    # ── file endpoints ────────────────────────────────────────────────────────

    def get_file(self, file_key: str, depth: int | None = None, ids: list[str] | None = None) -> dict:
        params: dict[str, Any] = {}
        if depth is not None:
            params["depth"] = depth
        if ids:
            params["ids"] = ",".join(ids)
        return self._get(f"/v1/files/{file_key}", params or None)

    def get_file_nodes(self, file_key: str, ids: list[str], depth: int | None = None) -> dict:
        params: dict[str, Any] = {"ids": ",".join(ids)}
        if depth is not None:
            params["depth"] = depth
        return self._get(f"/v1/files/{file_key}/nodes", params)

    def get_file_versions(self, file_key: str, page_size: int | None = None) -> dict:
        params = {}
        if page_size:
            params["page_size"] = page_size
        return self._get(f"/v1/files/{file_key}/versions", params or None)

    # ── image / export endpoints ──────────────────────────────────────────────

    def get_images(
        self,
        file_key: str,
        ids: list[str],
        scale: float = 1.0,
        format: str = "png",
        svg_outline_text: bool = True,
        use_absolute_bounds: bool = False,
    ) -> dict:
        params: dict[str, Any] = {
            "ids": ",".join(ids),
            "scale": scale,
            "format": format,
            "svg_outline_text": str(svg_outline_text).lower(),
            "use_absolute_bounds": str(use_absolute_bounds).lower(),
        }
        return self._get(f"/v1/images/{file_key}", params)

    def get_image_fills(self, file_key: str) -> dict:
        return self._get(f"/v1/files/{file_key}/images")

    # ── component / style endpoints ───────────────────────────────────────────

    def get_file_components(self, file_key: str) -> dict:
        return self._get(f"/v1/files/{file_key}/components")

    def get_file_component_sets(self, file_key: str) -> dict:
        return self._get(f"/v1/files/{file_key}/component_sets")

    def get_component(self, component_key: str) -> dict:
        return self._get(f"/v1/components/{component_key}")

    def get_file_styles(self, file_key: str) -> dict:
        return self._get(f"/v1/files/{file_key}/styles")

    def get_style(self, style_key: str) -> dict:
        return self._get(f"/v1/styles/{style_key}")

    # ── variable endpoints ────────────────────────────────────────────────────

    def get_local_variables(self, file_key: str) -> dict:
        return self._get(f"/v1/files/{file_key}/variables/local")

    # ── comment endpoints ─────────────────────────────────────────────────────

    def get_comments(self, file_key: str) -> dict:
        return self._get(f"/v1/files/{file_key}/comments")

    def post_comment(self, file_key: str, message: str, reply_to: str | None = None) -> dict:
        body: dict[str, Any] = {"message": message}
        if reply_to:
            body["comment_id"] = reply_to
        return self._post(f"/v1/files/{file_key}/comments", body)

    def delete_comment(self, file_key: str, comment_id: str) -> dict:
        return self._delete(f"/v1/files/{file_key}/comments/{comment_id}")

    # ── project endpoints ─────────────────────────────────────────────────────

    def get_team_projects(self, team_id: str) -> dict:
        return self._get(f"/v1/teams/{team_id}/projects")

    def get_project_files(self, project_id: str, branch_data: bool = False) -> dict:
        params = {"branch_data": "true"} if branch_data else None
        return self._get(f"/v1/projects/{project_id}/files", params)

    # ── user endpoint ─────────────────────────────────────────────────────────

    def get_me(self) -> dict:
        return self._get("/v1/me")
