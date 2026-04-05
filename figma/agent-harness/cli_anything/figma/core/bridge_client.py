"""HTTP client — sends a single command to the bridge server and returns the result."""
from __future__ import annotations

from typing import Any

import requests

DEFAULT_URL = "http://localhost:7777"


def send_command(command: str, args: dict[str, Any], url: str = DEFAULT_URL) -> dict:
    """POST a command to the bridge and block until the plugin responds."""
    try:
        resp = requests.post(
            f"{url}/command",
            json={"command": command, "args": args},
            timeout=35,
        )
        return resp.json()
    except requests.ConnectionError:
        return {
            "status": "error",
            "error": (
                "Cannot connect to bridge. "
                "Start it with: python figma.py design serve"
            ),
        }
    except requests.Timeout:
        return {"status": "error", "error": "Timed out waiting for plugin response."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_status(url: str = DEFAULT_URL) -> dict:
    """Check if the bridge is running and whether the plugin is connected."""
    try:
        resp = requests.get(f"{url}/status", timeout=3)
        return resp.json()
    except requests.ConnectionError:
        return {"status": "error", "error": "Bridge server is not running."}
    except Exception as e:
        return {"status": "error", "error": str(e)}
