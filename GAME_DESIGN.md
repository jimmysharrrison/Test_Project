# Embervault — Ice Mage and Frostweave Enchanter

## Direction

An original isometric action dungeon crawler combining Gauntlet's pressure from
enemy generators with mouse movement, skill shots, and a small spell kit.
The playable hero is a female Ice Mage who controls crowds through cold.

## Current playable loop

The title screen offers Start Game, Continue, Level Select, How to Play, and
Quit. Start Game creates a fresh level-1 character and asks before replacing an
existing one. Continue uses the current level, separately from the highest
unlocked level. Level Select preserves gear and permits only reached levels.
Escape opens a pause menu with Resume, How to Play, and Main Menu. Frontend
screens suspend simulation and accept mouse or keyboard navigation.

1. Enter Frostfall Glade, a forest ruin occupied by molten skeletons and skitters.
2. Right click to move, or hold right mouse to continually follow the cursor.
3. Aim and cast QWER spells; select enemies with left click to inspect them.
4. Destroy three rifts to open the gate. Surviving enemies are optional.
5. Collect ranked gear, equip it with I, and spend gold with B.
6. Reach the gate and enter Thornveil Forest; equipment and gold persist.
7. Fight dark-magic treants, spiders, and skeletal archers; purge three Blighted
   Hearts to open the next portal.

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
- Escape pauses, focus loss pauses, I opens inventory, and B opens the enchanter.
- Enter advances a cleared level or restarts after death with earned gear retained.

## Provisional kit

| Slot | Ability | Role |
| --- | --- | --- |
| Q | Frost Bolt | Free repeatable skill shot; damage and chill |
| W | Frost Nova | Close-range damage and a hard freeze for breathing room |
| E | Ice Wall | Temporary terrain to redirect a crowd |
| R | Glacial Prison | Long-cooldown defensive stasis followed by a damaging shatter |

Initial numerical values are centralized in `dungeon/abilities.py` and documented
in README.md. Treat them as starting points for playtesting. Freeze stops movement
and attacks; chill slows movement. Molten rifts take damage but cannot be frozen.
Temporary walls must not overlap actors or cut a reachable area off from the map.

## Equipment and progression

Five slots: Helm (damage), Chest (maximum health), Legs (flat armor), Gloves
(cooldown reduction), and Boots (speed and critical-hit bonuses). Dropped ranks
are 1–3; enchanting purchased Rank 0 blanks or existing loot can reach Rank 5.
The final upgrade costs 15,000 gold. Rank 1 boots are guaranteed once for the
first level clear, while higher-rank boots remain rare drops or costly enchants.

Enchanter blanks form the Frostweave set. All five pieces must be equipped at
Rank 3+; backpack ownership does not count. The lowest equipped piece sets a
15% / 25% / 40% Frost Bolt freeze chance at full-set Rank 3 / 4 / 5. Freeze lasts
one second and preserves any longer existing freeze. Set identity survives
enchants and saves and is separate from dropped/reward gear. Old shop blanks
are recognized; old enchanted items without origin metadata are not retagged.

The enchanter uses an explicit target slot. Worn or backpack gear can be dragged
there, with a selected-item button as an alternative. The target is a UID
reference, so placement does not move or unequip the item. Enchant charges the
displayed cost only when pressed and applies only to the loaded target. Future
enchantments can build on this target selection. The shop includes a paged
backpack and accepts drags that hover the Enchanter tab from inventory.

Inventory, tooltips, live effective stats, a paged backpack, and the enchanter
are available in paused menus. Spare items can be sold for a rank-based gold
value or destroyed after confirmation. Equipped items must be unequipped first.
Upgrades have green checks/borders and sort first in the backpack. Comparisons
use rank within the matching equipment slot. Single sales at Rank 3 or higher
require confirmation. Rank-filtered Sell All includes every matching backpack
item across pages, keeps equipped gear, and always confirms the count and price.
Confirmations warn when upgrades are included and validate the exact quoted
items before any removal or payment.
Gear cannot be changed during Glacial Prison.
Chest swaps cannot heal the player. Saves preserve gear, enchants, gold, and
current level and highest reached depth locally. Entering a new level unlocks
it permanently for that character; clearing its predecessor only opens the
portal. Replaying an earlier level keeps the higher unlock. Death retries the
current level. Existing saves preserve their previous unlocks.
See `docs/EQUIPMENT.md` for the initial balance tables.

On a clear, remaining equipment and gold are collected. At the exit, the mage
advances from the original arena to the distinct forest layout. Depths 3 onward
repeat the forest with scaled enemies and gold. Additional chapters and bosses
remain future milestones.

## Level 2: Thornveil Forest

The forest uses tree obstacles, a worn earth path, undergrowth, roots, mushrooms,
green wisps, and purple blight. Darkroot Treants replace Molten Skeletons and
Thornwood Spiders replace Ember Skitters; their base melee roles are preserved.
Briarbone Archers are nature-themed skeletons with bows and leaf-covered antlers.
Blighted Hearts replace the three molten generators and spawn only forest mobs
(45% treants, 35% spiders, 20% archers).

Archers seek a clear shot within 7.5 tiles and retreat inside 2.6 tiles while
their bow is on cooldown. A 0.65-second draw displays the locked aim direction;
the arrow flies straight at 5.5 tiles/second and expires after 1.7 seconds.
After firing, the archer waits 2.8 seconds before drawing again. Freeze cancels
the draw. Terrain and Ice Wall block both sight and arrows. Arrows share the
player's armor, post-hit immunity, and Glacial Prison protection with melee hits.

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
4. Tune equipment, the enchanting economy, and depth scaling from playtesting.
5. Evaluate co-op as a separate design and networking milestone.

## Runtime

Python 3.14.8 desktop application using Pygame CE, with two distinct arenas,
progressive depth scaling, and one hero.
The original console game remains available with `python main.py --text`.
