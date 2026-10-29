# Floor 9 — The Fractured Hour

The elven wardens were trying to close the Arcanist's breach. They are now
trapped between repeating moments. The Keeper's downward containment and the
Arcanist's control of Floors 11–15 remain the larger story. Floor 9 stops at
the threshold of the final void creature. Its stair now leads into
[Floor 10 — The Maw Between Worlds](VOID_FLOOR_10.md).

## Two wave phases

Break two Chronal Rifts, wait the normal three-second intermission, then break
three more. Normal wave loot and floor scaling apply. Surviving wave enemies
are recalled on boss entry, and earned ground gold/equipment are banked.

- **Time-Displaced Warden:** warns for 1.3 seconds at its portal destination.
  Arrival rechecks walls, player distance and occupancy. Its 0.95-second locked
  shot leaves one pale echo, which repeats the same origin and direction after
  another 1.3 seconds. Echoes never create further echoes; cap four pending.
- **Chronal Scholar:** warns for 1.3 seconds before a radius-1.6 stasis circle
  becomes active for two seconds. Both projectile teams pause inside it,
  retaining velocity and remaining lifetime, then resume when it expires.
  The field shows its release countdown; cap two pending/active circles.
- Freezes cancel pending portals, shots and fields. Established fields and
  echoes finish their visible lifetime even if the original caster dies.
  Ice Patch slows the caster's warning/cooldown clocks. Portal summons use
  the existing population cap and safe-placement checks.

## The Hourless Breach

This is an environmental encounter. Damage and freeze cannot close the breach
itself. Its bar represents three remaining anchor/survival cycles.

1. **Demonstration (3.2s):** a surviving warden visibly anchors in ice.
2. **Safe practice:** time stops; press R when prompted. Missing it causes a
   harmless 1.3-second reset and another practice. No lives or potions are lost.
3. **Fracture (4.2s):** portal exits appear before two guards arrive, or three
   in later cycles. Their projectiles and fields use the ordinary floor rules.
4. **Exposed anchor:** destroy the 300-HP dimensional anchor with normal spells.
   The encounter automatically selects it. This stage has no time limit.
5. **Stopped Hour (1.55s):** ordinary actors, projectiles, their lifetimes,
   enemy status timers, hazard clocks and scene animation pause. The mage can
   still move and cast. A 0.45-second cue precedes a 1.1-second inward pull;
   the whole arena loses its anchor at the end unless the mage is in Prison.
6. Survive, recover for two seconds, then repeat. Three successful real pulses
   seal the breach and award its one normal boss reward.

### R timing guarantee

Glacial Prison lasts **2.5 seconds**, longer than the entire **1.55-second**
Stopped Hour. Pressing R at the first cue safely covers the whole pulse.
Each cue clears R's cooldown, grants a reserved mana-free cast, and bypasses
cast recovery for that cast. Even zero mana or a pre-existing cooldown cannot
softlock the puzzle. The R button labels this charge **RESERVED / FREE CAST**.
If Prison is already active when time stops, its remaining duration is extended
to cover the pulse. Ordinary R costs and cooldowns apply outside the cue.

### Checkpoint and persistence

The boss checkpoint sits at (8.5, 12.5). A real missed pulse or combat death
causes a two-second retry, then restores full current maximum health/mana,
ready cooldowns and the checkpoint potion count. The three real cycles restart;
the successful lesson remains learned. Timing eligibility is invalidated.

Attempt guards and anchors grant no gold, equipment or food, so retries cannot
farm rewards. Inventory and current gold are preserved without rolling back
shop purchases. Prior wave loot is banked before the checkpoint is established.
Saves retain lesson state, reserved R, active Prison, owner/anchor references,
projectile/field clocks, cycle progress and retry state. Completed Floor 8 saves
load as a cleared floor and can enter Floor 9.

## Validation

`tests/test_temporal.py` covers cue timing, zero resources, already-active R,
safe failure, three required cycles, checkpoint recovery, loot suppression,
portal occupancy/freezes, both projectile teams, single echoes, world stasis,
live save roundtrips, Codex values and Floor 8 continuation.

`tools/temporal_playtest.py` uses actual movement, spells and potion rules with
two loadouts and three seeds. It includes an intentional failed second pulse
followed by checkpoint recovery and a full clear. Results are saved in
`temporal-playtest.json`. It reads warning geometry, so it verifies completion
and resource handling rather than human reaction time or final difficulty.

The Floor 9 release passed **427 tests**. All seven full playthroughs cleared the
floor: six clean attempts in approximately 61–70 seconds, and the deliberate
checkpoint failure/recovery run in approximately 94 seconds. All ended with
three anchors sealed; field/echo limits held. Offscreen captures exercise the
lesson, portal/field warnings, exposed anchors, Stopped Hour and retry UI.

All validation is background/headless. Interactive visual verification and a
human readability/difficulty pass remain pending; no game window or preview
was opened during this build.
