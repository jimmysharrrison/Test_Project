# Frost Mage

A Python 3.14 desktop action dungeon crawler inspired by Gauntlet and Diablo.
An as-yet nameless wanderer, trained at Drearamore's elemental college, arrives
at **The Tower**. She carries its motto, **elementis fidelis est**, into a
twenty-story mystery. This build covers the first three floors of the opening
five-floor arc: a stone entrance hall, a vast indoor forest atrium, and an
alchemist's workshop where spilled potions have driven the helpers mad.

![Title menu](docs/title.png)

![The Tower's ground floor](docs/preview.png)

![Thornveil Atrium, floor 2](docs/forest.png)

![The Alchemist's Workshop, floor 3](docs/alchemist.png)

## Install or update

Install [Git](https://git-scm.com/downloads) and
[uv](https://docs.astral.sh/uv/getting-started/installation/).
For a new checkout:

```sh
git clone --branch work https://github.com/jimmysharrrison/Test_Project.git
cd Test_Project
uv run main.py
```

If you already cloned the `work` branch, close the game and run these commands
from its folder:

```sh
git pull --ff-only
uv run main.py
```

On Windows, the project folder in the current setup is `C:\Projects\Test_Project`.
uv selects Python 3.14.8 and installs the locked Pygame CE dependency. A graphical
desktop is required for interactive play. Every normal launch opens the title
menu and waits for your choice; combat does not run behind it.

## Title menu and starting over

- **Start Game** begins a fresh Frost Mage on the ground floor. If a character exists, a
  confirmation explains that starting over replaces its gear, gold, and unlocks.
- **Continue** resumes your current level with your saved character. A fresh
  room is loaded after reopening the app; returning from the pause menu keeps
  the current room. Continue is disabled until a character exists.
- **Level Select** replays any reached level while keeping equipment and gold.
  A destination unlocks only after you enter it through the preceding portal.
  Replaying level 1 retains previously earned unlocks. New characters start
  with only level 1 available.
- **How to Play** explains mouse movement, targeting, spells, healing, gear,
  and portal progression. It is also available from the pause menu.
- **The Story** introduces the wanderer, Drearamore, and The Tower. **J** opens
  the current floor's journal, including its story and three encounter phases.
- **Quit** closes the game. Merely browsing menus does not create a character.

Click buttons, or use **Up / Down** and **Enter**. Press **Escape** in game,
then **Main Menu**, to return to the title screen and start over or select a
level. The game stays paused while you read instructions or browse levels.

## Controls

| Control | Action |
| --- | --- |
| Right click | Find a path to the clicked floor position |
| Hold right mouse button | Continually follow the cursor, routing around obstacles |
| Left click an enemy or rift | Select it; inspect health and active effects |
| Left click empty ground | Clear selection |
| Q / hold Q | Cast / repeat Frost Bolt toward the cursor |
| W | Cast Frost Nova around the mage |
| E | Place Ice Wall at the cursor |
| R | Enter Glacial Prison |
| Left click a spell button | Cast a self spell, or arm an aimed spell |
| Left click ground after arming Q or E | Confirm the aimed spell |
| Right click / Escape while aiming | Cancel aiming |
| 1 / click the potion button | Use a healing potion |
| S | Stop moving |
| Escape | Pause / resume |
| M | Mute / unmute effects |
| I / click Gear | Open or close inventory |
| B | Open or close the shop and enchanter |
| J / click Floor Journal | Read the floor's story and phase objectives; combat pauses |
| Enter / click the end-screen button | Climb to the next floor, retry after death, or return to title at chapter end |
| Up / Down + Enter | Navigate title, level, instructions, and pause menus |

Left click selects enemies; it never performs an automatic attack. A selection
does not redirect skill shots. Q aims where the cursor is pointing. Ice Wall's
placement preview appears when its button is clicked; red tiles explain an
invalid placement. Clicking a disabled spell reports why it cannot be cast.

WASD and left-click attacks from the Warden prototype have been replaced. E and R
are now spells; healing moved to 1 and restarting moved to Enter.

## Frost Mage spells

| Key | Spell | Effect | Mana | Cooldown |
| --- | --- | --- | --- | --- |
| Q | Frost Bolt | 24 damage; chills movement by 40% for 2 seconds | 0 | 0.35s |
| W | Frost Nova | 14 damage within 2.8 tiles; freezes movement and attacks for 2.25 seconds | 25 | 8s |
| E | Ice Wall | Three-tile barrier lasting 6 seconds; blocks characters and projectiles | 30 | 14s |
| R | Glacial Prison | Stationary and immune to damage for 2.5 seconds; shatters for 90 damage within 3.2 tiles and freezes survivors for 2 seconds | 45 | 45s |

Spell values in the table are base values before equipment and critical hits.
Mana regenerates at 8 per second, up to 100. Quick spells briefly interrupt
movement, then the current movement order resumes. Glacial Prison prevents
casting and potion use while encased; its explosion happens automatically.
Walls block area effects as well as projectiles. Cooldowns and effect timers
freeze while the game is paused.

Ice Wall has a range of 5 tiles. Placement cannot overlap walls, characters,
rifts, or the gate, and cannot seal off a reachable part of the map. Both the
mage and enemies update their routes when a wall appears or melts. Clicking an
unreachable position chooses nearby reachable floor.

The target frame shows real health and timed freeze/chill effects. Current
enemies have no mana resource; no decorative mana bar is shown for them. Damage
over time spells and further buff types are future work.

## Equipment and enchantments

Press **I** to inspect Helm, Chest, Legs, Gloves, and Boots, or **B** to visit the
enchanter. Both menus pause combat. Hover an item for its stats, rank, and next
enchantment price. Click a backpack item and then **Equip Item**; click an
already-equipped item and **Unequip** to return it to the backpack.

The enchanter's Rank 0 blanks are the **Frostweave set**: Crown, Vestment,
Leggings, Grips, and Treads. Equip all five pieces at Rank 3 or higher to give
**Q / Frost Bolt** a chance to freeze a surviving enemy for **1 second**:

| Lowest equipped Frostweave rank | Freeze chance per hit |
| --- | ---: |
| 3 | 15% |
| 4 | 25% |
| 5 | 40% |

The lowest-ranked piece determines the set tier. Backpack pieces do not count.
Missing a piece, wearing non-set gear, or dropping below Rank 3 disables the
bonus. Item tooltips explain the set, character stats show its progress, and
the Frost Bolt tooltip shows the active chance. Enchanting preserves set
membership, and the set identity saves with the character. Dropped and reward
equipment remains separate from Frostweave even when enchanted.
See the [Frostweave freeze preview](docs/frostweave-freeze.png).

On the enchanter page, drag worn or backpack gear into the **Enchanting Slot**,
then click **Enchant** for the displayed gold cost. Dropping into the slot does
not spend gold, unequip the item, or remove it from the backpack. The slot keeps
its target when you select other gear. **Place Selected Item** is an alternative
to dragging; **Clear Slot** removes the target. New purchases enter the slot
automatically. You can also start a drag in inventory and hover the Enchanter
tab before dropping. Escape or focus loss cancels a drag; dropping elsewhere
keeps the item. The shop backpack supports paging through all owned spares.
See the [enchanter preview](docs/enchanter.png).

Older shop blanks are recognized automatically. Previously enchanted items
without set metadata keep their existing identity: the old format no longer
records whether those items originally came from the shop or a drop.

Backpack upgrades have a **green border and checkmark** and appear first, with
the highest ranks first. An upgrade means a higher rank than the piece worn in
the same slot; helpful gear for an empty slot also counts. Equal ranks and
unranked blanks for empty slots are not upgrades. Markers update when equipment
or enchantments change, and upgrade tooltips explain the comparison.

Select a spare item and click **Sell** for the displayed gold amount, or
**Destroy** to remove it without payment. Individual sales of **Rank 3–5** ask
**ARE YOU SURE?** before selling. Rank 0–2 single sales remain immediate.
Destruction always asks for confirmation. **Cancel** or **Escape** keeps the
items and leaves the menu open. Equipped gear must be unequipped first.
Sell values also appear in item tooltips. Sales and removals save with your
character, and the selected item can be sold or destroyed from either menu.

For bulk cleanup, choose **R0–R5** under **Sell Backpack by Rank**, then click
**Sell All Rank N**. This sells only that exact rank across every backpack page.
Every bulk sale asks **ARE YOU SURE?**, showing the item count and total gold.
The confirmation warns if upgrades are included. Equipped items are always
kept. Switching menus cancels a pending confirmation.
See the [bulk-sale confirmation preview](docs/sell-all.png).

- Helm increases all spell damage; chest increases maximum health.
- Legs add armor that reduces incoming hits; gloves shorten newly cast cooldowns.
- Boots add movement speed, critical chance, and critical damage. They are the
  rarest random drop and a guaranteed Rank 1 reward for clearing level 1.
- Dropped equipment is Rank 1–3. Rank 3 has the best dropped stats.
- The shop sells Frostweave Rank 0 items. Enchant them one rank at a time through
  Rank 5. The final upgrade costs **15,000 gold**.
- Items fill empty slots automatically. Other pieces go into the paged backpack.
- Maximum health increases do not heal you; use food or potions to fill it.

See [the full equipment and economy tables](docs/EQUIPMENT.md) for every bonus,
price, and drop rate. The menu displays your current effective character stats.

## Progression and presentation

Read [The Story](docs/story.png) from the title menu or press **J** for the
current floor's journal. The [phase preview](docs/phase.png) shows the countdown
and next spawner locations.

Each floor has **three phases**. Destroy the current phase's spawners to begin
a **3-second intermission**, then the next group appears. Survivors can still
attack during the wait. The phase banner shows the countdown, remaining
spawners, and movement speed; rings preview the next spawn locations. Spawners
relocate to nearby clear floor if an actor or Ice Wall occupies a planned spot.

| Phase | Spawners | New mob movement speed |
| --- | ---: | ---: |
| 1 | 2 | 100% |
| 2 | 3 | 115% |
| 3 | 4 | 130% |

The stair portal opens only after all **nine** spawners have fallen. Surviving
monsters are optional. Equipment and gold are banked after each phase. The
one-time first-floor boots arrive only after the final phase. Health, mana,
and cooldowns continue normally between phases; they reset when climbing to
the next floor. Gear, gold, potions, and kills carry forward.

**Floor 1 — The Ground Floor:** worn stone, a central inlay, and four equally
spaced load-bearing columns. Molten Skeletons and Ember Skitters emerge from
ember rifts between the pillars.

**Floor 2 — Thornveil Atrium:** the former forest is now an indoor garden under
a glass vault, surrounded by the stone walls of The Tower. Darkroot Treants,
Thornwood Spiders, and Briarbone Archers emerge from Blighted Hearts.

| Atrium enemy | Floor 2 health | Damage before armor | Behavior |
| --- | --- | --- | --- |
| Darkroot Treant | 51 | 11 | Slow melee attacker animated by dark magic |
| Thornwood Spider | 30 | 7 | Fast melee attacker |
| Briarbone Archer | 39 | 9 | Keeps its distance and periodically fires arrows |

Archers show a dotted aim line during a **0.65-second bow draw**. Aim locks when
the draw begins, so moving sideways can dodge the arrow. A shot travels at 5.5
tiles per second, followed by a 2.8-second cooldown before the next draw. Terrain
and Ice Wall block arrows; freeze interrupts a bow draw, and Glacial Prison
absorbs incoming arrows. Armor and the shared brief protection after taking a
hit apply to arrow damage too. Archers navigate around blocked sight lines.

**Floor 3 — The Alchemist's Workshop:** bubbling alembics, stocked benches,
colored spills, and magic gone wrong. The wizard's little helper fairies have
spilled the potions and lost their senses, while enchanted belongings run amok.

| Workshop enemy | Floor 3 health | Damage before armor | Behavior |
| --- | ---: | ---: | --- |
| Bewitched Armor | 75 | 15 | Slow, tough melee attacker |
| Runaway Grimoire | 39 | 9 | Faster animated book |
| Potion-Maddened Fairy | 36 | 9 | Aims for 0.8s, then throws a dodgeable potion bolt |

Fairy bolts travel at 4.4 tiles/second, with 2.3 seconds between casts after
release. Terrain and Ice Wall block them; freeze interrupts the cast. Each
additional floor adds 15% to base enemy/spawner health and gold, and 12% to
base attack damage. Phase speed changes apply to newly spawned mobs; survivors
keep the speed of their original phase.

Floors 4 and 5 are visible as **Coming Later**. Clearing floor 3 reaches a
**To Be Continued** screen and returns to the title menu; there is no repeated
placeholder floor. The Tower itself remains twenty stories in the story.
Level Select replays reached floors while preserving gear. The optional
`--level N` flag chooses a reached floor in interactive play. Headless previews
can choose any implemented floor (1–3), for example `--headless --level 3 --frames 120`.

Gold and equipment can be collected on contact before the clear. Food heals
injured players. Potions restore up to 40 health, respect your equipped maximum
health, and are not consumed at full health.

The local character saves equipment, enchantments, gold, potions, kills, current
level, and highest reached depth automatically. On Windows the save is in
`%LOCALAPPDATA%\Embervault\profile.json`. The legacy folder name is retained to
preserve existing characters after the rename. Old endless depths above 3 map
to floor 3, retaining equipment, gold, and the first-clear reward state.
Continue loads your current level, which can differ from your highest unlock.
Use `uv run main.py --no-save` for a temporary
character, or `--profile PATH` to choose another save file. Profile errors appear
in-game; an invalid profile is preserved instead of being overwritten.

The visual direction keeps the blue-and-silver female mage, pale fur collar,
and original frozen glyph from the earlier art direction, now within the
interiors of The Tower. This build uses procedural artwork and synthesized
sound. Detailed animated sprites and final environmental art remain future work.

Below 35% of maximum health, a dark red vignette grows around the screen edges.
It strengthens as health falls and clears when healed above the threshold. The
center, HUD, and menus remain readable; chest bonuses count toward maximum health.

The game pauses on focus loss and supports resizing with a fixed aspect ratio.
Sound falls back to silence when no audio device is available.

## Verification

```sh
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q dungeon main.py text_game.py
uv run main.py --headless --frames 120 --seed 7 --screenshot preview.png
```

The last command uses a virtual display and starts immediately; it works in a
headless environment. `--frames` exits after the given frame count.

## Code layout

- `dungeon/items.py`: ranked equipment, character bonuses, drop values, and prices.
- `dungeon/armory.py`: inventory, item tooltips, backpack pages, and enchanting UI.
- `dungeon/profile.py`: local character saves.
- `dungeon/menus.py`: splash menu, instructions, pause navigation, and level selection.
- `dungeon/abilities.py`: spell definitions and initial balance values.
- `dungeon/levels.py`: chapter themes, distinct layouts, and enemy rosters.
- `dungeon/controls.py`: mouse orders, button targeting, and hotkey casting.
- `dungeon/navigation.py`: reachable destinations and smoothed grid paths.
- `dungeon/world.py`: collision, spells, effects, enemies, spawning, and progression.
- `dungeon/render.py`: procedural art, target frame, ability buttons, and previews.
- `dungeon/audio.py`: synthesized spell and combat cues.
- `dungeon/app.py`: desktop events, viewport conversion, pause, and restart.
- `tests/`: simulation, controls, desktop input, and original-game regression tests.

The original text prototype remains available with `uv run main.py --text`.
See [GAME_DESIGN.md](GAME_DESIGN.md) for the direction and later milestones.
