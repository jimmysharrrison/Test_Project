# Embervault

An original, Gauntlet-inspired isometric action dungeon crawler, built with
Python 3.14 and Pygame CE. This first playable prototype includes one dungeon,
a Warden with throwing axes and a dash, two enemy types, destructible enemy
rifts, healing, gold, sound effects, and a complete escape objective.

![The Hollow Sanctum](docs/preview.png)

## Play

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
these commands from this project folder:

```sh
uv sync --locked
uv run main.py
```

uv installs the pinned Python 3.14.8 runtime and the game dependency as needed.
A graphical desktop is required to play. A headless/cloud terminal can run the
simulation and generate screenshots, but cannot show an interactive game window.

Press **Enter** or click **Begin Descent** on the title screen.

| Control | Action |
| --- | --- |
| WASD / arrow keys | Move relative to the screen |
| Mouse | Aim |
| Hold left mouse button | Throw axes |
| Space | Dash in the movement direction (or aim direction when stationary) |
| E | Drink a potion; restores up to 40 health |
| Escape | Pause / resume |
| M | Mute / unmute sound effects |
| R | Restart after death or victory |

Destroy all three violet rifts to stop enemies spawning. Clear the surviving
enemies, then reach the northern gate. Gold is collected on contact; food heals
you when injured. A dash briefly protects you from damage. Potions are limited,
and using one at full health does not consume it.

The game pauses when the window loses focus. Resize the window freely; the
view keeps its aspect ratio. Sound automatically falls back to silence when no
audio device is available.

## Original text prototype

The original game remains available:

```sh
uv run main.py --text
```

## Verification

```sh
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q dungeon main.py text_game.py
uv run main.py --headless --frames 120 --seed 7 --screenshot /tmp/embervault.png
```

`--headless` uses a virtual display and begins the run immediately. `--frames`
exits after the specified number of frames. Neither requires a desktop.

## Project structure

- `dungeon/world.py`: time-based combat, collision, navigation, spawning, and progression.
- `dungeon/geometry.py`: world vectors and isometric projection.
- `dungeon/render.py`: procedural dungeon art, depth sorting, and interface.
- `dungeon/audio.py`: synthesized sound effects; no audio files required.
- `dungeon/app.py`: window, input, pause/restart, and command-line options.
- `text_game.py`, `gameobjects.py`, `monsters.py`, `settings.py`: original console game.
- `tests/`: simulation tests and console regression tests.

All visual art and sound effects in the prototype are generated in code. This
milestone is single-player, with one room and one hero; final art, multiple
levels, equipment, and co-op are future work. See [GAME_DESIGN.md](GAME_DESIGN.md).
