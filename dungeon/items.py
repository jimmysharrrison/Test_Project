"""Stable item definitions, rolled enchantments, ownership, and equipment bonuses."""

from dataclasses import dataclass, replace

SLOTS = ("helm", "chest", "legs", "gloves", "boots")
NAMES = {
    "helm": "Rimeweaver Crown",
    "chest": "Frostmantle Vestment",
    "legs": "Glacierweave Leggings",
    "gloves": "Wintercall Grips",
    "boots": "Everfrost Treads",
}
FROSTWEAVE_NAMES = {
    "helm": "Frostweave Crown", "chest": "Frostweave Vestment",
    "legs": "Frostweave Leggings", "gloves": "Frostweave Grips", "boots": "Frostweave Treads",
}
FROSTWEAVE_CHANCE = {3: .15, 4: .25, 5: .40}
FROSTWEAVE_FREEZE = 1.0
SLOT_PURPOSE = {
    "helm": "Increases all spell damage.",
    "chest": "Increases maximum health.",
    "legs": "Armor reduces damage from each hit.",
    "gloves": "Reduces cooldowns of newly cast spells.",
    "boots": "Speed, critical chance, and critical damage.",
}
RANK_NAMES = ("Unranked", "Tempered", "Runed", "Perfect", "Ascendant", "Mythic")
RANK_COLORS = ((139, 151, 162), (122, 198, 161), (114, 174, 235),
               (192, 141, 235), (243, 174, 104), (246, 218, 132))
BLANK_COST = {"helm": 40, "chest": 60, "legs": 40, "gloves": 50, "boots": 200}
# Price for the next rank, never the cumulative price. Rank 5 is deliberately aspirational.
ENCHANT_COST = {1: 50, 2: 150, 3: 450, 4: 2500, 5: 15000}
VALUES = {
    "damage": (0, .10, .20, .30, .45, .65),
    "health": (0, 20, 40, 60, 90, 130),
    "armor": (0, 1, 2, 3, 5, 8),
    "cooldown": (0, .05, .10, .15, .22, .30),
    "speed": (0, .06, .10, .15, .22, .30),
    "crit_chance": (0, .02, .04, .06, .09, .12),
    "crit_damage": (0, .10, .20, .35, .50, .75),
}


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    id: str
    name: str
    slot: str
    effect: str
    ranges: tuple
    icon: str
    set_id: str | None = None

    @property
    def max_rank(self):
        return 5 if self.set_id else 3

# Bounds are tenths of a percent (1 = 0.1%); crit uses percentage points.
SMALL = ((1, 59), (10, 79), (20, 99))
RESOURCE = ((1, 59), (10, 89), (20, 119))
MODEST = ((1, 29), (5, 39), (10, 49))
DEFENSE = ((1, 19), (3, 29), (5, 39))
EFFECT_LABELS = {
    'damage': 'spell damage', 'mana': 'maximum mana', 'area': 'spell area radius',
    'health_percent': 'maximum health', 'stationary_regen': 'mana regeneration while stationary',
    'retaliation_slow': 'attacker movement slow for 1s (3s trigger cooldown)',
    'damage_reduction': 'incoming damage reduction', 'slow_recovery': 'shorter movement slows on you',
    'healing': 'food and potion healing', 'cooldown': 'spell cooldown reduction',
    'mana_cost': 'spell mana-cost reduction', 'slow_duration': 'longer chill / gear slows (not freezes)',
    'speed': 'movement speed', 'trail_slow': 'ice-trail movement slow (1s trail; no spell-field bonus)',
    'crit_chance': 'critical-hit chance (percentage points)',
}
NEW_DEFINITIONS = (
    ('apprentice_rimeband', "Apprentice’s Rimeband", 'helm', 'damage', SMALL, 'Simple silver band with one pale-blue ice shard.'),
    ('deepwell_circlet', 'Deepwell Circlet', 'helm', 'mana', SMALL, 'Dark-blue circlet cradling a round, glowing mana gem.'),
    ('snowseer_hood', 'Snowseer Hood', 'helm', 'area', MODEST, 'Soft white hood with a widening snowflake halo.'),
    ('snowbound_robe', 'Snowbound Robe', 'chest', 'health_percent', RESOURCE, 'Padded blue robe with a snow-covered heart clasp.'),
    ('stillwater_vestment', 'Stillwater Vestment', 'chest', 'stationary_regen', RESOURCE, 'Deep teal robe bearing a still pool and rising blue mote.'),
    ('winterthorn_coat', 'Winterthorn Coat', 'chest', 'retaliation_slow', SMALL, 'Short fur-lined coat with icy thorns around the collar.'),
    ('stonefrost_leggings', 'Stonefrost Leggings', 'legs', 'damage_reduction', DEFENSE, 'Slate-gray leg guards with frosted stone knee plates.'),
    ('driftwalker_trousers', 'Driftwalker Trousers', 'legs', 'slow_recovery', ((1,59),(10,99),(20,149)), 'Light trousers with wind-swept snow curling around the cuffs.'),
    ('runestitched_leggings', 'Runestitched Leggings', 'legs', 'healing', RESOURCE, 'Indigo leggings stitched with small green restorative runes.'),
    ('quickrime_gloves', 'Quickrime Gloves', 'gloves', 'cooldown', DEFENSE, 'Slim icy gloves with a small hourglass rune.'),
    ('frugalweave_wraps', 'Frugalweave Wraps', 'gloves', 'mana_cost', MODEST, 'Blue cloth hand wraps protecting a single bright mana droplet.'),
    ('lingering_frost_grips', 'Lingering Frost Grips', 'gloves', 'slow_duration', RESOURCE, 'Long gloves with delicate frost tendrils trailing from the fingers.'),
    ('snowstep_boots', 'Snowstep Boots', 'boots', 'speed', SMALL, 'Light blue boots with white wing-like snow streaks.'),
    ('rimetrail_boots', 'Rimetrail Boots', 'boots', 'trail_slow', SMALL, 'Dark boots leaving a short trail of icy footprints.'),
    ('shardhunter_boots', 'Shardhunter Boots', 'boots', 'crit_chance', ((1,9),(2,14),(3,19)), 'Sharp-toed boots with a tiny crystal crosshair on each cuff.'),
)
DEFINITIONS = {}
for slot, effect, ranges, icon in (
    ('helm', 'damage', SMALL, 'Angular silver crown with a central rime crystal.'),
    ('chest', 'health_percent', RESOURCE, 'Heavy blue vestment with a broad white fur mantle.'),
    ('legs', 'damage_reduction', DEFENSE, 'Layered blue leggings patterned like overlapping glacier plates.'),
    ('gloves', 'cooldown', DEFENSE, 'Dark gloves with bright frost runes across the knuckles.'),
    ('boots', 'speed', SMALL, 'Sturdy snow boots with icy soles and thick white cuffs.'),
):
    key = 'standard:' + slot
    DEFINITIONS[key] = ItemDefinition(key, NAMES[slot], slot, effect, ranges, icon)
for key, name, slot, effect, ranges, icon in NEW_DEFINITIONS:
    DEFINITIONS[key] = ItemDefinition(key, name, slot, effect, ranges, icon)
for slot in SLOTS:
    key = 'frostweave:' + slot
    DEFINITIONS[key] = ItemDefinition(key, FROSTWEAVE_NAMES[slot], slot, '', (), {
        'helm': 'Tall translucent ice-crystal crown with a luminous blue core.',
        'chest': 'Elegant white-and-cyan mage robe woven with branching frost crystals.',
        'legs': 'Pale crystal armor plates over a dark blue woven underlayer.',
        'gloves': 'Crystalline blue gauntlets with sparkling ice fingertips.',
        'boots': 'Polished crystal boots with faceted toes and glowing frost seams.',
    }[slot], 'frostweave')
TRAIL_LIFE = 1.0
TRAIL_SPACING = .3
TRAIL_RADIUS = .38
THORN_DURATION = 1.0
THORN_COOLDOWN = 3.0
PLAYER_SLOW_PULSE = .3


def roll_value(definition, rank, quality):
    if not definition.ranges or not 1 <= rank <= definition.max_rank:
        return 0
    low, high = definition.ranges[rank - 1]
    return (low + round((high - low) * quality / 10000)) / 1000


def stock_price(slot, frostweave=False):
    return BLANK_COST[slot] + sum(ENCHANT_COST[r] for r in range(1, 4 if frostweave else 2))


@dataclass(frozen=True, slots=True)
class Item:
    uid: int
    slot: str
    rank: int
    source: str = "drop"
    set_id: str | None = None
    template_id: str | None = None
    quality: int | None = None

    def __post_init__(self):
        if self.slot not in SLOTS or type(self.rank) is not int or not 0 <= self.rank <= 5:
            raise ValueError("Invalid equipment slot or rank")
        if type(self.uid) is not int or self.uid < 1:
            raise ValueError("Invalid item identifier")
        if self.source not in ("drop", "shop", "reward", "enchanted"):
            raise ValueError("Invalid item origin")
        if self.set_id not in (None, "frostweave"):
            raise ValueError("Invalid equipment set")
        if self.template_id is not None:
            definition = DEFINITIONS.get(self.template_id)
            if definition is None or definition.slot != self.slot or definition.set_id != self.set_id:
                raise ValueError("Item template does not match slot/set")
            if not (3 if self.set_id else 1) <= self.rank <= definition.max_rank:
                raise ValueError("Unsupported template rank")
            if not self.set_id and (type(self.quality) is not int or not 0 <= self.quality <= 10000):
                raise ValueError("Invalid enchantment quality")
            if self.set_id and self.quality is not None:
                raise ValueError("Frostweave has fixed stats")
        elif self.quality is not None:
            raise ValueError("Roll without template")
        if self.source == "shop" and self.set_id is None and self.template_id is None:
            object.__setattr__(self, "set_id", "frostweave")

    @property
    def name(self):
        return DEFINITIONS[self.template_id].name if self.template_id else FROSTWEAVE_NAMES[self.slot] if self.set_id == "frostweave" else NAMES[self.slot]

    @property
    def catalog_id(self):
        return self.template_id or f"{self.set_id or 'standard'}:{self.slot}"

    @property
    def max_rank(self):
        return 5 if self.set_id else 3

    @property
    def enchantment_slots(self):
        return 1 if self.rank >= 1 and self.set_id is None else 0

    @property
    def enchantment_value(self):
        return roll_value(DEFINITIONS[self.template_id], self.rank, self.quality) if self.template_id and self.set_id is None else 0

    @property
    def lines(self):
        rank = self.rank
        if self.template_id and not self.set_id:
            definition = DEFINITIONS[self.template_id]
            import textwrap
            return ['Enchantment slot 1/1 (rolled)'] + textwrap.wrap(f"+{self.enchantment_value * 100:.1f}% {EFFECT_LABELS[definition.effect]}", width=43)
        if rank == 0:
            return ["No bonus yet. Ready for enchantment."]
        if self.slot == "helm":
            return [f"+{VALUES['damage'][rank]:.0%} spell damage"]
        if self.slot == "chest":
            return [f"+{VALUES['health'][rank]} maximum health"]
        if self.slot == "legs":
            return [f"+{VALUES['armor'][rank]} armor (damage reduced per hit)"]
        if self.slot == "gloves":
            return [f"{VALUES['cooldown'][rank]:.0%} shorter spell cooldowns"]
        return [f"+{VALUES['speed'][rank]:.0%} movement speed",
                f"+{VALUES['crit_chance'][rank]:.0%} critical-hit chance",
                f"+{VALUES['crit_damage'][rank]:.2f}× critical damage"]

    @property
    def next_cost(self):
        return ENCHANT_COST.get(self.rank + 1) if self.rank < self.max_rank else None

    @property
    def sell_value(self):
        investment = BLANK_COST[self.slot] + sum(ENCHANT_COST[rank] for rank in range(1, self.rank + 1))
        return investment // 4


@dataclass(frozen=True, slots=True)
class GearStats:
    damage: float = 0
    health: int = 0
    armor: int = 0
    cooldown: float = 0
    speed: float = 0
    crit_chance: float = 0
    crit_damage: float = 0
    health_percent: float = 0
    mana: float = 0
    area: float = 0
    stationary_regen: float = 0
    retaliation_slow: float = 0
    damage_reduction: float = 0
    slow_recovery: float = 0
    healing: float = 0
    mana_cost: float = 0
    slow_duration: float = 0
    trail_slow: float = 0
    frostweave_pieces: int = 0
    frostweave_rank: int = 0
    frostweave_freeze_chance: float = 0


class Inventory:
    def __init__(self):
        self.items = []
        self.catalog_seen = []
        self.equipped = dict.fromkeys(SLOTS)
        self.next_uid = 1
        self.revision = 0
        self._stats_revision = -1
        self._stats = GearStats()

    def create(self, slot, rank, source="drop"):
        """Legacy authoring/practice factory; live acquisition uses create_template.

        Unversioned old items retain their fixed stats, including old high ranks.
        They cannot be enchanted beyond their current family's cap.
        """
        item = Item(self.next_uid, slot, rank, source)
        self.next_uid += 1
        return item

    def create_template(self, template_id, rank, rng, source="drop"):
        definition = DEFINITIONS[template_id]
        item = Item(self.next_uid, definition.slot, rank, source, definition.set_id,
                    template_id, None if definition.set_id else rng.randint(0, 10000))
        self.next_uid += 1
        return item

    def get(self, uid):
        return next((item for item in self.items if item.uid == uid), None)

    def worn(self, slot):
        return self.get(self.equipped[slot])

    @property
    def backpack(self):
        worn = set(self.equipped.values())
        return [item for item in self.items if item.uid not in worn]

    def is_upgrade(self, item):
        """Only compare matching templates; different effects are customization choices."""
        current = self.worn(item.slot)
        if current is not None and current.uid == item.uid:
            return False
        if current and item.catalog_id != current.catalog_id:
            return False  # Different effects are choices, not automatic upgrades.
        if current and item.template_id and not item.set_id:
            if current.template_id is None:
                return False  # Legacy fixed packages are not comparable to a single new roll.
            return item.enchantment_value > current.enchantment_value
        return item.rank > (current.rank if current is not None else 0)

    @property
    def prioritized_backpack(self):
        def priority(item):
            upgrade = self.is_upgrade(item)
            return not upgrade, -item.rank if upgrade else 0, item.uid
        return sorted(self.backpack, key=priority)

    def add(self, item, auto_equip=True):
        if self.get(item.uid) is not None:
            raise ValueError("Item is already owned")
        key = item.catalog_id
        if key not in self.catalog_seen:
            self.catalog_seen.append(key)
        self.items.append(item)
        self.next_uid = max(self.next_uid, item.uid + 1)
        if auto_equip and self.equipped[item.slot] is None:
            self.equipped[item.slot] = item.uid
        self.revision += 1

    def equip(self, uid):
        item = self.get(uid)
        if item is None:
            return False
        self.equipped[item.slot] = uid
        self.revision += 1
        return True

    def unequip(self, slot):
        if self.equipped.get(slot) is None:
            return False
        self.equipped[slot] = None
        self.revision += 1
        return True

    def upgrade(self, uid):
        item = self.get(uid)
        if item is None or item.rank >= item.max_rank:
            return False
        index = self.items.index(item)
        self.items[index] = replace(item, rank=item.rank + 1, source="enchanted")
        self.revision += 1
        return True

    def remove(self, uid):
        item = self.get(uid)
        if item is None or uid in self.equipped.values():
            return None
        self.items.remove(item)
        self.revision += 1
        return item

    @property
    def stats(self):
        if self._stats_revision != self.revision:
            equipped = [self.worn(slot) for slot in SLOTS]
            ranks = {slot: item.rank if item and (item.template_id is None or item.set_id) else 0 for slot, item in zip(SLOTS, equipped)}
            frostweave = [item for item in equipped if item and item.set_id == "frostweave"]
            set_rank = min(item.rank for item in frostweave) if len(frostweave) == 5 else 0
            self._stats = GearStats(
                damage=VALUES["damage"][ranks["helm"]], health=VALUES["health"][ranks["chest"]],
                armor=VALUES["armor"][ranks["legs"]], cooldown=VALUES["cooldown"][ranks["gloves"]],
                speed=VALUES["speed"][ranks["boots"]], crit_chance=VALUES["crit_chance"][ranks["boots"]],
                crit_damage=VALUES["crit_damage"][ranks["boots"]],
                frostweave_pieces=len(frostweave), frostweave_rank=set_rank,
                frostweave_freeze_chance=FROSTWEAVE_CHANCE.get(set_rank, 0),
            )
            additions = {}
            for item in equipped:
                if item and item.template_id and not item.set_id:
                    effect = DEFINITIONS[item.template_id].effect
                    additions[effect] = additions.get(effect, 0) + item.enchantment_value
            self._stats = replace(self._stats, **{key: getattr(self._stats, key) + value for key, value in additions.items()})
            self._stats_revision = self.revision
        return self._stats

    def to_dict(self):
        return {"catalog_seen": self.catalog_seen.copy(), "items": [{"uid": i.uid, "slot": i.slot, "rank": i.rank, "source": i.source,
                           "set_id": i.set_id, "template_id": i.template_id, "quality": i.quality} for i in self.items],
                "equipped": dict(self.equipped), "next_uid": self.next_uid}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError("Invalid inventory")
        inv = cls()
        seen = data.get("catalog_seen", [])
        if not isinstance(seen, list) or any(not isinstance(key, str) for key in seen):
            raise ValueError("Invalid catalog history")
        inv.catalog_seen = list(dict.fromkeys(seen))
        for raw in data["items"]:
            if not isinstance(raw, dict):
                raise ValueError("Invalid item")
            inv.add(Item(raw["uid"], raw["slot"], raw["rank"], raw.get("source", "drop"),
                         raw.get("set_id"), raw.get("template_id"), raw.get("quality")), auto_equip=False)
        equipped = data.get("equipped", {})
        if not isinstance(equipped, dict) or set(equipped) - set(SLOTS):
            raise ValueError("Invalid equipment")
        for slot in SLOTS:
            uid = equipped.get(slot)
            if uid is not None:
                item = inv.get(uid)
                if type(uid) is not int or item is None or item.slot != slot:
                    raise ValueError("Equipment does not match its slot")
            inv.equipped[slot] = uid
        next_uid = data.get("next_uid", inv.next_uid)
        if type(next_uid) is not int or next_uid < inv.next_uid:
            raise ValueError("Invalid next item identifier")
        inv.next_uid = next_uid
        inv.revision += 1
        return inv
