"""Export orchestration: download rendered images from Figma to disk."""
from __future__ import annotations

import os
from pathlib import Path

import requests

from cli_anything.figma.core.client import FigmaClient
from cli_anything.figma.utils.formatting import flatten_node_tree, slugify


def _safe_filename(name: str, fmt: str) -> str:
    safe = slugify(name) or "node"
    return f"{safe}.{fmt}"


def export_nodes(
    client: FigmaClient,
    file_key: str,
    node_ids: list[str],
    format: str = "png",
    scale: float = 1.0,
    output_dir: str = ".",
    use_absolute_bounds: bool = False,
) -> list[dict]:
    """Export specific nodes and download resulting images to output_dir."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    resp = client.get_images(
        file_key, node_ids,
        scale=scale, format=format,
        use_absolute_bounds=use_absolute_bounds,
    )
    images: dict = resp.get("images", {})
    if resp.get("err"):
        raise ValueError(f"Figma render error: {resp['err']}")

    # Get node names for nice filenames
    names: dict[str, str] = {}
    try:
        nodes_resp = client.get_file_nodes(file_key, node_ids)
        for nid, node_data in nodes_resp.get("nodes", {}).items():
            if node_data and node_data.get("document"):
                names[nid] = node_data["document"].get("name", nid)
    except Exception:
        pass

    results = []
    for node_id, url in images.items():
        if url is None:
            results.append({"node_id": node_id, "status": "error", "error": "render failed"})
            continue
        name = names.get(node_id, node_id)
        filename = _safe_filename(name, format)
        dest = Path(output_dir) / filename
        try:
            dl = requests.get(url, timeout=60)
            dl.raise_for_status()
            dest.write_bytes(dl.content)
            results.append({
                "node_id": node_id,
                "name": name,
                "path": str(dest),
                "size_bytes": len(dl.content),
                "status": "ok",
            })
        except Exception as e:
            results.append({"node_id": node_id, "name": name, "status": "error", "error": str(e)})
    return results


def export_batch(
    client: FigmaClient,
    file_key: str,
    format: str = "png",
    scale: float = 1.0,
    output_dir: str = ".",
    filter_type: str = "FRAME",
) -> list[dict]:
    """Auto-discover all nodes of filter_type and export them."""
    file_data = client.get_file(file_key, depth=3)
    doc = file_data.get("document", {})
    all_nodes = flatten_node_tree(doc)
    target_ids = [n["id"] for n in all_nodes if n["type"] == filter_type.upper()]
    if not target_ids:
        return []
    return export_nodes(client, file_key, target_ids, format, scale, output_dir)


def export_image_fills(
    client: FigmaClient,
    file_key: str,
    output_dir: str = ".",
) -> list[dict]:
    """Download all embedded image fills from a file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    resp = client.get_image_fills(file_key)
    images: dict = resp.get("meta", {}).get("images", {})
    results = []
    for image_ref, url in images.items():
        if not url:
            continue
        filename = f"{slugify(image_ref) or image_ref}.png"
        dest = Path(output_dir) / filename
        try:
            dl = requests.get(url, timeout=60)
            dl.raise_for_status()
            dest.write_bytes(dl.content)
            results.append({"image_ref": image_ref, "path": str(dest), "size_bytes": len(dl.content), "status": "ok"})
        except Exception as e:
            results.append({"image_ref": image_ref, "status": "error", "error": str(e)})
    return results
