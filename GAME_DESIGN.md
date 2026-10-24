# Frost Mage

## Story

The heroine is an as-yet nameless Frost Mage and a wanderer. She trained at
Drearamore, a college focused on the elemental arts, whose motto is
**elementis fidelis est**. Her travels bring her to **The Tower**, a twenty-story
structure where each floor conceals a different kind of magical disorder.

The opening story arc focuses on the first five floors. This build authors the
first three; floors 4 and 5 remain visible as coming later. Reaching the third
floor's exit ends this chapter instead of generating another placeholder room.
The title's Story screen introduces the setting. Each floor has a journal
opened with J, a story subtitle, and phase-specific narrative announcements.

## Current playable loop

The title offers Start Game, Continue, Level Select, How to Play, The Story,
and Quit. Start Game creates a fresh ground-floor character after confirmation
if one exists. Continue resumes the current floor, separately from the highest
reached floor. Level Select preserves gear and permits only reached, authored
floors. Escape opens Resume, How to Play, and Main Menu. Menus and the journal
suspend simulation and support mouse or keyboard navigation.

1. Enter The Tower's ground floor, occupied by molten skeletons and skitters.
2. Right click to move, aim with the mouse, and cast QWER frost spells.
3. Destroy two spawners, wait three seconds, destroy three, then destroy four.
4. Collect ranked gear, equip it with I, and visit the enchanter with B.
5. Survive the remaining mobs while reaching the stair portal.
6. Climb into Thornveil Atrium, then the Alchemist's Workshop.
7. Clear all three phases on each floor, carrying equipment and gold forward.

## Encounter phases

Every authored floor uses the same controller:

| Phase | Spawners | Movement speed of new mobs |
| --- | ---: | ---: |
| 1 | 2 | 100% |
| 2 | 3 | 115% |
| 3 | 4 | 130% |

Destroying a phase's last spawner banks gold and equipment and starts a
three-second countdown. Survivors keep attacking and retain their birth-phase
speed; the player may move and heal during the wait. Health, mana, and spell
cooldowns continue normally. Upcoming spawners are previewed with ground rings.

Spawners use clear reachable floor near the authored location when a player,
survivor, or temporary Ice Wall occupies it. No spawner appears inside terrain
or a character. A blocked phase is deferred until safe placement is possible.
The portal stays sealed until phase 3 is finished. Surviving mobs are optional.
The first-floor boots are awarded once, only after that final clear.

## Floors

**1 — The Ground Floor:** a broad stone entrance hall with a central inlay and
four equally spaced load-bearing columns around the center. These are solid
obstacles supporting the rest of the twenty-story tower. Molten Skeletons and
Ember Skitters emerge from ember rifts. Their base combat roles are retained.

**2 — Thornveil Atrium:** a vast indoor garden under a glass vault. Stone walls
and tower windows frame moss, roots, trees, mushrooms, and green wisps. Darkroot
Treants, Thornwood Spiders, and Briarbone Archers emerge from Blighted Hearts
in a 45% / 35% / 20% mix. The corrupted garden hints at chemical trouble above.

**3 — The Alchemist's Workshop:** the wizard's little helper fairies spilled the
potions and lost their senses. Bewitched Armor walks without an owner, Runaway
Grimoires flap between benches, and Potion-Maddened Fairies throw unstable magic.
Unstable Alembics spawn these mobs in a 35% / 35% / 30% mix. Benches obstruct
movement; colored spills, glowing bottles, and bubbling stills establish the
accident without adding extra ground-damage mechanics in this build.

Archers lock an aim line during a 0.65-second draw, shoot at 5.5 tiles/second,
and wait 2.8 seconds before drawing again. Fairies aim for 0.8 seconds, throw
potion bolts at 4.4 tiles/second, and wait 2.3 seconds before casting again.
Both seek line of sight, retreat when approached, and can be frozen to interrupt
the windup. Terrain and Ice Wall block their shots; Glacial Prison absorbs them.

## Interaction rules and spells

- Right click owns movement. Orders persist until arrival, stop, or replacement.
- Paths route around permanent terrain and temporary ice.
- Left click owns selection and UI; it never performs an automatic attack.
- QWER hotkeys and spell buttons share the same resource and cooldown checks.
- Q and E buttons arm targeting; left click confirms, right click or Escape cancels.
- W and R cast around the mage. Brief casts interrupt movement, then orders resume.
- Glacial Prison prevents movement, casting, potion use, and damage until shatter.
- Escape pauses, focus loss pauses, I opens gear, B opens the shop, and J opens the journal.
- Enter climbs after a floor clear, retries the current floor after death, or returns
  to the title after the third floor's ending.

| Key | Ability | Role |
| --- | --- | --- |
| Q | Frost Bolt | Free repeatable skill shot; damage and chill |
| W | Frost Nova | Close damage and hard freeze |
| E | Ice Wall | Temporary terrain that blocks movement and projectiles |
| R | Glacial Prison | Defensive stasis followed by an area shatter |

Base values remain in `dungeon/abilities.py` and README.md. Freeze stops movement
and attacks; chill slows movement. Spawners take damage but cannot be frozen.
Temporary walls cannot overlap actors or disconnect reachable parts of a floor.

## Equipment and persistence

Five slots: Helm (damage), Chest (maximum health), Legs (flat armor), Gloves
(cooldown reduction), and Boots (speed, critical chance, and critical damage).
Drops are Rank 1–3; purchased Rank 0 blanks and loot can be enchanted through
Rank 5. The final upgrade costs 15,000 gold per item. First-floor Rank 1 boots
remain a one-time reward after all three phases.

Purchased blanks form Frostweave. All five pieces must be equipped at Rank 3+.
The lowest equipped rank sets a 15% / 25% / 40% Frost Bolt freeze chance at
full-set Rank 3 / 4 / 5. Freeze lasts one second and never shortens a longer
freeze. Set identity survives enchanting and saving. Legacy shop blanks are
recognized; old enchanted items without origin metadata are not retagged.

The enchanter has an explicit target slot, accepts worn or backpack drags, and
provides a Place Selected Item alternative. Placing the UID reference does not
move or unequip gear; only pressing Enchant charges gold. Upgrade markers,
prioritized backpack pages, tooltips, confirmed Rank 3+ sales, rank-filtered Sell
All, and confirmed destruction remain available in paused menus. Equipped items
cannot be sold. Confirmed quotes validate every item before paying or removing.

Chest swaps cannot heal the mage. Saves preserve equipment, gold, potions, kills,
current floor, highest reached floor, and the first-clear reward state. Replays
keep unlocks; entering the next floor unlocks it. Rooms and phases restart when
loading or retrying. Old endless depths above 3 map to floor 3 without losing
gear or gold. The legacy save location remains to preserve local characters.
See `docs/EQUIPMENT.md` for the complete balance and economy tables.

## Architecture and next work

Simulation and navigation remain independent of Pygame. World coordinates are
projected to an isometric screen. Selection, movement, and skill-shot aim are
separate state. Phase countdowns and status timers use simulation time, so
pausing freezes them. Authored floor data contains terrain, story, enemy rosters,
and three spawner layouts; future floors use the same controller.

The next story milestones are floors 4 and 5. Further work can develop their
themes, encounters, and bosses, followed by final directional sprites and a
balance pass through the opening arc. Co-op remains a separate future project.

Runtime: Python 3.14.8 and Pygame CE, with three authored tower interiors and
one Frost Mage. The preserved console prototype runs with `main.py --text`.
