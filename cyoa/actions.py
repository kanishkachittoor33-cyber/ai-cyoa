"""Action availability and resolution."""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Optional

from .clock import apply_ticks
from .types import (
    ActionKind,
    AreaAction,
    ChanceOutcome,
    ClockConfig,
    GameState,
    GameStatus,
    GateStatus,
    ItemKind,
    LoadoutChance,
    MapGraph,
    TransitionGate,
    _clamp,
)


class ActionResult:
    def __init__(self, state: GameState, message: str, ok: bool = True):
        self.state = state
        self.message = message
        self.ok = ok


def effective_gate(action: AreaAction, state: GameState) -> Optional[TransitionGate]:
    if action.kind != ActionKind.TRANSITION:
        return None
    if action.id in state.opened_gates:
        return TransitionGate(status=GateStatus.OPEN)
    return action.gate or TransitionGate(status=GateStatus.OPEN)


def resolve_success_chance(action: AreaAction, state: GameState) -> Optional[float]:
    if action.loadout_chances:
        for loadout in action.loadout_chances:
            if all(state.character.has_item(i) for i in loadout.item_ids):
                return loadout.chance
        return 0.0
    return action.success_chance


def can_perform(action: AreaAction, state: GameState) -> tuple[bool, str]:
    c = state.character

    if action.once_flag and action.once_flag in state.flags:
        return False, "Already done"

    for flag in action.require_flags:
        if flag not in state.flags:
            return False, "Not yet"

    for flag in action.forbid_flags:
        if flag in state.flags:
            return False, "No longer needed"

    if action.required_tool_id and not c.has_item(action.required_tool_id):
        tool = state.world_items.get(action.required_tool_id)
        name = tool.name if tool else action.required_tool_id
        return False, f"Requires: {name}"

    if action.required_any_item_ids and not c.has_any(action.required_any_item_ids):
        names = [
            state.world_items[i].name if i in state.world_items else i
            for i in action.required_any_item_ids
        ]
        return False, f"Requires: {' or '.join(names)}"

    if action.transform_item:
        from_id, _to_id = action.transform_item
        if not c.has_item(from_id):
            item = state.world_items.get(from_id)
            name = item.name if item else from_id
            return False, f"Requires: {name}"

    if action.kind == ActionKind.COMBAT and action.loadout_chances:
        if resolve_success_chance(action, state) == 0.0 and not any(
            c.has_item(i) for loadout in action.loadout_chances for i in loadout.item_ids
        ):
            return False, "You need a weapon"

    energy_needed = action.energy_cost
    if action.kind == ActionKind.TRANSITION:
        gate = effective_gate(action, state)
        assert gate is not None
        if gate.status == GateStatus.CLOSED:
            if gate.requires_tool_id and not c.has_item(gate.requires_tool_id):
                tool = state.world_items.get(gate.requires_tool_id)
                name = tool.name if tool else gate.requires_tool_id
                return False, f"Path closed — needs {name}"
            if gate.requires_any_item_ids and not c.has_any(gate.requires_any_item_ids):
                return False, "Path closed — missing required item"
            if gate.min_energy and c.energy < gate.min_energy:
                return False, f"Too fatigued (need {gate.min_energy} energy)"
            energy_needed = max(energy_needed, gate.energy_cost)

    if energy_needed and c.energy < energy_needed:
        return False, f"Not enough energy (need {energy_needed})"

    if action.consume_item_id and not c.has_item(action.consume_item_id):
        return False, "You don't have that item"

    return True, ""


def available_actions(map_graph: MapGraph, state: GameState) -> list[dict]:
    area = map_graph.area(state.character.location_id)
    locked_ids = _initially_locked_ids(map_graph)
    result = []

    for action in area.actions:
        if action.once_flag and action.once_flag in state.flags:
            continue
        if action.require_flags and not all(f in state.flags for f in action.require_flags):
            continue
        if action.forbid_flags and any(f in state.flags for f in action.forbid_flags):
            continue
        if action.id in locked_ids and action.id not in state.unlocked_action_ids:
            continue

        ok, reason = can_perform(action, state)
        chance = resolve_success_chance(action, state)
        payload = {
            **action.to_dict(),
            "available": ok,
            "blocked_reason": reason,
            "resolved_chance": chance,
            "gate": (
                effective_gate(action, state).to_dict()
                if action.kind == ActionKind.TRANSITION
                else (action.gate.to_dict() if action.gate else None)
            ),
        }
        result.append(payload)

    for item in state.character.items:
        if item.kind in (ItemKind.FOOD, ItemKind.DRINK):
            aid = f"use:{item.id}"
            result.append(
                {
                    "id": aid,
                    "label": f"Consume {item.name}",
                    "kind": ActionKind.UNIVERSAL.value,
                    "narrative": f"You consume the {item.name}.",
                    "energy_cost": 0,
                    "available": True,
                    "blocked_reason": "",
                    "consume_item_id": item.id,
                    "advances_clock": True,
                    "ticks": 1,
                    "resolved_chance": None,
                }
            )
    return result


def _initially_locked_ids(map_graph: MapGraph) -> set[str]:
    locked: set[str] = set()
    for area in map_graph.areas.values():
        for action in area.actions:
            locked.update(action.unlock_action_ids)
    return locked


def _rng(state: GameState) -> random.Random:
    # Deterministic-ish stream from seed + t + location
    base = state.rng_seed if state.rng_seed is not None else random.randrange(1 << 30)
    return random.Random(f"{base}:{state.t}:{state.character.location_id}:{len(state.log)}")


def perform_action(
    map_graph: MapGraph,
    state: GameState,
    action_id: str,
    clock: ClockConfig | None = None,
) -> ActionResult:
    if state.status != GameStatus.PLAYING:
        return ActionResult(state, "The adventure has ended.", ok=False)

    clock = clock or ClockConfig()

    if action_id.startswith("use:"):
        item_id = action_id.split(":", 1)[1]
        return _consume_item(map_graph, state, item_id, clock)

    area = map_graph.area(state.character.location_id)
    action = next((a for a in area.actions if a.id == action_id), None)
    if action is None:
        return ActionResult(state, "That action isn't available here.", ok=False)

    ok, reason = can_perform(action, state)
    if not ok:
        return ActionResult(state, reason, ok=False)

    # Chance / combat branch
    if action.success is not None and action.failure is not None:
        chance = resolve_success_chance(action, state)
        if chance is None:
            chance = 1.0
        roll = _rng(state).random()
        branch = action.success if roll < chance else action.failure
        return _apply_outcome(
            map_graph,
            state,
            action,
            branch,
            clock,
            preface=action.narrative,
            roll_note=f"(roll {roll:.2f} vs {chance:.0%})",
        )

    return _apply_deterministic(map_graph, state, action, clock)


def _apply_deterministic(
    map_graph: MapGraph,
    state: GameState,
    action: AreaAction,
    clock: ClockConfig,
) -> ActionResult:
    outcome = ChanceOutcome(
        narrative=action.narrative or action.label,
        health_delta=action.health_delta,
        satiation_delta=action.satiation_delta,
        energy_delta=action.energy_delta,
        target_area_id=action.target_area_id if action.kind == ActionKind.TRANSITION else None,
        grant_item_id=action.grant_item_id,
        remove_item_ids=(action.consume_item_id,) if action.consume_item_id else (),
        transform_item=action.transform_item,
        set_flags=action.set_flags + ((action.once_flag,) if action.once_flag else ()),
        unlock_action_ids=action.unlock_action_ids,
    )
    return _apply_outcome(map_graph, state, action, outcome, clock)


def _apply_outcome(
    map_graph: MapGraph,
    state: GameState,
    action: AreaAction,
    outcome: ChanceOutcome,
    clock: ClockConfig,
    preface: str = "",
    roll_note: str = "",
) -> ActionResult:
    character = state.character
    messages: list[str] = []
    opened = set(state.opened_gates)
    unlocked = set(state.unlocked_action_ids)
    flags = set(state.flags)

    energy_cost = action.energy_cost
    if action.kind == ActionKind.TRANSITION:
        gate = effective_gate(action, state)
        if gate and gate.status == GateStatus.CLOSED:
            energy_cost = max(energy_cost, gate.energy_cost)
            opened.add(action.id)

    if energy_cost:
        character = character.with_stats(energy=character.energy - energy_cost)

    if outcome.health_delta or outcome.satiation_delta or outcome.energy_delta:
        character = character.with_stats(
            health=_clamp(character.health + outcome.health_delta),
            satiation=_clamp(character.satiation + outcome.satiation_delta),
            energy=_clamp(character.energy + outcome.energy_delta),
        )

    items = list(character.items)

    if outcome.remove_item_ids:
        remove = set(outcome.remove_item_ids)
        items = [i for i in items if i.id not in remove]

    if outcome.transform_item:
        from_id, to_id = outcome.transform_item
        items = [i for i in items if i.id != from_id]
        new_item = state.world_items.get(to_id)
        if new_item and not any(i.id == to_id for i in items):
            items.append(new_item)
            messages.append(f"Your {state.world_items.get(from_id, new_item).name} is now: {new_item.name}.")

    # Also support transform on the action itself when outcome didn't set it
    if action.transform_item and not outcome.transform_item:
        from_id, to_id = action.transform_item
        if any(i.id == from_id for i in items):
            items = [i for i in items if i.id != from_id]
            new_item = state.world_items.get(to_id)
            if new_item:
                items.append(new_item)
                messages.append(f"Sharpened into: {new_item.name}.")

    if outcome.grant_item_id:
        item = state.world_items.get(outcome.grant_item_id)
        if item and not any(i.id == item.id for i in items):
            items.append(item)
            messages.append(f"You obtained: {item.name}.")

    character = replace(character, items=items)

    dest_id = outcome.target_area_id
    if dest_id:
        character = replace(character, location_id=dest_id)
        dest = map_graph.area(dest_id)
        messages.append(f"You arrive at {dest.name}.")

    if outcome.unlock_action_ids:
        unlocked.update(outcome.unlock_action_ids)
    if action.unlock_action_ids and not outcome.unlock_action_ids:
        unlocked.update(action.unlock_action_ids)

    flags.update(outcome.set_flags)
    if action.once_flag:
        flags.add(action.once_flag)
    if action.set_flags:
        flags.update(action.set_flags)

    text_parts = []
    if preface and preface != outcome.narrative:
        text_parts.append(preface)
    text_parts.append(outcome.narrative)
    if roll_note:
        text_parts.append(roll_note)
    messages = text_parts + messages

    t = state.t
    if action.advances_clock:
        character = apply_ticks(character, action.ticks, clock)
        t += action.ticks

    status = GameStatus.PLAYING
    if outcome.win:
        status = GameStatus.WON
        messages.append(map_graph.win_message)
    if outcome.lose:
        status = GameStatus.LOST
        messages.append(map_graph.lose_message)

    new_state = GameState(
        t=t,
        character=character,
        status=status,
        unlocked_action_ids=unlocked,
        opened_gates=opened,
        flags=flags,
        log=state.log + messages,
        world_items=state.world_items,
        rng_seed=state.rng_seed,
    )
    if status == GameStatus.PLAYING:
        new_state = _check_end(map_graph, new_state)
    return ActionResult(new_state, "\n".join(messages), ok=True)


def _consume_item(
    map_graph: MapGraph,
    state: GameState,
    item_id: str,
    clock: ClockConfig,
) -> ActionResult:
    item = state.character.get_item(item_id)
    if item is None:
        return ActionResult(state, "You don't have that.", ok=False)
    if item.kind not in (ItemKind.FOOD, ItemKind.DRINK):
        return ActionResult(state, "You can't consume that.", ok=False)

    character = state.character.with_stats(
        health=_clamp(state.character.health + item.health_restore),
        satiation=_clamp(state.character.satiation + item.satiation_restore),
        energy=_clamp(state.character.energy + item.energy_restore),
    )
    items = [i for i in character.items if i.id != item_id]
    character = replace(character, items=items)
    character = apply_ticks(character, 1, clock)

    if item.health_restore < 0:
        msg = f"You eat the {item.name}. Your gut twists — poison."
    else:
        msg = f"You consume the {item.name}."

    new_state = GameState(
        t=state.t + 1,
        character=character,
        status=GameStatus.PLAYING,
        unlocked_action_ids=set(state.unlocked_action_ids),
        opened_gates=set(state.opened_gates),
        flags=set(state.flags),
        log=state.log + [msg],
        world_items=state.world_items,
        rng_seed=state.rng_seed,
    )
    new_state = _check_end(map_graph, new_state)
    return ActionResult(new_state, msg, ok=True)


def _check_end(map_graph: MapGraph, state: GameState) -> GameState:
    if state.character.health <= 0:
        return replace(
            state,
            status=GameStatus.LOST,
            character=state.character.with_stats(health=0),
            log=state.log + [map_graph.lose_message],
        )
    if state.character.location_id in map_graph.exit_area_ids:
        return replace(
            state,
            status=GameStatus.WON,
            log=state.log + [map_graph.win_message],
        )
    return state
