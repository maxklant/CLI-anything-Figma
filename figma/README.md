# cli-anything-figma

> A full-featured CLI harness for Figma — inspect files, export assets, extract design tokens, manage comments, **and create designs live in the Figma canvas**, all from the terminal.

Built on the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) framework.

---

## Table of Contents

- [How It Works (Flowchart)](#how-it-works-flowchart)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Setup](#setup)
- [Command Reference](#command-reference)
  - [config](#config)
  - [file](#file)
  - [export](#export)
  - [component](#component)
  - [style](#style)
  - [comment](#comment)
  - [project](#project)
  - [user](#user)
  - [session](#session)
  - [design](#design) ← **create & edit designs live**
- [Plugin Bridge](#plugin-bridge)
- [Interactive REPL](#interactive-repl)
- [CI/CD Integration](#cicd-integration)
- [Design Token Extraction](#design-token-extraction)
- [Limitations](#limitations)

---

## How It Works (Flowchart)

### REST API path (read / export / comments)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INVOCATION                             │
│   python figma.py [--json] COMMAND [ARGS]                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    figma_cli.py  (Click Root Group)                 │
│                                                                     │
│   No subcommand? ── YES ──► REPL (repl_skin.py + prompt-toolkit)   │
│         │ NO                                                        │
│         ▼                                                           │
│   Route: config │ file │ export │ component │ style │ comment      │
│          project │ user │ session │ design                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                      @handle_error decorator
                  (catches HTTP / Value errors)
                               │
              ┌────────────────┴─────────────────┐
              │ REST path                         │ design path
              ▼                                   ▼
   Session (token, LRU cache,          bridge_client.py
   undo/redo)                          POST http://localhost:7777/command
              │                                   │
              ▼                                   ▼
   FigmaClient → api.figma.com         [see Plugin Bridge flowchart]
              │
              ▼
   Core logic (export / components /
   comments / projects)
              │
              ▼
   output()  ── --json → json.dumps
             └─ default → _print_human
```

### Plugin Bridge path (design commands)

```
python figma.py design frame "Hero" --width 390 --fill "#0D0D1A"
         │
         ▼
  bridge_client.py
  POST http://localhost:7777/command
  {"command":"create_frame","args":{...}}
         │
         ▼
┌─────────────────────────────────────────┐
│   bridge.py  (ThreadingHTTPServer)      │
│                                         │
│   POST /command  ── push to queue       │
│   GET  /poll     ── plugin polls here   │  ◄── Figma plugin ui.html
│   POST /result/  ── plugin posts result │
│   GET  /status   ── health check        │
└──────────┬──────────────────────────────┘
           │ plugin picks up command via /poll
           ▼
  Figma Plugin  ui.html  (fetch loop)
           │ window.parent.postMessage
           ▼
  Figma Plugin  code.js  (main thread)
  figma.createFrame() / figma.createText() / etc.
           │ figma.ui.postMessage (result)
           ▼
  ui.html  POST /result/{id}
           │
           ▼
  bridge.py resolves queue → returns to CLI
           │
           ▼
  output() prints result
```

---

## Architecture

```
figma.py  (root launcher — adds agent-harness to sys.path)
     │
     ▼
figma_cli.py
     │
     ├── utils/config.py        token from ~/.cli-anything-figma/config.json
     │                          or FIGMA_TOKEN env var
     ├── core/session.py        LRU cache (100), undo/redo (50), token header
     ├── core/client.py         all REST → https://api.figma.com/v1
     │
     ├── core/export.py         render + download to disk
     ├── core/components.py     components, design tokens, styles
     ├── core/comments.py       comment CRUD
     ├── core/projects.py       teams / projects / files
     │
     ├── core/bridge.py         HTTP server (localhost:7777) — design bridge
     ├── core/bridge_client.py  POST commands to bridge, return result
     │
     └── utils/formatting.py   token → CSS/SCSS, node tree, slugify

plugin/
     ├── manifest.json          Figma plugin registration
     ├── code.js                plugin main thread — all figma.* API calls
     └── ui.html                plugin UI thread — HTTP fetch/poll loop
```

---

## Project Structure

```
figma/
├── README.md                               ← you are here
├── plugin/                                 ← Figma plugin (import in Figma)
│   ├── manifest.json
│   ├── code.js                             ← executes figma.* API calls
│   └── ui.html                             ← HTTP bridge (fetch/poll loop)
└── agent-harness/
    ├── setup.py
    ├── FIGMA.md
    └── cli_anything/
        └── figma/
            ├── figma_cli.py                ← root CLI + all 10 command groups
            ├── core/
            │   ├── session.py
            │   ├── client.py
            │   ├── export.py
            │   ├── components.py
            │   ├── comments.py
            │   ├── projects.py
            │   ├── bridge.py               ← HTTP bridge server
            │   └── bridge_client.py        ← HTTP command sender
            ├── utils/
            │   ├── config.py
            │   ├── formatting.py
            │   └── repl_skin.py
            └── skills/
                └── SKILL.md
```

---

## Installation

```bash
# From the project root
cd figma/agent-harness
pip install -e .

# Dependencies
pip install websockets   # only needed for bridge server
```

Or run directly from the project root using the launcher:

```bash
python figma.py --help
```

---

## Setup

### 1. Get a Figma Personal Access Token

1. Open Figma → avatar → **Settings → Personal access tokens**
2. Click **Generate new token** → copy it (starts with `figd_`)

### 2. Store the token

```bash
python figma.py config set-token figd_xxxxxxxxxxxx
# or
export FIGMA_TOKEN=figd_xxxxxxxxxxxx
```

### 3. Find your File Key

```
https://www.figma.com/file/AbCdEfGhIjKl/My-File
                           ^^^^^^^^^^^^
                           FILE_KEY
```

---

## Command Reference

```bash
python figma.py [--json] COMMAND SUBCOMMAND [ARGS] [OPTIONS]
```

---

### config

```bash
python figma.py config set-token figd_xxxx
python figma.py config show
```

---

### file

```bash
python figma.py file info FILE_KEY
python figma.py file pages FILE_KEY
python figma.py file nodes FILE_KEY [--depth 5] [--node-id ID]
python figma.py file versions FILE_KEY [--limit 50]
```

---

### export

```bash
# Export specific nodes by ID (comma-separated)
python figma.py export frame FILE_KEY "1:2,1:5" --format svg --scale 2 --output-dir ./dist

# Batch export all frames
python figma.py export batch FILE_KEY --output-dir ./assets --filter-type FRAME

# Download embedded image fills
python figma.py export fills FILE_KEY --output-dir ./images
```

---

### component

```bash
python figma.py component list FILE_KEY [--include-sets]
python figma.py component sets FILE_KEY
python figma.py component info COMPONENT_KEY
python figma.py component tokens FILE_KEY --format css --output-file tokens.css
```

---

### style

```bash
python figma.py style list FILE_KEY [--type fill|text|effect|grid|all]
python figma.py style info STYLE_KEY
```

---

### comment

```bash
python figma.py comment list FILE_KEY [--resolved]
python figma.py comment post FILE_KEY "message" [--reply-to ID]
python figma.py comment delete FILE_KEY COMMENT_ID
```

---

### project

```bash
python figma.py project team TEAM_ID
python figma.py project files PROJECT_ID [--branch-data]
```

---

### user

```bash
python figma.py user me
```

---

### session

```bash
python figma.py session status
python figma.py session clear-cache
python figma.py session history
python figma.py session undo
python figma.py session redo
```

---

### design

Create and modify nodes directly on the Figma canvas. Requires the **plugin bridge** to be running (see [Plugin Bridge](#plugin-bridge)).

```bash
# Bridge control
python figma.py design serve [--port 7777]    # start bridge server (blocking)
python figma.py design status                  # check plugin connection

# Create nodes
python figma.py design frame NAME [--width 1440] [--height 900] [--fill #hex] [--corner-radius N] [--x N] [--y N] [--parent-id ID]
python figma.py design text CONTENT [--font-size 16] [--color #hex] [--font-family Inter] [--bold] [--x N] [--y N] [--parent-id ID]
python figma.py design rect [--name] [--width] [--height] [--x] [--y] [--fill #hex] [--stroke #hex] [--corner-radius N] [--parent-id ID]
python figma.py design ellipse [--name] [--width] [--height] [--x] [--y] [--fill #hex] [--parent-id ID]
python figma.py design component NAME [--width] [--height] [--fill #hex]
python figma.py design instance COMPONENT_ID [--x] [--y] [--parent-id ID]

# Layout
python figma.py design auto-layout NODE_ID [--direction horizontal|vertical] [--gap N] [--padding N] [--align start|center|end]

# Mutate existing nodes
python figma.py design move NODE_ID --x N --y N
python figma.py design resize NODE_ID --width N --height N
python figma.py design fill NODE_ID --color #hex
python figma.py design stroke NODE_ID --color #hex [--weight N]
python figma.py design font NODE_ID [--size N] [--family Inter] [--weight Bold] [--color #hex]
python figma.py design opacity NODE_ID --value 0.8
python figma.py design corner-radius NODE_ID --radius N
python figma.py design rename NODE_ID NEW_NAME
python figma.py design duplicate NODE_ID [--x N] [--y N]
python figma.py design visible NODE_ID [--show / --hide]
python figma.py design select NODE_ID
python figma.py design delete NODE_ID

# Page
python figma.py design clear-page
python figma.py design selection
```

---

## Plugin Bridge

The `design` commands work by talking to a small Figma plugin that runs inside the app. The plugin executes `figma.*` API calls (create, move, delete, etc.) and reports back results.

### How it works

```
Terminal 1                Terminal 2               Figma App
──────────                ──────────               ─────────
python figma.py    ──►  HTTP :7777  ◄──────────  plugin ui.html
design frame "X"        bridge.py   long-poll     (fetch loop)
                            │
                            └──► plugin code.js
                                 figma.createFrame()
                                 ◄── result ──────────────────
```

### Setup

**Step 1 — Start the bridge** (keep this terminal open):
```bash
python figma.py design serve
# [bridge] HTTP server listening on http://localhost:7777
# [bridge] Waiting for Figma plugin to connect...
```

**Step 2 — Load the plugin in Figma:**
1. Plugins → Development → **Import plugin from manifest**
2. Select `figma/plugin/manifest.json`
3. Run the plugin — panel turns **green** when connected

**Step 3 — Design from the CLI:**
```bash
python figma.py design status
# plugin_connected: True

python figma.py --json design frame "Dashboard" --width 390 --height 844 --fill "#0D0D1A"
# {"status": "ok", "node_id": "123:4", "name": "Dashboard"}

python figma.py design text "Good morning" --font-size 32 --color "#FFFFFF" --bold --x 24 --y 80 --parent-id "123:4"
```

### Full sleep tracker example

```bash
F=$(python figma.py --json design frame "Home Screen" --width 390 --height 844 --fill "#0D0D1A" | python -c "import sys,json; print(json.load(sys.stdin)['node_id'])")

python figma.py design text "Noctis" --font-size 32 --color "#FFFFFF" --bold --x 24 --y 76 --parent-id $F
python figma.py design rect --name "Score Card" --width 342 --height 230 --x 24 --y 148 --fill "#1A1A2E" --corner-radius 24 --parent-id $F
python figma.py design ellipse --name "Score Ring" --width 120 --height 120 --x 110 --y 178 --fill "#6C63FF" --parent-id $F
python figma.py design text "87" --font-size 36 --color "#FFFFFF" --bold --x 155 --y 216 --parent-id $F
```

---

## Interactive REPL

```bash
python figma.py
```

Launches the interactive REPL with banner, command history, and inline error handling. All commands work identically to CLI mode.

---

## CI/CD Integration

```yaml
# .github/workflows/design-sync.yml
- name: Export all frames as SVG
  env:
    FIGMA_TOKEN: ${{ secrets.FIGMA_TOKEN }}
  run: |
    python figma.py --json export batch $FILE_KEY \
      --format svg --output-dir src/assets/

- name: Extract design tokens
  run: |
    python figma.py component tokens $FILE_KEY \
      --format css --output-file src/styles/tokens.css
```

---

## Design Token Extraction

```bash
python figma.py component tokens FILE_KEY --format json   # default
python figma.py component tokens FILE_KEY --format css    # CSS :root vars
python figma.py component tokens FILE_KEY --format scss   # SCSS $vars
python figma.py component tokens FILE_KEY --format css --output-file tokens.css
```

Sources: `/v1/files/:key/variables/local` (Enterprise) + `/v1/files/:key/styles` (all plans).

---

## Limitations

| Limitation | Detail |
|---|---|
| Design commands need plugin | The `design` group requires Figma app open with the plugin running |
| REST API read-mostly | Without plugin bridge, REST API cannot create/modify design elements |
| Variables API | Full token extraction requires Figma Enterprise; gracefully degrades to styles-only |
| Rate limits | Figma REST API is rate-limited; LRU cache reduces repeat calls |
| Plugin is local-only | Bridge server runs on localhost — not usable in headless CI for design creation |
