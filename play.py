#!/usr/bin/env python3
"""Terminal play loop for Abandoned Cottage."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cyoa import create_game
from cyoa.types import GameStatus


def _bar(value: int, width: int = 20) -> str:
    filled = round((value / 100) * width)
    return "█" * filled + "░" * (width - filled)


def _print_status(game) -> None:
    c = game.state.character
    area = game.current_area()
    hungry = "hungry" if c.is_hungry else "satiated"
    tired = "fatigued" if c.is_fatigued else "energized"
    print()
    print("═" * 56)
    print(f"  {game.title}   ·   t={game.state.t}   ·   {area.name}")
    print("─" * 56)
    print(f"  Health     [{_bar(c.health)}] {c.health}")
    print(f"  Satiation  [{_bar(c.satiation)}] {c.satiation}  ({hungry})")
    print(f"  Energy     [{_bar(c.energy)}] {c.energy}  ({tired})")
    if c.items:
        names = ", ".join(i.name for i in c.items)
        print(f"  Items      {names}")
    else:
        print("  Items      (none)")
    print("─" * 56)
    print(f"  {area.description}")
    print("═" * 56)


def main() -> None:
    game = create_game()
    print(f"\n{game.title}")
    print(game.premise)
    for line in game.state.log:
        print(f"\n› {line}")

    while game.status == GameStatus.PLAYING:
        _print_status(game)
        actions = game.actions()
        print("\nWhat do you do?\n")
        for i, action in enumerate(actions, start=1):
            mark = " " if action["available"] else "✗"
            extra = ""
            if action.get("energy_cost"):
                extra += f"  [-{action['energy_cost']} energy]"
            if (
                action.get("show_chance")
                and action.get("resolved_chance") is not None
                and action["available"]
            ):
                extra += f"  [{round(action['resolved_chance'] * 100)}%]"
            if not action["available"]:
                extra += f"  ({action['blocked_reason']})"
            print(f"  {mark} {i}. {action['label']}{extra}")

        print("  · 0. Quit")
        raw = input("\nChoice: ").strip()
        if raw in {"0", "q", "quit"}:
            print("You leave the story untold.")
            return
        if not raw.isdigit() or not (1 <= int(raw) <= len(actions)):
            print("Pick a numbered action.")
            continue
        action = actions[int(raw) - 1]
        if not action["available"]:
            print(action["blocked_reason"])
            continue
        message = game.act(action["id"])
        print(f"\n› {message}")

    _print_status(game)
    if game.status == GameStatus.WON:
        print("\n★ Freedom beyond the bridge.\n")
    else:
        print("\n† You fall. The cottage waits.\n")


if __name__ == "__main__":
    main()
