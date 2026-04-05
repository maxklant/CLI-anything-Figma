"""Config management for cli-anything-figma.

Config is stored at ~/.cli-anything-figma/config.json.
The FIGMA_TOKEN environment variable overrides the stored token.
"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".cli-anything-figma"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load config from disk. Returns empty dict if file missing."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    """Write config atomically."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def get_token() -> str | None:
    """Return token from env var (highest priority) or config file."""
    env_token = os.environ.get("FIGMA_TOKEN")
    if env_token:
        return env_token
    return load_config().get("token")


def set_token(token: str) -> None:
    cfg = load_config()
    cfg["token"] = token
    save_config(cfg)


def mask_token(token: str) -> str:
    if not token or len(token) < 12:
        return "***"
    return token[:8] + "***" + token[-4:]
