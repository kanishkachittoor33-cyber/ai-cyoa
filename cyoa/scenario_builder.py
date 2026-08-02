"""Build a playable Game from a JSON-serializable scenario spec."""

from __future__ import annotations

from typing import Any

from .types import (
    ActionKind,
    Area,
    AreaAction,
    ChanceOutcome,
    CharacterState,
    ClockConfig,
    GameState,
    GateStatus,
    Item,
    ItemKind,
    LoadoutChance,
    MapGraph,
    TransitionGate,
)


def _item(data: dict[str, Any]) -> Item:
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


def _gate(data: dict[str, Any] | None) -> TransitionGate | None:
    if not data:
        return None
    return TransitionGate(
        status=GateStatus(data.get("status", "open")),
        requires_tool_id=data.get("requires_tool_id") or data.get("requires_item_id"),
        requires_any_item_ids=tuple(data.get("requires_any_item_ids") or ()),
        energy_cost=int(data.get("energy_cost", 0)),
        min_energy=int(data.get("min_energy", 0)),
    )


def _outcome(data: dict[str, Any] | None) -> ChanceOutcome | None:
    if not data:
        return None
    transform = data.get("transform_item")
    transform_t = tuple(transform) if transform else None
    return ChanceOutcome(
        narrative=data.get("narrative", ""),
        health_delta=int(data.get("health_delta", 0)),
        satiation_delta=int(data.get("satiation_delta", 0)),
        energy_delta=int(data.get("energy_delta", 0)),
        target_area_id=data.get("target_area_id"),
        grant_item_id=data.get("grant_item_id"),
        remove_item_ids=tuple(data.get("remove_item_ids") or ()),
        transform_item=transform_t,  # type: ignore[arg-type]
        set_flags=tuple(data.get("set_flags") or ()),
        unlock_action_ids=tuple(data.get("unlock_action_ids") or ()),
        win=bool(data.get("win", False)),
        lose=bool(data.get("lose", False)),
    )


def _action(data: dict[str, Any]) -> AreaAction:
    kind = ActionKind(data.get("kind", "universal"))
    transform = data.get("transform_item")
    loadouts = tuple(
        LoadoutChance(tuple(L["item_ids"]), float(L["chance"]))
        for L in (data.get("loadout_chances") or [])
    )
    gate = _gate(data.get("gate"))
    if kind == ActionKind.TRANSITION and gate is None:
        gate = TransitionGate(status=GateStatus.OPEN)

    return AreaAction(
        id=data["id"],
        label=data["label"],
        kind=kind,
        narrative=data.get("narrative", ""),
        energy_cost=int(data.get("energy_cost", 0)),
        required_tool_id=data.get("required_tool_id"),
        required_any_item_ids=tuple(data.get("required_any_item_ids") or ()),
        target_area_id=data.get("target_area_id"),
        gate=gate,
        grant_item_id=data.get("grant_item_id"),
        consume_item_id=data.get("consume_item_id"),
        transform_item=tuple(transform) if transform else None,  # type: ignore[arg-type]
        health_delta=int(data.get("health_delta", 0)),
        satiation_delta=int(data.get("satiation_delta", 0)),
        energy_delta=int(data.get("energy_delta", 0)),
        unlock_action_ids=tuple(data.get("unlock_action_ids") or ()),
        set_flags=tuple(data.get("set_flags") or ()),
        require_flags=tuple(data.get("require_flags") or ()),
        forbid_flags=tuple(data.get("forbid_flags") or ()),
        once_flag=data.get("once_flag"),
        advances_clock=bool(data.get("advances_clock", True)),
        ticks=int(data.get("ticks", 1)),
        success_chance=data.get("success_chance"),
        loadout_chances=loadouts,
        success=_outcome(data.get("success")),
        failure=_outcome(data.get("failure")),
        show_chance=bool(data.get("show_chance", False)),
    )


def build_from_spec(spec: dict[str, Any]):
    """Return (map_graph, state, meta) from a scenario spec dict."""
    items = {_item(i).id: _item(i) for i in spec.get("items") or []}
    areas: dict[str, Area] = {}
    for a in spec["areas"]:
        areas[a["id"]] = Area(
            id=a["id"],
            name=a["name"],
            description=a["description"],
            actions=[_action(act) for act in a.get("actions") or []],
        )

    start = spec.get("start_area_id") or next(iter(areas))
    map_graph = MapGraph(
        areas=areas,
        start_area_id=start,
        exit_area_ids=tuple(spec.get("exit_area_ids") or ()),
        win_message=spec.get("win_message", "You win."),
        lose_message=spec.get("lose_message", "You lose."),
    )

    ch = spec.get("character") or {}
    character = CharacterState(
        health=int(ch.get("health", 85)),
        satiation=int(ch.get("satiation", 70)),
        energy=int(ch.get("energy", 75)),
        items=[],
        location_id=start,
    )

    clock_data = spec.get("clock") or {}
    clock = ClockConfig(
        satiation_loss_per_tick=int(clock_data.get("satiation_loss_per_tick", 4)),
        energy_gain_per_tick=int(clock_data.get("energy_gain_per_tick", 3)),
        health_loss_per_tick=int(clock_data.get("health_loss_per_tick", 5)),
    )

    state = GameState(
        t=0,
        character=character,
        world_items=items,
        log=[spec.get("opening", spec.get("premise", "Your adventure begins."))],
    )

    meta = {
        "title": spec.get("title", "Adventure"),
        "premise": spec.get("premise", ""),
        "objective": spec.get("objective", ""),
        "clock": clock,
        "generated": bool(spec.get("generated", False)),
        "source": spec.get("source", "spec"),
    }
    return map_graph, state, meta
