# Drearamore interactive tutorial

Choose **Tutorial / Drearamore Practice** on the title screen to replay. New Game offers Play Tutorial or Skip / Start Game; Load Game does not show the offer. Practice has its own character and room. Save Game is disabled during practice. Returning to the menu or closing practice does not save or normalize any slot, including older version-1 saves. Starting the actual game after a confirmed new-game flow creates a fresh character without replacing a saved slot; choose Save Game when ready to keep it.

The lessons cover movement, target inspection, Frost Bolt, Frost Nova, Ice Patch, Glacial Prison, potion healing, walking over loot, inspecting and comparing equipment, equipping and swapping, ranks/Frostweave, and a final harmless encounter. Each action has a success indicator and an explicit Next lesson button. Retry Step restores the setup and resources; Skip Step records a skip separately from completion. The final encounter has Restart Practice. Exit Tutorial is always available in the footer. Completion offers Start Game, Return to Menu, and Restart Tutorial.

## Verified current behavior

| Control | Current behavior |
| --- | --- |
| Right click / hold | Move / follow cursor. S stops movement. |
| Left click | Select an enemy for its health/status panel, without a basic attack. |
| Q | Cursor-aimed Frost Bolt: 24 base damage, 40% movement slow for 2 seconds; 0 mana, 0.35-second cooldown. Hold to repeat. Does not inherently freeze. |
| W | Frost Nova: 14 base damage within 2.8 tiles, freezes surviving enemies for 2.25 seconds; 25 mana, 8-second cooldown. |
| E | Ice Patch, replacing the outdated Ice Wall request: place within 5 tiles on clear floor with line of sight; radius 2.4, lasts 6 seconds. Enemies move 50% slower and attack 40% slower; mage inside gains 30% frost damage. Costs 30 mana, 14-second cooldown. Does not block movement or projectiles. |
| R | Glacial Prison: stationary, immune to damage, unable to cast or heal for 2.5 seconds; movement orders can resume afterward. Shatter deals 90 base damage within 3.2 tiles and freezes survivors for 2 seconds. Costs 45 mana, 45-second cooldown. |
| 1 / potion button | Consume one potion, restoring up to 40 health; no mana cost or cooldown. Full health consumes nothing. Cannot heal during Prison. Food pickups also heal. |
| Spell HUD buttons | Q/E arm targeting, then left click to cast. W/R cast immediately. Right click or Escape cancels targeting. |
| Walk over loot | Pick up within 0.65 tiles. Empty slots auto-equip; otherwise equipment goes into the paged backpack, with no fixed item capacity. |
| I / Gear button | Open inventory. Click backpack item, hover for details/comparison, click Equip Item. Previous worn item returns to backpack. |
| B | Shop and enchanter. Enchanting spends gold to increase rank. No tutorial purchase is required. |
| Escape / J / M | Pause or close panel / floor journal / toggle sound. |

Five slots: helm (spell damage), chest (maximum health), legs (armor), gloves (cooldown reduction), boots (speed and critical stats). The practice crown swaps Rank 1 / Tempered / +10% damage for Rank 2 / Runed / +20% damage.

Frostweave requires **all five pieces equipped**, with set rank determined by the lowest worn rank. Set rank 3/4/5 gives Frost Bolt a 15/25/40% chance to freeze for one second. Pieces in the backpack contribute nothing. Spell damage and cooldowns can change with equipment and Ice Patch; the tutorial states base values.

## Implementation

`dungeon/tutorial.py` contains explicit lesson state and a disposable `PracticeWorld` subclass. It inherits actual spell validation, projectile collisions, damage/status resolution, potion healing, navigation, pickup and equipment behavior. Only encounter progression, hostile damage, random equipment drops, and training-dummy movement are suppressed. The final practice restores enemy movement and the Prison lesson uses the real archer windup and projectile collision. Real combat resolution events determine success; key presses alone do not count.

`dungeon/app.py` suspends the original world and armory, routes menu and lesson controls, excludes practice from autosave/final saving and normal combat telemetry, and restores the original world on exit. No save schema change or tutorial-completed flag is needed. The inventory remains open between inspection and equipping. Retry rebuilds missing/sold/destroyed practice equipment and clears targeting and confirmations. Actual rejection messages remain visible below the arena. Callouts and input use the existing logical canvas and window scaling together.

## Validation

- Final result: **264 tests passed**, including **20 tutorial tests**. `git diff --check` passed.
- Full existing regression suite plus tutorial tests, using a workspace-local temporary directory on Windows. Tests cover action completion, rejected casts, misses, dual-target Nova, Patch enemy/mage effects, Prison protection and release, potion consumption, real armory selection/equip, unequipping after success, retries, skips, death recovery, rapid inputs, inventory reopening, new-game handoff, and byte-identical existing/legacy save preservation.
- Full live-window playthrough at normal speed, using mouse movement and real HUD/armory interactions through the computer-use skill: all lessons completed without skipping, final targets defeated, and Start Game returned to clean normal gameplay. Keyboard event routing is covered by automated desktop regression tests; the Windows input helper's letter-key attempts were not independently reliable during this playthrough.
- Rendered spell/equipment callouts at 1024×768, 1280×800, 1440×900, and 1920×1080; inspected screenshots and checked text widths, target clearance, and inventory control clearance. These additional sizes use the same letterboxing and scaling as the app; live play used the default 1280×800 window. Sizes below 1024×768 were not visually assessed.
- Reproduce screenshots with `.venv/Scripts/python.exe -m tools.tutorial_preview`. Images are in `docs/tutorial/`; `equipment-live.png` shows the live completed swap, while the other images show the final code's guidance at the named size.

No changes were pushed to GitHub. Existing unrelated working-tree edits were retained.
