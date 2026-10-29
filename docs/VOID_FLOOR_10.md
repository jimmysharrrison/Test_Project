# Floor 10 — The Maw Between Worlds

The Threshold Devourer has pushed its head, shoulders and tentacles through
the floor. Its lower body remains in another dimension. The monster never
walks or teleports. The arena and giant torso share a broad, broken rupture
with foreground floor plates obscuring its submerged half.

This closes the void arc the Keeper held back. The Arcanist, who oversaw the
experiments, still controls the five floors above it (11–15). Those floors
remain future work; the current upper stair ends the build after Floor 10.

## Progression and combat

Two Breach Seals, a three-second intermission, three seals, and another
intermission lead to the boss. Wave creatures combine Floors 6–9. On boss
arrival, survivors are recalled and old projectiles/warnings clear. Earned
ground loot stays collectible; health, mana, potions and cooldowns carry through.

The boss has **3,600 HP** and remains fixed at (8.5, 5.5). Damage works normally;
there is no channeler shield or required puzzle spell. It cycles these patterns:

1. **Breach Communion:** up to three named portal arrivals warn for two seconds.
   Destinations are chosen away from the mage, walls, other actors and darkness.
   Release rechecks terrain and occupancy. Freezing the boss cancels pending
   arrivals. Summons expire after 26 seconds; at most six are alive at once.
2. **Inward Convergence:** a two-second warning precedes an arena gravity draw.
   The inner 1.5 tiles hurt for 18 base damage under the ordinary armor and hit
   immunity rules. Stage strengths are 1.25 / 1.5 / 1.75 tiles per second, lasting
   2.5 / 3 / 3.5 seconds. Run outward and keep clear of the core. Wall collision
   stops displacement; Glacial Prison resists it without being required.
3. **Tentacle slams:** one, two or three fixed circles, depending on health stage,
   warn for 1.8 seconds plus 0.45 seconds per subsequent strike. Each radius-1.1
   strike deals 16 base damage. Moving after the tell does not redirect a strike.
4. **Tentacle lashes:** one, two or three locked lanes warn for 1.8 seconds plus
   0.3 seconds per later lane. Reach nine tiles; radius 0.4; 16 base damage.

Health stages change at two-thirds and one-third. Shared warning limits allow
at most three mechanics and one force. Pulls and grabs exclude each other.
The boss does not start another major pattern while its current one is active,
while a foreign gravity field is active, or while the mage is grasped. Recovery
provides at least 1.3 seconds after a finished strike; neutral intervals also
follow arrivals. During recovery the usual 35% damage vulnerability applies.

Ice Patch slows the boss's warning, cooldown and recovery clocks. A freeze
interrupts pending warnings and arrivals for at most 0.55 seconds, followed by
3.5 seconds of resistance. Already-active fields finish their visible life.
Warnings account for a Prison or spell cast already in progress.

## Familiar creatures

The rotating roster contains all eleven regular void creatures introduced on
Floors 6–9: voidlings, binders, lashers, graspers, anchor tentacles, enthralled
wizards, gravity adepts, repulsion constructs, orbiting fragments, rift wardens
and chronal scholars. Three are requested per call, in a saved rotation; a full
population skips the summon call and allows the other boss attacks to proceed.
Early packs mix floors, while later packs reveal the rest of the roster.

Their original behavior remains intact, including root source counterplay,
bounded darkness, gravity fields, portal revalidation, single-shot echoes and
projectile stasis/release. In particular, temporal minions retain their own
spells without starting Floor 9's lesson or Stopped Hour puzzle. R keeps its
normal mana/cooldown, and death uses the ordinary floor retry flow.

## Completion and saves

Victory recalls summons and removes pending arrivals, roots, force fields,
darkness, temporal fields and echoes. The ordinary boss reward drops once.
Player death wins over a boss kill in the same simulation tick. Floor 10's stair
ends at To Be Continued; Floor 11 is unavailable. Old completed Floor 9 saves
load as cleared and can enter Floor 10, preserving the character's progress.

Live saves preserve the fixed boss, health stage, current warnings, summon
rotation, portal arrival ownership, minion identities and temporal sources.
New actors use separate default aim vectors so post-load summoning preserves
the same object graph and deterministic continuation as uninterrupted play.

## Validation

`tests/test_maw.py` covers fixed position across all patterns/stages, roster
coverage and caps, warned/revalidated arrivals, frost interruption, movement
escape and Prison anchoring, pull/root exclusion, locked attacks and recovery,
temporal minions without the Floor 9 puzzle, cleanup, same-tick death, reward
idempotence, save/slot roundtrips, Codex values and Floor 9 continuation.

`tools/maw_playtest.py` clears the entire floor with real movement, spells and
potions, using three seeds and two loadouts. No direct kills, invulnerability
or R casts are used. It reads warning geometry, so the results verify completion
and resource pressure rather than human reaction time or final balance.
Results are in `maw-playtest.json`.

The full suite passed **446 tests**. All six full-floor runs cleared, taking
approximately 47–71 seconds. The boss stayed fixed in every run, and the observed
mechanics respected their caps. Separate encounter tests exercise all eleven
summon kinds and the full six-minion cap. Offscreen checks cover 25 render states;
boss, gravity and arrival captures were inspected. Warnings draw over the giant
torso so it cannot hide a portal tell or the dangerous core.

[Boss capture](boss-floor-10.png) · [Gravity warning](gravity-floor-10.png)
· [Summon portals](summons-floor-10.png)

Validation runs in the background with an SDL dummy display for offscreen
rendering. No desktop game window is opened and no desktop input is sent.
Interactive visual/readability and human difficulty review remain pending.
