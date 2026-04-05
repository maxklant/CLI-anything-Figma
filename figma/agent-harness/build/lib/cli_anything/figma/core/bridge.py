"""WebSocket bridge server — routes CLI design commands to the Figma plugin."""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from typing import Optional

import websockets
from websockets.server import WebSocketServerProtocol

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

HOST = "localhost"
DEFAULT_PORT = 7777
COMMAND_TIMEOUT = 30.0

# ── shared state (reset each server start) ────────────────────────────────────
_plugin_ws: Optional[WebSocketServerProtocol] = None
_pending: dict[str, asyncio.Future] = {}


async def _handle_plugin(ws: WebSocketServerProtocol) -> None:
    global _plugin_ws
    _plugin_ws = ws
    print("[bridge] Figma plugin connected.", flush=True)
    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_id = msg.get("id")
            if msg_id and msg_id in _pending:
                fut = _pending.pop(msg_id)
                if not fut.done():
                    fut.set_result(msg)
    finally:
        if _plugin_ws is ws:
            _plugin_ws = None
        print("[bridge] Figma plugin disconnected.", flush=True)


async def _handle_cli(ws: WebSocketServerProtocol, msg: dict) -> None:
    global _plugin_ws, _pending

    if _plugin_ws is None:
        await ws.send(json.dumps({
            "id": msg.get("id", ""),
            "status": "error",
            "error": "Figma plugin is not connected. Open the CLI-Anything Bridge plugin in Figma first.",
        }))
        return

    msg_id = msg.get("id") or str(uuid.uuid4())
    msg["id"] = msg_id

    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[msg_id] = fut

    try:
        await _plugin_ws.send(json.dumps(msg))
    except Exception as e:
        _pending.pop(msg_id, None)
        await ws.send(json.dumps({
            "id": msg_id, "status": "error",
            "error": f"Failed to forward to plugin: {e}",
        }))
        return

    try:
        result = await asyncio.wait_for(fut, timeout=COMMAND_TIMEOUT)
        await ws.send(json.dumps(result))
    except asyncio.TimeoutError:
        _pending.pop(msg_id, None)
        await ws.send(json.dumps({
            "id": msg_id, "status": "error",
            "error": f"Plugin did not respond within {COMMAND_TIMEOUT}s. Is the plugin open?",
        }))


async def _handler(ws: WebSocketServerProtocol) -> None:
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
    except (asyncio.TimeoutError, websockets.ConnectionClosed):
        return
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return

    if msg.get("type") == "plugin_hello":
        await _handle_plugin(ws)
    else:
        await _handle_cli(ws, msg)


async def serve(port: int = DEFAULT_PORT) -> None:
    async with websockets.serve(_handler, HOST, port):
        print(f"[bridge] Listening on ws://{HOST}:{port}", flush=True)
        print("[bridge] Waiting for Figma plugin to connect...", flush=True)
        print("[bridge] Press Ctrl-C to stop.", flush=True)
        await asyncio.Future()


def run_server(port: int = DEFAULT_PORT) -> None:
    asyncio.run(serve(port))
