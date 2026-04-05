"""Comment read/write logic."""
from __future__ import annotations

from cli_anything.figma.core.client import FigmaClient


def list_comments(client: FigmaClient, file_key: str, include_resolved: bool = False) -> list[dict]:
    resp = client.get_comments(file_key)
    comments = []
    for c in resp.get("comments", []):
        if not include_resolved and c.get("resolved_at"):
            continue
        comments.append({
            "id": c.get("id", ""),
            "message": c.get("message", ""),
            "author": c.get("user", {}).get("handle", "unknown"),
            "created_at": c.get("created_at", ""),
            "resolved_at": c.get("resolved_at"),
            "parent_id": c.get("parent_id"),
        })
    return comments


def post_comment(
    client: FigmaClient,
    file_key: str,
    message: str,
    reply_to: str | None = None,
) -> dict:
    resp = client.post_comment(file_key, message, reply_to)
    c = resp.get("comment", resp)
    return {
        "id": c.get("id", ""),
        "message": c.get("message", message),
        "created_at": c.get("created_at", ""),
    }


def delete_comment(client: FigmaClient, file_key: str, comment_id: str) -> dict:
    client.delete_comment(file_key, comment_id)
    return {"status": "deleted", "comment_id": comment_id}
