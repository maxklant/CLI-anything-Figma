# CLI-anything-Figma

A command-line interface for Figma. Drive your designs from the terminal — or let an agent like Claude Code do it for you — through a Figma bridge.

## What it does

Most design work lives behind a GUI. `CLI-anything-Figma` exposes Figma as a scriptable surface so you can:

- Create, edit, and inspect Figma files from the terminal
- Pipe design operations through standard Unix tools
- Let coding agents (Claude Code, Cursor, etc.) read and manipulate Figma directly without leaving the editor

It's part of a broader "CLI anything" pattern — turning visual tools into composable text-first interfaces.

## How it works

The CLI talks to Figma through a bridge process. The launcher (`figma.py`) bootstraps the `cli_anything` harness from `figma/agent-harness/` and dispatches commands to the Figma plugin layer.

```
figma.py  →  figma/agent-harness/cli_anything/figma/figma_cli.py  →  Figma bridge
```

## Quick start

```bash
# Clone
git clone https://github.com/maxklant/CLI-anything-Figma.git
cd CLI-anything-Figma

# Run
python figma.py --help
```

Requirements:
- Python 3.10+
- A running Figma desktop app with the bridge plugin connected

## Usage with Claude Code

The CLI is designed to be agent-friendly. Point Claude Code at the repo and ask it to:
- "Create a new frame with three buttons"
- "Rename every layer matching `btn-*` to `button-*`"
- "Export every component on the current page as PNG"

The agent calls `python figma.py ...` and reads the structured output.

## Status

Active development. APIs may change between commits — pin to a SHA if you build on it.

## License

MIT — see `LICENSE` once added.
