"""Abandoned Cottage — explore river & forest, prepare, defeat the troll."""

from __future__ import annotations

from ..types import (
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


def build_abandoned_cottage():
    items = {
        "axe": Item(
            id="axe",
            name="Axe",
            kind=ItemKind.WEAPON,
            description="A serviceable axe from the cottage chest.",
        ),
        "axe_sharp": Item(
            id="axe_sharp",
            name="Sharpened Axe",
            kind=ItemKind.WEAPON,
            sharpened=True,
            description="Honed on the grindstone. Better against thick hide.",
        ),
        "wood": Item(
            id="wood",
            name="Piece of Wood",
            kind=ItemKind.MATERIAL,
            description="A stout branch — enough to pole a boat downstream.",
        ),
        "water": Item(
            id="water",
            name="River Water",
            kind=ItemKind.DRINK,
            satiation_restore=8,
            energy_restore=5,
            description="Cool water from the river.",
        ),
        "berry_red": Item(
            id="berry_red",
            name="Red Berries",
            kind=ItemKind.FOOD,
            satiation_restore=5,
            health_restore=-25,
            description="Bright red. You can't tell if they're safe.",
        ),
        "berry_dark": Item(
            id="berry_dark",
            name="Dark Berries",
            kind=ItemKind.FOOD,
            satiation_restore=20,
            energy_restore=5,
            description="Deep purple. You can't tell if they're safe.",
        ),
        "key": Item(
            id="key",
            name="Iron Key",
            kind=ItemKind.KEY,
            description="Rusty key from a discarded bag.",
        ),
        "fishing_rod": Item(
            id="fishing_rod",
            name="Fishing Rod",
            kind=ItemKind.TOOL,
            description="A worn rod from the shed.",
        ),
        "fish": Item(
            id="fish",
            name="River Fish",
            kind=ItemKind.FOOD,
            satiation_restore=18,
            energy_restore=2,
            description="Fresh from the current. Edible raw if you must.",
        ),
        "scroll": Item(
            id="scroll",
            name="Troll Scroll",
            kind=ItemKind.LORE,
            description=(
                "Ink sketches of a bridge troll. Margin note: "
                "'Strike the soft underjaw — a keen edge finds it.'"
            ),
        ),
    }

    cottage = Area(
        id="cottage",
        name="Abandoned Cottage",
        description=(
            "Dust floats in slanted light. A chest sits under the window. "
            "A grindstone leans by the hearth. The door leads outside."
        ),
        actions=[
            AreaAction(
                id="sleep",
                label="Sleep",
                kind=ActionKind.UNIVERSAL,
                narrative="You curl on the pallet. Dreams of water and teeth.",
                energy_delta=25,
                advances_clock=True,
                ticks=3,
            ),
            AreaAction(
                id="open_chest",
                label="Open the chest",
                kind=ActionKind.UNIVERSAL,
                narrative="The lid groans. Inside: an axe, wrapped in oilcloth.",
                grant_item_id="axe",
                once_flag="chest_opened",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="grindstone",
                label="Use the grindstone",
                kind=ActionKind.TOOL,
                narrative="Sparks spit from the wheel as you hone the edge.",
                transform_item=("axe", "axe_sharp"),
                required_any_item_ids=("axe",),
                forbid_flags=("axe_sharpened",),
                set_flags=("axe_sharpened",),
                energy_cost=8,
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="go_outside",
                label="Go outside",
                kind=ActionKind.TRANSITION,
                target_area_id="outside",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You step into the yard. Air smells of wet leaves and river mud.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    outside = Area(
        id="outside",
        name="Outside the Cottage",
        description=(
            "A crooked yard. The river murmurs to the west. "
            "Dark trees press close to the east. The cottage door waits behind you."
        ),
        actions=[
            AreaAction(
                id="to_river",
                label="Go to the river",
                kind=ActionKind.TRANSITION,
                target_area_id="river",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You follow a muddy path down to the water.",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="to_forest",
                label="Enter the forest",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_entrance",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="Needles hush your steps as you enter the trees.",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="go_inside",
                label="Go inside",
                kind=ActionKind.TRANSITION,
                target_area_id="cottage",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You duck back into the cottage.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    river = Area(
        id="river",
        name="Riverbank",
        description=(
            "Grey water slides past. Fish flash under the surface. "
            "An abandoned boat is tied to a root. Downstream, the current "
            "disappears under a low stone bridge — something large moves in the shadow."
        ),
        actions=[
            AreaAction(
                id="collect_water",
                label="Collect water",
                kind=ActionKind.UNIVERSAL,
                narrative="You fill a cracked jug from the current.",
                grant_item_id="water",
                once_flag="water_taken",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="fish",
                label="Fish for food",
                kind=ActionKind.TOOL,
                narrative="You cast into the current and haul up a wriggling river fish.",
                required_any_item_ids=("fishing_rod",),
                grant_item_id="fish",
                energy_cost=8,
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="swim",
                label="Swim along the bank",
                kind=ActionKind.ENERGY,
                energy_cost=15,
                narrative="Cold bites your limbs. You gain little but exhaustion.",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="ride_boat",
                label="Board the abandoned boat",
                kind=ActionKind.TRANSITION,
                target_area_id="boat",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="The hull rocks. Oarlocks are empty — you'll need leverage to steer.",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="downstream",
                label="Pole downstream under the bridge",
                kind=ActionKind.TRANSITION,
                target_area_id="troll",
                gate=TransitionGate(
                    status=GateStatus.CLOSED,
                    requires_tool_id="wood",
                    energy_cost=10,
                ),
                narrative="You shove off with the wood. The boat slides toward the bridge.",
                advances_clock=True,
                ticks=2,
            ),
            AreaAction(
                id="river_to_outside",
                label="Return to the cottage yard",
                kind=ActionKind.TRANSITION,
                target_area_id="outside",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You climb the bank toward the cottage.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    boat = Area(
        id="boat",
        name="Abandoned Boat",
        description=(
            "You sit in the damp boat. Upstream the water is shallow and calm. "
            "Downstream needs a pole — a piece of wood — to risk the bridge."
        ),
        actions=[
            AreaAction(
                id="go_upstream",
                label="Go upstream",
                kind=ActionKind.TRANSITION,
                target_area_id="river",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You haul against the current and drift back to the familiar bank.",
                energy_cost=6,
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="boat_downstream",
                label="Push downstream (needs wood)",
                kind=ActionKind.TRANSITION,
                target_area_id="troll",
                gate=TransitionGate(
                    status=GateStatus.CLOSED,
                    requires_tool_id="wood",
                    energy_cost=10,
                ),
                narrative="With the wood as a pole, you commit to the current.",
                advances_clock=True,
                ticks=2,
            ),
        ],
    )

    troll = Area(
        id="troll",
        name="Bridge — the Troll",
        description=(
            "A troll fills the arch. Wet stone, yellow eyes, breath like spoiled meat. "
            "Freedom lies past it — if you live."
        ),
        actions=[
            AreaAction(
                id="flee",
                label="Flee back (100%)",
                kind=ActionKind.CHANCE,
                narrative="You scramble from the boat.",
                success_chance=1.0,
                show_chance=True,
                success=ChanceOutcome(
                    narrative="You flee. The troll's laugh follows you all the way home.",
                    target_area_id="cottage",
                ),
                failure=ChanceOutcome(
                    narrative="Impossible — you always get away when you run.",
                    target_area_id="cottage",
                ),
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="run_past",
                label="Run past (20%)",
                kind=ActionKind.CHANCE,
                narrative="You bolt for the far bank.",
                success_chance=0.20,
                show_chance=True,
                success=ChanceOutcome(
                    narrative="Mud flies. Somehow you slip under its arm into daylight.",
                    win=True,
                ),
                failure=ChanceOutcome(
                    narrative="A backhand sends you sprawling. You crawl back toward the cottage.",
                    health_delta=-20,
                    target_area_id="cottage",
                ),
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="fight_troll",
                label="Fight the troll",
                kind=ActionKind.COMBAT,
                narrative="You raise your weapon.",
                show_chance=True,
                loadout_chances=(
                    LoadoutChance(("axe_sharp", "scroll"), 1.0),
                    LoadoutChance(("axe_sharp",), 0.75),
                    LoadoutChance(("axe", "scroll"), 0.75),
                    LoadoutChance(("axe",), 0.50),
                ),
                required_any_item_ids=("axe", "axe_sharp"),
                success=ChanceOutcome(
                    narrative="You find the underjaw. The troll falls. The path beyond is yours.",
                    win=True,
                ),
                failure=ChanceOutcome(
                    narrative="The axe glances off. The troll answers.",
                    health_delta=-35,
                    target_area_id="cottage",
                ),
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    forest_entrance = Area(
        id="forest_entrance",
        name="Forest Entrance",
        description=(
            "Trees crowd the path. A stand of young trunks looks cuttable. "
            "Deeper in, the woods thicken."
        ),
        actions=[
            AreaAction(
                id="chop_wood",
                label="Chop wood",
                kind=ActionKind.TOOL,
                narrative="You fell a limb and trim a sturdy pole.",
                required_any_item_ids=("axe", "axe_sharp"),
                grant_item_id="wood",
                energy_cost=12,
                once_flag="wood_chopped",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="to_forest_1",
                label="Walk deeper among the trees",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_1",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="Birds fall silent as you press inward.",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="forest_to_outside",
                label="Return to the cottage yard",
                kind=ActionKind.TRANSITION,
                target_area_id="outside",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You step back into open air.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    forest_1 = Area(
        id="forest_1",
        name="Forest — Berry Clearing",
        description=(
            "Two berry bushes grow at the path's edge — one heavy with red fruit, "
            "one with dark. You cannot tell which is safe."
        ),
        actions=[
            AreaAction(
                id="pick_berry_1",
                label="Pick the red berries",
                kind=ActionKind.UNIVERSAL,
                narrative="You pocket a handful of red berries. They smell sweet — maybe too sweet.",
                grant_item_id="berry_red",
                once_flag="berry_red_picked",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="pick_berry_2",
                label="Pick the dark berries",
                kind=ActionKind.UNIVERSAL,
                narrative="You gather dark berries. Juice stains your fingers.",
                grant_item_id="berry_dark",
                once_flag="berry_dark_picked",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="to_forest_2",
                label="Continue deeper",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_2",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="The path narrows. Something dry rasps in the leaves ahead.",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="forest_1_back",
                label="Back toward the forest entrance",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_entrance",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You retreat to the entrance.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    forest_2 = Area(
        id="forest_2",
        name="Forest — Snake Path",
        description=(
            "A thick snake lies across the trail. To the left, a locked shed door. "
            "Beyond, the path continues."
        ),
        actions=[
            AreaAction(
                id="face_snake",
                label="Pass the snake",
                kind=ActionKind.CHANCE,
                narrative="You edge forward.",
                success_chance=0.50,
                show_chance=True,
                forbid_flags=("snake_passed",),
                success=ChanceOutcome(
                    narrative="The snake watches but does not strike. You are past.",
                    set_flags=("snake_passed",),
                ),
                failure=ChanceOutcome(
                    narrative="Fangs flash. Fire races up your leg.",
                    health_delta=-20,
                    set_flags=("snake_passed",),
                ),
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="to_forest_3",
                label="Press on to the far path",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_3",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="Past the snake's resting place, the woods open a little.",
                require_flags=("snake_passed",),
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="to_shed",
                label="Unlock the shed",
                kind=ActionKind.TRANSITION,
                target_area_id="shed",
                gate=TransitionGate(
                    status=GateStatus.CLOSED,
                    requires_tool_id="key",
                ),
                narrative="The iron key turns. The shed breathes dust and oil.",
                require_flags=("snake_passed",),
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="forest_2_back",
                label="Return to the berry clearing",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_1",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You back away from the snake path.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    forest_3 = Area(
        id="forest_3",
        name="Forest — Discarded Bag",
        description=(
            "A torn canvas bag lies against a stump. Something metallic glints inside."
        ),
        actions=[
            AreaAction(
                id="open_bag",
                label="Open the bag",
                kind=ActionKind.UNIVERSAL,
                narrative="Inside: an iron key on a leather thong.",
                grant_item_id="key",
                once_flag="bag_opened",
                advances_clock=True,
                ticks=1,
            ),
            AreaAction(
                id="leave_forest_3",
                label="Leave",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_2",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You return along the snake path.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    shed = Area(
        id="shed",
        name="Locked Shed",
        description=(
            "Tools hang on pegs. A fishing rod leans in the corner. "
            "A scroll is pinned under a jar of nails."
        ),
        actions=[
            AreaAction(
                id="take_rod",
                label="Take the fishing rod",
                kind=ActionKind.UNIVERSAL,
                narrative="You take the fishing rod.",
                grant_item_id="fishing_rod",
                once_flag="rod_taken",
                advances_clock=False,
                ticks=0,
            ),
            AreaAction(
                id="take_scroll",
                label="Take the scroll",
                kind=ActionKind.UNIVERSAL,
                narrative=(
                    "The scroll describes a bridge troll — and a soft spot under the jaw "
                    "that a sharpened edge can find."
                ),
                grant_item_id="scroll",
                once_flag="scroll_taken",
                advances_clock=False,
                ticks=0,
            ),
            AreaAction(
                id="leave_shed",
                label="Leave the shed",
                kind=ActionKind.TRANSITION,
                target_area_id="forest_2",
                gate=TransitionGate(status=GateStatus.OPEN),
                narrative="You close the shed door behind you.",
                advances_clock=True,
                ticks=1,
            ),
        ],
    )

    freedom = Area(
        id="freedom",
        name="Beyond the Bridge",
        description="Open road. Birds. No cottage walls. You are free.",
        actions=[],
    )

    map_graph = MapGraph(
        areas={
            a.id: a
            for a in (
                cottage,
                outside,
                river,
                boat,
                troll,
                forest_entrance,
                forest_1,
                forest_2,
                forest_3,
                shed,
                freedom,
            )
        },
        start_area_id="cottage",
        exit_area_ids=(),  # win via troll defeat / run past
        win_message="The bridge is yours. Freedom.",
        lose_message="You collapse. The cottage waits for the next lost soul.",
    )

    character = CharacterState(
        health=85,
        satiation=70,
        energy=75,
        items=[],
        location_id="cottage",
    )

    state = GameState(
        t=0,
        character=character,
        world_items=items,
        log=[
            "You wake in an abandoned cottage. Outside: river, forest, and a troll under the bridge. Defeat it — or run — to be free.",
        ],
    )

    meta = {
        "title": "Abandoned Cottage",
        "premise": (
            "Gather axe and wood, learn the troll's weakness, survive the forest — "
            "then face what waits under the bridge."
        ),
        "clock": ClockConfig(
            satiation_loss_per_tick=4,
            energy_gain_per_tick=3,
            health_loss_per_tick=5,
        ),
    }
    return map_graph, state, meta


# Back-compat alias used by older imports
def build_lost_in_the_woods():
    return build_abandoned_cottage()
