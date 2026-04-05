"""Design token extraction and tree/table formatting helpers."""
from __future__ import annotations

import re
from typing import Any


# ── design token extraction ───────────────────────────────────────────────────

def slugify(name: str) -> str:
    """'Primary / Blue 500' -> 'primary-blue-500'"""
    s = name.lower().strip()
    s = re.sub(r"[\s/]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _rgba_to_hex(r: float, g: float, b: float, a: float = 1.0) -> str:
    ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
    if a < 1.0:
        ai = int(a * 255)
        return f"#{ri:02x}{gi:02x}{bi:02x}{ai:02x}"
    return f"#{ri:02x}{gi:02x}{bi:02x}"


def extract_tokens(variables_resp: dict, styles_resp: dict) -> dict:
    """Normalise Figma variables + styles into a flat token dict."""
    tokens: dict[str, dict] = {"colors": {}, "typography": {}, "effects": {}, "other": {}}

    # --- variables (design tokens / variable collections) ---
    meta = variables_resp.get("meta", {})
    variables = meta.get("variables", {})
    collections = meta.get("variableCollections", {})

    for var_id, var in variables.items():
        name = var.get("name", var_id)
        slug = slugify(name)
        resolved = var.get("resolvedType", "")
        values = var.get("valuesByMode", {})
        # Take first mode's value
        value = next(iter(values.values()), None) if values else None

        if resolved == "COLOR" and isinstance(value, dict):
            hex_val = _rgba_to_hex(
                value.get("r", 0), value.get("g", 0),
                value.get("b", 0), value.get("a", 1)
            )
            tokens["colors"][slug] = hex_val
        elif resolved == "FLOAT" and value is not None:
            tokens["other"][slug] = value
        elif resolved == "STRING" and value is not None:
            tokens["typography"][slug] = value
        elif value is not None:
            tokens["other"][slug] = value

    # --- published styles ---
    for meta_style in styles_resp.get("meta", {}).get("styles", []):
        name = meta_style.get("name", "")
        slug = slugify(name)
        style_type = meta_style.get("style_type", "")
        desc = meta_style.get("description", "")

        if style_type == "FILL":
            if slug not in tokens["colors"]:
                tokens["colors"][slug] = {"style_key": meta_style.get("key"), "description": desc}
        elif style_type == "TEXT":
            tokens["typography"][slug] = {"style_key": meta_style.get("key"), "description": desc}
        elif style_type == "EFFECT":
            tokens["effects"][slug] = {"style_key": meta_style.get("key"), "description": desc}

    return tokens


def tokens_to_css(tokens: dict) -> str:
    lines = [":root {"]
    for category, items in tokens.items():
        if not items:
            continue
        lines.append(f"  /* {category} */")
        for name, value in items.items():
            if isinstance(value, dict):
                v = value.get("style_key", str(value))
            else:
                v = str(value)
            lines.append(f"  --{category}-{name}: {v};")
    lines.append("}")
    return "\n".join(lines)


def tokens_to_scss(tokens: dict) -> str:
    lines = []
    for category, items in tokens.items():
        if not items:
            continue
        lines.append(f"// {category}")
        for name, value in items.items():
            if isinstance(value, dict):
                v = value.get("style_key", str(value))
            else:
                v = str(value)
            lines.append(f"${category}-{name}: {v};")
        lines.append("")
    return "\n".join(lines)


# ── node tree helpers ─────────────────────────────────────────────────────────

def flatten_node_tree(node: dict, depth: int = 0) -> list[dict]:
    """Recursively flatten a Figma node tree into a list."""
    result = [
        {
            "id": node.get("id", ""),
            "name": node.get("name", ""),
            "type": node.get("type", ""),
            "depth": depth,
        }
    ]
    for child in node.get("children", []):
        result.extend(flatten_node_tree(child, depth + 1))
    return result


def format_node_table(nodes: list[dict]) -> str:
    lines = []
    for n in nodes:
        indent = "  " * n["depth"]
        lines.append(f"{indent}[{n['type']}] {n['name']}  (id: {n['id']})")
    return "\n".join(lines)


def format_table(rows: list[dict], columns: list[str] | None = None) -> str:
    """Generic table formatter."""
    if not rows:
        return "(none)"
    cols = columns or list(rows[0].keys())
    widths = {c: len(c) for c in cols}
    for row in rows:
        for c in cols:
            widths[c] = max(widths[c], len(str(row.get(c, ""))))
    header = "  ".join(c.upper().ljust(widths[c]) for c in cols)
    sep = "  ".join("-" * widths[c] for c in cols)
    body = "\n".join(
        "  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols)
        for row in rows
    )
    return f"{header}\n{sep}\n{body}"
