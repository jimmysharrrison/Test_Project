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
2.35× critical multiplier. With a Rank 3 helm, a normal Ice Bolt deals 31 damage
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

Destroy opens a confirmation naming the exact item and rank. **Cancel** or
**Escape** closes that confirmation without removing the item; the armory stays
open. A confirmation blocks other menu actions until it is resolved. Selling
and destruction update the existing save automatically. Sold or destroyed gear
cannot be recovered, and disposing of the first-clear boots does not reset
that one-time reward.

## Depth progression and persistence

A level is complete as soon as all three spawners are destroyed. The gate opens
and the first-level boot reward is granted at that moment. Surviving enemies
can still attack while the mage heads to the exit, but do not keep the gate shut.

At the gate, choose **Enter / Next Depth**. Gear, gold, potions, and kills carry
forward; health and mana refill, and spell cooldowns reset. Later depths reuse
the current arena with 15% more enemy/rift health and gold value per additional
depth, and 12% more enemy attack damage per additional depth. Each new room has
its own rifts and enemies. Distinct maps and bosses are future work.

Equipment, enchantments, gold, potions, kills, unlocked depth, and the claimed
boot reward are saved locally. A new session starts a fresh room at the highest
unlocked depth with full health and mana. Death keeps earned equipment and gold.
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
