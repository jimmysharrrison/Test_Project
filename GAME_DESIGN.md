# Embervault — first Ice Mage build

## Direction

An original isometric action dungeon crawler combining Gauntlet's pressure from
enemy generators with mouse movement, skill shots, and a small spell kit.
The playable hero is a female Ice Mage who controls crowds through cold.

## Current playable loop

1. Enter Frostfall Glade, a forest ruin occupied by molten skeletons and skitters.
2. Right click to move, or hold right mouse to continually follow the cursor.
3. Aim and cast QWER spells; select enemies with left click to inspect them.
4. Destroy three rifts, clear the surviving enemies, and reach the gate.
5. Restart with Enter after death or victory.

## Interaction rules

- Right click owns movement. Orders persist until arrival, cancellation, or replacement.
- Pathfinding routes around stone and temporary ice; unreachable clicks resolve to reachable floor.
- Left click owns selection and UI. It never fires an automatic attack.
- QWER hotkeys cast toward the cursor or around the caster, according to the spell.
- Spell buttons use the same resource, cooldown, and validity rules as hotkeys.
- Clicking Q or E arms aiming. Left click confirms; right click or Escape cancels.
- Clicking W or R casts around the mage immediately.
- Brief casts pause movement; the existing order resumes afterward.
- Glacial Prison prevents movement, casting, potion use, and damage until it shatters.
- Escape pauses, focus loss pauses, and Enter restarts a completed run.

## Provisional kit

| Slot | Ability | Role |
| --- | --- | --- |
| Q | Ice Bolt | Free repeatable skill shot; damage and chill |
| W | Frost Nova | Close-range damage and a hard freeze for breathing room |
| E | Ice Wall | Temporary terrain to redirect a crowd |
| R | Glacial Prison | Long-cooldown defensive stasis followed by a damaging shatter |

Initial numerical values are centralized in `dungeon/abilities.py` and documented
in README.md. Treat them as starting points for playtesting. Freeze stops movement
and attacks; chill slows movement. Molten rifts take damage but cannot be frozen.
Temporary walls must not overlap actors or cut a reachable area off from the map.

## Visual direction

Written reference prompts were recovered from the recent chat titled **Ice Mage
Game Art**. The chat reader exposed the user's descriptions without the generated
image files. The current original procedural interpretation uses:

- A female mage with silver hair and a deep blue cloak edged in silver.
- A pale fur collar inspired by luxurious cold-weather clothing.
- An original cloak/robe glyph representing “forever frozen.”
- Icy cyan projectiles, faceted ice walls, frozen shells, and expanding nova rings.
- Molten demonic skeletons and ember-colored rifts.
- A dark forest ruin with sharp silhouettes and readable spell effects.

Use this build to evaluate controls and the class identity. Final sprites,
animation, materials, and environments should follow a more detailed art pass.

## Architecture

Keep simulation and navigation independent of Pygame. World coordinates remain
separate from isometric screen coordinates. Enemy selection, movement orders,
and skill-shot aim are separate state. Status timers and cooldowns use elapsed
time. Keyboard and UI actions share one casting path.

## Next milestones

1. Tune click-to-move responsiveness, targeting, spell costs, and crowd pressure.
2. Refine the mage silhouette and create directional animated sprites.
3. Add more encounters, terrain, enemies, and a boss.
4. Add meaningful equipment and progression once the basic kit feels good.
5. Evaluate co-op as a separate design and networking milestone.

## Runtime

Python 3.14.8 desktop application using Pygame CE, with one room and one hero.
The original console game remains available with `python main.py --text`.
