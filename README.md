# Embervault — Ice Mage build

A Python 3.14 desktop action dungeon crawler inspired by Gauntlet and Diablo.
Play a female Ice Mage in Frostfall Glade: move with the mouse, control crowds
with ice, destroy three molten rifts, then clear the survivors and escape.

![Ice Mage gameplay](docs/preview.png)

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
desktop is required for interactive play. Press **Enter** or click **Begin
Descent** on the title screen.

## Controls

| Control | Action |
| --- | --- |
| Right click | Find a path to the clicked floor position |
| Hold right mouse button | Continually follow the cursor, routing around obstacles |
| Left click an enemy or rift | Select it; inspect health and active effects |
| Left click empty ground | Clear selection |
| Q / hold Q | Cast / repeat Ice Bolt toward the cursor |
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
| Enter / click the end-screen button | Restart after death or victory |

Left click selects enemies; it never performs an automatic attack. A selection
does not redirect skill shots. Q aims where the cursor is pointing. Ice Wall's
placement preview appears when its button is clicked; red tiles explain an
invalid placement. Clicking a disabled spell reports why it cannot be cast.

WASD and left-click attacks from the Warden prototype have been replaced. E and R
are now spells; healing moved to 1 and restarting moved to Enter.

## Ice Mage spells

| Key | Spell | Effect | Mana | Cooldown |
| --- | --- | --- | --- | --- |
| Q | Ice Bolt | 24 damage; chills movement by 40% for 2 seconds | 0 | 0.35s |
| W | Frost Nova | 14 damage within 2.8 tiles; freezes movement and attacks for 2.25 seconds | 25 | 8s |
| E | Ice Wall | Three-tile barrier lasting 6 seconds; blocks characters and projectiles | 30 | 14s |
| R | Glacial Prison | Stationary and immune to damage for 2.5 seconds; shatters for 90 damage within 3.2 tiles and freezes survivors for 2 seconds | 45 | 45s |

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

## Progression and presentation

Destroy all three rifts to stop spawning, defeat the survivors, and reach the
gate. Gold is collected on contact. Food heals injured players. Potions restore
up to 40 health, cannot exceed 100 health, and are not consumed at full health.

The visual direction follows the written prompts in the recent **Ice Mage Game
Art** chat: a blue-and-silver female mage, pale fur collar, an original “forever
frozen” glyph, molten demonic skeletons, and a dark forest setting. This build
uses original procedural artwork and synthesized sound. The generated reference
image files were not available through the chat reader. Detailed animated
sprites and final environmental art remain future work.

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

- `dungeon/abilities.py`: spell definitions and initial balance values.
- `dungeon/controls.py`: mouse orders, button targeting, and hotkey casting.
- `dungeon/navigation.py`: reachable destinations and smoothed grid paths.
- `dungeon/world.py`: collision, spells, effects, enemies, spawning, and progression.
- `dungeon/render.py`: procedural art, target frame, ability buttons, and previews.
- `dungeon/audio.py`: synthesized spell and combat cues.
- `dungeon/app.py`: desktop events, viewport conversion, pause, and restart.
- `tests/`: simulation, controls, desktop input, and original-game regression tests.

The original text prototype remains available with `uv run main.py --text`.
See [GAME_DESIGN.md](GAME_DESIGN.md) for the direction and later milestones.
