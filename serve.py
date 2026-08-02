#!/usr/bin/env python3
"""Stdlib HTTP server: browser UI + JSON game API."""

from __future__ import annotations

import json
import sys
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cyoa.game import create_game, create_game_from_spec
from cyoa.generate import generate_scenario, load_dotenv, preview_from_spec
from cyoa.observability import bind_preview_id

load_dotenv(ROOT / ".env")

from cyoa.save import (
    adventure_card,
    build_save_payload,
    delete_save,
    list_saves,
    read_save,
    restore_game_from_save,
    write_save,
)
from cyoa.types import GameStatus

SESSIONS: dict[str, object] = {}
PREVIEWS: dict[str, dict] = {}
# adventure_id -> session_id for open tabs
ADVENTURE_SESSIONS: dict[str, str] = {}


def _json_response(handler: SimpleHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _start_session(game, adventure_id: str | None = None) -> dict:
    sid = str(uuid.uuid4())
    aid = adventure_id or game.adventure_id or str(uuid.uuid4())
    game.adventure_id = aid
    SESSIONS[sid] = game
    ADVENTURE_SESSIONS[aid] = sid
    snap = game.snapshot()
    card = adventure_card(game, aid, sid)
    return {"session_id": sid, "adventure": card, **snap}


def _open_sessions_cards() -> list[dict]:
    cards = []
    for aid, sid in list(ADVENTURE_SESSIONS.items()):
        game = SESSIONS.get(sid)
        if not game:
            ADVENTURE_SESSIONS.pop(aid, None)
            continue
        cards.append(adventure_card(game, aid, sid))
    return cards


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)

        if path == "/api/adventures":
            open_cards = _open_sessions_cards()
            open_ids = {c["id"] for c in open_cards}
            saved = [s for s in list_saves() if s["id"] not in open_ids]
            _json_response(
                self,
                200,
                {"open": open_cards, "saved": saved},
            )
            return

        if path == "/api/new":
            scenario = (query.get("scenario") or ["lost_in_the_woods"])[0]
            game = create_game(scenario)
            _json_response(self, 200, _start_session(game))
            return

        if path.startswith("/api/state/"):
            sid = path.rsplit("/", 1)[-1]
            game = SESSIONS.get(sid)
            if not game:
                _json_response(self, 404, {"error": "session not found"})
                return
            card = adventure_card(game, game.adventure_id or "", sid)
            _json_response(self, 200, {"session_id": sid, "adventure": card, **game.snapshot()})
            return

        if path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            _json_response(self, 400, {"error": "invalid json"})
            return

        if path == "/api/generate":
            try:
                spec = generate_scenario(prefer_llm=True)
            except Exception as exc:  # noqa: BLE001
                _json_response(self, 500, {"error": str(exc)})
                return
            preview_id = str(uuid.uuid4())
            PREVIEWS[preview_id] = spec
            bind_preview_id(spec.get("trace_id"), preview_id)
            _json_response(
                self,
                200,
                {
                    "preview_id": preview_id,
                    "trace_id": spec.get("trace_id"),
                    **preview_from_spec(spec),
                },
            )
            return

        if path == "/api/start":
            scenario = data.get("scenario")
            preview_id = data.get("preview_id")
            if preview_id:
                spec = PREVIEWS.get(preview_id)
                if not spec:
                    _json_response(self, 404, {"error": "preview expired — generate again"})
                    return
                try:
                    game = create_game_from_spec(spec)
                except Exception as exc:  # noqa: BLE001
                    _json_response(self, 400, {"error": f"invalid scenario: {exc}"})
                    return
                _json_response(self, 200, _start_session(game))
                return
            if scenario:
                try:
                    game = create_game(scenario)
                except ValueError as exc:
                    _json_response(self, 400, {"error": str(exc)})
                    return
                _json_response(self, 200, _start_session(game))
                return
            _json_response(self, 400, {"error": "scenario or preview_id required"})
            return

        if path == "/api/act":
            sid = data.get("session_id")
            action_id = data.get("action_id")
            game = SESSIONS.get(sid)
            if not game:
                _json_response(self, 404, {"error": "session not found"})
                return
            if game.status != GameStatus.PLAYING:
                card = adventure_card(game, game.adventure_id or "", sid)
                _json_response(
                    self,
                    200,
                    {
                        "session_id": sid,
                        "adventure": card,
                        "message": "Game over.",
                        **game.snapshot(),
                    },
                )
                return
            message = game.act(action_id)
            card = adventure_card(game, game.adventure_id or "", sid)
            # autosave progress to disk when adventure has an id
            if game.adventure_id:
                write_save(build_save_payload(game, game.adventure_id))
            _json_response(
                self,
                200,
                {
                    "session_id": sid,
                    "adventure": card,
                    "message": message,
                    **game.snapshot(),
                },
            )
            return

        if path == "/api/adventures/save":
            sid = data.get("session_id")
            game = SESSIONS.get(sid)
            if not game:
                _json_response(self, 404, {"error": "session not found"})
                return
            payload = build_save_payload(game, game.adventure_id)
            game.adventure_id = payload["id"]
            ADVENTURE_SESSIONS[payload["id"]] = sid
            write_save(payload)
            card = adventure_card(game, payload["id"], sid)
            _json_response(self, 200, {"ok": True, "adventure": card})
            return

        if path == "/api/adventures/switch":
            adventure_id = data.get("adventure_id")
            if not adventure_id:
                _json_response(self, 400, {"error": "adventure_id required"})
                return
            # Prefer live session
            sid = ADVENTURE_SESSIONS.get(adventure_id)
            if sid and sid in SESSIONS:
                game = SESSIONS[sid]
                card = adventure_card(game, adventure_id, sid)
                _json_response(
                    self, 200, {"session_id": sid, "adventure": card, **game.snapshot()}
                )
                return
            # Load from disk
            try:
                saved = read_save(adventure_id)
            except FileNotFoundError:
                _json_response(self, 404, {"error": "adventure not found"})
                return
            game = restore_game_from_save(saved)
            _json_response(self, 200, _start_session(game, adventure_id))
            return

        if path == "/api/adventures/delete":
            adventure_id = data.get("adventure_id")
            if not adventure_id:
                _json_response(self, 400, {"error": "adventure_id required"})
                return
            sid = ADVENTURE_SESSIONS.pop(adventure_id, None)
            if sid:
                SESSIONS.pop(sid, None)
            delete_save(adventure_id)
            _json_response(self, 200, {"ok": True})
            return

        _json_response(self, 404, {"error": "not found"})


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"CYOA — http://127.0.0.1:{port}")
    print("Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
