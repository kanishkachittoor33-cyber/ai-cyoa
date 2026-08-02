"""Persist LLM request/response traces for debugging generation quality."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs" / "llm"
GEN_DIR = ROOT / "logs" / "generations"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]


def log_llm_attempt(
    *,
    trace_id: str,
    model: str,
    system: str,
    user: str,
    raw_content: str | None = None,
    parsed: dict[str, Any] | None = None,
    error: str | None = None,
    http_status: int | None = None,
    openrouter_id: str | None = None,
) -> Path:
    """Write one OpenRouter call (never includes API keys)."""
    path = LOG_DIR / f"{_ts()}_{trace_id}_request.json"
    return _write(
        path,
        {
            "trace_id": trace_id,
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "provider": "openrouter",
            "model": model,
            "request": {
                "system": system,
                "user": user,
            },
            "response": {
                "http_status": http_status,
                "openrouter_id": openrouter_id,
                "raw_content": raw_content,
                "parsed": parsed,
                "error": error,
            },
        },
    )


def log_generation(
    *,
    trace_id: str,
    preview_id: str | None,
    final_spec: dict[str, Any],
    llm_accepted: bool,
    reject_reason: str | None = None,
    llm_path: str | None = None,
) -> Path:
    """Write the scenario the app actually received after generate()."""
    path = GEN_DIR / f"{_ts()}_{trace_id}_generation.json"
    return _write(
        path,
        {
            "trace_id": trace_id,
            "preview_id": preview_id,
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "llm_accepted": llm_accepted,
            "reject_reason": reject_reason,
            "llm_trace_file": llm_path,
            "source": final_spec.get("source"),
            "title": final_spec.get("title"),
            "premise": final_spec.get("premise"),
            "objective": final_spec.get("objective"),
            "spec": final_spec,
        },
    )


def bind_preview_id(trace_id: str | None, preview_id: str) -> None:
    """Attach preview_id to the latest generation log for this trace."""
    if not trace_id or not GEN_DIR.exists():
        return
    matches = sorted(GEN_DIR.glob(f"*_{trace_id}_generation.json"))
    if not matches:
        return
    path = matches[-1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    data["preview_id"] = preview_id
    _write(path, data)
