"""Compose a brand-new adventure every call — unique topology, win rule, actions."""

from __future__ import annotations

import json
import os
import random
import re
import ssl
import urllib.error
import urllib.request
from typing import Any

import certifi


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _id(rng: random.Random, *parts: str) -> str:
    base = "_".join(re.sub(r"[^a-z0-9]+", "", p.lower())[:10] for p in parts if p)
    return f"{base or 'a'}{rng.randint(1000, 9999)}"


# ---------------------------------------------------------------------------
# Lexicons — mixed every generation so names/actions never freeze into one kit
# ---------------------------------------------------------------------------

DOMAINS = [
    {
        "world": "a floating tax office above storm clouds",
        "tone": "bureaucratic dread and thin air",
        "fail": "You are audited out of existence.",
        "verbs": ["stamp", "file", "appeal", "notarize", "escalate"],
    },
    {
        "world": "an underground mushroom transit hub",
        "tone": "bioluminescent schedules and spore delays",
        "fail": "You miss the last cap and petrify on the platform.",
        "verbs": ["board", "signal", "inoculate", "reroute", "ferment"],
    },
    {
        "world": "a rooftop apiary embassy",
        "tone": "diplomacy measured in dances and honey",
        "fail": "The swarm votes you out of the skyline.",
        "verbs": ["dance", "offer", "translate", "calm", "harvest"],
    },
    {
        "world": "a sunken cinema that still sells tickets",
        "tone": "saltwater velvet and unfinished reels",
        "fail": "The credits roll without you in them.",
        "verbs": ["project", "splice", "focus", "cue", "ticket"],
    },
    {
        "world": "a mobile kitchen racing a monsoon",
        "tone": "steam, knives, and a finishing window",
        "fail": "The judges taste rain and nothing else.",
        "verbs": ["plate", "reduce", "char", "season", "serve"],
    },
    {
        "world": "a clocktower that runs on confessions",
        "tone": "gears fed by secrets",
        "fail": "Midnight arrives early and takes your name.",
        "verbs": ["wind", "confess", "balance", "chime", "align"],
    },
    {
        "world": "a ferry trapped between two fog banks",
        "tone": "passengers arguing with the horizon",
        "fail": "The ferry docks nowhere, forever.",
        "verbs": ["steer", "sound", "bargain", "ballast", "moor"],
    },
    {
        "world": "a greenhouse courtroom for extinct plants",
        "tone": "photosynthesis and cross-examination",
        "fail": "Judgment: compost.",
        "verbs": ["testify", "graft", "present", "pollinate", "adjourn"],
    },
    {
        "world": "a radio telescope pointed at a sleeping city",
        "tone": "static that almost forms sentences",
        "fail": "The city dreams you away.",
        "verbs": ["tune", "amplify", "decode", "calibrate", "broadcast"],
    },
    {
        "world": "a pawnshop that buys hours of your future",
        "tone": "velvet trays and borrowed time",
        "fail": "You sell one hour too many.",
        "verbs": ["appraise", "haggle", "redeem", "collateral", "recall"],
    },
]

TOPOLOGIES = [
    "chain",       # A -> B -> C -> win room
    "hub",         # center with 3 spokes, return to finish
    "loop",        # circle; win by completing circuit with item
    "layers",      # downstairs/upstairs gated by flag
    "fork",        # early choice of two routes that rejoin
    "single_phase" # one primary space that changes via phases/flags
]

WIN_MODES = [
    "assemble",    # collect parts, combine
    "sequence",    # do actions in order
    "threshold",   # raise a meter via flags then exit
    "trade",       # give item to NPC-like action
    "timing",      # open a window then commit
    "correct_pick" # choose the right of several finals
]

# Forbidden echoes of Lost in the Woods / cottage (matched as whole words / phrases)
_BANNED_TERMS = (
    "troll", "cottage", "hatchet", "axe", "scroll", "grindstone", "thicket",
    "berry", "snake", "shed", "fishing rod", "woods", "bridge troll",
    "sharpen", "weakness", "forest clearing", "lost in the",
)
# Back-compat alias
_BANNED_SUBSTR = _BANNED_TERMS

_ALLOWED_ACTION_KINDS = frozenset({"universal", "energy", "tool", "transition", "chance"})
_ALLOWED_ITEM_KINDS = frozenset({"tool", "weapon", "food", "drink", "key", "lore", "material"})

_LLM_SYSTEM = (
    "You create playable CYOA scenario JSON for a game engine. "
    "Output ONE JSON object only. "
    "Every generation must be structurally NEW: different map shape, win condition, and verbs. "
    "Do NOT use these whole words/themes: troll, cottage, hatchet, axe, scroll, grindstone, "
    "thicket, berry, snake, shed, woods, sharpen, weakness. No combat kind. "
    "CRITICAL: every actions[] entry MUST be an object, never a bare string. "
    "Required action fields: id (string), label (human-readable string), kind "
    "(universal|energy|tool|transition|chance). "
    "transition actions also need target_area_id. "
    "chance actions need success_chance (0-1) and success/failure outcome objects. "
    "items[].kind MUST be one of: tool|weapon|food|drink|key|lore|material. "
    "ENGINE WIN RULES: entering any id in exit_area_ids wins immediately. "
    "Therefore set exit_area_ids to [] and win ONLY via an action or outcome with "
    '"win": true on a late/gated step (requires items, flags, or a closed gate). '
    "If you invent an exit area, it must NOT be reachable by an ungated transition from start. "
    "When an action finds/gives an item, set grant_item_id (or success.grant_item_id) "
    "to a real items[].id — narrative alone does not grant. "
    "All target_area_id / required_tool_id / gate requires_* must reference real ids. "
    "Build a multi-step adventure: at least 3 areas, 6+ actions, and at least one "
    "non-transition action. The player must not be able to win in one free move. "
    "objective and labels must be plain English."
)

_LLM_USER = (
    "Invent a COMPLETELY new playable adventure. "
    "Vary topology (hub/chain/loop/phases/fork) and win rule "
    "(assemble/sequence/trade/timing/choice). "
    "Return JSON with: title, premise, objective, opening, win_message, lose_message, "
    "start_area_id, exit_area_ids (MUST be [] unless a single gated end area), "
    "character {health,satiation,energy}, "
    "clock {satiation_loss_per_tick,energy_gain_per_tick,health_loss_per_tick}, "
    "items (non-empty array of {id,name,kind,description}), "
    "areas (non-empty array of {id,name,description,actions}). "
    "Include at least one action/outcome with win:true that requires prior progress "
    "(items granted via grant_item_id and/or flags/gates). "
    "Example transition: "
    '{"id":"go_dock","label":"Walk to the dock","kind":"transition",'
    '"narrative":"Boards creak underfoot.","target_area_id":"dock"}. '
    "Example win (gated): "
    '{"id":"finish","label":"Assemble the device","kind":"universal",'
    '"required_any_item_ids":["part_a","part_b"],'
    '"narrative":"It locks into place.","win":true}. '
    "Never put strings directly in actions[]."
)

_LLM_REPAIR_HINTS = (
    "Return a FIXED complete scenario that satisfies engine playability. "
    "Set exit_area_ids to []. Win only with win:true on a late/gated action. "
    "Every actions[] entry MUST be an object with id, label, kind "
    "(and target_area_id for transitions). "
    "items[].kind must be tool|weapon|food|drink|key|lore|material. "
    "Use grant_item_id when finding items. No bare strings in actions[]. "
    "No instant win: start must not reach an exit or win:true action via ungated moves."
)


def _banned_hits(text: str) -> list[str]:
    """Whole-word / phrase bans so 'embellished' does not match 'shed'."""
    lower = text.lower()
    hits: list[str] = []
    for term in _BANNED_TERMS:
        if " " in term:
            if term in lower:
                hits.append(term)
        elif re.search(rf"\b{re.escape(term)}\b", lower):
            hits.append(term)
    return hits


def _action_is_free(act: dict[str, Any]) -> bool:
    """True if the action can be taken with no items/flags/tools/closed gates."""
    if act.get("required_tool_id") or act.get("required_any_item_ids") or act.get("require_flags"):
        return False
    if act.get("consume_item_id"):
        return False
    gate = act.get("gate")
    if isinstance(gate, dict):
        status = (gate.get("status") or "open").lower()
        if status == "closed":
            return False
        if gate.get("requires_tool_id") or gate.get("requires_item_id"):
            return False
        if gate.get("requires_any_item_ids"):
            return False
        if int(gate.get("min_energy") or 0) > 0:
            return False
    return True


def _outcome_wins(obj: dict[str, Any] | None) -> bool:
    return bool(isinstance(obj, dict) and obj.get("win"))


def _action_always_wins(act: dict[str, Any]) -> bool:
    if act.get("win"):
        return True
    if _outcome_wins(act.get("success")) and _outcome_wins(act.get("failure")):
        return True
    kind = act.get("kind", "universal")
    if kind == "chance":
        chance = act.get("success_chance")
        if chance is not None and float(chance) >= 1.0 and _outcome_wins(act.get("success")):
            return True
        return False
    return _outcome_wins(act.get("success"))


def _iter_item_refs(act: dict[str, Any]) -> list[tuple[str, str]]:
    """Yield (field_path, item_id) references on an action."""
    refs: list[tuple[str, str]] = []
    for key in ("grant_item_id", "required_tool_id", "consume_item_id"):
        val = act.get(key)
        if val:
            refs.append((key, str(val)))
    for key in ("required_any_item_ids",):
        for iid in act.get(key) or []:
            refs.append((key, str(iid)))
    gate = act.get("gate")
    if isinstance(gate, dict):
        for key in ("requires_tool_id", "requires_item_id"):
            val = gate.get(key)
            if val:
                refs.append((f"gate.{key}", str(val)))
        for iid in gate.get("requires_any_item_ids") or []:
            refs.append(("gate.requires_any_item_ids", str(iid)))
    for side in ("success", "failure"):
        outcome = act.get(side)
        if isinstance(outcome, dict):
            gid = outcome.get("grant_item_id")
            if gid:
                refs.append((f"{side}.grant_item_id", str(gid)))
            for iid in outcome.get("remove_item_ids") or []:
                refs.append((f"{side}.remove_item_ids", str(iid)))
    return refs


def _collect_win_markers(areas: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """List (area_id, action_id) that can declare a win via win:true."""
    wins: list[tuple[str, str]] = []
    for area in areas:
        aid = area.get("id", "")
        for act in area.get("actions") or []:
            if not isinstance(act, dict):
                continue
            if (
                act.get("win")
                or _outcome_wins(act.get("success"))
                or _outcome_wins(act.get("failure"))
            ):
                wins.append((aid, str(act.get("id", ""))))
    return wins


def _free_transition_graph(areas: list[dict[str, Any]]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {str(a["id"]): set() for a in areas if a.get("id")}
    for area in areas:
        aid = str(area["id"])
        for act in area.get("actions") or []:
            if not isinstance(act, dict):
                continue
            if act.get("kind") != "transition":
                continue
            if not _action_is_free(act):
                continue
            dest = act.get("target_area_id")
            if dest:
                graph.setdefault(aid, set()).add(str(dest))
    return graph


def _reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for nxt in graph.get(node, ()):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def _has_progression_hook(areas: list[dict[str, Any]]) -> bool:
    for area in areas:
        for act in area.get("actions") or []:
            if not isinstance(act, dict):
                continue
            if act.get("grant_item_id"):
                return True
            if act.get("set_flags") or act.get("require_flags"):
                return True
            gate = act.get("gate")
            if isinstance(gate, dict) and (
                gate.get("requires_tool_id")
                or gate.get("requires_item_id")
                or gate.get("requires_any_item_ids")
                or (gate.get("status") or "").lower() == "closed"
            ):
                return True
            for side in ("success", "failure"):
                outcome = act.get(side)
                if isinstance(outcome, dict) and (
                    outcome.get("grant_item_id") or outcome.get("set_flags")
                ):
                    return True
    return False


def _validate_llm_spec(spec: dict[str, Any]) -> str | None:
    """Return a reject reason, or None if the spec is structurally valid and playable."""
    if not isinstance(spec, dict):
        return "not_an_object"
    for key in ("title", "premise", "objective", "areas", "items", "start_area_id"):
        if key not in spec:
            return f"missing_keys: {key}"
    if not isinstance(spec["title"], str) or not spec["title"].strip():
        return "empty_title"
    if not isinstance(spec["objective"], str) or not spec["objective"].strip():
        return "empty_objective"

    items = spec.get("items")
    if not isinstance(items, list) or not items:
        return "items_empty"
    item_ids: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return f"item[{i}]_not_object"
        for k in ("id", "name", "kind"):
            if not item.get(k):
                return f"item[{i}]_missing_{k}"
        kind = str(item["kind"]).lower()
        if kind not in _ALLOWED_ITEM_KINDS:
            return f"bad_item_kind: {item.get('kind')}"
        iid = str(item["id"])
        if iid in item_ids:
            return f"duplicate_item_id: {iid}"
        item_ids.add(iid)

    areas = spec.get("areas")
    if not isinstance(areas, list) or not areas:
        return "areas_empty"
    area_ids: set[str] = set()
    action_count = 0
    non_transition = 0
    for i, area in enumerate(areas):
        if not isinstance(area, dict):
            return f"area[{i}]_not_object"
        for k in ("id", "name", "description"):
            if not area.get(k):
                return f"area[{i}]_missing_{k}"
        aid = str(area["id"])
        if aid in area_ids:
            return f"duplicate_area_id: {aid}"
        area_ids.add(aid)
        actions = area.get("actions")
        if not isinstance(actions, list):
            return f"area[{aid}]_actions_not_list"
        for j, act in enumerate(actions):
            if isinstance(act, str):
                return f"area[{aid}].actions[{j}]_is_string"
            if not isinstance(act, dict):
                return f"area[{aid}].actions[{j}]_not_object"
            if not act.get("id") or not act.get("label"):
                return f"area[{aid}].actions[{j}]_missing_id_or_label"
            kind = act.get("kind", "universal")
            if kind not in _ALLOWED_ACTION_KINDS:
                return f"area[{aid}].actions[{j}]_bad_kind:{kind}"
            if kind == "transition":
                if not act.get("target_area_id"):
                    return f"area[{aid}].actions[{j}]_transition_missing_target"
            else:
                non_transition += 1
            for field, ref in _iter_item_refs(act):
                if ref not in item_ids:
                    return f"dangling_{field}: {ref}"
            action_count += 1

    # Resolve transition targets after all area ids known
    for area in areas:
        aid = str(area["id"])
        for j, act in enumerate(area.get("actions") or []):
            if not isinstance(act, dict):
                continue
            dest = act.get("target_area_id")
            if dest and str(dest) not in area_ids:
                return f"dangling_target_area_id: {dest}"

    if action_count == 0:
        return "no_actions"
    if len(areas) < 3:
        return "too_few_areas"
    if action_count < 6:
        return "too_few_actions"
    if non_transition < 1:
        return "no_non_transition_actions"

    start = str(spec.get("start_area_id"))
    if start not in area_ids:
        return f"bad_start_area_id: {start}"

    exits = [str(x) for x in (spec.get("exit_area_ids") or [])]
    for ex in exits:
        if ex not in area_ids:
            return f"dangling_exit_area_id: {ex}"
    if start in exits:
        return "start_is_exit"

    banned = _banned_hits(json.dumps(spec))
    if banned:
        return f"banned_terms: {', '.join(banned[:8])}"

    win_markers = _collect_win_markers(areas)
    if not win_markers and not exits:
        return "no_win_condition"

    # Free-graph reachability: exits reachable without gates => trivial win
    free_graph = _free_transition_graph(areas)
    free_reach = _reachable(free_graph, start)
    free_exits = [ex for ex in exits if ex in free_reach]
    if free_exits:
        return f"trivial_exit_win: {', '.join(free_exits[:4])}"

    # Ungated multi-exit lists are almost always mistaken "destinations"
    if len(exits) > 1:
        gated_into_exit = False
        for area in areas:
            for act in area.get("actions") or []:
                if not isinstance(act, dict) or act.get("kind") != "transition":
                    continue
                if act.get("target_area_id") in exits and not _action_is_free(act):
                    gated_into_exit = True
                    break
            if gated_into_exit:
                break
        if not gated_into_exit:
            return "ungated_multi_exit"

    # Instant win from start via a free local action
    start_area = next(a for a in areas if str(a["id"]) == start)
    for act in start_area.get("actions") or []:
        if not isinstance(act, dict):
            continue
        if _action_is_free(act) and _action_always_wins(act):
            return f"trivial_win_action: {act.get('id')}"

    # Free transition into an area that has a free always-win action
    for area in areas:
        aid = str(area["id"])
        if aid not in free_reach:
            continue
        for act in area.get("actions") or []:
            if not isinstance(act, dict):
                continue
            if _action_is_free(act) and _action_always_wins(act):
                return f"trivial_win_action: {act.get('id')}"

    if not _has_progression_hook(areas):
        return "no_progression_hooks"

    try:
        from .scenario_builder import build_from_spec

        build_from_spec(spec)
    except Exception as exc:  # noqa: BLE001
        return f"build_failed: {type(exc).__name__}: {exc}"
    return None


def _item(iid: str, name: str, kind: str, **kwargs) -> dict[str, Any]:
    return {
        "id": iid,
        "name": name,
        "kind": kind,
        "description": kwargs.get("desc", ""),
        "satiation_restore": kwargs.get("sat", 0),
        "energy_restore": kwargs.get("en", 0),
        "health_restore": kwargs.get("hp", 0),
    }


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def _food_item(rng: random.Random) -> dict[str, Any]:
    foods = [
        ("Tin of Bitter Tea", "drink", 8, 10),
        ("Pocket Dumpling", "food", 16, 2),
        ("Candied Rind", "food", 12, 0),
        ("Salt Broth Cup", "drink", 10, 6),
        ("Charcoal Biscuit", "food", 14, 3),
        ("Ferment Ampoule", "drink", 6, 12),
        ("Sour Pear Leather", "food", 15, 1),
        ("Night-Shift Coffee", "drink", 4, 14),
    ]
    name, kind, sat, en = rng.choice(foods)
    return _item(_id(rng, "food"), name, kind, sat=sat, en=en, desc="Keeps the clock from eating you.")


class ActionDeck:
    """Compose brand-new action labels every deal — no fixed catchphrases."""

    def __init__(self, rng: random.Random, domain: dict):
        self.rng = rng
        self.domain = domain
        self.verbs = list(domain["verbs"])
        rng.shuffle(self.verbs)
        self._used_labels: set[str] = set()
        self._kind_cycle = ["universal", "chance", "energy", "universal", "chance"]
        self._ki = 0
        # Large mutable lexicons — shuffled per adventure
        self.nouns = [
            "ledger", "valve", "apron", "gantry", "whistle", "cipher", "pallet",
            "lantern", "receipt", "hinge", "spool", "clamp", "beacon", "stencil",
            "funnel", "relay", "badge", "trowel", "bellows", "dial", "latch",
            "courier-bag", "timbre", "scaffold", "inkwell", "manifold", "chit",
        ]
        self.adjs = [
            "warped", "unlisted", "secondhand", "contraband", "overbright",
            "salt-stained", "unsigned", "jittering", "borrowed", "ashen",
            "left-handed", "midnight", "provisional", "countersigned", "hollow",
        ]
        self.beings = [
            "shift captain", "meter-reader", "underclerk", "signal-runner",
            "night auditor", "stagehand", "dock tallyman", "apiary envoy",
            "boiler-warden", "index ghost", "relief cook", "fence-sitter",
            "loaned understudy", "fog pilot", "stamp warden",
        ]
        self.places_bits = [
            "behind the false panel", "under the warm grate", "inside the mute cabinet",
            "along the service crawl", "beside the cracked porthole", "at the unpaid desk",
            "near the spoiling crates", "in the echo stair", "at the ink-stained rail",
        ]
        self.manner = [
            "without asking", "twice, carefully", "like you own the debt",
            "as if audited", "before the bell", "with both hands empty",
            "using only rumor", "against advice", "in reverse order",
        ]
        for bag in (self.nouns, self.adjs, self.beings, self.places_bits, self.manner):
            rng.shuffle(bag)
        self._ni = self._ai = self._bi = self._pi = self._mi = 0

    def _n(self) -> str:
        x = self.nouns[self._ni % len(self.nouns)]
        self._ni += 1
        return x

    def _a(self) -> str:
        x = self.adjs[self._ai % len(self.adjs)]
        self._ai += 1
        return x

    def _b(self) -> str:
        x = self.beings[self._bi % len(self.beings)]
        self._bi += 1
        return x

    def _p(self) -> str:
        x = self.places_bits[self._pi % len(self.places_bits)]
        self._pi += 1
        return x

    def _m(self) -> str:
        x = self.manner[self._mi % len(self.manner)]
        self._mi += 1
        return x

    def _v(self, i: int = 0) -> str:
        return self.verbs[i % len(self.verbs)]

    def _fresh_label(self, templates: list[str], **extra: str) -> str:
        for _ in range(40):
            t = self.rng.choice(templates)
            fields = {
                "v": self._v(self.rng.randint(0, 4)),
                "v2": self._v(self.rng.randint(0, 4)),
                "n": self._n(),
                "a": self._a(),
                "b": self._b(),
                "p": self._p(),
                "m": self._m(),
                "tone": self.domain["tone"].split(",")[0],
                "world": self.domain["world"],
                "d": "",
                "i": "",
            }
            fields.update({k: str(v) for k, v in extra.items()})
            lab = _cap(t.format(**fields))
            key = lab.lower()
            if key not in self._used_labels:
                self._used_labels.add(key)
                return lab
        lab = _cap(f"{self._v()} the {self._a()} {self._n()} {self.rng.randint(100,999)}")
        self._used_labels.add(lab.lower())
        return lab

    def _make_act(self, area_id: str, area_name: str, kind: str) -> dict[str, Any]:
        rng = self.rng
        if kind == "chance":
            label = self._fresh_label(
                [
                    "{v} the {a} {n} {m}",
                    "dare the {b} {p}",
                    "bluff past the {a} {n}",
                    "gamble the {a} {n} against the {b}",
                    "test the {n} until it lies or yields",
                    "interrupt the {b} mid-shift",
                    "force a verdict from the {a} {n}",
                ]
            )
            return {
                "id": _id(rng, area_id, "c"),
                "label": label,
                "kind": "chance",
                "narrative": f"In {area_name}, odds rearrange themselves.",
                "success_chance": rng.choice([0.4, 0.5, 0.55, 0.65, 0.7]),
                "show_chance": True,
                "success": {
                    "narrative": rng.choice(
                        [
                            "It breaks your way.",
                            "The risk pays a thin dividend.",
                            "You keep the advantage.",
                        ]
                    ),
                    "energy_delta": rng.randint(2, 7),
                    "set_flags": ["helped"],
                },
                "failure": {
                    "narrative": rng.choice(
                        [
                            "It costs you.",
                            "The place collects a fee in bruises.",
                            "You misread the give.",
                        ]
                    ),
                    "health_delta": -rng.randint(5, 14),
                    "energy_delta": -rng.randint(1, 6),
                },
            }
        if kind == "energy":
            label = self._fresh_label(
                [
                    "haul the {a} {n} {p}",
                    "rebuild the {n} {m}",
                    "spend a shift on the {a} {n}",
                    "muscle the {n} into alignment",
                    "carry out a full {v} on the {n}",
                    "dig the {n} free {p}",
                ]
            )
            return {
                "id": _id(rng, area_id, "e"),
                "label": label,
                "kind": "energy",
                "energy_cost": rng.randint(7, 15),
                "narrative": f"Labor reshapes {area_name}.",
                "set_flags": ["helped"],
                "satiation_delta": -rng.randint(0, 3),
            }
        # universal — split into recover / inspect / social-ish via templates
        flavor = rng.choice(["recover", "inspect", "social", "tinker", "odd"])
        if flavor == "recover":
            label = self._fresh_label(
                [
                    "borrow stillness {p}",
                    "shake the {tone} out of your wrists",
                    "sit on the {a} {n} until calm returns",
                    "breathe like the {b} taught you",
                    "ration one quiet minute {m}",
                ]
            )
            return {
                "id": _id(rng, area_id, "r"),
                "label": label,
                "kind": "universal",
                "narrative": "You reclaim a little stamina.",
                "energy_delta": rng.randint(5, 12),
                "ticks": rng.randint(1, 2),
            }
        if flavor == "inspect":
            label = self._fresh_label(
                [
                    "chart every scratch on the {a} {n}",
                    "read the {n} {p}",
                    "press your ear to the {a} {n}",
                    "sketch the {n} before it changes",
                    "audit the {a} {n} for contradictions",
                ]
            )
            return {
                "id": _id(rng, area_id, "i"),
                "label": label,
                "kind": "universal",
                "narrative": f"Details in {area_name} rearrange into a clue.",
                "ticks": 1,
                "set_flags": [f"noticed_{area_id}"],
            }
        if flavor == "social":
            label = self._fresh_label(
                [
                    "corner the {b} {m}",
                    "trade a half-truth with the {b}",
                    "apologize to the {b} for the wrong crime",
                    "recruit the {b} for a {v}",
                    "listen to the {b} invent tomorrow",
                ]
            )
            return {
                "id": _id(rng, area_id, "s"),
                "label": label,
                "kind": "universal",
                "narrative": "Someone else's map briefly becomes yours.",
                "set_flags": ["helped"],
                "ticks": 1,
            }
        if flavor == "tinker":
            label = self._fresh_label(
                [
                    "retune the {a} {n}",
                    "oil the {n} {m}",
                    "rewire rumor into the {n}",
                    "nest a false note inside the {a} {n}",
                    "{v} the {n} until it answers",
                ]
            )
            return {
                "id": _id(rng, area_id, "t"),
                "label": label,
                "kind": "universal",
                "narrative": f"{area_name} ticks one notch toward usable.",
                "set_flags": [f"noticed_{area_id}"],
                "ticks": 1,
            }
        label = self._fresh_label(
            [
                "pocket grit from {p}",
                "taste the air near the {a} {n}",
                "name the {n} something kinder",
                "bow to the {a} {n} and mean none of it",
                "leave a mark only the {b} would notice",
            ]
        )
        return {
            "id": _id(rng, area_id, "o"),
            "label": label,
            "kind": "universal",
            "narrative": "A small, strange gain.",
            "satiation_delta": rng.choice([0, 0, 3, 5]),
            "ticks": 1,
            "once_flag": f"odd_{area_id}_{rng.randint(1,999)}",
        }

    def deal(
        self,
        area_id: str,
        area_name: str,
        n: int = 3,
        phase_flag: bool = False,
    ) -> list[dict[str, Any]]:
        picks: list[dict[str, Any]] = []
        # Ensure mixed kinds within the area
        kinds = []
        for _ in range(n):
            kinds.append(self._kind_cycle[self._ki % len(self._kind_cycle)])
            self._ki += 1
        self.rng.shuffle(kinds)
        for kind in kinds:
            picks.append(self._make_act(area_id, area_name, kind))
        if phase_flag and picks:
            flags = list(picks[0].get("set_flags") or [])
            flags.append(f"noticed_{area_id}")
            picks[0]["set_flags"] = list(dict.fromkeys(flags))
        return picks

    def travel(self, dest: str) -> str:
        dest = dest.replace(" fork", "").strip()
        return self._fresh_label(
            [
                "slip toward {d}",
                "commit to {d}",
                "follow the draft into {d}",
                "take the unposted path to {d}",
                "leave for {d} before you rethink it",
                "let {d} pull you in",
                "drift into {d}",
                "cut across to {d}",
                "thread yourself into {d}",
                "cross under a false name into {d}",
                "arrive at {d} looking owed",
                "smuggle your intent into {d}",
            ],
            d=dest,
        )

    def progress(self, verb: str, item: str) -> str:
        return self._fresh_label(
            [
                "{v} until the {i} loosens",
                "coax out the {i}",
                "earn the {i} the hard way",
                "make the {i} admit it is yours",
                "finish the rite that yields the {i}",
                "sign for the {i} in wet ink",
                "fish the {i} from where it hides",
                "unhook the {i} from policy",
                "whisper the {i} into your palm",
                "pry the {i} free with {v}",
                "negotiate custody of the {i}",
                "smuggle the {i} past procedure",
            ],
            v=verb.strip(),
            i=item.strip(),
        )

def _baseline_actions(
    deck: ActionDeck,
    area_id: str,
    area_name: str,
    phase_flag: str | None = None,
    n: int | None = None,
) -> list[dict[str, Any]]:
    count = n if n is not None else deck.rng.randint(3, 4)
    return deck.deal(area_id, area_name, n=count, phase_flag=bool(phase_flag))


def _progress_label(deck: ActionDeck, verb: str, item_name: str) -> str:
    return deck.progress(verb, item_name)


def _travel_label(deck: ActionDeck, dest: str) -> str:
    return deck.travel(dest)


def _freshen_labels(
    deck: ActionDeck,
    areas: list[dict],
    verbs: list[str],
    items: list[dict],
) -> None:
    """Rewrite travel/loot by structure (target area / granted item), not by parsing text."""
    by_id = {a["id"]: a["name"] for a in areas}
    item_by_id = {it["id"]: it["name"] for it in items}
    vi = 0
    for area in areas:
        for act in area["actions"]:
            if act.get("kind") == "transition" and act.get("target_area_id"):
                dest = by_id.get(act["target_area_id"], area["name"])
                dest = dest.replace(" Hub", "").strip()
                act["label"] = _travel_label(deck, dest)
                continue
            gid = act.get("grant_item_id")
            if gid:
                name = item_by_id.get(gid, "prize")
                act["label"] = _progress_label(
                    deck, verbs[vi % len(verbs)], name
                )
                vi += 1
                continue
            # Verb+item harvests without grant_item_id (assemble steps, etc.)
            lab = act.get("label") or ""
            if any(
                lab.startswith(p)
                for p in (
                    "Reveal the ",
                    "Reveal ",
                    "Also claim ",
                    "Lift the ",
                    "Find the ",
                    "Find ",
                    "Secure ",
                    "Claim ",
                    "Scavenge ",
                    "Uncover ",
                    "Pocket ",
                )
            ) and act.get("kind") in ("universal", "energy", "tool", "chance"):
                # Only rewrite if label still looks like a stock loot phrase
                item = lab
                for p in (
                    "Reveal the ",
                    "Reveal ",
                    "Also claim the ",
                    "Also claim ",
                    "Lift the ",
                    "Find the ",
                    "Find ",
                    "Secure ",
                    "Claim ",
                    "Scavenge ",
                    "Uncover ",
                    "Pocket ",
                ):
                    if item.startswith(p):
                        item = item[len(p) :]
                        break
                if item.lower().startswith("the "):
                    item = item[4:]
                for noise in (" from the hub stores", " at the join", " fork", " up"):
                    item = item.replace(noise, "")
                # Skip if this looks like a composed baseline (no title-case item remnant)
                if item and item[0].isupper() and len(item.split()) <= 4:
                    act["label"] = _progress_label(
                        deck, verbs[vi % len(verbs)], item.strip()
                    )
                    vi += 1


def _ensure_unique_action_labels(deck: ActionDeck, areas: list[dict]) -> None:
    """Force every non-identical action label in the adventure to be unique."""
    seen: set[str] = set()
    n = 0
    for area in areas:
        for act in area["actions"]:
            lab = act.get("label") or "Act"
            key = lab.lower()
            if key not in seen:
                seen.add(key)
                continue
            n += 1
            # Specialize by area + index without colliding
            suffix = area["name"].split()[0]
            candidate = _cap(f"{lab} — {suffix} variant")
            while candidate.lower() in seen:
                n += 1
                candidate = _cap(
                    f"{deck.verbs[n % len(deck.verbs)]} differently in {area['name']} (#{n})"
                )
            act["label"] = candidate
            seen.add(candidate.lower())


def procedural_scenario(rng: random.Random | None = None) -> dict[str, Any]:
    rng = rng or random.Random()
    domain = dict(rng.choice(DOMAINS))
    # mutate world phrasing slightly
    if rng.random() < 0.4:
        domain["world"] = domain["world"].replace("a ", rng.choice(["a forgotten ", "a renegade ", "an unofficial "]), 1)

    topo = rng.choice(TOPOLOGIES)
    win_mode = rng.choice(WIN_MODES)
    verbs = list(domain["verbs"])
    rng.shuffle(verbs)
    deck = ActionDeck(rng, domain)

    # Unique place names from combinatorial bits
    adj = ["amber", "hollow", "ledger", "brine", "copper", "violet", "ashen", "mirrored", "stammering", "ordinal"]
    noun = ["annex", "gantry", "vestry", "kiln", "apron", "nave", "switch", "gallery", "pantry", "well"]
    place_names = []
    used = set()
    while len(place_names) < 6:
        p = f"{rng.choice(adj).title()} {rng.choice(noun).title()}"
        if p not in used:
            used.add(p)
            place_names.append(p)

    food = _food_item(rng)
    part_a = _item(_id(rng, "part", "a"), rng.choice(["Keystone Chip", "Signed Writ", "Seed Crystal", "Tone Fork", "Red Token"]), "material", desc="One third of finishing.")
    part_b = _item(_id(rng, "part", "b"), rng.choice(["Counterweight", "Wet Seal", "Second Voice", "Blue Token", "Calibration Pin"]), "material", desc="Another third.")
    part_c = _item(_id(rng, "part", "c"), rng.choice(["Final Clause", "Green Token", "Heart Spring", "Witness Mark", "Closing Chord"]), "key", desc="Makes the ending possible.")
    tool = _item(_id(rng, "tool"), rng.choice(["Skew Lens", "Mute Cloth", "Parity Wand", "Tasting Spoon", "Ledger Needle"]), "tool", desc="Changes what the place allows.")

    items = [food, part_a, part_b, part_c, tool]
    areas: list[dict[str, Any]] = []
    start_id = "a0"

    objective_bits = {
        "assemble": f"Gather what the {place_names[0]} demands and assemble a way out of {domain['world']}.",
        "sequence": f"Perform the right order of {verbs[0]}/{verbs[1]}/{verbs[2]} before {domain['tone']} finishes you.",
        "threshold": f"Push the situation past a tipping point, then leave {domain['world']} while the window holds.",
        "trade": f"Make the one trade the place respects, then walk away owned by yourself.",
        "timing": f"Catch the brief alignment inside {domain['world']} and commit.",
        "correct_pick": f"Choose the only ending that does not collapse {domain['world']}.",
    }
    objective = objective_bits[win_mode]
    title = rng.choice(
        [
            f"{place_names[0]}",
            f"The {verbs[0].title()} Accord",
            f"{place_names[1]} Protocol",
            f"After {place_names[2]}",
        ]
    )
    premise = (
        f"You arrive in {domain['world']}. {domain['tone'].capitalize()}. "
        f"{objective}"
    )
    win_msg = rng.choice(
        [
            "The structure releases you. Air tastes like decisions that worked.",
            "You leave with the ending intact.",
            "Outside exists again. You use it.",
        ]
    )
    lose_msg = domain["fail"]

    flag_seq = [f"step_{i}" for i in range(3)]
    assembled = "assembled"
    window = "window_open"
    traded = "traded"
    threshold = "threshold_met"

    def finish_actions(area_id: str) -> list[dict[str, Any]]:
        """Win actions shaped by win_mode — never a boss fight."""
        out: list[dict[str, Any]] = []
        if win_mode == "assemble":
            out.append(
                {
                    "id": _id(rng, "assemble"),
                    "label": deck._fresh_label(["{v} the pieces into an exit", "fit every shard until an exit appears", "seat the last fragment and open the way"], v=verbs[0]),
                    "kind": "tool",
                    "required_tool_id": part_c["id"],
                    "require_flags": [f"has_{part_a['id']}", f"has_{part_b['id']}"],
                    "narrative": "Parts lock. A door that was a metaphor becomes wood — or light — or permission.",
                    "set_flags": [assembled],
                    "forbid_flags": [assembled],
                    "energy_cost": 8,
                }
            )
            out.append(
                {
                    "id": _id(rng, "leave"),
                    "label": deck._fresh_label(["take the assembled way out", "step through what you built", "leave by the door you invented"]),
                    "kind": "chance",
                    "require_flags": [assembled],
                    "success_chance": 1.0,
                    "narrative": "You commit.",
                    "success": {"narrative": win_msg, "win": True},
                    "failure": {"narrative": win_msg, "win": True},
                }
            )
        elif win_mode == "sequence":
            out.append(
                {
                    "id": _id(rng, "final_seq"),
                    "label": deck._fresh_label(["complete the {v} after the prior marks", "finish the sequence with a final {v}", "close the pattern with one last {v}"], v=verbs[2]),
                    "kind": "chance",
                    "require_flags": flag_seq[:],
                    "success_chance": 0.9,
                    "show_chance": True,
                    "narrative": "Order holds.",
                    "success": {"narrative": win_msg, "win": True},
                    "failure": {
                        "narrative": "Almost — the order slips. Reset the last mark and try again.",
                        "energy_delta": -8,
                    },
                }
            )
        elif win_mode == "threshold":
            out.append(
                {
                    "id": _id(rng, "push"),
                    "label": deck._fresh_label(["{v} until the place tips", "lean on the room until it yields", "press past the tipping line"], v=verbs[1]),
                    "kind": "universal",
                    "require_flags": [f"noticed_a0", "helped"],
                    "forbid_flags": [threshold],
                    "narrative": "Pressure changes quality. The threshold is real.",
                    "set_flags": [threshold],
                    "ticks": 2,
                }
            )
            out.append(
                {
                    "id": _id(rng, "exit_th"),
                    "label": deck._fresh_label(["cross while it still tips your way", "ride the tip out of here", "leave on the slant before it rights itself"]),
                    "kind": "chance",
                    "require_flags": [threshold],
                    "success_chance": 0.85,
                    "show_chance": True,
                    "narrative": "You move with the tip.",
                    "success": {"narrative": win_msg, "win": True},
                    "failure": {"narrative": "It tips back. Gather more pressure.", "energy_delta": -6},
                }
            )
        elif win_mode == "trade":
            out.append(
                {
                    "id": _id(rng, "trade"),
                    "label": deck._fresh_label(["offer the {i} in the only trade that counts", "hand over the {i} for passage", "pay with the {i} and nothing else"], i=part_c["name"]),
                    "kind": "tool",
                    "required_tool_id": part_c["id"],
                    "consume_item_id": part_c["id"],
                    "require_flags": ["counterparty_ready"],
                    "narrative": "Hands change. Rules change with them.",
                    "set_flags": [traded],
                    "forbid_flags": [traded],
                }
            )
            out.append(
                {
                    "id": _id(rng, "walk"),
                    "label": deck._fresh_label(["walk out under the new rule", "leave while the bargain still holds", "exit on the ink that just dried"]),
                    "kind": "chance",
                    "require_flags": [traded],
                    "success_chance": 1.0,
                    "narrative": "No one stops you.",
                    "success": {"narrative": win_msg, "win": True},
                    "failure": {"narrative": win_msg, "win": True},
                }
            )
        elif win_mode == "timing":
            out.append(
                {
                    "id": _id(rng, "open_window"),
                    "label": deck._fresh_label(["use the {i} to open a brief window", "pry a seam open with the {i}", "wake a short exit using the {i}"], i=tool["name"]),
                    "kind": "tool",
                    "required_tool_id": tool["id"],
                    "narrative": "A seam appears. It will not wait.",
                    "set_flags": [window],
                    "forbid_flags": [window],
                    "ticks": 1,
                }
            )
            out.append(
                {
                    "id": _id(rng, "commit"),
                    "label": deck._fresh_label(["commit through the seam now", "dive the seam before it seals", "take the gap while it breathes"]),
                    "kind": "chance",
                    "require_flags": [window],
                    "success_chance": 0.8,
                    "show_chance": True,
                    "narrative": "You do not hesitate.",
                    "success": {"narrative": win_msg, "win": True},
                    "failure": {
                        "narrative": "The seam pinches shut. Reopen it.",
                        "energy_delta": -10,
                    },
                }
            )
        else:  # correct_pick
            good = _id(rng, "pick_good")
            bad1 = _id(rng, "pick_bad1")
            bad2 = _id(rng, "pick_bad2")
            out.extend(
                [
                    {
                        "id": good,
                        "label": deck._fresh_label(["{v} the quiet option", "choose the muted path", "take the soft door"], v=verbs[0]),
                        "kind": "chance",
                        "require_flags": ["seen_choices"],
                        "success_chance": 1.0,
                        "narrative": "Quiet was correct.",
                        "success": {"narrative": win_msg, "win": True},
                        "failure": {"narrative": win_msg, "win": True},
                    },
                    {
                        "id": bad1,
                        "label": deck._fresh_label(["{v} the loud option", "grab the obvious lure", "force the noisy door"], v=verbs[1]),
                        "kind": "chance",
                        "require_flags": ["seen_choices"],
                        "success_chance": 0.15,
                        "show_chance": True,
                        "narrative": "Loud feels brave.",
                        "success": {"narrative": "Somehow loud works.", "win": True},
                        "failure": {"narrative": lose_msg, "lose": True},
                    },
                    {
                        "id": bad2,
                        "label": deck._fresh_label(["{v} the ornate option", "fall for the gilded bait", "touch the decorated lie"], v=verbs[2]),
                        "kind": "chance",
                        "require_flags": ["seen_choices"],
                        "success_chance": 0.15,
                        "show_chance": True,
                        "narrative": "Ornate feels earned.",
                        "success": {"narrative": "Ornate fools the world.", "win": True},
                        "failure": {
                            "narrative": "Ornate collapses. You retreat bruised.",
                            "health_delta": -15,
                        },
                    },
                ]
            )
        return out

    # Build topology-specific maps
    if topo == "single_phase":
        aid = "a0"
        acts = _baseline_actions(deck, aid, place_names[0], phase_flag=True)
        acts.append(
            {
                "id": _id(rng, "phase1"),
                "label": f"{verbs[0].title()} the first layer of the room",
                "kind": "universal",
                "narrative": f"The {place_names[0]} accepts a first change.",
                "set_flags": [flag_seq[0], "helped"],
                "forbid_flags": [flag_seq[0]],
                "grant_item_id": part_a["id"] if win_mode == "assemble" else None,
                "once_flag": f"has_{part_a['id']}" if win_mode == "assemble" else "p1",
            }
        )
        acts.append(
            {
                "id": _id(rng, "phase2"),
                "label": f"{verbs[1].title()} what the first change revealed",
                "kind": "energy",
                "energy_cost": rng.randint(6, 12),
                "require_flags": [flag_seq[0]],
                "narrative": "A second layer peels back.",
                "set_flags": [flag_seq[1], f"has_{part_b['id']}"] if win_mode == "assemble" else [flag_seq[1]],
                "grant_item_id": part_b["id"] if win_mode == "assemble" else tool["id"],
                "once_flag": "p2",
            }
        )
        acts.append(
            {
                "id": _id(rng, "phase3"),
                "label": f"Reveal the {part_c['name']}",
                "kind": "tool",
                "required_tool_id": tool["id"] if win_mode != "assemble" else part_b["id"],
                "require_flags": [flag_seq[1]],
                "narrative": "The last piece admits it was always here.",
                "grant_item_id": part_c["id"],
                "once_flag": f"has_{part_c['id']}",
                "set_flags": [flag_seq[2], "counterparty_ready", "seen_choices", f"has_{part_a['id']}", f"has_{part_b['id']}"],
            }
        )
        # clean None grant
        for a in acts:
            if a.get("grant_item_id") is None:
                a.pop("grant_item_id", None)
            if a.get("once_flag") is None:
                a.pop("once_flag", None)
        acts.extend(finish_actions(aid))
        acts.append(
            {
                "id": _id(rng, "eatspot"),
                "label": f"Find {food['name']}",
                "kind": "universal",
                "narrative": "Sustenance, improbably.",
                "grant_item_id": food["id"],
                "once_flag": "food_got",
            }
        )
        areas.append(
            {
                "id": aid,
                "name": place_names[0],
                "description": (
                    f"One chamber, many moods. {domain['tone'].capitalize()}. "
                    f"The room itself is the map."
                ),
                "actions": acts,
            }
        )

    elif topo == "hub":
        hub, s1, s2, s3 = "hub", "s1", "s2", "s3"
        # hub
        hub_acts = _baseline_actions(deck, hub, place_names[0], phase_flag=True)
        for sid, label, dest in [
            (s1, place_names[1], s1),
            (s2, place_names[2], s2),
            (s3, place_names[3], s3),
        ]:
            hub_acts.append(
                {
                    "id": _id(rng, "to", sid),
                    "label": f"Enter {label}",
                    "kind": "transition",
                    "target_area_id": dest,
                    "narrative": f"You leave the hub for {label}.",
                }
            )
        hub_acts.extend(finish_actions(hub))
        hub_acts.append(
            {
                "id": _id(rng, "hubfood"),
                "label": f"Claim {food['name']} from the hub stores",
                "kind": "universal",
                "grant_item_id": food["id"],
                "once_flag": "food_got",
                "narrative": "You eat like someone with a timetable.",
            }
        )
        # mark counterparty / choices on hub study
        hub_acts[0]["set_flags"] = ["noticed_a0", "counterparty_ready", "seen_choices"]
        areas.append(
            {
                "id": hub,
                "name": place_names[0] + " Hub",
                "description": f"Three mouths open off this center. {domain['tone'].capitalize()}.",
                "actions": hub_acts,
            }
        )
        spoke_parts = [part_a, part_b, part_c]
        spoke_flags = [flag_seq[0], flag_seq[1], flag_seq[2]]
        for i, sid in enumerate([s1, s2, s3]):
            acts = _baseline_actions(deck, sid, place_names[i + 1])
            acts.append(
                {
                    "id": _id(rng, sid, "claim"),
                    "label": f"{verbs[i].title()} the {spoke_parts[i]['name']}",
                    "kind": "energy" if i == 1 else "universal",
                    "energy_cost": 8 if i == 1 else 0,
                    "narrative": f"You secure the {spoke_parts[i]['name']}.",
                    "grant_item_id": spoke_parts[i]["id"],
                    "once_flag": f"has_{spoke_parts[i]['id']}",
                    "set_flags": [spoke_flags[i], f"has_{spoke_parts[i]['id']}", "helped"],
                }
            )
            if i == 2:
                acts.append(
                    {
                        "id": _id(rng, sid, "tool"),
                        "label": f"Also claim the {tool['name']}",
                        "kind": "universal",
                        "grant_item_id": tool["id"],
                        "once_flag": "tool_got",
                        "narrative": f"The {tool['name']} fits the work.",
                    }
                )
            acts.append(
                {
                    "id": _id(rng, sid, "back"),
                    "label": f"Return to {place_names[0]} Hub",
                    "kind": "transition",
                    "target_area_id": hub,
                    "narrative": "Back to the center.",
                }
            )
            areas.append(
                {
                    "id": sid,
                    "name": place_names[i + 1],
                    "description": f"A spoke of {domain['world']}. Purpose: {verbs[i]}.",
                    "actions": acts,
                }
            )
        start_id = hub

    elif topo == "loop":
        ids = ["l0", "l1", "l2", "l3"]
        for i, lid in enumerate(ids):
            nxt = ids[(i + 1) % 4]
            acts = _baseline_actions(deck, lid, place_names[i], phase_flag=(i == 0))
            if i == 0:
                acts[0]["set_flags"] = ["noticed_a0", "seen_choices", "counterparty_ready"]
            acts.append(
                {
                    "id": _id(rng, lid, "mark"),
                    "label": _cap(
                        deck.rng.choice(
                            [
                                f"{verbs[i % 3]} a unique seal at {place_names[i]}",
                                f"press circuit notch {i + 1} into {place_names[i]}",
                                f"brand step {i + 1} onto the loop here",
                                f"leave {verbs[i % 3]}-sign #{i + 1} only in this segment",
                            ]
                        )
                    ),
                    "kind": "universal",
                    "narrative": f"Mark {i + 1} of the loop settles.",
                    "set_flags": [flag_seq[min(i, 2)], "helped"],
                    "forbid_flags": [flag_seq[min(i, 2)]] if i < 3 else [],
                    "once_flag": f"mark_{i}",
                }
            )
            if i == 1:
                acts.append(
                    {
                        "id": _id(rng, lid, "pa"),
                        "label": f"Lift the {part_a['name']}",
                        "kind": "universal",
                        "grant_item_id": part_a["id"],
                        "once_flag": f"has_{part_a['id']}",
                        "set_flags": [f"has_{part_a['id']}"],
                        "narrative": "Taken from the loop's first gift.",
                    }
                )
            if i == 2:
                acts.append(
                    {
                        "id": _id(rng, lid, "pb"),
                        "label": f"Lift the {part_b['name']}",
                        "kind": "universal",
                        "grant_item_id": part_b["id"],
                        "once_flag": f"has_{part_b['id']}",
                        "set_flags": [f"has_{part_b['id']}"],
                        "narrative": "The second gift.",
                    }
                )
                acts.append(
                    {
                        "id": _id(rng, lid, "tol"),
                        "label": f"Claim {tool['name']}",
                        "kind": "universal",
                        "grant_item_id": tool["id"],
                        "once_flag": "tool_got",
                        "narrative": "Useful against the loop's stubbornness.",
                    }
                )
            if i == 3:
                acts.append(
                    {
                        "id": _id(rng, lid, "pc"),
                        "label": f"Lift the {part_c['name']}",
                        "kind": "universal",
                        "grant_item_id": part_c["id"],
                        "once_flag": f"has_{part_c['id']}",
                        "set_flags": [f"has_{part_c['id']}"],
                        "narrative": "The loop's closing gift.",
                    }
                )
                acts.append(
                    {
                        "id": _id(rng, lid, "food"),
                        "label": f"Scavenge {food['name']}",
                        "kind": "universal",
                        "grant_item_id": food["id"],
                        "once_flag": "food_got",
                        "narrative": "Even loops must feed their walkers.",
                    }
                )
                acts.extend(finish_actions(lid))
            acts.append(
                {
                    "id": _id(rng, lid, "next"),
                    "label": f"Follow the circuit toward {place_names[(i+1)%4]}",
                    "kind": "transition",
                    "target_area_id": nxt,
                    "narrative": "The path curves without asking.",
                    "energy_cost": 4,
                }
            )
            areas.append(
                {
                    "id": lid,
                    "name": place_names[i],
                    "description": f"Segment {i+1} of a closed path through {domain['world']}.",
                    "actions": acts,
                }
            )
        start_id = "l0"

    elif topo == "layers":
        low, high = "low", "high"
        low_acts = _baseline_actions(deck, low, place_names[0], phase_flag=True)
        low_acts[0]["set_flags"] = ["noticed_a0"]
        low_acts.extend(
            [
                {
                    "id": _id(rng, "get_a"),
                    "label": f"{verbs[0].title()} up the {part_a['name']}",
                    "kind": "universal",
                    "grant_item_id": part_a["id"],
                    "once_flag": f"has_{part_a['id']}",
                    "set_flags": [flag_seq[0], f"has_{part_a['id']}", "helped"],
                    "narrative": "Lower layer yields.",
                },
                {
                    "id": _id(rng, "get_tool"),
                    "label": f"Find the {tool['name']}",
                    "kind": "energy",
                    "energy_cost": 7,
                    "grant_item_id": tool["id"],
                    "once_flag": "tool_got",
                    "narrative": "Hidden under the lower work.",
                },
                {
                    "id": _id(rng, "food"),
                    "label": f"Uncover {food['name']}",
                    "kind": "universal",
                    "grant_item_id": food["id"],
                    "once_flag": "food_got",
                    "narrative": "Lower kitchens never sleep.",
                },
                {
                    "id": _id(rng, "ascend"),
                    "label": f"Ascend using the {tool['name']}",
                    "kind": "transition",
                    "target_area_id": high,
                    "gate": {
                        "status": "closed",
                        "requires_tool_id": tool["id"],
                        "energy_cost": 8,
                    },
                    "narrative": "Up becomes allowed.",
                },
            ]
        )
        high_acts = _baseline_actions(deck, high, place_names[1])
        high_acts.extend(
            [
                {
                    "id": _id(rng, "get_b"),
                    "label": f"{verbs[1].title()} the {part_b['name']}",
                    "kind": "universal",
                    "grant_item_id": part_b["id"],
                    "once_flag": f"has_{part_b['id']}",
                    "set_flags": [flag_seq[1], f"has_{part_b['id']}"],
                    "narrative": "Upper layer answers.",
                },
                {
                    "id": _id(rng, "get_c"),
                    "label": f"{verbs[2].title()} the {part_c['name']}",
                    "kind": "universal",
                    "grant_item_id": part_c["id"],
                    "once_flag": f"has_{part_c['id']}",
                    "set_flags": [flag_seq[2], f"has_{part_c['id']}", "counterparty_ready", "seen_choices"],
                    "narrative": "The upper prize.",
                },
                {
                    "id": _id(rng, "down"),
                    "label": f"Descend to {place_names[0]}",
                    "kind": "transition",
                    "target_area_id": low,
                    "narrative": "Gravity still works.",
                },
            ]
        )
        high_acts.extend(finish_actions(high))
        areas.extend(
            [
                {
                    "id": low,
                    "name": place_names[0] + " (Below)",
                    "description": f"Underlayer of {domain['world']}.",
                    "actions": low_acts,
                },
                {
                    "id": high,
                    "name": place_names[1] + " (Above)",
                    "description": f"Overlayer. Access is earned.",
                    "actions": high_acts,
                },
            ]
        )
        start_id = low

    elif topo == "fork":
        start, left, right, merge = "start", "left", "right", "merge"
        st_acts = _baseline_actions(deck, start, place_names[0], phase_flag=True)
        st_acts[0]["set_flags"] = ["noticed_a0"]
        st_acts.extend(
            [
                {
                    "id": _id(rng, "food"),
                    "label": f"Pocket {food['name']}",
                    "kind": "universal",
                    "grant_item_id": food["id"],
                    "once_flag": "food_got",
                    "narrative": "For the fork ahead.",
                },
                {
                    "id": _id(rng, "tol"),
                    "label": f"Take the {tool['name']}",
                    "kind": "universal",
                    "grant_item_id": tool["id"],
                    "once_flag": "tool_got",
                    "narrative": "Either path may need it.",
                },
                {
                    "id": _id(rng, "go_l"),
                    "label": f"Take the {place_names[1]} fork",
                    "kind": "transition",
                    "target_area_id": left,
                    "narrative": "Left smells like one kind of mistake.",
                },
                {
                    "id": _id(rng, "go_r"),
                    "label": f"Take the {place_names[2]} fork",
                    "kind": "transition",
                    "target_area_id": right,
                    "narrative": "Right smells like another.",
                },
            ]
        )
        left_acts = _baseline_actions(deck, left, place_names[1])
        left_acts.extend(
            [
                {
                    "id": _id(rng, "la"),
                    "label": f"{verbs[0].title()} the {part_a['name']}",
                    "kind": "universal",
                    "grant_item_id": part_a["id"],
                    "set_flags": [flag_seq[0], f"has_{part_a['id']}", "helped"],
                    "once_flag": f"has_{part_a['id']}",
                    "narrative": "Left path payment.",
                },
                {
                    "id": _id(rng, "lm"),
                    "label": f"Push on to {place_names[3]}",
                    "kind": "transition",
                    "target_area_id": merge,
                    "narrative": "Paths remember how to meet.",
                },
            ]
        )
        right_acts = _baseline_actions(deck, right, place_names[2])
        right_acts.extend(
            [
                {
                    "id": _id(rng, "rb"),
                    "label": f"{verbs[1].title()} the {part_b['name']}",
                    "kind": "energy",
                    "energy_cost": 9,
                    "grant_item_id": part_b["id"],
                    "set_flags": [flag_seq[1], f"has_{part_b['id']}", "helped"],
                    "once_flag": f"has_{part_b['id']}",
                    "narrative": "Right path payment.",
                },
                {
                    "id": _id(rng, "rm"),
                    "label": f"Push on to {place_names[3]}",
                    "kind": "transition",
                    "target_area_id": merge,
                    "narrative": "Convergence.",
                },
            ]
        )
        merge_acts = _baseline_actions(deck, merge, place_names[3])
        merge_acts.extend(
            [
                {
                    "id": _id(rng, "mc"),
                    "label": f"{verbs[2].title()} the {part_c['name']} at the join",
                    "kind": "tool",
                    "required_tool_id": tool["id"],
                    "grant_item_id": part_c["id"],
                    "set_flags": [flag_seq[2], f"has_{part_c['id']}", "counterparty_ready", "seen_choices"],
                    "once_flag": f"has_{part_c['id']}",
                    "narrative": "The join pays those who arrived.",
                },
                {
                    "id": _id(rng, "back_s"),
                    "label": f"Retreat toward {place_names[0]}",
                    "kind": "transition",
                    "target_area_id": start,
                    "narrative": "You can still rechoose.",
                },
            ]
        )
        merge_acts.extend(finish_actions(merge))
        areas.extend(
            [
                {"id": start, "name": place_names[0], "description": f"The split in {domain['world']}.", "actions": st_acts},
                {"id": left, "name": place_names[1], "description": "Fork A.", "actions": left_acts},
                {"id": right, "name": place_names[2], "description": "Fork B.", "actions": right_acts},
                {"id": merge, "name": place_names[3], "description": "Where forks forget they argued.", "actions": merge_acts},
            ]
        )
        start_id = start

    else:  # chain
        n = rng.randint(3, 4)
        ids = [f"c{i}" for i in range(n)]
        for i, cid in enumerate(ids):
            acts = _baseline_actions(deck, cid, place_names[i], phase_flag=(i == 0))
            if i == 0:
                acts[0]["set_flags"] = ["noticed_a0"]
                acts.append(
                    {
                        "id": _id(rng, "food"),
                        "label": f"Secure {food['name']}",
                        "kind": "universal",
                        "grant_item_id": food["id"],
                        "once_flag": "food_got",
                        "narrative": "First link feeds you.",
                    }
                )
                acts.append(
                    {
                        "id": _id(rng, "pa"),
                        "label": f"{verbs[0].title()} the {part_a['name']}",
                        "kind": "universal",
                        "grant_item_id": part_a["id"],
                        "once_flag": f"has_{part_a['id']}",
                        "set_flags": [flag_seq[0], f"has_{part_a['id']}", "helped"],
                        "narrative": "Chain begins.",
                    }
                )
            elif i == 1:
                acts.append(
                    {
                        "id": _id(rng, "pb"),
                        "label": f"{verbs[1].title()} the {part_b['name']}",
                        "kind": "energy",
                        "energy_cost": 8,
                        "grant_item_id": part_b["id"],
                        "once_flag": f"has_{part_b['id']}",
                        "set_flags": [flag_seq[1], f"has_{part_b['id']}"],
                        "narrative": "Second link.",
                    }
                )
                acts.append(
                    {
                        "id": _id(rng, "tol"),
                        "label": f"Claim {tool['name']}",
                        "kind": "universal",
                        "grant_item_id": tool["id"],
                        "once_flag": "tool_got",
                        "narrative": "Middle tools matter.",
                    }
                )
            elif i == n - 1:
                acts.append(
                    {
                        "id": _id(rng, "pc"),
                        "label": f"{verbs[2].title()} the {part_c['name']}",
                        "kind": "tool",
                        "required_tool_id": tool["id"],
                        "grant_item_id": part_c["id"],
                        "once_flag": f"has_{part_c['id']}",
                        "set_flags": [flag_seq[2], f"has_{part_c['id']}", "counterparty_ready", "seen_choices"],
                        "narrative": "Last link.",
                    }
                )
                acts.extend(finish_actions(cid))
            else:
                acts.append(
                    {
                        "id": _id(rng, "mid"),
                        "label": f"{verbs[1].title()} the middle obligation",
                        "kind": "universal",
                        "set_flags": [flag_seq[1], "helped"],
                        "forbid_flags": [flag_seq[1]],
                        "narrative": "The chain tightens usefully.",
                    }
                )
            if i < n - 1:
                acts.append(
                    {
                        "id": _id(rng, "next"),
                        "label": f"Advance to {place_names[i+1]}",
                        "kind": "transition",
                        "target_area_id": ids[i + 1],
                        "narrative": "Forward is a decision.",
                        "energy_cost": 3,
                    }
                )
            if i > 0:
                acts.append(
                    {
                        "id": _id(rng, "back"),
                        "label": f"Fall back to {place_names[i-1]}",
                        "kind": "transition",
                        "target_area_id": ids[i - 1],
                        "narrative": "Backward is allowed.",
                    }
                )
            areas.append(
                {
                    "id": cid,
                    "name": place_names[i],
                    "description": f"Link {i+1} in a chain through {domain['world']}.",
                    "actions": acts,
                }
            )
        start_id = ids[0]

    _freshen_labels(deck, areas, verbs, items)
    _ensure_unique_action_labels(deck, areas)

    # Sanitize actions: drop empty forbid, None grants; strip combat if any slipped
    for area in areas:
        clean = []
        for act in area["actions"]:
            if act.get("kind") == "combat":
                continue
            act = {k: v for k, v in act.items() if v not in (None, [], ())}
            if "forbid_flags" in act and not act["forbid_flags"]:
                del act["forbid_flags"]
            if "energy_cost" in act and act["energy_cost"] == 0:
                del act["energy_cost"]
            clean.append(act)
        area["actions"] = clean

    spec = {
        "title": title,
        "premise": premise,
        "objective": objective,
        "opening": premise,
        "win_message": win_msg,
        "lose_message": lose_msg,
        "generated": True,
        "source": "procedural",
        "topology": topo,
        "win_mode": win_mode,
        "start_area_id": start_id,
        "exit_area_ids": [],
        "character": {
            "health": rng.randint(78, 90),
            "satiation": rng.randint(60, 80),
            "energy": rng.randint(65, 85),
        },
        "clock": {
            "satiation_loss_per_tick": rng.choice([3, 4, 5, 6]),
            "energy_gain_per_tick": 3,
            "health_loss_per_tick": 5,
        },
        "items": items,
        "areas": areas,
    }

    blob = json.dumps(spec).lower()
    if _banned_hits(blob):
        # regenerate once with different seed offset
        return procedural_scenario(random.Random(rng.randint(1, 10_000_000)))
    return spec


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def load_dotenv(path: str | os.PathLike[str] | None = None) -> None:
    """Load KEY=VALUE pairs from .env into os.environ (does not override existing)."""
    env_path = path or os.path.join(os.path.dirname(__file__), "..", ".env")
    try:
        with open(env_path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        value = value.strip().strip("'").strip('"')
        if name and name not in os.environ:
            os.environ[name] = value


def _llm_openrouter(prompt: str, *, trace_id: str | None = None) -> dict[str, Any]:
    from .observability import log_llm_attempt, new_trace_id

    load_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("no openrouter key")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-5.6-terra")
    system = _LLM_SYSTEM
    tid = trace_id or new_trace_id()
    body = json.dumps(
        {
            "model": model,
            "temperature": 1.15,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "http://127.0.0.1:8765",
            "X-Title": "ai-cyoa",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=70, context=_ssl_context()) as resp:
            http_status = getattr(resp, "status", 200)
            payload = json.loads(resp.read().decode("utf-8"))
        raw = payload["choices"][0]["message"]["content"]
        parsed = _extract_json(raw)
        log_llm_attempt(
            trace_id=tid,
            model=model,
            system=system,
            user=prompt,
            raw_content=raw,
            parsed=parsed,
            http_status=http_status,
            openrouter_id=payload.get("id"),
        )
        return parsed
    except Exception as exc:
        raw = None
        http_status = None
        if isinstance(exc, urllib.error.HTTPError):
            http_status = exc.code
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                raw = None
        log_llm_attempt(
            trace_id=tid,
            model=model,
            system=system,
            user=prompt,
            raw_content=raw,
            error=f"{type(exc).__name__}: {exc}",
            http_status=http_status,
        )
        raise


def generate_scenario(prefer_llm: bool = True) -> dict[str, Any]:
    from .observability import LOG_DIR, log_generation, new_trace_id

    trace_id = new_trace_id()
    llm_path: str | None = None
    reject_reason: str | None = None
    last_bad: dict[str, Any] | None = None

    if prefer_llm:
        for attempt in range(2):
            if attempt == 0:
                prompt = _LLM_USER
            else:
                prompt = (
                    f"{_LLM_USER}\n\n"
                    f"PREVIOUS JSON FAILED VALIDATION: {reject_reason}. "
                    f"{_LLM_REPAIR_HINTS}"
                )
                if last_bad is not None:
                    prompt += (
                        "\nBroken JSON to repair (fix structure, keep the concept if possible):\n"
                        + json.dumps(last_bad)[:6000]
                    )
            try:
                spec = _llm_openrouter(prompt, trace_id=trace_id)
                matches = sorted(LOG_DIR.glob(f"*_{trace_id}_request.json"))
                llm_path = str(matches[-1]) if matches else None

                reason = _validate_llm_spec(spec)
                if reason:
                    reject_reason = reason
                    last_bad = spec
                    continue

                spec["generated"] = True
                spec["source"] = "llm"
                spec["trace_id"] = trace_id
                log_generation(
                    trace_id=trace_id,
                    preview_id=None,
                    final_spec=spec,
                    llm_accepted=True,
                    llm_path=llm_path,
                )
                return spec
            except (
                RuntimeError,
                urllib.error.URLError,
                urllib.error.HTTPError,
                KeyError,
                json.JSONDecodeError,
                TimeoutError,
            ) as exc:
                reject_reason = f"exception: {type(exc).__name__}: {exc}"
                matches = sorted(LOG_DIR.glob(f"*_{trace_id}_request.json"))
                llm_path = str(matches[-1]) if matches else llm_path
                break

    spec = procedural_scenario()
    spec["trace_id"] = trace_id
    log_generation(
        trace_id=trace_id,
        preview_id=None,
        final_spec=spec,
        llm_accepted=False,
        reject_reason=reject_reason or ("llm_disabled" if not prefer_llm else "unknown"),
        llm_path=llm_path,
    )
    return spec


def preview_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": spec.get("title", "Untitled"),
        "premise": spec.get("premise", ""),
        "objective": spec.get("objective", ""),
        "source": spec.get("source", "unknown"),
        "generated": bool(spec.get("generated", False)),
        "topology": spec.get("topology"),
        "win_mode": spec.get("win_mode"),
    }
