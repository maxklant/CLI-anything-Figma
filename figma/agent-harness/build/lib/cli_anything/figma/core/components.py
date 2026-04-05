"""Component, style, and design token logic."""
from __future__ import annotations

from cli_anything.figma.core.client import FigmaClient
from cli_anything.figma.utils.formatting import extract_tokens, tokens_to_css, tokens_to_scss


def list_components(client: FigmaClient, file_key: str, include_sets: bool = False) -> list[dict]:
    resp = client.get_file_components(file_key)
    components = []
    for c in resp.get("meta", {}).get("components", []):
        entry = {
            "key": c.get("key", ""),
            "name": c.get("name", ""),
            "description": c.get("description", ""),
            "component_set_key": c.get("containing_frame", {}).get("containingStateGroup", {}).get("name", ""),
        }
        components.append(entry)
    if include_sets:
        sets_resp = client.get_file_component_sets(file_key)
        for s in sets_resp.get("meta", {}).get("component_sets", []):
            components.append({
                "key": s.get("key", ""),
                "name": s.get("name", "") + " [SET]",
                "description": s.get("description", ""),
            })
    return components


def list_component_sets(client: FigmaClient, file_key: str) -> list[dict]:
    resp = client.get_file_component_sets(file_key)
    result = []
    for s in resp.get("meta", {}).get("component_sets", []):
        result.append({
            "key": s.get("key", ""),
            "name": s.get("name", ""),
            "description": s.get("description", ""),
        })
    return result


def get_component_info(client: FigmaClient, component_key: str) -> dict:
    resp = client.get_component(component_key)
    meta = resp.get("meta", resp)
    return {
        "key": meta.get("key", ""),
        "name": meta.get("name", ""),
        "description": meta.get("description", ""),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("updated_at", ""),
        "file_key": meta.get("file_key", ""),
        "node_id": meta.get("node_id", ""),
        "thumbnail_url": meta.get("thumbnail_url", ""),
    }


def get_design_tokens(
    client: FigmaClient,
    file_key: str,
    output_format: str = "json",
    output_file: str | None = None,
) -> dict | str:
    try:
        variables_resp = client.get_local_variables(file_key)
    except Exception:
        variables_resp = {}
    try:
        styles_resp = client.get_file_styles(file_key)
    except Exception:
        styles_resp = {}

    tokens = extract_tokens(variables_resp, styles_resp)

    if output_format == "css":
        content = tokens_to_css(tokens)
    elif output_format == "scss":
        content = tokens_to_scss(tokens)
    else:
        import json
        content = json.dumps(tokens, indent=2)

    if output_file:
        from pathlib import Path
        Path(output_file).write_text(content, encoding="utf-8")

    return content if output_format in ("css", "scss") else tokens
