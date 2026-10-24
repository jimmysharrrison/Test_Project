# Frostbound Armory — initial balance

The baseline Ice Mage has 100 maximum health, 3.1 movement speed, a 5% critical
chance, and a 2× critical damage multiplier. Armor is flat incoming-hit damage
reduction, with a minimum of 1 damage for a successful enemy hit. These values
fit the existing real-time combat; this is not a tabletop armor-class system.

Each piece has a fixed stat package per rank. Only the equipped piece in a slot
contributes bonuses. Spare pieces do not stack.

| Slot | Rank 1 | Rank 2 | Rank 3 | Rank 4 | Rank 5 |
| --- | --- | --- | --- | --- | --- |
| Helm: Rimeweaver Crown | +10% damage | +20% | +30% | +45% | +65% |
| Chest: Frostmantle Vestment | +20 max HP | +40 | +60 | +90 | +130 |
| Legs: Glacierweave Leggings | 1 armor | 2 | 3 | 5 | 8 |
| Gloves: Wintercall Grips | 5% cooldown reduction | 10% | 15% | 22% | 30% |
| Boots: Everfrost Treads | +6% speed | +10% | +15% | +22% | +30% |
| Boots: additional crit chance | +2 percentage points | +4 | +6 | +9 | +12 |
| Boots: additional crit multiplier | +0.10× | +0.20× | +0.35× | +0.50× | +0.75× |

For example, Rank 3 boots yield 3.565 movement speed, 11% critical chance, and a
2.35× critical multiplier. With a Rank 3 helm, a normal Frost Bolt deals 31 damage
and a critical bolt with those boots deals 73 damage (rounded after bonuses).

A Rank 5 chest gives 230 maximum HP. Equipping or enchanting a chest does not
heal the additional health. Removing it caps current health to the new maximum.
Gloves affect newly cast cooldowns; already-running timers keep their remaining
duration. Gear cannot be changed or enchanted while Glacial Prison is active.

## Loot and first-clear reward

- Normal enemies have a separate 0.5% boot-drop roll. Otherwise, a 12% roll can
  drop a helm, chest, legs, or gloves.
- Each rift guarantees one piece of equipment, with the same rare boot roll.
- Dropped ranks use weights 70% Rank 1, 25% Rank 2, and 5% Rank 3.
- Rank 3 is the highest dropped rank. Ranks 4 and 5 require enchanting.
- Clearing level 1 awards one guaranteed Rank 1 Everfrost Treads directly to the
  inventory. That reward can only be claimed once per local character profile.
- A piece fills an empty equipment slot automatically. Replacements go to the
  backpack for manual selection. The backpack supports multiple pages.
- Walk over drops to collect them. Hover the ground icon or an owned item to
  inspect its rank and bonuses. On a level clear, remaining equipment and gold
  are banked automatically, so taking the exit cannot discard earned loot.

## Shop and enchanting

Press **B** for the enchanter or **I** for inventory. Both menus pause combat.
Blank gear starts at Rank 0 with no bonuses.

All purchased blanks belong to the Frostweave set. Their names are Frostweave
Crown, Frostweave Vestment, Frostweave Leggings, Frostweave Grips, and Frostweave
Treads. Set identity is independent of rank and persists through every enchant
and save. Enchanting dropped or reward gear does not convert it into Frostweave.
Existing shop blanks migrate automatically. Legacy enchanted items lacking set
metadata remain ordinary equipment, because their original shop/drop origin
was not retained in the previous format.

| Blank item | Price |
| --- | ---: |
| Helm | 40 gold |
| Chest | 60 gold |
| Legs | 40 gold |
| Gloves | 50 gold |
| Boots | 200 gold |

Every rank must be purchased in order. The following prices are for the next
single upgrade, not cumulative totals:

| Upgrade | Price |
| --- | ---: |
| Rank 0 → 1 | 50 gold |
| Rank 1 → 2 | 150 gold |
| Rank 2 → 3 | 450 gold |
| Rank 3 → 4 | 2,500 gold |
| Rank 4 → 5 | 15,000 gold |

Enchanting a blank all the way to Rank 5 costs 18,150 gold, plus the blank's
purchase price. Rank 5 is intentionally an expensive long-term target. Existing
Rank 1–3 loot can also be enchanted, saving the cost of the lower upgrades.
Purchases and enchants check funds before changing ownership or taking gold.

Drag equipment from the worn slots or the shop's paged backpack into the
Enchanting Slot, then press Enchant to pay for the next rank. The slot refers
to the owned item; placing or clearing it does not transfer ownership, unequip,
duplicate, or destroy gear. Selecting a different item does not change the
loaded target. Place Selected Item is the click-only alternative. New purchases
are loaded automatically. A drag can start in inventory, hover the Enchanter
tab to switch views, and finish in the slot. Escape, focus loss, and invalid
drops cancel safely. Only the loaded item receives the enchant, with the normal
gold, rank, death, and Glacial Prison checks.

## Frostweave set bonus

All five different slots must have Frostweave pieces **equipped** at Rank 3 or
higher. Owning pieces in the backpack does not satisfy the requirement. The
lowest equipped piece controls the full-set rank, so a mixed Rank 3/4/5 set
uses the Rank 3 bonus until every piece reaches Rank 4.

| Full-set rank | Frost Bolt freeze chance | Freeze duration |
| --- | ---: | ---: |
| Below 3 or incomplete | 0% | — |
| 3 | 15% | 1 second |
| 4 | 25% | 1 second |
| 5 | 40% | 1 second |

The roll occurs when Q / Frost Bolt hits a surviving enemy and uses the set
equipped at that instant. The normal chill still applies. Freeze stops movement
and attacks and interrupts an archer's bow draw; it never shortens a longer
freeze already on the target. Spawners, misses, killing blows, enemy arrows,
and other spells do not trigger this bonus. Set progress appears in character
stats, set details in item tooltips, and the active chance in Q's tooltip.

## Selling and destroying spare gear

Select an unwanted item in the inventory. **Sell** exchanges it for the quoted
gold amount; **Destroy** permanently removes it for no gold. Both actions are
available in the inventory and enchanter menus for the selected owned item.
Equipped items must be unequipped first. Disposal is blocked during Glacial
Prison and after death, just like other gear changes.

Sell value is one quarter of the sum of the blank price and all enchantment
prices through that item's current rank, rounded down. The same rank has the same value
regardless of whether it was dropped or enchanted. For example:

- Rank 0 helm: 10 gold.
- Rank 1 helm: 22 gold.
- Rank 3 helm: 172 gold.
- Rank 5 boots: 4,587 gold.

The quote appears on the Sell button and in the item tooltip. Buying or
upgrading an item and reselling it always loses gold.

Backpack upgrades are shown first, highest rank first, with a green border and
checkmark. Each slot has fixed bonuses that increase with rank, so comparisons
use the equipped item in the same slot. Helpful ranked items for empty slots
count as upgrades; equal ranks and blank Rank 0 items do not. The comparison
updates after equipping, unequipping, or enchanting. Items remain selected by
their identifier when the order changes.

Individual sales of Rank 3, 4, or 5 require **ARE YOU SURE?** confirmation with
the item name, rank, and gold value. Single sales of Rank 0–2 remain immediate.
The **Sell Backpack by Rank** controls are available in both menus: select one
exact rank from R0 through R5 and click **Sell All Rank N**. The quote includes
every matching unequipped item across all pages, and never includes worn gear.
All bulk sales require confirmation, even for one Rank 0 item. The dialog shows
the number of items, total gold, and whether upgrades are included. Upgrades
are included when they match the selected rank, so review the quote before selling.
Only the quoted items can be sold. If one was equipped, enchanted, or removed
before confirmation, the whole sale is rejected without removing any items or
paying gold. Newly acquired items are not silently added to an existing quote.

Destroy opens a confirmation naming the exact item and rank. **Cancel** or
**Escape** closes that confirmation without removing the item; the armory stays
open. Sale confirmations use the same cancellation rules. Keyboard menu switches
cancel pending confirmations. A confirmation blocks other clicks until resolved. Selling
and destruction update the existing save automatically. Sold or destroyed gear
cannot be recovered, and disposing of the first-clear boots does not reset
that one-time reward.

## Depth progression and persistence

A level is complete as soon as all three spawners are destroyed. The gate opens
and the first-level boot reward is granted at that moment. Surviving enemies
can still attack while the mage heads to the exit, but do not keep the gate shut.

At the gate, choose **Enter / Next Depth**. Gear, gold, potions, and kills carry
forward; health and mana refill, and spell cooldowns reset. Level 2 enters a
distinct forest map with treants, spiders, skeletal archers, and three Blighted
Hearts in place of molten rifts. Forest drops use the same equipment rules.
Depths 3 onward reuse the forest. Each additional depth adds 15% to base enemy/
spawner health and gold, and 12% to base enemy attack damage. Each new room has
its own spawners and enemies. More chapters and bosses are future work.

Equipment, enchantments, gold, potions, kills, current level, highest reached
depth, and the claimed boot reward are saved locally. Launching shows the title
menu. Continue loads a fresh room at the current level with full health and
mana. Level Select replays reached levels while keeping gear and unlocks.
New destinations unlock on entry through the portal, rather than on clearing
the previous room. Start Game resets the character, including gear and unlocks,
after confirmation. Death keeps earned equipment and gold and retries the
current level.
The exact positions of enemies, temporary walls, and projectiles are not saved.

Default save location:

- Windows: `%LOCALAPPDATA%\Embervault\profile.json`
- Linux: `$XDG_DATA_HOME/embervault/profile.json`, or
  `~/.local/share/embervault/profile.json` when XDG_DATA_HOME is unset.

Saves replace the previous file atomically. An unreadable, corrupt, or newer
profile disables autosave and displays a warning, preserving the original file.
`--no-save` uses a temporary character; `--profile PATH` selects another save.
Headless runs do not touch a profile unless `--profile` is supplied explicitly.

The numerical tables and prices are defined in `dungeon/items.py`.
