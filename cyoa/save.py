"""Serialize / restore adventure progress for mid-run saves."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from .game import Game, create_game, create_game_from_spec
from .types import CharacterState, GameState, GameStatus, Item, ItemKind

SAVES_DIR = Path(__file__).resolve().parent.parent / "saves"


def ensure_saves_dir() -> Path:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)
    return SAVES_DIR


def _serialize_state(state: GameState) -> dict[str, Any]:
    return {
        "t": state.t,
        "status": state.status.value,
        "unlocked_action_ids": sorted(state.unlocked_action_ids),
        "opened_gates": sorted(state.opened_gates),
        "flags": sorted(state.flags),
        "log": list(state.log),
        "rng_seed": state.rng_seed,
        "character": {
            "health": state.character.health,
            "satiation": state.character.satiation,
            "energy": state.character.energy,
            "location_id": state.character.location_id,
            "item_ids": [i.id for i in state.character.items],
        },
        "world_items": {k: v.to_dict() for k, v in state.world_items.items()},
    }


def _item_from_dict(data: dict[str, Any]) -> Item:
    return Item(
        id=data["id"],
        name=data["name"],
        kind=ItemKind(data.get("kind", "tool")),
        satiation_restore=int(data.get("satiation_restore", 0)),
        energy_restore=int(data.get("energy_restore", 0)),
        health_restore=int(data.get("health_restore", 0)),
        description=data.get("description", ""),
        sharpened=bool(data.get("sharpened", False)),
    )


def apply_saved_state(game: Game, blob: dict[str, Any]) -> Game:
    world = {
        iid: _item_from_dict(d) for iid, d in (blob.get("world_items") or {}).items()
    }
    ch = blob["character"]
    items = []
    for iid in ch.get("item_ids") or []:
        if iid in world:
            items.append(world[iid])
    character = CharacterState(
        health=int(ch["health"]),
        satiation=int(ch["satiation"]),
        energy=int(ch["energy"]),
        location_id=ch["location_id"],
        items=items,
    )
    game.state = GameState(
        t=int(blob["t"]),
        character=character,
        status=GameStatus(blob.get("status", "playing")),
        unlocked_action_ids=set(blob.get("unlocked_action_ids") or []),
        opened_gates=set(blob.get("opened_gates") or []),
        flags=set(blob.get("flags") or []),
        log=list(blob.get("log") or []),
        world_items=world or game.state.world_items,
        rng_seed=blob.get("rng_seed"),
    )
    return game


def adventure_card(game: Game, adventure_id: str, session_id: str | None = None) -> dict:
    area = game.current_area()
    return {
        "id": adventure_id,
        "session_id": session_id,
        "title": game.title,
        "area_name": area.name,
        "t": game.state.t,
        "status": game.status.value,
        "health": game.state.character.health,
        "scenario_id": game.scenario_id,
    }


def build_save_payload(game: Game, adventure_id: str | None = None) -> dict[str, Any]:
    aid = adventure_id or str(uuid.uuid4())
    return {
        "id": aid,
        "title": game.title,
        "premise": game.premise,
        "objective": game.objective,
        "scenario_id": game.scenario_id,
        "spec": game.spec,
        "saved_at": time.time(),
        "state": _serialize_state(game.state),
        "summary": {
            "area_name": game.current_area().name,
            "t": game.state.t,
            "status": game.status.value,
            "health": game.state.character.health,
        },
    }


def write_save(payload: dict[str, Any]) -> Path:
    ensure_saves_dir()
    path = SAVES_DIR / f"{payload['id']}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_save(adventure_id: str) -> dict[str, Any]:
    path = SAVES_DIR / f"{adventure_id}.json"
    if not path.exists():
        raise FileNotFoundError(adventure_id)
    return json.loads(path.read_text(encoding="utf-8"))


def delete_save(adventure_id: str) -> bool:
    path = SAVES_DIR / f"{adventure_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


def list_saves() -> list[dict[str, Any]]:
    ensure_saves_dir()
    cards = []
    for path in sorted(SAVES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        summary = data.get("summary") or {}
        cards.append(
            {
                "id": data.get("id", path.stem),
                "title": data.get("title", "Adventure"),
                "area_name": summary.get("area_name", "?"),
                "t": summary.get("t", 0),
                "status": summary.get("status", "playing"),
                "health": summary.get("health"),
                "saved_at": data.get("saved_at"),
                "scenario_id": data.get("scenario_id"),
                "persisted": True,
            }
        )
    return cards


def restore_game_from_save(data: dict[str, Any]) -> Game:
    if data.get("spec"):
        game = create_game_from_spec(data["spec"])
    elif data.get("scenario_id"):
        game = create_game(data["scenario_id"])
    else:
        game = create_game("lost_in_the_woods")
    game.title = data.get("title", game.title)
    game.premise = data.get("premise", game.premise)
    game.objective = data.get("objective", game.objective)
    game.adventure_id = data.get("id")
    return apply_saved_state(game, data["state"])
