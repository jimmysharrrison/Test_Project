# Local playthrough logs

Logging is automatic in normal desktop play, starting with the next launch.
Play as usual, then close the game. In this checkout, open:

```text
C:\Projects\Test_Project\logs
```

Upload the newest `frost-mage-<UTC timestamp>-<random id>.zip` here. Two or three
sessions, plus a note about which fights felt easy or hard, are a useful start.
One session can contain several floors, deaths, retries, or new games.

Nothing is uploaded automatically. Logging uses only local files. The logs
folder is ignored by Git. Saves retain their existing format and location.

## What the ZIP contains

- `summary.txt`: readable results for each floor attempt.
- `summary.json`: structured totals, gear, tuning values and performance data.
- `events.jsonl`: detailed events in chronological order, one JSON object per line.

The game prints the upload ZIP's full path in the console when it closes.
The original files remain in the matching session folder as well.

## What we can analyze

- Floor/phase time, victories, deaths, abandoned attempts and explicit replays.
- Actual health lost, hit counts, largest hits, and damage grouped by enemy/attack.
- Spell casts, targets hit, effective damage, critical hits, Ice Patch boosts,
  and Frost Bolt hits versus terrain collisions or expired shots.
- Potions and food used, actual healing, low-health/low-mana time, and time
  spent empowered by Ice Patch or protected by Glacial Prison.
- Equipped gear and stats, changes to equipment, gold earned/spent, and peak
  enemy count, so different builds are not treated as equivalent.
- Boss attacks and stages, warning durations, safe markers, active Keeper
  duties, summons, recalls, and cleanup.
- One-second samples of position, HP, mana, enemy pressure and boss health.
- Wall time by menu/game state and slow-frame counts, separate from simulation time.
- A source-code fingerprint and tuning snapshot, to distinguish balance versions.

Combat time excludes paused/menu time and stops when the floor is cleared.
It includes travel, repositioning and intermissions, during which combat can
continue. Post-clear looting contributes only to the broader simulation time.
Damage totals use actual HP removed, excluding overkill. Environmental potion
damage is tracked separately from the mage's damage.

Warnings, projectile releases and hits are separate events. Do not sum these
as one attack count or infer an exact dodge percentage: hit immunity and
Glacial Prison can also prevent damage. A spell still in flight or a pending
shatter when the player leaves is unresolved, not a miss. Ice Patch resolves
when placed; its target count covers enemies initially inside, not later entries.
Its usefulness is also represented by empowerment time and boosted casts.

Restoring an already-cleared Keeper room is marked `previously_cleared`; it is
not another zero-second victory. Headless sessions are clearly marked and
should be excluded when assessing human difficulty. Seeds are included when
provided; these logs are observations, not a deterministic input replay.

The files contain game data, not screenshots, keystrokes, account identifiers,
computer details or the saved profile path. Crash stacks use file basenames
and line numbers; project/home prefixes in error messages are replaced.

## Crashes and write failures

Events flush as they occur. Summary JSON is checkpointed every five simulation
seconds and on a death or floor clear. Caught gameplay exceptions add a crash
event and attempt to create the ZIP before the original exception is re-raised.

After a hard process kill, there may be no ZIP. Upload `events.jsonl` and
`summary.json` from the latest session folder instead. Its checkpoint may be a
few seconds behind the event journal. Startup errors before gameplay logging
starts and power-loss durability are outside this recorder's guarantees.

A logging write error disables recording and shows an in-game notice. Gameplay
continues. Existing raw files are preserved when archive creation fails.

## Optional commands

```powershell
# Disable logging for this launch.
uv run main.py --no-telemetry

# Choose a different local destination.
uv run main.py --telemetry-dir C:\Projects\Test_Project\my-runs

# Explicitly log an automated/headless test; disabled by default in headless mode.
uv run main.py --headless --level 5 --frames 420 --no-save --telemetry
```

Balance changes remain a separate decision. Compare repeated attempts with
similar equipment, distinguish deaths from quits/replays, and pair the numbers
with how each encounter felt to play.
