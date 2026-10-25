"""OpenAI-compatible chat against Nebius Token Factory. The key stays on the server."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_BASE = "https://api.tokenfactory.nebius.com/v1"


class ModelError(Exception):
    def __init__(self, message: str, kind: str = "upstream"):
        super().__init__(message)
        self.kind = kind


def chat(api_key: str, model: str, messages: list[dict], base_url: str = DEFAULT_BASE, transport=None) -> dict:
    if not api_key.strip():
        raise ModelError("NEBIUS_API_KEY is not set", "config")
    url = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "temperature": 0.2,
        "messages": messages,
    }
    raw = json.dumps(body).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    status, payload = (transport or _urllib_transport)(url, headers, raw)
    if status == 401:
        raise ModelError("Token Factory rejected the API key.", "config")
    if status != 200 or not isinstance(payload, dict):
        raise ModelError(f"Token Factory returned HTTP {status}", "upstream")
    choices = payload.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ModelError("Token Factory returned no choices", "upstream")
    message = choices[0].get("message") or {}
    text = message.get("content")
    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
    if not isinstance(text, str) or not text.strip():
        raise ModelError("Token Factory returned an empty reply", "upstream")
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return {"text": text, "model": payload.get("model") or model, "usage": usage}


def _urllib_transport(url: str, headers: dict, raw: bytes) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=raw, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        return error.code, {}
    except urllib.error.URLError as error:
        raise ModelError(f"Could not reach Token Factory: {error.reason}", "upstream") from error
