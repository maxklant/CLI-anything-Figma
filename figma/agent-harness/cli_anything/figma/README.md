# cli-anything-figma

A CLI harness for Figma — inspect design files, export assets, manage comments, and extract design tokens, all from the terminal.

## Installation

```bash
cd figma/agent-harness
pip install -e .
```

## Quick Start

```bash
# 1. Set your Figma personal access token
#    Generate one at: https://www.figma.com/settings (Personal access tokens)
cli-anything-figma config set-token figd_xxxxxxxxxxxx

# Or use the environment variable (recommended for CI):
export FIGMA_TOKEN=figd_xxxxxxxxxxxx

# 2. Inspect a file (get the key from the URL: figma.com/file/KEY/...)
cli-anything-figma file info AbCdEfGhIjKl

# 3. Enter interactive REPL
cli-anything-figma
```

## Features

- **File inspection** — metadata, pages, full layer/node tree, version history
- **Asset export** — frames, components, or entire pages as PNG/SVG/PDF/JPG at any scale
- **Batch export** — auto-discover and export all frames in one command
- **Design tokens** — extract colors, typography, and effects as JSON, CSS, or SCSS
- **Components** — list, inspect, and query component sets and variants
- **Comments** — list, post, reply, and delete
- **Projects** — browse team projects and file lists
- **CI/CD ready** — `--json` flag, `FIGMA_TOKEN` env var, exit codes

## Usage

```
cli-anything-figma [--json] COMMAND [ARGS]...

Commands:
  config     Manage CLI configuration
  file       Inspect files, pages, and layer trees
  export     Export frames, batch assets, or image fills
  component  List components, sets, and extract tokens
  style      List and inspect published styles
  comment    Read and post comments
  project    Browse teams and projects
  user       Current user profile
  session    Cache, undo/redo, history
```

Run any command with `--help` for full option details.

## Finding Your File Key

The file key is the string in your Figma URL:

```
https://www.figma.com/file/AbCdEfGhIjKl/My-Design-File
                           ^^^^^^^^^^^^
                           This is your FILE_KEY
```

## CI/CD Example

```yaml
# .github/workflows/export-assets.yml
- name: Export Figma assets
  env:
    FIGMA_TOKEN: ${{ secrets.FIGMA_TOKEN }}
  run: |
    pip install cli-anything-figma
    cli-anything-figma --json export batch $FILE_KEY \
      --format svg \
      --output-dir src/assets/
    cli-anything-figma component tokens $FILE_KEY \
      --format css \
      --output-file src/styles/tokens.css
```
