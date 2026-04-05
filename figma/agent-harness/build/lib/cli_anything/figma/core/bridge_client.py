"""Synchronous client — sends a single command to the bridge server and returns the result."""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from typing import Any

import websockets

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

CONNECT_TIMEOUT = 5.0
RECV_TIMEOUT = 35.0


async def _send(command: str, args: dict, url: str) -> dict:
    try:
        async with websockets.connect(url, open_timeout=CONNECT_TIMEOUT) as ws:
            payload = {"id": str(uuid.uuid4()), "command": command, "args": args}
            await ws.send(json.dumps(payload))
            raw = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
            return json.loads(raw)
    except ConnectionRefusedError:
        return {
            "status": "error",
            "error": (
                "Cannot connect to bridge. "
                "Start it with: python -m cli_anything.figma design serve"
            ),
        }
    except asyncio.TimeoutError:
        return {"status": "error", "error": "Timed out waiting for bridge/plugin response."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def send_command(command: str, args: dict[str, Any], url: str = "ws://localhost:7777") -> dict:
    """Send a command to the bridge server and return the result synchronously."""
    return asyncio.run(_send(command, args, url))


def check_status(url: str = "ws://localhost:7777") -> dict:
    return send_command("plugin_status", {}, url)
