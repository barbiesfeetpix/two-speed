"""Nano drafts. Super runs only when Nano reports a high-severity behavior bug."""

from __future__ import annotations

import json
import os
import re
import time

NANO = os.environ.get("NEMOTRON_NANO", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
SUPER = os.environ.get("NEMOTRON_SUPER", "nvidia/nemotron-3-super-120b-a12b")
MAX_SOURCE = 12000

NANO_SYSTEM = """You review one Python snippet. Do not run it. Do not suggest network calls, shells, or credentials.
Reply with one JSON object and no markdown:
{"issues":[{"severity":"high","why":"what behavior breaks"}],"needs_super":false,"revision":"the full revised snippet"}
Set needs_super true only when a high issue changes what the code returns or stores. Style nits stay needs_super false.
"""

SUPER_SYSTEM = """You are the second pass. Nano already reviewed this Python. Fix only the behavior bugs Nano listed.
Do not run the code. Reply with one JSON object and no markdown:
{"issues":[{"severity":"high","why":"..."}],"revision":"the full revised snippet"}
"""


def _loads(text: str) -> dict:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.S)
    if fence:
        cleaned = fence.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise json.JSONDecodeError("object required", cleaned, 0)
    return payload


def _issues(payload: dict) -> list[dict]:
    rows = payload.get("issues")
    if not isinstance(rows, list):
        return []
    cleaned = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        severity = str(row.get("severity") or "low").lower()
        if severity not in ("high", "medium", "low"):
            severity = "low"
        why = str(row.get("why") or "").strip()
        if why:
            cleaned.append({"severity": severity, "why": why[:400]})
    return cleaned


def _call(complete, model: str, system: str, user: str) -> dict:
    started = time.perf_counter()
    reply = complete(model, [{"role": "system", "content": system}, {"role": "user", "content": user}])
    elapsed = int((time.perf_counter() - started) * 1000)
    parsed = {}
    error = ""
    try:
        parsed = _loads(reply["text"])
    except json.JSONDecodeError:
        error = "Model did not return JSON."
    revision = str(parsed.get("revision") or "").strip()
    return {
        "model": reply.get("model") or model,
        "ms": elapsed,
        "usage": reply.get("usage") or {},
        "issues": _issues(parsed),
        "revision": revision,
        "needs_super": bool(parsed.get("needs_super")),
        "raw": reply["text"] if error else "",
        "error": error,
    }


def review(source: str, complete) -> dict:
    source = source.strip()
    if not source:
        raise ValueError("Paste a Python snippet.")
    if len(source) > MAX_SOURCE:
        raise ValueError("Snippet is too long.")
    nano = _call(complete, NANO, NANO_SYSTEM, source)
    high = any(issue["severity"] == "high" for issue in nano["issues"])
    route = nano["needs_super"] or high or bool(nano["error"])
    super_pass = None
    if route:
        notes = json.dumps({"issues": nano["issues"], "revision": nano["revision"], "error": nano["error"]})
        super_pass = _call(complete, SUPER, SUPER_SYSTEM, f"Original:\n{source}\n\nNano:\n{notes}")
    final = ""
    if super_pass and super_pass["revision"]:
        final = super_pass["revision"]
    elif nano["revision"]:
        final = nano["revision"]
    return {
        "routed_to_super": super_pass is not None,
        "nano": nano,
        "super": super_pass,
        "final_revision": final,
    }
