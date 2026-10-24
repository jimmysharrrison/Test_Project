# Codex / Bestiary and Item Catalog

Open **Codex** from the title/pause menu or the gameplay header. The unused default shortcut is **C**. `--codex-key k` assigns another unused letter; reserved spell, inventory, shop, journal, movement, potion, pause and sound bindings are rejected. Escape or the shortcut restores the exact prior screen. The Bestiary is the first tab; Item Catalog is second. Click filters to cycle, type in Search, scroll either panel, or use Up/Down to select entries. Enemy numerical sorts use the selected preview context and put unknown values last. Item sorts support name, slot, and highest currently owned rank; rank filtering in the player view refers to currently owned instances, while developer rank filtering selects the template preview rank.

The registry derives its 18 entries from `world.ENEMY_STATS`, `encounters.BOSSES`, and `encounters.COMPANIONS`: 12 core species including the Keeper, three miniboss variants, and three distinct companion variants. Variant IDs are explicit and independent of editable names. New authored variants must use a stable ID in their spawn definition. There are no registered unfinished species/items in this build; unimplemented upper-floor ideas are not catalog entries. The item catalog derives all 25 templates from `items.DEFINITIONS`: five original ordinary templates, 15 additional ordinary templates, and five Frostweave pieces. Ordinary ranks 1–3 show actual random-roll ranges and a labeled midpoint preview; Frostweave ranks 3–5 show fixed bonuses. Unsupported ranks are labeled unavailable and excluded by rank filters. Templates are not owned instances.

## Discovery and saves

- Spawning alone grants nothing. A living actor is encountered when within 7.5 tiles, in the rendered world viewport, and in line of sight, or when directly hit by the player's combat. Visibility is evaluated during gameplay, not during menu rendering.
- Encounter unlocks name, existing procedural artwork, category, flavor text, and the floors actually encountered. First defeat unlocks mechanics, advice, observed maximum-health range, labeled base stats, and context previews. Keeper mechanics and later stages remain hidden until defeat, except in explicit Developer View.
- Anonymous entries have no art, names, species IDs, category, or floor information in their display/copy output. Search and semantic filters omit unknown rows uniformly rather than filtering on hidden metadata. Discovery counts always count earned entries, including in Developer View.
- Lifetime defeats, encounter/defeat status, UTC first-event dates, observed health, and encountered floors are separate fields. A lethal actor is counted once; existing damage guards and a per-actor Codex guard reject repeat callbacks.
- Summoned specimens use the same species entry and count an actual defeat. Timeout recalls, boss cleanup, and despawning do not count as defeats. Distinct authored miniboss companions have their own stable variant IDs. Practice worlds, debug-invulnerable/debug worlds, and explicitly debug-only actors cannot contribute.
- Bestiary and item discovery history live in the profile and survive Start Game/new runs. Collected equipment records its template before it can be sold/destroyed. Existing owned equipment backfills item discovery. Old aggregate kills, floor unlocks and completion flags do not supply species-level encounter records or dates, so old profiles start with unknown enemies rather than invented counts/dates. Version 1/2 saves remain readable, with additive optional fields and atomic writes. Invalid discovery data disables autosaving to preserve the original file.

## Developer inspection

Launch with `--development-mode` to expose the checkbox **Show undiscovered content**, initially off. Normal player launches omit the checkbox and stage/status inspection controls. Enabling it labels the screen **Developer View** and displays implemented species/templates independently of discoveries. It changes only the Codex's transient UI state: no grants, unlocks, counts, achievements, random rolls, run context, or save writes. Turning it off immediately restores the normal discovery projection. Previewing floor, spawn phase, Keeper stage, chill, Ice Patch, or equipment rank constructs disposable values without operating on the current run. No live editing is supported.

Enemy previews use `Enemy.max_hp`, `Enemy.move_speed`, the shared `combat_values` parameters actually consumed by combat, and Keeper tuning. Standard attacks scale by floor; charge/pounce, miniboss signatures, and Keeper duties retain their implemented fixed damage. Movement parameters are distinct from actual stationary behavior and special lunge speed. Attack intervals exclude warning, recovery and scheduling; durations, tile ranges, speed, HP and multipliers are labeled. There is no separate AI detection radius: the UI says so instead of substituting the discovery visibility radius. The Keeper's frost resistance is a temporary freeze restriction, not damage resistance. Damage is before player armor and invulnerability. Floor/phase/status modifiers are shown separately from base values.

**Copy details** uses the system clipboard as plain text and includes the selected developer entry's stable ID, actual definition/source locations, context, and the same displayed values. It reports clipboard unavailability in SDL dummy/headless environments. Sample output and screenshots are in `docs/codex/`; regenerate them with `.venv/Scripts/python tools/codex_preview.py`. That tool uses disposable characters and never loads/saves a profile.

## Pause and verification

Codex uses the existing app menu mode, suspending the same `World.update`/controls path as inventory and journal. Combat, mana regeneration, cooldowns, status durations, presentation delays, and active-play timers stop together. It does not set `world.state`, restart encounters, reset achievements, or alter Timing eligibility. Telemetry naturally records Codex wall time under `codex`, outside simulation time. Previous title, pause, inventory, floor-clear, dead and completed states are restored.

Run the suite on Windows with temporary files in the workspace when the sandbox's system temporary directory is not writable:

```powershell
$env:TEMP = 'C:\Projects\Test_Project\.test-tmp'
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

`tests/test_codex.py` covers registry completeness, visibility/contact discovery, repeated deaths, summons/debug exclusions, filtering/spoilers, all supported floor/phase/rank preview formulas, copying context, developer save isolation, normal-player control omission, migration/save-load, collected-item history, full pause/resume, end-state restoration and new-run persistence. Existing combat, tutorial, achievements, timing, inventory, encounter, tower and desktop regressions run alongside it.
