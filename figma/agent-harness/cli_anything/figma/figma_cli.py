"""Figma CLI — root Click group and all command groups."""
from __future__ import annotations

import json
import shlex
import sys
from functools import wraps
from typing import Any

import click
import requests

from cli_anything.figma.core.session import Session
from cli_anything.figma.core.client import FigmaClient

# ── global state ──────────────────────────────────────────────────────────────

_session: Session | None = None
_json_output: bool = False


def get_session() -> Session:
    global _session
    if _session is None:
        _session = Session()
    return _session


def get_client() -> FigmaClient:
    return FigmaClient(get_session())


# ── output helpers ────────────────────────────────────────────────────────────

def output(data: Any) -> None:
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        _print_human(data)


def _print_human(data: Any, indent: int = 0) -> None:
    pad = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                click.echo(f"{pad}{k}:")
                _print_human(v, indent + 1)
            else:
                click.echo(f"{pad}{k}: {v}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                click.echo(f"{pad}[{i}]")
                _print_human(item, indent + 1)
            else:
                click.echo(f"{pad}- {item}")
    else:
        click.echo(f"{pad}{data}")


# ── error handling decorator ──────────────────────────────────────────────────

def handle_error(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (requests.HTTPError, requests.ConnectionError) as e:
            msg = str(e)
            if _json_output:
                click.echo(json.dumps({"error": msg, "type": "http"}))
            else:
                click.echo(f"\033[31mHTTP Error:\033[0m {msg}", err=True)
            sys.exit(1)
        except ValueError as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": "value"}))
            else:
                click.echo(f"\033[31mError:\033[0m {e}", err=True)
            sys.exit(1)
        except (KeyError, FileNotFoundError) as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": type(e).__name__}))
            else:
                click.echo(f"\033[31mError:\033[0m {e}", err=True)
            sys.exit(1)
    return wrapper


# ── REPL ──────────────────────────────────────────────────────────────────────

def _start_repl() -> None:
    from cli_anything.figma.utils.repl_skin import ReplSkin
    skin = ReplSkin("figma", "1.0.0")
    skin.print_banner()
    while True:
        try:
            line = skin.get_input().strip()
        except EOFError:
            click.echo("\nBye!")
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            click.echo("Bye!")
            break
        try:
            args = shlex.split(line)
        except ValueError as e:
            skin.print_error(f"Parse error: {e}")
            continue
        try:
            cli.main(args, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            skin.print_error(str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# ROOT GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output results as JSON")
@click.pass_context
def cli(ctx: click.Context, use_json: bool) -> None:
    """CLI-Anything for Figma — design inspection, export, and collaboration."""
    global _json_output
    _json_output = use_json
    if ctx.invoked_subcommand is None:
        _start_repl()


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def config() -> None:
    """Manage CLI configuration (API token, defaults)."""


@config.command("set-token")
@click.argument("token")
@handle_error
def config_set_token(token: str) -> None:
    """Store your Figma personal access token."""
    from cli_anything.figma.utils.config import set_token
    sess = get_session()
    sess.snapshot("set-token")
    set_token(token)
    sess.token = token
    from cli_anything.figma.utils.config import mask_token
    output({"status": "ok", "token": mask_token(token)})


@config.command("show")
@handle_error
def config_show() -> None:
    """Show current configuration."""
    from cli_anything.figma.utils.config import load_config, mask_token
    cfg = load_config()
    display = dict(cfg)
    if "token" in display:
        display["token"] = mask_token(display["token"])
    output(display)


# ═══════════════════════════════════════════════════════════════════════════════
# FILE GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def file() -> None:
    """Inspect Figma files, pages, and layer trees."""


@file.command("info")
@click.argument("file_key")
@click.option("--depth", default=1, type=int, show_default=True, help="Node tree depth to fetch")
@handle_error
def file_info(file_key: str, depth: int) -> None:
    """Show file metadata (name, version, pages, last modified)."""
    data = get_client().get_file(file_key, depth=depth)
    doc = data.get("document", {})
    pages = [c.get("name") for c in doc.get("children", [])]
    result = {
        "name": data.get("name", ""),
        "version": data.get("version", ""),
        "last_modified": data.get("lastModified", ""),
        "editor_type": data.get("editorType", ""),
        "thumbnail_url": data.get("thumbnailUrl", ""),
        "schema_version": data.get("schemaVersion", ""),
        "page_count": len(pages),
        "pages": pages,
    }
    output(result)


@file.command("pages")
@click.argument("file_key")
@handle_error
def file_pages(file_key: str) -> None:
    """List all pages in a file."""
    data = get_client().get_file(file_key, depth=1)
    pages = []
    for canvas in data.get("document", {}).get("children", []):
        pages.append({
            "id": canvas.get("id", ""),
            "name": canvas.get("name", ""),
            "node_count": len(canvas.get("children", [])),
        })
    output(pages)


@file.command("nodes")
@click.argument("file_key")
@click.option("--depth", default=3, type=int, show_default=True)
@click.option("--node-id", "node_id", default=None, help="Start from a specific node ID")
@handle_error
def file_nodes(file_key: str, depth: int, node_id: str | None) -> None:
    """Print the layer/node tree of a file."""
    from cli_anything.figma.utils.formatting import flatten_node_tree, format_node_table
    if node_id:
        data = get_client().get_file_nodes(file_key, [node_id], depth=depth)
        node = data.get("nodes", {}).get(node_id, {}).get("document", {})
        nodes = flatten_node_tree(node)
    else:
        data = get_client().get_file(file_key, depth=depth)
        doc = data.get("document", {})
        nodes = flatten_node_tree(doc)
    if _json_output:
        output(nodes)
    else:
        click.echo(format_node_table(nodes))


@file.command("versions")
@click.argument("file_key")
@click.option("--limit", default=20, type=int, show_default=True)
@handle_error
def file_versions(file_key: str, limit: int) -> None:
    """List version history of a file."""
    data = get_client().get_file_versions(file_key, page_size=limit)
    versions = []
    for v in data.get("versions", [])[:limit]:
        versions.append({
            "id": v.get("id", ""),
            "label": v.get("label") or "(auto-save)",
            "description": v.get("description", ""),
            "created_at": v.get("created_at", ""),
            "user": v.get("user", {}).get("handle", ""),
        })
    output(versions)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def export() -> None:
    """Export frames, components, or assets from a Figma file."""


@export.command("frame")
@click.argument("file_key")
@click.argument("node_ids")
@click.option("--format", "fmt", default="png",
              type=click.Choice(["png", "svg", "pdf", "jpg"], case_sensitive=False),
              show_default=True)
@click.option("--scale", default=1.0, type=float, show_default=True)
@click.option("--output-dir", default=".", show_default=True)
@click.option("--use-absolute-bounds", is_flag=True, default=False)
@handle_error
def export_frame(
    file_key: str, node_ids: str, fmt: str,
    scale: float, output_dir: str, use_absolute_bounds: bool,
) -> None:
    """Export specific frames/nodes by ID (comma-separated)."""
    from cli_anything.figma.core.export import export_nodes
    ids = [n.strip() for n in node_ids.split(",") if n.strip()]
    results = export_nodes(
        get_client(), file_key, ids, fmt, scale, output_dir, use_absolute_bounds
    )
    output(results)
    if not _json_output:
        ok = sum(1 for r in results if r.get("status") == "ok")
        click.echo(f"\n[ok] Exported {ok}/{len(results)} nodes to {output_dir}/")


@export.command("batch")
@click.argument("file_key")
@click.option("--format", "fmt", default="png",
              type=click.Choice(["png", "svg", "pdf", "jpg"], case_sensitive=False),
              show_default=True)
@click.option("--scale", default=1.0, type=float, show_default=True)
@click.option("--output-dir", default=".", show_default=True)
@click.option("--filter-type", default="FRAME", show_default=True,
              help="Node type to export (FRAME, COMPONENT, etc.)")
@handle_error
def export_batch(
    file_key: str, fmt: str, scale: float,
    output_dir: str, filter_type: str,
) -> None:
    """Auto-discover and export all nodes of a given type."""
    from cli_anything.figma.core.export import export_batch as _batch
    results = _batch(get_client(), file_key, fmt, scale, output_dir, filter_type)
    output(results)
    if not _json_output:
        ok = sum(1 for r in results if r.get("status") == "ok")
        click.echo(f"\n[ok] Exported {ok}/{len(results)} {filter_type} nodes to {output_dir}/")


@export.command("fills")
@click.argument("file_key")
@click.option("--output-dir", default=".", show_default=True)
@handle_error
def export_fills(file_key: str, output_dir: str) -> None:
    """Download all embedded image fill assets from a file."""
    from cli_anything.figma.core.export import export_image_fills
    results = export_image_fills(get_client(), file_key, output_dir)
    output(results)
    if not _json_output:
        ok = sum(1 for r in results if r.get("status") == "ok")
        click.echo(f"\n[ok] Downloaded {ok}/{len(results)} image fills to {output_dir}/")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def component() -> None:
    """Inspect components, variants, and extract design tokens."""


@component.command("list")
@click.argument("file_key")
@click.option("--include-sets", is_flag=True, default=False)
@handle_error
def component_list(file_key: str, include_sets: bool) -> None:
    """List all published components in a file."""
    from cli_anything.figma.core.components import list_components
    result = list_components(get_client(), file_key, include_sets)
    if not _json_output:
        from cli_anything.figma.utils.formatting import format_table
        click.echo(format_table(result, ["key", "name", "description"]))
    else:
        output(result)


@component.command("sets")
@click.argument("file_key")
@handle_error
def component_sets(file_key: str) -> None:
    """List all component sets (variant groups) in a file."""
    from cli_anything.figma.core.components import list_component_sets
    result = list_component_sets(get_client(), file_key)
    if not _json_output:
        from cli_anything.figma.utils.formatting import format_table
        click.echo(format_table(result, ["key", "name", "description"]))
    else:
        output(result)


@component.command("info")
@click.argument("component_key")
@handle_error
def component_info(component_key: str) -> None:
    """Show full metadata for a single component."""
    from cli_anything.figma.core.components import get_component_info
    output(get_component_info(get_client(), component_key))


@component.command("tokens")
@click.argument("file_key")
@click.option("--format", "fmt", default="json",
              type=click.Choice(["json", "css", "scss"], case_sensitive=False),
              show_default=True)
@click.option("--output-file", default=None, help="Write tokens to this file")
@handle_error
def component_tokens(file_key: str, fmt: str, output_file: str | None) -> None:
    """Extract design tokens (colors, typography, effects) from a file."""
    from cli_anything.figma.core.components import get_design_tokens
    result = get_design_tokens(get_client(), file_key, fmt, output_file)
    if isinstance(result, str):
        click.echo(result)
        if output_file and not _json_output:
            click.echo(f"\n[ok] Tokens written to {output_file}")
    else:
        output(result)


# ═══════════════════════════════════════════════════════════════════════════════
# STYLE GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def style() -> None:
    """List and inspect published styles."""


@style.command("list")
@click.argument("file_key")
@click.option("--type", "style_type", default="all",
              type=click.Choice(["fill", "text", "effect", "grid", "all"], case_sensitive=False),
              show_default=True)
@handle_error
def style_list(file_key: str, style_type: str) -> None:
    """List published styles in a file."""
    resp = get_client().get_file_styles(file_key)
    styles = []
    for s in resp.get("meta", {}).get("styles", []):
        if style_type != "all" and s.get("style_type", "").lower() != style_type:
            continue
        styles.append({
            "key": s.get("key", ""),
            "name": s.get("name", ""),
            "style_type": s.get("style_type", ""),
            "description": s.get("description", ""),
        })
    if not _json_output:
        from cli_anything.figma.utils.formatting import format_table
        click.echo(format_table(styles, ["key", "name", "style_type"]))
    else:
        output(styles)


@style.command("info")
@click.argument("style_key")
@handle_error
def style_info(style_key: str) -> None:
    """Show full metadata for a style."""
    resp = get_client().get_style(style_key)
    output(resp.get("meta", resp))


# ═══════════════════════════════════════════════════════════════════════════════
# COMMENT GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def comment() -> None:
    """Read and post comments on a Figma file."""


@comment.command("list")
@click.argument("file_key")
@click.option("--resolved", is_flag=True, default=False, help="Include resolved comments")
@handle_error
def comment_list(file_key: str, resolved: bool) -> None:
    """List comments on a file."""
    from cli_anything.figma.core.comments import list_comments
    result = list_comments(get_client(), file_key, include_resolved=resolved)
    if not _json_output:
        for c in result:
            ts = c.get("created_at", "")[:10]
            author = c.get("author", "")
            msg = c.get("message", "")
            cid = c.get("id", "")
            parent = f"  [reply to {c['parent_id']}]" if c.get("parent_id") else ""
            click.echo(f"[{cid}] {ts} @{author}{parent}")
            click.echo(f"  {msg}")
            click.echo()
    else:
        output(result)


@comment.command("post")
@click.argument("file_key")
@click.argument("message")
@click.option("--reply-to", default=None, help="Comment ID to reply to")
@handle_error
def comment_post(file_key: str, message: str, reply_to: str | None) -> None:
    """Post a comment on a file."""
    from cli_anything.figma.core.comments import post_comment
    result = post_comment(get_client(), file_key, message, reply_to)
    output(result)


@comment.command("delete")
@click.argument("file_key")
@click.argument("comment_id")
@handle_error
def comment_delete(file_key: str, comment_id: str) -> None:
    """Delete a comment."""
    from cli_anything.figma.core.comments import delete_comment
    output(delete_comment(get_client(), file_key, comment_id))


# ═══════════════════════════════════════════════════════════════════════════════
# PROJECT GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def project() -> None:
    """Browse teams, projects, and files."""


@project.command("team")
@click.argument("team_id")
@handle_error
def project_team(team_id: str) -> None:
    """List all projects in a team."""
    from cli_anything.figma.core.projects import list_team_projects
    result = list_team_projects(get_client(), team_id)
    if not _json_output:
        from cli_anything.figma.utils.formatting import format_table
        click.echo(format_table(result, ["id", "name"]))
    else:
        output(result)


@project.command("files")
@click.argument("project_id")
@click.option("--branch-data", is_flag=True, default=False)
@handle_error
def project_files(project_id: str, branch_data: bool) -> None:
    """List all files in a project."""
    from cli_anything.figma.core.projects import list_project_files
    result = list_project_files(get_client(), project_id, branch_data)
    if not _json_output:
        from cli_anything.figma.utils.formatting import format_table
        click.echo(format_table(result, ["key", "name", "last_modified"]))
    else:
        output(result)


# ═══════════════════════════════════════════════════════════════════════════════
# USER GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def user() -> None:
    """Current authenticated user information."""


@user.command("me")
@handle_error
def user_me() -> None:
    """Show the authenticated user's profile."""
    data = get_client().get_me()
    output({
        "id": data.get("id", ""),
        "handle": data.get("handle", ""),
        "email": data.get("email", ""),
        "img_url": data.get("img_url", ""),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION GROUP
# ═══════════════════════════════════════════════════════════════════════════════

@cli.group()
def session() -> None:
    """Session state: cache, token, undo/redo history."""


@session.command("status")
@handle_error
def session_status() -> None:
    """Show session status."""
    output(get_session().status())


@session.command("clear-cache")
@handle_error
def session_clear_cache() -> None:
    """Clear the in-memory response cache."""
    count = get_session().clear_cache()
    output({"cleared": count})


@session.command("history")
@handle_error
def session_history() -> None:
    """Show command history."""
    output(get_session().list_history())


@session.command("undo")
@handle_error
def session_undo() -> None:
    """Undo last state-mutating command (within session)."""
    output({"result": get_session().undo()})


@session.command("redo")
@handle_error
def session_redo() -> None:
    """Redo last undone command."""
    output({"result": get_session().redo()})


# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN GROUP  (requires bridge server + Figma plugin)
# ═══════════════════════════════════════════════════════════════════════════════

def _bridge_url(port: int) -> str:
    return f"http://localhost:{port}"


def _design_cmd(command: str, args: dict, port: int) -> None:
    from cli_anything.figma.core.bridge_client import send_command
    result = send_command(command, args, _bridge_url(port))
    output(result)
    if not _json_output and result.get("status") == "error":
        sys.exit(1)


@cli.group()
def design() -> None:
    """Create and modify Figma designs via the plugin bridge (run 'design serve' first)."""


@design.command("serve")
@click.option("--port", default=7777, type=int, show_default=True)
def design_serve(port: int) -> None:
    """Start the WebSocket bridge server (blocking — run in a separate terminal)."""
    from cli_anything.figma.core.bridge import run_server
    click.echo(f"[bridge] Starting on ws://localhost:{port}")
    click.echo("[bridge] Open the CLI-Anything Bridge plugin in Figma to connect.")
    click.echo("[bridge] Press Ctrl-C to stop.")
    run_server(port)


@design.command("status")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_status(port: int) -> None:
    """Check if the bridge server is running and the Figma plugin is connected."""
    from cli_anything.figma.core.bridge_client import check_status
    output(check_status(_bridge_url(port)))


# ── creation commands ──────────────────────────────────────────────────────────

@design.command("frame")
@click.argument("name")
@click.option("--width", default=1440.0, type=float, show_default=True)
@click.option("--height", default=900.0, type=float, show_default=True)
@click.option("--x", default=0.0, type=float, show_default=True)
@click.option("--y", default=0.0, type=float, show_default=True)
@click.option("--fill", default=None, help="Background fill as #hex")
@click.option("--corner-radius", "corner_radius", default=None, type=float)
@click.option("--parent-id", "parent_id", default=None, help="Parent node ID")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_frame(name, width, height, x, y, fill, corner_radius, parent_id, port):
    """Create a frame on the current Figma page."""
    args = {"name": name, "width": width, "height": height, "x": x, "y": y}
    if fill: args["fill"] = fill
    if corner_radius is not None: args["corner_radius"] = corner_radius
    if parent_id: args["parent_id"] = parent_id
    _design_cmd("create_frame", args, port)


@design.command("text")
@click.argument("content")
@click.option("--font-size", "font_size", default=16.0, type=float, show_default=True)
@click.option("--color", default=None, help="Text color as #hex")
@click.option("--font-family", "font_family", default="Inter")
@click.option("--bold", is_flag=True, default=False)
@click.option("--x", default=0.0, type=float)
@click.option("--y", default=0.0, type=float)
@click.option("--parent-id", "parent_id", default=None)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_text(content, font_size, color, font_family, bold, x, y, parent_id, port):
    """Create a text node."""
    args = {"content": content, "font_size": font_size, "font_family": font_family,
            "bold": bold, "x": x, "y": y}
    if color: args["color"] = color
    if parent_id: args["parent_id"] = parent_id
    _design_cmd("create_text", args, port)


@design.command("rect")
@click.option("--name", default="Rectangle")
@click.option("--width", default=100.0, type=float, show_default=True)
@click.option("--height", default=100.0, type=float, show_default=True)
@click.option("--x", default=0.0, type=float)
@click.option("--y", default=0.0, type=float)
@click.option("--fill", default=None)
@click.option("--stroke", default=None, help="Stroke color as #hex")
@click.option("--stroke-weight", "stroke_weight", default=1.0, type=float)
@click.option("--corner-radius", "corner_radius", default=None, type=float)
@click.option("--parent-id", "parent_id", default=None)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_rect(name, width, height, x, y, fill, stroke, stroke_weight, corner_radius, parent_id, port):
    """Create a rectangle."""
    args = {"name": name, "width": width, "height": height, "x": x, "y": y}
    if fill: args["fill"] = fill
    if stroke: args["stroke"] = stroke; args["stroke_weight"] = stroke_weight
    if corner_radius is not None: args["corner_radius"] = corner_radius
    if parent_id: args["parent_id"] = parent_id
    _design_cmd("create_rect", args, port)


@design.command("ellipse")
@click.option("--name", default="Ellipse")
@click.option("--width", default=100.0, type=float, show_default=True)
@click.option("--height", default=100.0, type=float, show_default=True)
@click.option("--x", default=0.0, type=float)
@click.option("--y", default=0.0, type=float)
@click.option("--fill", default=None)
@click.option("--parent-id", "parent_id", default=None)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_ellipse(name, width, height, x, y, fill, parent_id, port):
    """Create an ellipse/circle."""
    args = {"name": name, "width": width, "height": height, "x": x, "y": y}
    if fill: args["fill"] = fill
    if parent_id: args["parent_id"] = parent_id
    _design_cmd("create_ellipse", args, port)


@design.command("component")
@click.argument("name")
@click.option("--width", default=200.0, type=float, show_default=True)
@click.option("--height", default=200.0, type=float, show_default=True)
@click.option("--fill", default=None)
@click.option("--x", default=0.0, type=float)
@click.option("--y", default=0.0, type=float)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_component(name, width, height, fill, x, y, port):
    """Create a component (master)."""
    args = {"name": name, "width": width, "height": height, "x": x, "y": y}
    if fill: args["fill"] = fill
    _design_cmd("create_component", args, port)


@design.command("instance")
@click.argument("component_id")
@click.option("--x", default=0.0, type=float)
@click.option("--y", default=0.0, type=float)
@click.option("--parent-id", "parent_id", default=None)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_instance(component_id, x, y, parent_id, port):
    """Create an instance of a component."""
    args = {"component_id": component_id, "x": x, "y": y}
    if parent_id: args["parent_id"] = parent_id
    _design_cmd("create_instance", args, port)


# ── layout ─────────────────────────────────────────────────────────────────────

@design.command("auto-layout")
@click.argument("node_id")
@click.option("--direction", default="horizontal",
              type=click.Choice(["horizontal", "vertical"], case_sensitive=False),
              show_default=True)
@click.option("--gap", default=None, type=float)
@click.option("--padding", default=None, type=float)
@click.option("--align", default=None,
              type=click.Choice(["start", "center", "end", "space-between"], case_sensitive=False))
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_auto_layout(node_id, direction, gap, padding, align, port):
    """Apply auto-layout to a frame."""
    args = {"node_id": node_id, "direction": direction}
    if gap is not None: args["gap"] = gap
    if padding is not None: args["padding"] = padding
    if align: args["align"] = align
    _design_cmd("auto_layout", args, port)


# ── mutation commands ──────────────────────────────────────────────────────────

@design.command("move")
@click.argument("node_id")
@click.option("--x", required=True, type=float)
@click.option("--y", required=True, type=float)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_move(node_id, x, y, port):
    """Move a node to an absolute position."""
    _design_cmd("move", {"node_id": node_id, "x": x, "y": y}, port)


@design.command("resize")
@click.argument("node_id")
@click.option("--width", required=True, type=float)
@click.option("--height", required=True, type=float)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_resize(node_id, width, height, port):
    """Resize a node."""
    _design_cmd("resize", {"node_id": node_id, "width": width, "height": height}, port)


@design.command("delete")
@click.argument("node_id")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_delete(node_id, port):
    """Delete a node by ID."""
    _design_cmd("delete", {"node_id": node_id}, port)


@design.command("select")
@click.argument("node_id")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_select(node_id, port):
    """Select a node and scroll it into view."""
    _design_cmd("select", {"node_id": node_id}, port)


@design.command("fill")
@click.argument("node_id")
@click.option("--color", required=True, help="Fill color as #hex")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_fill(node_id, color, port):
    """Set the fill color of a node."""
    _design_cmd("fill", {"node_id": node_id, "color": color}, port)


@design.command("stroke")
@click.argument("node_id")
@click.option("--color", required=True, help="Stroke color as #hex")
@click.option("--weight", default=1.0, type=float, show_default=True)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_stroke(node_id, color, weight, port):
    """Set the stroke of a node."""
    _design_cmd("stroke", {"node_id": node_id, "color": color, "weight": weight}, port)


@design.command("font")
@click.argument("node_id")
@click.option("--size", default=None, type=float)
@click.option("--family", default=None)
@click.option("--weight", default=None, help="Font style e.g. Regular, Bold, Medium")
@click.option("--color", default=None)
@click.option("--line-height", "line_height", default=None, type=float)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_font(node_id, size, family, weight, color, line_height, port):
    """Update font properties of a text node."""
    args = {"node_id": node_id}
    if size is not None: args["size"] = size
    if family: args["family"] = family
    if weight: args["weight"] = weight
    if color: args["color"] = color
    if line_height is not None: args["line_height"] = line_height
    _design_cmd("font", args, port)


@design.command("opacity")
@click.argument("node_id")
@click.option("--value", required=True, type=float, help="0.0 to 1.0")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_opacity(node_id, value, port):
    """Set node opacity (0.0–1.0)."""
    _design_cmd("opacity", {"node_id": node_id, "value": value}, port)


@design.command("rename")
@click.argument("node_id")
@click.argument("new_name")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_rename(node_id, new_name, port):
    """Rename a node."""
    _design_cmd("rename", {"node_id": node_id, "new_name": new_name}, port)


@design.command("duplicate")
@click.argument("node_id")
@click.option("--x", default=None, type=float)
@click.option("--y", default=None, type=float)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_duplicate(node_id, x, y, port):
    """Duplicate a node."""
    args = {"node_id": node_id}
    if x is not None: args["x"] = x
    if y is not None: args["y"] = y
    _design_cmd("duplicate", args, port)


@design.command("corner-radius")
@click.argument("node_id")
@click.option("--radius", required=True, type=float)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_corner_radius(node_id, radius, port):
    """Set corner radius of a node."""
    _design_cmd("corner_radius", {"node_id": node_id, "radius": radius}, port)


@design.command("visible")
@click.argument("node_id")
@click.option("--show/--hide", default=True)
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_visible(node_id, show, port):
    """Show or hide a node."""
    _design_cmd("visible", {"node_id": node_id, "visible": show}, port)


@design.command("clear-page")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_clear_page(port):
    """Remove all nodes from the current page."""
    _design_cmd("clear_page", {}, port)


@design.command("selection")
@click.option("--port", default=7777, type=int, show_default=True)
@handle_error
def design_selection(port):
    """Get the currently selected nodes in Figma."""
    _design_cmd("get_selection", {}, port)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    cli()


if __name__ == "__main__":
    main()
