"""Review server. Inference runs on Nebius Token Factory."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from two_speed.agent import review
from two_speed.client import ModelError, chat

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
MAX_BODY = 20000


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


load_env(ROOT / ".env")


def complete(model: str, messages: list[dict]) -> dict:
    return chat(
        os.environ.get("NEBIUS_API_KEY", ""),
        model,
        messages,
        os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1"),
    )


class Handler(BaseHTTPRequestHandler):
    completer = staticmethod(complete)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._json(200, {"ok": True, "token_factory": bool(os.environ.get("NEBIUS_API_KEY", "").strip())})
        if path == "/":
            return self._file(STATIC / "index.html", "text/html; charset=utf-8")
        if path.startswith("/static/"):
            name = path.removeprefix("/static/")
            if "/" in name or name.startswith("."):
                return self._json(404, {"error": "Not found"})
            kind = "text/css; charset=utf-8" if name.endswith(".css") else "text/javascript; charset=utf-8"
            return self._file(STATIC / name, kind)
        return self._json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/review":
            return self._json(404, {"error": "Not found"})
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._json(400, {"error": "Paste a short snippet.", "kind": "input"})
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._json(400, {"error": "Body must be JSON.", "kind": "input"})
        try:
            result = review(str(body.get("source") or ""), self.completer)
        except ValueError as error:
            return self._json(400, {"error": str(error), "kind": "input"})
        except ModelError as error:
            status = 400 if error.kind == "config" else 502
            return self._json(status, {"error": str(error), "kind": error.kind})
        return self._json(200, result)

    def _json(self, status: int, payload: dict):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _file(self, path: Path, content_type: str):
        if not path.is_file():
            return self._json(404, {"error": "Not found"})
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args):
        return


def main():
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
