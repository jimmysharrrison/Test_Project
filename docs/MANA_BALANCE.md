# Mana regeneration tuning

Chosen default: **6 mana/second**, down from 8 (25%). Configurable through
`python main.py --mana-regen 6`, or `World(mana_regen=6)`. Invalid negative or
nonfinite rates are rejected. Configuration survives floor transitions and new
characters within the running app; it is a launch setting, not saved gear.
No costs, cooldowns, or regeneration-delay mechanic changed.

## Current resource rules

Maximum mana is 100 at every equipment tier. No gear, enchantment, pickup,
food, potion, kill, or combat effect increases maximum mana or restores mana.
Regeneration runs during casting and Prison. Floor transitions and fresh-room
save resumes refill mana and reset cooldowns, as before. Mana and cooldowns
are not persisted by the existing profile format. Menu/inventory/focus pauses
suspend simulation. Tutorial retry refills its separate PracticeWorld only.

| Ability | Mana | Early cooldown | Rank 5 cooldown |
| --- | ---: | ---: | ---: |
| Frost Bolt (Q) | 0 | 0.35s | 0.245s |
| Frost Nova (W) | 25 | 8s | 5.6s |
| Ice Patch (E) | 30 | 14s | 9.8s |
| Glacial Prison (R) | 45 | 45s | 31.5s |

Glove ranks 1–5 reduce cooldowns 5/10/15/22/30%; helms increase damage
10/20/30/45/65%; chests add 20/40/60/90/130 health; legs add armor
1/2/3/5/8; boots add speed, critical chance and critical damage. Full
Frostweave ranks 3/4/5 give Bolt a 15/25/40% one-second freeze chance.
These affect combat effectiveness, not resource supply or costs.

## Recovery from empty (cooldown ready)

These times are identical for early and fully geared characters. Continuous
regeneration is rate × simulation seconds, capped at maximum mana; cast
availability is quantized by the update interval.

| Available action | Before: 8/s | After: 6/s |
| --- | ---: | ---: |
| Useful damage/chill: Frost Bolt | immediate | immediate |
| Nova: 25 mana | 3.125s | 4.167s |
| Ice Patch: 30 mana | 3.750s | 5.000s |
| Prison: 45 mana | 5.625s | 7.500s |
| Full pool: 100 mana | 12.500s | 16.667s |

A ready W/E/R chain spends 100 total; actual casts must respect brief cast
locks and Prison's 2.5s stasis. Bolt is always a viable zero-mana fallback,
including its damage, chill and equipped freeze bonus. Stasis still prevents
casting as designed. No waiting period is imposed after spending mana.

## Repeated rotations

`python tools/mana_balance.py` produces [raw measurements](mana-measurements.json).
Seed 7; empty arena with dormant rifts, 120 updates/second, full initial pool,
180 seconds, normal cast locks and stasis. W then E then R priority, retry on
availability; no direct mana manipulation after initialization. First denial
means a requested ready spell lacks mana, not that all attacks are unavailable.
The idle gaps would normally contain free Bolts; omitting them measures the
most aggressive paid-spell demand without Bolt's short casting locks.

| Gear | Rotation | First mana denial at 8/s | First mana denial at 6/s |
| --- | --- | ---: | ---: |
| Early, no gear | W | none in 180s | none in 180s |
| Early | W + E | none in 180s | none in 180s |
| Early | W + E + R | none in 180s | 56.208s |
| All Rank 5 Frostweave | W | none in 180s | none in 180s |
| All Rank 5 | W + E | none in 180s | 39.383s |
| All Rank 5 | W + E + R | 31.867s | 11.200s |

Theoretical paid-spell demand on cooldown: W+E is 5.268/s early and
7.526/s geared; W+E+R is 6.268/s early and 8.954/s geared. Thus 6/s supports
ordinary early control but limits extended aggressive chains. Fully geared
W/E/R casts over 180s changed from 31/16/6 to 28/14/1: blind W/E priority
starves Prison. Reserving 45 mana becomes a deliberate choice. This is a
balance concern to watch in human play, not evidence that every rotation is fun.

## Scripted encounter playtests

Normal combat bot from `tools/lower_tower_playtest.py`, seed 7, 60 FPS;
no invulnerability, damage overrides, direct kills, mana refills or tutorial
assistance. Uses Q, situational W/R, and E when at least 55 mana remains.
Each room starts fresh. Floor 1 covers ordinary waves and its miniboss;
floor 5 covers the Keeper. The conservative bot did not trigger Prison in
these short runs, so the rotation test above covers its resource pressure.

| Gear / encounter | Clear time before → after | Lowest mana before → after | End HP before → after |
| --- | --- | --- | --- |
| Early / floor 1 | 39.77 → 39.77s | 56.07 → 53.30 | 100 → 100 |
| Early / Keeper | 48.00 → 48.00s | 46.60 → 46.20 | 100 → 100 |
| Rank 5 / floor 1 | 20.12 → 20.12s | 70.13 → 70.10 | 230 → 230 |
| Rank 5 / Keeper | 13.42 → 13.42s | 62.33 → 58.00 | 218 → 218 |

These scripted runs support ordinary-play viability but cannot establish fun.
Only one seed and conservative spending are represented; geared damage and
free Bolt freeze can make fights short enough to mask resource pressure.
Human encounter playtesting remains outstanding.

## Verification and limits

Regression coverage checks regeneration at 30/60/144 FPS, cap enforcement,
empty-mana Bolt, pause, stasis, equipment swaps, finite configuration, and
profile save/load under the existing fresh-room resume contract. Existing
pause/menu/tutorial and spell tests cover their integration. HUD shows the
active regeneration rate and pool; spell buttons retain costs, cooldowns and
insufficient-mana feedback, with FREE / HOLD Q on Bolt.

Existing simulation caps updates at 1/30s: a 15 FPS frame restores 0.2 mana
at 6/s, matching 1/30 simulation second, so wall-clock recovery slows below
30 FPS along with combat/cooldowns. This tuning does not change the timestep
policy. Save/reload still refills the room's resources; repeated reloading can
bypass attrition, an existing persistence design limitation.

Validation completed: full suite 275/275 passed with workspace-local TEMP/TMP;
the expanded mana suite separately passed 7/7 (including two additional
recovery/transition checks). Compilation and a headless HUD render passed.
The default sandbox temporary directory initially caused filesystem errors;
using `.test-tmp` resolved them without changing game behavior.
