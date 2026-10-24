"""Ranked Ice Mage equipment, ownership, and the initial economy."""

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
class Item:
    uid: int
    slot: str
    rank: int
    source: str = "drop"
    set_id: str | None = None

    def __post_init__(self):
        if self.slot not in SLOTS or type(self.rank) is not int or not 0 <= self.rank <= 5:
            raise ValueError("Invalid equipment slot or rank")
        if type(self.uid) is not int or self.uid < 1:
            raise ValueError("Invalid item identifier")
        if self.source not in ("drop", "shop", "reward", "enchanted"):
            raise ValueError("Invalid item origin")
        if self.set_id not in (None, "frostweave"):
            raise ValueError("Invalid equipment set")
        if self.source == "shop" and self.set_id is None:
            object.__setattr__(self, "set_id", "frostweave")

    @property
    def name(self):
        return FROSTWEAVE_NAMES[self.slot] if self.set_id == "frostweave" else NAMES[self.slot]

    @property
    def lines(self):
        rank = self.rank
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
        return ENCHANT_COST.get(self.rank + 1)

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
    frostweave_pieces: int = 0
    frostweave_rank: int = 0
    frostweave_freeze_chance: float = 0


class Inventory:
    def __init__(self):
        self.items = []
        self.equipped = dict.fromkeys(SLOTS)
        self.next_uid = 1
        self.revision = 0
        self._stats_revision = -1
        self._stats = GearStats()

    def create(self, slot, rank, source="drop"):
        item = Item(self.next_uid, slot, rank, source)
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
        """Every slot's fixed bonuses increase with rank; compare like slots."""
        current = self.worn(item.slot)
        if current is not None and current.uid == item.uid:
            return False
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
        if item is None or item.rank >= 5:
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
            ranks = {slot: item.rank if item else 0 for slot, item in zip(SLOTS, equipped)}
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
            self._stats_revision = self.revision
        return self._stats

    def to_dict(self):
        return {"items": [{"uid": i.uid, "slot": i.slot, "rank": i.rank, "source": i.source,
                           "set_id": i.set_id} for i in self.items],
                "equipped": dict(self.equipped), "next_uid": self.next_uid}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError("Invalid inventory")
        inv = cls()
        for raw in data["items"]:
            if not isinstance(raw, dict):
                raise ValueError("Invalid item")
            inv.add(Item(raw["uid"], raw["slot"], raw["rank"], raw.get("source", "drop"),
                         raw.get("set_id")), auto_equip=False)
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
