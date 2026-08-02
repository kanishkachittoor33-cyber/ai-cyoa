# Abandoned Cottage

Choose-your-own-adventure engine with survival clock, gated paths, and chance combat.

## Map

```
Cottage ──outside──┬── River ── boat ──(wood)──► Troll ──► Freedom
                   │              ▲
                   └── Forest entrance ── Forest 1 (berries)
                                              │
                                         Forest 2 (snake, shed)
                                              │
                                         Forest 3 (key) ──► Shed (rod, scroll)
```

### Cottage
Sleep · Open chest (axe) · Grindstone (sharpen axe) · Go outside

### River
Collect water · Swim · Board boat · Downstream (**needs wood**) · Return

### Troll
Flee 100% → cottage · Run past 20% → freedom · Fight (axe 50% / sharp 75%; +scroll → 75% / 100%)

### Forest
Chop wood (axe) · Berries (one poison, unmarked) · Snake 50% bite · Bag → key · Shed → rod + troll scroll

## Play

```bash
python3 serve.py    # http://127.0.0.1:8765
python3 play.py     # terminal
```

## Engine

Clock, areas, universal / energy / tool / transition / chance / combat actions, item transforms, flags, loadout-based success rates.
