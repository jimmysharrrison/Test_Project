# Frost Mage

## Story

The heroine is an as-yet nameless Frost Mage and a wanderer. She trained at
Drearamore, a college focused on the elemental arts, whose motto is
**elementis fidelis est**. Her travels bring her to **The Tower**, a twenty-story
structure where each floor conceals a different kind of magical disorder.

The opening story arc focuses on the first five floors. This build authors all
five. The Keeper completes this section; fifteen more stories remain. His upper
stair is sealed until a future chapter, rather than loading a placeholder floor.
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
3. Destroy two spawners, wait three seconds, destroy three, then face the floor mini-boss.
4. Collect ranked gear, equip it with I, and visit the enchanter with B.
5. Survive the remaining mobs while reaching the stair portal.
6. Climb into Thornveil Atrium, then the Alchemist's Workshop.
7. Clear all three phases on each floor, carrying equipment and gold forward.

## Encounter phases

Floors 1-3 each start with two spawners, followed after a three-second
intermission by three spawners. A second intermission leads to a mini-boss
encounter instead of another spawner wave. Phase 2 mobs move at 115% speed;
final encounter actors use 130%. Existing survivors retain their birth speed.
Safe placement defers the encounter if terrain or actors occupy its positions.

- **Ground Floor — Oathbound Warden:** two Animated Shields reduce damage to
  the Warden while unfrozen. Winterbreaker marks a lane for 1.2 seconds, then
  charges until terrain stops it (or the charge expires). Recovery lasts 2.2 seconds.
- **Thornveil — Rootbound Heart:** stationary, healed by unfrozen Thorn Tenders
  within five tiles. Briar Cage warns for 1.6 seconds, then closes around the
  marked location. A green gap points toward the Heart. Recovery lasts 1.8 seconds.
- **Workshop — Splintered Alchemist:** two Volatile Duplicates accompany the
  caster. Chain Reaction marks three potion pools, igniting at 1.2, 1.75, and
  2.3 seconds. Explosions also damage duplicates. Recovery lasts 1.8 seconds.

Frost interrupts pending signatures. Bosses take 35% extra damage during
recovery. Bosses and companions guarantee equipment drops; the main boss drops
500 base gold, scaled by floor (500 / 575 / 650 on floors 1–3). Boss and companions must all fall before the
portal opens; ordinary survivors remain optional. First-floor boots are awarded
once after the encounter clears.

Gold and equipment remain on the ground during intermissions and after victory,
without a timer. Walk over them to collect them. Entering the stair portal banks
any remaining gold and gear before leaving the room.

Every fifth floor is reserved for an entire authored boss encounter, rather than
ordinary mob-clearing phases. Floor 4 uses 2/3/4 containment devices, and floor 5
is the Keeper's health-stage encounter; see `docs/LOWER_TOWER.md`.

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
the windup. Terrain blocks their shots; Glacial Prison absorbs them.

## Interaction rules and spells

- Right click owns movement. Orders persist until arrival, stop, or replacement.
- Paths route around terrain; Ice Patch is walkable ground.
- Left click owns selection and UI; it never performs an automatic attack.
- QWER hotkeys and spell buttons share the same resource and cooldown checks.
- Q and E buttons arm targeting; left click confirms, right click or Escape cancels.
- W and R cast around the mage. Brief casts interrupt movement, then orders resume.
- Glacial Prison prevents movement, casting, potion use, and damage until shatter.
- Escape pauses, focus loss pauses, I opens gear, B opens the shop, and J opens the journal.
- Enter climbs after a floor clear, retries the current floor after death, or returns
  to the title after the lower five-floor section.

| Key | Ability | Role |
| --- | --- | --- |
| Q | Frost Bolt | Free repeatable skill shot; damage and chill |
| W | Frost Nova | Close damage and hard freeze |
| E | Ice Patch | Six-second, 2.4-tile-radius field: half enemy movement, 60% attack rate, +30% mage frost damage |
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
loading or retrying, except a saved defeated Keeper room, which stays cleared
until an explicit replay. Old endless depths above 5 map to floor 5 without losing
gear or gold. The legacy save location remains to preserve local characters.
See `docs/EQUIPMENT.md` for the complete balance and economy tables.

## Architecture and next work

Simulation and navigation remain independent of Pygame. World coordinates are
projected to an isometric screen. Selection, movement, and skill-shot aim are
separate state. Phase countdowns and status timers use simulation time, so
pausing freezes them. Authored floor data contains terrain, story, enemy rosters,
and encounter layouts. Floors 1-3 retain mini-boss finales; floor 4 uses three
spawner waves. The separate Keeper controller schedules persistent mechanics
and certifies escape routes against actual terrain, enemies, movement
speed and vine costs. It never counts casting animations alone.

The next story milestones lie above floor 5. Further work can develop the upper
tower, final directional sprites, and a human balance pass through the opening arc. Co-op remains a separate future project.

Runtime: Python 3.14.8 and Pygame CE, with five authored tower interiors and
one Frost Mage. The preserved console prototype runs with `main.py --text`.


Ice Patch keeps E's 30 mana, 14s cooldown and five-tile placement range. It can be
placed under actors, does not block paths or projectiles, and does not stack
with itself. Enemy windups, attack cooldowns, recovery and boss scheduling slow
inside; charges and pounces also travel slower. Freeze/status durations and
existing hostile projectile flight remain unchanged. Chill multiplies with the
movement slow. The mage's frost bonus is captured when casting Q, W or R, then
multiplies with equipment and critical damage. No patch state enters the save.


## Local playthrough telemetry

Normal desktop play records local event journals and per-floor summaries under
`logs/`. Closing a session creates an uploadable ZIP with detailed combat data,
gear and tuning snapshots, health/resource pressure, outcomes and performance
context. Pauses are excluded from simulation/combat time. Gameplay exceptions
are captured without replacing the original traceback, and recorder failures
must not interrupt play. Headless logging is opt-in and labelled. No network
transport is used. See `docs/TELEMETRY.md` for upload instructions and metric
interpretation. Logging is covered by combat/RNG equivalence tests.
