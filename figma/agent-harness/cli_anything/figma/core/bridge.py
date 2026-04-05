"""HTTP bridge server — routes CLI design commands to the Figma plugin via HTTP polling."""
from __future__ import annotations

import json
import queue
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "localhost"
DEFAULT_PORT = 7777

# ── shared state ──────────────────────────────────────────────────────────────
_pending_commands: queue.Queue = queue.Queue()          # commands waiting for plugin
_pending_results: dict[str, queue.Queue] = {}           # id → result queue
_plugin_connected = threading.Event()


class _BridgeHandler(BaseHTTPRequestHandler):

    # ── CORS preflight ────────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self._cors(200)

    # ── GET endpoints ─────────────────────────────────────────────────────────
    def do_GET(self):
        if self.path == "/poll":
            # Plugin long-polls for the next command (blocks up to 25s)
            _plugin_connected.set()
            try:
                cmd = _pending_commands.get(timeout=25)
                self._json(200, cmd)
            except queue.Empty:
                self._json(204, {})

        elif self.path in ("/", ""):
            self._json(200, {"service": "cli-anything-figma bridge", "status": "running"})

        elif self.path == "/status":
            self._json(200, {
                "status": "ok",
                "plugin_connected": _plugin_connected.is_set(),
                "pending_commands": _pending_commands.qsize(),
                "pending_results": len(_pending_results),
            })

        else:
            self._json(404, {"error": "Not found"})

    # ── POST endpoints ────────────────────────────────────────────────────────
    def do_POST(self):
        body = self._read_body()

        if self.path == "/command":
            # CLI submitting a command — wait for plugin to execute and return result
            if not _plugin_connected.is_set():
                self._json(503, {
                    "status": "error",
                    "error": "Figma plugin is not connected. Open the CLI-Anything Bridge plugin in Figma first.",
                })
                return

            cmd_id = str(uuid.uuid4())
            body["id"] = cmd_id
            result_q: queue.Queue = queue.Queue()
            _pending_results[cmd_id] = result_q
            _pending_commands.put(body)

            try:
                result = result_q.get(timeout=30)
                self._json(200, result)
            except queue.Empty:
                self._json(408, {"id": cmd_id, "status": "error",
                                  "error": "Plugin did not respond within 30s."})
            finally:
                _pending_results.pop(cmd_id, None)

        elif self.path.startswith("/result/"):
            # Plugin posting a command result
            cmd_id = self.path.split("/result/", 1)[-1]
            if cmd_id in _pending_results:
                _pending_results[cmd_id].put(body)
            self._json(200, {"ok": True})

        else:
            self._json(404, {"error": "Not found"})

    # ── helpers ───────────────────────────────────────────────────────────────
    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            try:
                return json.loads(self.rfile.read(length))
            except Exception:
                pass
        return {}

    def _cors(self, code: int):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, code: int, data: dict):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if data:  # don't write body for 204
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Only log plugin connection events, not every poll
        if "/result/" in (args[0] if args else ""):
            pass
        elif "/poll" not in (args[0] if args else ""):
            print(f"[bridge] {fmt % args}", flush=True)


def run_server(port: int = DEFAULT_PORT) -> None:
    """Start the HTTP bridge server (blocking)."""
    _plugin_connected.clear()
    server = ThreadingHTTPServer((HOST, port), _BridgeHandler)
    print(f"[bridge] HTTP server listening on http://{HOST}:{port}", flush=True)
    print("[bridge] Open the CLI-Anything Bridge plugin in Figma to connect.", flush=True)
    print("[bridge] Press Ctrl-C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bridge] Stopped.", flush=True)
        server.shutdown()
