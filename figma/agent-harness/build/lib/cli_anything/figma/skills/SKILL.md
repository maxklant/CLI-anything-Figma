---
name: figma
version: 1.0.0
description: CLI harness for Figma — design file inspection, export, and collaboration via the Figma REST API
tags: [design, figma, export, tokens, components, comments]
entry_point: cli-anything-figma
---

# Figma CLI

A full-featured CLI for interacting with Figma files via the official REST API.

## Setup

```bash
cli-anything-figma config set-token YOUR_TOKEN
# Or export FIGMA_TOKEN=YOUR_TOKEN
```

## Command Reference

### config
| Command | Description |
|---|---|
| `config set-token TOKEN` | Store Figma personal access token |
| `config show` | Show current config (token masked) |

### file
| Command | Description |
|---|---|
| `file info FILE_KEY` | File metadata: name, version, pages, last modified |
| `file pages FILE_KEY` | List all pages |
| `file nodes FILE_KEY [--depth N] [--node-id ID]` | Print layer/node tree |
| `file versions FILE_KEY [--limit N]` | Version history |

### export
| Command | Description |
|---|---|
| `export frame FILE_KEY NODE_IDS [--format png\|svg\|pdf\|jpg] [--scale N] [--output-dir DIR]` | Export specific nodes |
| `export batch FILE_KEY [--format] [--scale] [--output-dir] [--filter-type FRAME]` | Batch-export all nodes of a type |
| `export fills FILE_KEY [--output-dir DIR]` | Download all image fill assets |

### component
| Command | Description |
|---|---|
| `component list FILE_KEY [--include-sets]` | List published components |
| `component sets FILE_KEY` | List component sets (variant groups) |
| `component info COMPONENT_KEY` | Full metadata for a component |
| `component tokens FILE_KEY [--format json\|css\|scss] [--output-file PATH]` | Extract design tokens |

### style
| Command | Description |
|---|---|
| `style list FILE_KEY [--type fill\|text\|effect\|grid\|all]` | List published styles |
| `style info STYLE_KEY` | Full metadata for a style |

### comment
| Command | Description |
|---|---|
| `comment list FILE_KEY [--resolved]` | List comments |
| `comment post FILE_KEY MESSAGE [--reply-to ID]` | Post a comment |
| `comment delete FILE_KEY COMMENT_ID` | Delete a comment |

### project
| Command | Description |
|---|---|
| `project team TEAM_ID` | List projects in a team |
| `project files PROJECT_ID [--branch-data]` | List files in a project |

### user
| Command | Description |
|---|---|
| `user me` | Show authenticated user profile |

### session
| Command | Description |
|---|---|
| `session status` | Token, cache, undo depth |
| `session clear-cache` | Wipe response cache |
| `session history` | Command history |
| `session undo` | Undo last state-mutating command |
| `session redo` | Redo last undone command |

## Global Flags
- `--json` — Output all results as JSON (machine-readable, for CI/CD pipelines)

## CI/CD Usage

```bash
# Export all frames on every push
export FIGMA_TOKEN=${{ secrets.FIGMA_TOKEN }}
cli-anything-figma --json export batch $FILE_KEY --format svg --output-dir dist/assets/

# Extract design tokens to CSS
cli-anything-figma component tokens $FILE_KEY --format css --output-file src/tokens.css

# Export specific frames
cli-anything-figma --json export frame $FILE_KEY "1:2,1:3,1:4" --format png --scale 2
```
