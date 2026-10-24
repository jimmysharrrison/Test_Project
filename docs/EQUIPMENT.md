# Equipment and enchantments

The catalog has 25 stable templates: five original ordinary pieces, 15 additional ordinary pieces, and five Frostweave set pieces. Only equipped items contribute stats. New ordinary items have exactly one rolled enchantment and no inherited fixed slot package. These smaller bonuses replace the old acquisition balance, without changing already-saved gear.

## Ranks and acquisition

- Ordinary items support Ranks 1–3. Enchanting to Rank 2 requires reaching floor 3; Rank 3 requires reaching floor 5. Upgrades cost 150 and 450 gold. Ordinary items cannot become Frostweave.
- Floors 1–2 drop Rank 1 only. Floors 3–4 use 90% Rank 1 / 10% Rank 2. Floor 5 uses 75% / 23% / 2% for Ranks 1 / 2 / 3. The existing rare boot slot roll is retained; each slot draws uniformly from its four ordinary templates.
- Before the first Keeper victory, the shop sells the five original ordinary templates at Rank 1. The first ground-floor clear still awards Rank 1 Everfrost Treads, now with a random speed roll.
- The first Keeper victory awards a Rank 3 Frostweave Crown and permanently unlocks Rank 3 Frostweave stock. Once unlocked, 12% of equipment drops are replaced by Rank 3 Frostweave of that slot. No pre-unlock stock/drop/reward grants newly created Frostweave.
- Ranks 4–5 are exclusive to newly acquired Frostweave. The next upgrades cost 2,500 and 15,000 gold per piece. Repeat Keeper victories do not duplicate the first-victory crown. The profile unlock survives new runs.

| Slot | Ordinary Rank 1 stock | Frostweave Rank 3 stock |
|---|---:|---:|
| Helm | 90 gold | 690 gold |
| Chest | 110 gold | 710 gold |
| Legs | 90 gold | 690 gold |
| Gloves | 100 gold | 700 gold |
| Boots | 250 gold | 850 gold |

## Rolls and effects

An ordinary drop stores its stable template ID and a quality integer from 0 through 10,000. The definition maps that percentile into its rank’s permitted range and rounds to 0.1 percentage-point increments. Enchanting preserves the percentile and improves the range; it never rerolls. Save/load, selling, equipping and opening the Codex never reroll. Crit chance is added in percentage points; other numerical enchantments are relative percentages. Catalog values are labeled midpoint previews with the real possible ranges, not actual owned instances.

| Item | Slot | Enchantment | Rank 1 | Rank 2 | Rank 3 |
|---|---|---|---|---|---|
| Rimeweaver Crown | Helm | spell damage | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Frostmantle Vestment | Chest | maximum health | 0.1–5.9% | 1.0–8.9% | 2.0–11.9% |
| Glacierweave Leggings | Legs | incoming damage reduction | 0.1–1.9% | 0.3–2.9% | 0.5–3.9% |
| Wintercall Grips | Gloves | spell cooldown reduction | 0.1–1.9% | 0.3–2.9% | 0.5–3.9% |
| Everfrost Treads | Boots | movement speed | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Apprentice’s Rimeband | Helm | spell damage | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Deepwell Circlet | Helm | maximum mana | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Snowseer Hood | Helm | spell area radius | 0.1–2.9% | 0.5–3.9% | 1.0–4.9% |
| Snowbound Robe | Chest | maximum health | 0.1–5.9% | 1.0–8.9% | 2.0–11.9% |
| Stillwater Vestment | Chest | mana regeneration while stationary | 0.1–5.9% | 1.0–8.9% | 2.0–11.9% |
| Winterthorn Coat | Chest | attacker movement slow for 1s (3s trigger cooldown) | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Stonefrost Leggings | Legs | incoming damage reduction | 0.1–1.9% | 0.3–2.9% | 0.5–3.9% |
| Driftwalker Trousers | Legs | shorter movement slows on you | 0.1–5.9% | 1.0–9.9% | 2.0–14.9% |
| Runestitched Leggings | Legs | food and potion healing | 0.1–5.9% | 1.0–8.9% | 2.0–11.9% |
| Quickrime Gloves | Gloves | spell cooldown reduction | 0.1–1.9% | 0.3–2.9% | 0.5–3.9% |
| Frugalweave Wraps | Gloves | spell mana-cost reduction | 0.1–2.9% | 0.5–3.9% | 1.0–4.9% |
| Lingering Frost Grips | Gloves | longer chill / gear slows (not freezes) | 0.1–5.9% | 1.0–8.9% | 2.0–11.9% |
| Snowstep Boots | Boots | movement speed | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Rimetrail Boots | Boots | ice-trail movement slow (1s trail; no spell-field bonus) | 0.1–5.9% | 1.0–7.9% | 2.0–9.9% |
| Shardhunter Boots | Boots | critical-hit chance (percentage points) | 0.1–0.9% | 0.2–1.4% | 0.3–1.9% |

Winterthorn slows the exact enemy that damaged the mage, including ranged shooters, for 1 second with a 3-second trigger cooldown. Invulnerable/stasis hits do not trigger it. It slows movement only, never freezes or changes attack clocks.

Rimetrail emits a small trail patch every 0.3 tiles actually walked. Each patch has a 0.38-tile radius and lasts 1 second. It affects enemies touching it; standing still emits nothing. It grants no Ice Patch damage bonus, freeze, attack slow or Frostweave capstone interaction. It is separate from spell fields. Multiple gear slows use the strongest active strength, each retaining its own lifetime; they cannot amplify a stronger native chill/patch combination.

Lingering Frost extends Bolt chill and the lifetimes of gear slows/trails. It does not extend freezes, stasis or Ice Patch fields. Snowseer expands Nova, Ice Patch field radius and Prison shatter radius, not Bolt range or Ice Patch placement distance. Stillwater checks actual movement during the simulation step, including blocked movement, to determine stationary regeneration.

Driftwalker shortens timed player movement slows. Keeper vines refresh a 0.3-second contact pulse; the enchantment shortens that pulse, allowing brief recovery between pulses while inside vines. Leaving the vines clears their contact pulse immediately. Baseline movement is unchanged and the Keeper’s safe-route certification remains conservative because it assumes the full original vine slowdown. Timed slow strength and duration are distinct from spell freezing.

Health/mana increases do not refill current resources when equipping. Removing gear clamps current values to the new maximum. Food/potion healing is multiplied before clamping. Damage reduction applies after legacy flat armor, preserving the existing one-HP minimum hit. Cooldown/mana-cost reductions apply to newly cast spells; active cooldowns are not rescaled. All new timers and trail lifetimes run in World.update and therefore pause with combat, mana regeneration and the existing Timing system.

## Frostweave and compatibility

Frostweave retains its existing fixed rank packages and five-piece bonuses. The lowest equipped rank determines the set bonus: R3 / R4 / R5 give 15% / 25% / 40% Bolt freeze chance for 1 second. The existing Rank 5 Ice Patch / Prison capstone is unchanged. Backpack items do not activate bonuses.

Old untemplated saves keep their exact fixed stats, identity and ranks, even previously owned ordinary Rank 4/5 pieces. Such legacy ordinary pieces cannot be upgraded further. Historical shop items remain Frostweave; they are not confiscated or treated as proof of a Keeper defeat. Old lower-tower completion history can support the unlock. Live acquisition exclusively uses the validated template factory; the legacy factory remains for old authoring/practice fixtures. Version 1/2 profiles remain readable, and unknown/invalid template IDs or rolls cause autosave protection rather than discarding items. New gear IDs/quality, collection history and the Frostweave unlock are persisted atomically.

The active-play timing balance version is now active-v1-balance-2, so new equipment records do not compete with old balance records. Telemetry includes stable item IDs, roll quality, effective enchantments and the definition registry.

Backpack upgrade markers compare matching templates and rolled strength. Different effects are sidegrades for the player to compare. Existing confirmed sale, destruction, drag targeting and pause rules continue to apply.

## Icon direction

New ordinary items currently reuse the slot silhouettes with small colored runes. Frostweave reuses the existing five illustrations. These descriptions specify future individual artwork; no new raster art is required to use the items.

| Item | Slot | Icon description |
|---|---|---|
| Rimeweaver Crown | Helm | Angular silver crown with a central rime crystal. |
| Frostmantle Vestment | Chest | Heavy blue vestment with a broad white fur mantle. |
| Glacierweave Leggings | Legs | Layered blue leggings patterned like overlapping glacier plates. |
| Wintercall Grips | Gloves | Dark gloves with bright frost runes across the knuckles. |
| Everfrost Treads | Boots | Sturdy snow boots with icy soles and thick white cuffs. |
| Apprentice’s Rimeband | Helm | Simple silver band with one pale-blue ice shard. |
| Deepwell Circlet | Helm | Dark-blue circlet cradling a round, glowing mana gem. |
| Snowseer Hood | Helm | Soft white hood with a widening snowflake halo. |
| Snowbound Robe | Chest | Padded blue robe with a snow-covered heart clasp. |
| Stillwater Vestment | Chest | Deep teal robe bearing a still pool and rising blue mote. |
| Winterthorn Coat | Chest | Short fur-lined coat with icy thorns around the collar. |
| Stonefrost Leggings | Legs | Slate-gray leg guards with frosted stone knee plates. |
| Driftwalker Trousers | Legs | Light trousers with wind-swept snow curling around the cuffs. |
| Runestitched Leggings | Legs | Indigo leggings stitched with small green restorative runes. |
| Quickrime Gloves | Gloves | Slim icy gloves with a small hourglass rune. |
| Frugalweave Wraps | Gloves | Blue cloth hand wraps protecting a single bright mana droplet. |
| Lingering Frost Grips | Gloves | Long gloves with delicate frost tendrils trailing from the fingers. |
| Snowstep Boots | Boots | Light blue boots with white wing-like snow streaks. |
| Rimetrail Boots | Boots | Dark boots leaving a short trail of icy footprints. |
| Shardhunter Boots | Boots | Sharp-toed boots with a tiny crystal crosshair on each cuff. |
| Frostweave Crown | Helm | Tall translucent ice-crystal crown with a luminous blue core. |
| Frostweave Vestment | Chest | Elegant white-and-cyan mage robe woven with branching frost crystals. |
| Frostweave Leggings | Legs | Pale crystal armor plates over a dark blue woven underlayer. |
| Frostweave Grips | Gloves | Crystalline blue gauntlets with sparkling ice fingertips. |
| Frostweave Treads | Boots | Polished crystal boots with faceted toes and glowing frost seams. |
