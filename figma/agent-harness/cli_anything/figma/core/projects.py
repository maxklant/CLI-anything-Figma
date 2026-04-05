"""Team / project / file listing logic."""
from __future__ import annotations

from cli_anything.figma.core.client import FigmaClient


def list_team_projects(client: FigmaClient, team_id: str) -> list[dict]:
    resp = client.get_team_projects(team_id)
    return [
        {"id": p.get("id", ""), "name": p.get("name", "")}
        for p in resp.get("projects", [])
    ]


def list_project_files(
    client: FigmaClient,
    project_id: str,
    branch_data: bool = False,
) -> list[dict]:
    resp = client.get_project_files(project_id, branch_data)
    files = []
    for f in resp.get("files", []):
        entry = {
            "key": f.get("key", ""),
            "name": f.get("name", ""),
            "last_modified": f.get("last_modified", ""),
            "thumbnail_url": f.get("thumbnail_url", ""),
        }
        files.append(entry)
    return files
