"""Game session orchestration."""

from __future__ import annotations

from typing import Any, Optional

from .actions import available_actions, perform_action
from .scenario_builder import build_from_spec
from .scenarios.abandoned_cottage import build_abandoned_cottage
from .types import ClockConfig, GameState, GameStatus, MapGraph


class Game:
    def __init__(
        self,
        map_graph: MapGraph,
        state: GameState,
        clock: ClockConfig | None = None,
        title: str = "Adventure",
        premise: str = "",
        objective: str = "",
        scenario_id: Optional[str] = None,
        spec: Optional[dict[str, Any]] = None,
        adventure_id: Optional[str] = None,
    ):
        self.map_graph = map_graph
        self.state = state
        self.clock = clock or ClockConfig()
        self.title = title
        self.premise = premise
        self.objective = objective
        self.scenario_id = scenario_id
        self.spec = spec
        self.adventure_id = adventure_id

    @property
    def status(self) -> GameStatus:
        return self.state.status

    def current_area(self):
        return self.map_graph.area(self.state.character.location_id)

    def actions(self) -> list[dict]:
        return available_actions(self.map_graph, self.state)

    def act(self, action_id: str) -> str:
        result = perform_action(self.map_graph, self.state, action_id, self.clock)
        self.state = result.state
        return result.message

    def snapshot(self) -> dict:
        area = self.current_area()
        return {
            "title": self.title,
            "premise": self.premise,
            "objective": self.objective,
            "scenario_id": self.scenario_id,
            "adventure_id": self.adventure_id,
            "area": area.to_dict(),
            "state": self.state.to_dict(),
            "actions": self.actions(),
        }


def _game_from_parts(map_graph, state, meta, *, scenario_id=None, spec=None) -> Game:
    return Game(
        map_graph=map_graph,
        state=state,
        clock=meta["clock"],
        title=meta["title"],
        premise=meta["premise"],
        objective=meta.get("objective", ""),
        scenario_id=scenario_id,
        spec=spec,
    )


def create_game(scenario: str = "abandoned_cottage") -> Game:
    if scenario in ("abandoned_cottage", "lost_in_the_woods"):
        map_graph, state, meta = build_abandoned_cottage()
        meta = {
            **meta,
            "objective": meta.get(
                "objective",
                "Defeat the bridge troll (or slip past) to win your freedom.",
            ),
        }
        if scenario == "lost_in_the_woods":
            meta = {
                **meta,
                "title": "Lost in the Woods",
                "premise": (
                    "An abandoned cottage at the edge of river and forest. "
                    "Gather what you need — then face the troll under the bridge."
                ),
            }
        return _game_from_parts(
            map_graph, state, meta, scenario_id=scenario, spec=None
        )
    raise ValueError(f"Unknown scenario: {scenario}")


def create_game_from_spec(spec: dict[str, Any]) -> Game:
    map_graph, state, meta = build_from_spec(spec)
    return _game_from_parts(map_graph, state, meta, scenario_id=None, spec=spec)
