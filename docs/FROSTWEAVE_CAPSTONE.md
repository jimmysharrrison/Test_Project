# Frostweave Rank 5 capstone

Damage = 90 x 1.65 (helm) x 1.30 (patch) x 2.75 (critical) x 3 = 1592.6625, rounded once to 1593. Ordinary critical: 531. Radius: 3.2 to 6.4 tiles.

| Floor | Ordinary enemy HP | Device HP | Miniboss / support HP |
|---|---|---|---|
| 1 | husk: 44, skitter: 26 | 176 | 380 / 85 |
| 2 | archer: 39, spider: 30, tree: 51 | 202 | 437 / 98 |
| 3 | armor: 75, fairy: 36, grimoire: 39 | 229 | 494 / 110 |
| 4 | arcane: 55, crystal: 96, predator: 46 | 255 | none |
| 5 | arcane: 61, crystal: 106, predator: 51 | - | Keeper: 3000 |

Existing Warden shield: x0.65 = 1035 damage while any living support is unfrozen. Miniboss recovery takes precedence: x1.35 = 2150. All ordinary enemies, devices and minibosses die if eligible and in range/line of sight. Keeper survives at 1407 HP. Crystal guard and Keeper frost resistance affect control, not damage. Existing freeze rules remain. No health changes, immunity, or execution rule; no balance adjustment required.

The six-second patch permits the 2.5-second Prison: activate R less than 3.5 seconds after patch placement, allowing for cast lock. Combined cost: 75 mana. Longest remaining patch wins, ties follow insertion order. Object identity prevents replacement substitution. Lifetime is checked at the actual explosion instant within the tick, before field aging; expiry equality fails. Patch boundary is inclusive with 1e-9 coordinate tolerance.

Pause stops simulation. Save Game captures active combat, including patches, stasis, and the identity of the patch linked to a pending capstone. Load Game restores that relationship and the remaining lifetimes. Legacy character-only profiles preserve the set but rebuild the room without active spells.

Rank 3-5 Frost Bolt freeze bonuses remain. R tooltip explains both equipment checks, same-patch setup and expiry, guaranteed critical then 3x, radius 6.4, and normal fallback. Armory points to R. Blast adds a thick gold ring and a distinct synthesized sound.

Tests cover missing/lower-rank gear, swaps, late equipment, overlap/ties, identity/replacement, expiry equality, boundary/displacement, ownership, exact damage/no critical roll, range/LOS, defenses, duplicate targets, pause/load, and ordinary radius. Existing spell, encounter, desktop, and inventory regressions run in the full suite.
