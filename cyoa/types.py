from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Optional


class ItemKind(str, Enum):
    TOOL = "tool"
    WEAPON = "weapon"
    FOOD = "food"
    DRINK = "drink"
    KEY = "key"
    LORE = "lore"
    MATERIAL = "material"


class ActionKind(str, Enum):
    UNIVERSAL = "universal"
    ENERGY = "energy"
    TOOL = "tool"
    TRANSITION = "transition"
    COMBAT = "combat"
    CHANCE = "chance"


class GateStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class GameStatus(str, Enum):
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    kind: ItemKind
    satiation_restore: int = 0
    energy_restore: int = 0
    health_restore: int = 0
    description: str = ""
    sharpened: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind.value,
            "satiation_restore": self.satiation_restore,
            "energy_restore": self.energy_restore,
            "health_restore": self.health_restore,
            "description": self.description,
            "sharpened": self.sharpened,
        }


@dataclass(frozen=True)
class TransitionGate:
    status: GateStatus = GateStatus.OPEN
    requires_tool_id: Optional[str] = None
    requires_any_item_ids: tuple[str, ...] = ()
    energy_cost: int = 0
    min_energy: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "requires_tool_id": self.requires_tool_id,
            "requires_any_item_ids": list(self.requires_any_item_ids),
            "energy_cost": self.energy_cost,
            "min_energy": self.min_energy,
        }


@dataclass(frozen=True)
class ChanceOutcome:
    """One branch of a probabilistic resolution."""

    narrative: str
    health_delta: int = 0
    satiation_delta: int = 0
    energy_delta: int = 0
    target_area_id: Optional[str] = None
    grant_item_id: Optional[str] = None
    remove_item_ids: tuple[str, ...] = ()
    transform_item: Optional[tuple[str, str]] = None  # (from_id, to_id)
    set_flags: tuple[str, ...] = ()
    unlock_action_ids: tuple[str, ...] = ()
    win: bool = False
    lose: bool = False


@dataclass(frozen=True)
class LoadoutChance:
    """First matching loadout (all listed item ids present) sets success chance."""

    item_ids: tuple[str, ...]
    chance: float  # 0.0–1.0


@dataclass(frozen=True)
class AreaAction:
    id: str
    label: str
    kind: ActionKind
    narrative: str = ""
    energy_cost: int = 0
    required_tool_id: Optional[str] = None
    required_any_item_ids: tuple[str, ...] = ()
    target_area_id: Optional[str] = None
    gate: Optional[TransitionGate] = None
    grant_item_id: Optional[str] = None
    consume_item_id: Optional[str] = None
    transform_item: Optional[tuple[str, str]] = None
    health_delta: int = 0
    satiation_delta: int = 0
    energy_delta: int = 0
    unlock_action_ids: tuple[str, ...] = ()
    set_flags: tuple[str, ...] = ()
    require_flags: tuple[str, ...] = ()
    forbid_flags: tuple[str, ...] = ()
    once_flag: Optional[str] = None  # if set and already present, action hidden/disabled
    advances_clock: bool = True
    ticks: int = 1
    # Chance / combat
    success_chance: Optional[float] = None
    loadout_chances: tuple[LoadoutChance, ...] = ()
    success: Optional[ChanceOutcome] = None
    failure: Optional[ChanceOutcome] = None
    show_chance: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind.value,
            "narrative": self.narrative,
            "energy_cost": self.energy_cost,
            "required_tool_id": self.required_tool_id,
            "required_any_item_ids": list(self.required_any_item_ids),
            "target_area_id": self.target_area_id,
            "gate": self.gate.to_dict() if self.gate else None,
            "grant_item_id": self.grant_item_id,
            "consume_item_id": self.consume_item_id,
            "health_delta": self.health_delta,
            "satiation_delta": self.satiation_delta,
            "energy_delta": self.energy_delta,
            "unlock_action_ids": list(self.unlock_action_ids),
            "set_flags": list(self.set_flags),
            "once_flag": self.once_flag,
            "advances_clock": self.advances_clock,
            "ticks": self.ticks,
            "success_chance": self.success_chance,
            "show_chance": self.show_chance,
        }


@dataclass
class Area:
    id: str
    name: str
    description: str
    actions: list[AreaAction] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class MapGraph:
    areas: dict[str, Area]
    start_area_id: str
    exit_area_ids: tuple[str, ...] = ()
    win_message: str = "You are free."
    lose_message: str = "Your story ends here."

    def area(self, area_id: str) -> Area:
        return self.areas[area_id]


@dataclass
class CharacterState:
    health: int = 80
    satiation: int = 70
    energy: int = 70
    items: list[Item] = field(default_factory=list)
    location_id: str = ""

    @property
    def is_hungry(self) -> bool:
        return self.satiation <= 50

    @property
    def is_fatigued(self) -> bool:
        return self.energy <= 50

    @property
    def is_satiated(self) -> bool:
        return self.satiation >= 51

    @property
    def is_energized(self) -> bool:
        return self.energy >= 51

    def has_item(self, item_id: str) -> bool:
        return any(i.id == item_id for i in self.items)

    def has_any(self, item_ids: tuple[str, ...] | list[str]) -> bool:
        return any(self.has_item(i) for i in item_ids)

    def get_item(self, item_id: str) -> Optional[Item]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def with_stats(
        self,
        *,
        health: Optional[int] = None,
        satiation: Optional[int] = None,
        energy: Optional[int] = None,
    ) -> CharacterState:
        return replace(
            self,
            health=_clamp(health if health is not None else self.health),
            satiation=_clamp(satiation if satiation is not None else self.satiation),
            energy=_clamp(energy if energy is not None else self.energy),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "health": self.health,
            "satiation": self.satiation,
            "energy": self.energy,
            "is_hungry": self.is_hungry,
            "is_fatigued": self.is_fatigued,
            "items": [i.to_dict() for i in self.items],
            "location_id": self.location_id,
        }


@dataclass
class ClockConfig:
    satiation_loss_per_tick: int = 4
    energy_gain_per_tick: int = 3
    health_loss_per_tick: int = 5


@dataclass
class GameState:
    t: int
    character: CharacterState
    status: GameStatus = GameStatus.PLAYING
    unlocked_action_ids: set[str] = field(default_factory=set)
    opened_gates: set[str] = field(default_factory=set)
    flags: set[str] = field(default_factory=set)
    log: list[str] = field(default_factory=list)
    world_items: dict[str, Item] = field(default_factory=dict)
    rng_seed: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "t": self.t,
            "character": self.character.to_dict(),
            "status": self.status.value,
            "unlocked_action_ids": sorted(self.unlocked_action_ids),
            "opened_gates": sorted(self.opened_gates),
            "flags": sorted(self.flags),
            "log": self.log[-12:],
        }


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))
