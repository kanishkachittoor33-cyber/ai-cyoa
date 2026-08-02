"""Global clock: time elapses and mutates character vitals."""

from __future__ import annotations

from .types import CharacterState, ClockConfig, _clamp


def apply_tick(character: CharacterState, cfg: ClockConfig | None = None) -> CharacterState:
    """Apply one unit of elapsed time.

    Rules:
    - Always: satiation decreases (hunger increases)
    - If not hungry: energy increases
    - If satiation is depleted (0): health decreases each tick
    """
    cfg = cfg or ClockConfig()
    satiation = _clamp(character.satiation - cfg.satiation_loss_per_tick)
    energy = character.energy

    if satiation >= 51:
        energy = _clamp(energy + cfg.energy_gain_per_tick)

    health = character.health
    if satiation <= 0:
        health = _clamp(health - cfg.health_loss_per_tick)

    return character.with_stats(health=health, satiation=satiation, energy=energy)


def apply_ticks(
    character: CharacterState,
    ticks: int,
    cfg: ClockConfig | None = None,
) -> CharacterState:
    result = character
    for _ in range(max(0, ticks)):
        result = apply_tick(result, cfg)
    return result
