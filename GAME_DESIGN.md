# Isometric dungeon crawler

## Direction

An original action dungeon crawler inspired by Gauntlet's fast combat and
pressure from enemy generators. Build on the existing dungeon, monster, health,
and potion ideas, with real-time movement and an isometric camera.

The first milestone should answer one question: is moving through the dungeon
and fighting a crowd fun?

## First playable milestone

- One compact dungeon with walls, obstacles, and an exit.
- One hero with responsive movement, a repeatable aimed attack, and a dash.
- Enemy generators that continually create enemies until destroyed.
- A slow enemy and a faster, weaker enemy with readable silhouettes.
- Health, limited healing potions, and gold pickups.
- A complete run: enter, destroy the generators, clear the enemies, and escape.
- Clear damage feedback, health bars, death, victory, pause, and restart.

### Controls

- WASD or arrow keys: move relative to the screen.
- Mouse: aim; left mouse button: attack.
- Space: dash.
- E: use a potion.
- Escape: pause.
- R: restart after death or victory.

### Presentation

Use a fixed isometric view with depth sorting, distinct floor and wall shapes,
warm torchlight, cool stone, and a bright player silhouette. Start with original
procedural shapes so camera, collisions, and combat can be evaluated before
commissioning final art. Ensure attacks and enemy damage cues stay readable
when several enemies overlap.

## Implementation principles

- Keep simulation coordinates independent of the isometric screen projection.
- Use elapsed time for movement, attacks, and spawning.
- Keep collision, damage, and progression logic testable without a display.
- Treat the current text game as a reference for its mechanics.
- Establish one playable loop before adding progression or more rooms.

## Later milestones

1. Tune combat feel, enemy navigation, and encounter pacing from playtesting.
2. Add room transitions, more enemy types, traps, and a boss.
3. Introduce heroes with distinct weapons and abilities.
4. Add permanent progression and equipment if they improve the core loop.
5. Evaluate cooperative play as a separate milestone because it changes input,
   camera behavior, combat balance, and networking requirements.

## Runtime

Python 3.14 desktop application, using Pygame CE for rendering and input.
Simulation code stays independent of Pygame so it can be tested without a window.
The original console prototype remains available with `python main.py --text`.
