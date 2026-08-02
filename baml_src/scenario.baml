// Typed CYOA scenario schema returned by the LLM.
// The return type IS the JSON schema the model must produce.
// Enum variants must be PascalCase; @alias keeps engine JSON lowercase.

enum ItemKind {
  Tool @alias("tool")
  Weapon @alias("weapon")
  Food @alias("food")
  Drink @alias("drink")
  Key @alias("key")
  Lore @alias("lore")
  Material @alias("material")
}

enum ActionKind {
  Universal @alias("universal")
  Energy @alias("energy")
  Tool @alias("tool")
  Transition @alias("transition")
  Chance @alias("chance")
}

enum GateStatus {
  Open @alias("open")
  Closed @alias("closed")
}

class CharacterStats {
  health int @description("Starting health, typically 70-95")
  satiation int @description("Starting satiation, typically 55-85")
  energy int @description("Starting energy, typically 60-90")
}

class ClockConfig {
  satiation_loss_per_tick int @description("Usually 3-6")
  energy_gain_per_tick int @description("Usually 2-4")
  health_loss_per_tick int @description("Usually 4-6")
}

class Item {
  id string @description("Stable snake_case id referenced by actions")
  name string
  kind ItemKind
  description string
  satiation_restore int? @description("For food/drink; omit otherwise")
  energy_restore int? @description("For food/drink; omit otherwise")
  health_restore int? @description("For food/drink; omit otherwise")
}

class TransitionGate {
  status GateStatus @description("closed means blocked until requirements met")
  requires_tool_id string?
  requires_any_item_ids string[]?
  energy_cost int?
  min_energy int?
}

class ChanceOutcome {
  narrative string
  health_delta int?
  satiation_delta int?
  energy_delta int?
  target_area_id string?
  grant_item_id string?
  remove_item_ids string[]?
  set_flags string[]?
  unlock_action_ids string[]?
  win bool?
  lose bool?
}

class AreaAction {
  id string
  label string @description("Plain English player-facing choice text")
  kind ActionKind
  narrative string?
  energy_cost int?
  required_tool_id string?
  required_any_item_ids string[]?
  target_area_id string? @description("Required when kind is transition")
  gate TransitionGate?
  grant_item_id string?
  consume_item_id string?
  health_delta int?
  satiation_delta int?
  energy_delta int?
  unlock_action_ids string[]?
  set_flags string[]?
  require_flags string[]?
  forbid_flags string[]?
  once_flag string?
  advances_clock bool?
  ticks int?
  success_chance float? @description("0-1 for chance actions")
  success ChanceOutcome?
  failure ChanceOutcome?
  show_chance bool?
  win bool? @description("true ends the game as a win — use only on gated/late actions")
  lose bool?
}

class Area {
  id string
  name string
  description string
  actions AreaAction[] @description("Must be objects, never bare strings")
}

class Scenario {
  title string
  premise string
  objective string @description("Clear multi-step goal in plain English")
  opening string
  win_message string
  lose_message string
  start_area_id string
  exit_area_ids string[] @description("Prefer empty []. Entering these areas wins immediately")
  character CharacterStats
  clock ClockConfig
  items Item[]
  areas Area[]
}
