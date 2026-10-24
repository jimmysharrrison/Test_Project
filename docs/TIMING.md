# Gameplay timers and personal bests

Timing/balance rules ID: `active-v1-balance-1`. Profile schema 2 accepts schema 1.

Timers accumulate floating-point seconds supplied to active World updates, before
combat's simulation-step cap. They do not use launch timestamps, frame counts, or
offline time. The header displays floor time, the previous floor PB, and campaign
or practice run time as `MM:SS.hh` (minutes can exceed 59; hundredths truncate).
The completion panel marks a new floor best and labels the separate **First-five
campaign best**. Comparisons use full precision, not displayed hundredths.

A ready floor starts counting with its first controlled gameplay update. Logical
successful clear stops the floor timer immediately, before victory effects,
completion countdowns, or splash screens. The overall timer includes active play
on all floors, including controllable loot collection after nonfinal clears. It
excludes completion countdowns/splashes, loading, transitions, title and other
frontend menus, explicit/focus-loss pause, journal, inventory and shop (all three
currently pause the world). Any future overlay that keeps World.update running
also keeps timing running. Tutorial sessions use a disposable, untimed world.
Final logical floor-five clear or run-ending death stops the overall timer.
The completion frame is included at its supplied elapsed duration; no subframe
kill timestamp is inferred.

Only successful eligible clears write records. Death cannot replace a best.
New Game starts a fresh campaign and retains all PBs; retries and level selection
reset active timers into a separate practice category, since they retain earned
gear. Campaign floors and practice floors have separate record keys. Only an
uninterrupted eligible campaign sequence of floors 1,2,3,4,5 writes the first-five
record. This is not a future full-tower record. Nondefault mana regeneration is
ineligible. Balance/timing changes must bump the rules ID; old records remain
stored under their original ID and are not compared to current records.

Continue restores accumulated floor/run seconds and eligibility; it adds no
offline time. The existing save system rebuilds the current encounter, rather
than restoring enemies or their health. Replayed active seconds add to the saved
times, so Continue never grants an artificially fast record. A saved successful
floor stays stopped for floor timing and cannot commit its record twice. Old
schema-1 saves have unknown prior time and remain ineligible until a new campaign
or practice attempt starts. Unknown rules versions also remain ineligible.
Record commits are guarded by the stopped state and logical-clear transaction;
repeated clears and repeated atomic autosaves are idempotent.

Verification: `tests/test_timing.py` covers 20/30/60/144 FPS, resume accumulation,
precise persistence and legacy saves, deaths, restart/PB retention, separate
practice records, complete first-five eligibility, repeated clears, completion
delays, tutorials, custom balance, formatting and unknown rules. The desktop
suite additionally exercises actual pause, inventory, shop and journal events.
