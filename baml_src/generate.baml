// LLM functions that invent / repair playable CYOA scenarios via OpenRouter.

function GenerateScenario() -> Scenario {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    You create playable CYOA scenario JSON for a game engine.
    Every generation must be structurally NEW: different map shape, win condition, and verbs.
    Do NOT use these whole words/themes: troll, cottage, hatchet, axe, scroll, grindstone,
    thicket, berry, snake, shed, woods, sharpen, weakness. No combat kind.

    ENGINE WIN RULES: entering any id in exit_area_ids wins immediately.
    Therefore set exit_area_ids to [] and win ONLY via an action with win=true
    (or success.win=true) on a late/gated step that requires items, flags, or a closed gate.
    When an action finds/gives an item, set grant_item_id (or success.grant_item_id)
    to a real items[].id — narrative alone does not grant.
    All target_area_id / required_tool_id / gate requires_* must reference real ids.
    Build a multi-step adventure: at least 3 areas, 6+ actions, and at least one
    non-transition action. The player must not be able to win in one free move.
    objective and labels must be plain English.

    {{ _.role("user") }}
    Invent a COMPLETELY new playable adventure.
    Vary topology (hub/chain/loop/phases/fork) and win rule
    (assemble/sequence/trade/timing/choice).
    Include at least one win=true action that requires prior progress
    (items granted via grant_item_id and/or flags/gates).

    {{ ctx.output_format }}
  "#
}

function RepairScenario(reject_reason: string, broken_json: string) -> Scenario {
  client OpenRouter
  prompt #"
    {{ _.role("system") }}
    You fix invalid CYOA scenario JSON for a game engine.
    Set exit_area_ids to []. Win only with win=true on a late/gated action.
    items[].kind must be tool|weapon|food|drink|key|lore|material.
    Use grant_item_id when finding items. No bare strings in actions[].
    No instant win: start must not reach an exit or win=true action via ungated moves.
    Do NOT use: troll, cottage, hatchet, axe, scroll, grindstone, thicket, berry,
    snake, shed, woods, sharpen, weakness.

    {{ _.role("user") }}
    PREVIOUS JSON FAILED VALIDATION: {{ reject_reason }}

    Return a FIXED complete scenario. Keep the concept if possible.

    Broken JSON:
    {{ broken_json }}

    {{ ctx.output_format }}
  "#
}
