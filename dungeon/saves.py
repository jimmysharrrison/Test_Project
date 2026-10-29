"""Four atomic save slots, with an allowlisted JSON snapshot of live combat."""

from collections import deque
from dataclasses import fields, is_dataclass
from datetime import datetime, timezone
import json
from math import isfinite
from random import Random

from .profile import ProfileStore

SLOT_COUNT = 4
MAX_SAVE_BYTES = 32 * 1024 * 1024
DERIVED_WORLD = {"telemetry", "level_data", "layout", "walls"}


def snapshot_types():
    from .world import World, Player, Enemy, Spawner, IcePatch, RimeTrail, Projectile, Pickup, Effect
    from .geometry import Vec
    from .items import Item
    from .keeper import KeeperFight, KeeperTuning, Mechanic
    from .encounters import Hazard
    from .void import VoidFloor, GroundZone
    from .void_depths import VoidDepths, VoidMechanic
    from .temporal import TemporalFloor, TemporalEcho, TemporalField, TemporalPortal
    from .maw import MawFloor, VoidArrival
    return {cls.__name__: cls for cls in (World, Player, Enemy, Spawner, IcePatch, RimeTrail,
            Projectile, Pickup, Effect, Vec, Item, KeeperFight, KeeperTuning, Mechanic, Hazard,
            VoidFloor, GroundZone, VoidDepths, VoidMechanic,
            TemporalFloor, TemporalEcho, TemporalField, TemporalPortal, MawFloor, VoidArrival)}


def encode_world(world):
    """Preserve shared actor/patch references and RNG state without executable data."""
    from .items import Inventory
    from .timing import Timing
    from .achievements import AchievementRun
    from .world import World
    types = snapshot_types()
    seen = {}
    retained = []  # Keep temporary RNG tuples alive so object IDs cannot be reused.

    def encode(value):
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            if not isfinite(value):
                raise ValueError("Non-finite snapshot value")
            return value
        identity = id(value)
        if identity in seen:
            return {"ref": seen[identity]}
        node = {"id": len(seen)}
        seen[identity] = node["id"]
        retained.append(value)
        if isinstance(value, Inventory):
            node.update(type="Inventory", data=value.to_dict())
        elif isinstance(value, (Timing, AchievementRun)):
            node.update(type=type(value).__name__, data=value.to_dict())
        elif isinstance(value, Random):
            node.update(type="Random", data=encode(value.getstate()))
        elif type(value) in (list, tuple, set, frozenset, deque):
            node.update(type=type(value).__name__, data=[encode(v) for v in value])
        elif type(value) is dict:
            node.update(type="dict", data=[[encode(k), encode(v)] for k, v in value.items()])
        elif types.get(type(value).__name__) is type(value):
            names = [f.name for f in fields(value)] if is_dataclass(value) else list(vars(value))
            if isinstance(value, World):
                names = [name for name in names if name not in DERIVED_WORLD]
            node.update(type=type(value).__name__, data={name: encode(getattr(value, name)) for name in names})
        else:
            raise ValueError(f"Unsupported save value: {type(value).__name__}")
        return node

    return {"version": 1, "world": encode(world)}


def decode_world(snapshot):
    from .items import Inventory, Item
    from .timing import Timing
    from .achievements import AchievementRun
    from .world import World, Player
    from .levels import PLAYABLE_FLOORS, level_for_depth
    from .geometry import Vec
    if not isinstance(snapshot, dict) or snapshot.get("version") != 1:
        raise ValueError("Unsupported game state")
    types = snapshot_types()
    seen = {}

    def decode(node):
        if node is None or type(node) in (str, bool, int):
            return node
        if type(node) is float and isfinite(node):
            return node
        if not isinstance(node, dict):
            raise ValueError("Invalid game state value")
        if set(node) == {"ref"}:
            return seen[node["ref"]]
        if set(node) != {"id", "type", "data"} or type(node["id"]) is not int or node["id"] != len(seen) or len(seen) > 50000:
            raise ValueError("Invalid game state reference")
        key, kind, data = node["id"], node["type"], node["data"]
        if kind == "Inventory":
            value = Inventory.from_dict(data)
        elif kind == "Timing":
            value = Timing.from_dict(data)
        elif kind == "AchievementRun":
            value = AchievementRun.from_dict(data, data["floor"])
        elif kind == "Random":
            value = Random()
        elif kind in ("list", "tuple", "set", "frozenset", "deque"):
            value = []
        elif kind == "dict":
            value = {}
        elif kind in types:
            value = types[kind].__new__(types[kind])
            if not isinstance(data, dict):
                raise ValueError("Invalid saved object")
            if is_dataclass(value):
                expected = {f.name for f in fields(value)}
                legacy_player = (kind == "Player" and set(data) <= expected
                                 and expected - set(data) <= {"visual_facing", "walk_distance", "walking"})
                if set(data) != expected and not legacy_player:
                    raise ValueError("Invalid saved fields")
        else:
            raise ValueError("Unknown saved object type")
        seen[key] = value
        if kind == "Random":
            value.setstate(decode(data))
        elif kind in ("list", "tuple", "set", "frozenset", "deque"):
            value.extend(decode(v) for v in data)
            if kind != "list":
                value = {"tuple": tuple, "set": set, "frozenset": frozenset, "deque": deque}[kind](value)
                seen[key] = value
        elif kind == "dict":
            for k, v in data:
                decoded_key = decode(k)
                value[decoded_key] = decode(v)
        elif kind in types:
            if any(not isinstance(name, str) or name.startswith("__") for name in data):
                raise ValueError("Invalid saved attribute")
            for name, v in data.items():
                object.__setattr__(value, name, decode(v))
            if kind == "Player" and "visual_facing" not in data:
                value.visual_facing = value.facing
            if kind == "Player":
                if "walk_distance" not in data:
                    value.walk_distance = 0.0
                if "walking" not in data:
                    value.walking = False
            if isinstance(value, Item):
                value.__post_init__()
        return value

    world = decode(snapshot["world"])
    if not isinstance(world, World) or not isinstance(world.player, Player):
        raise ValueError("Invalid saved world/player")
    if type(world.level) is not int or not 1 <= world.level <= PLAYABLE_FLOORS:
        raise ValueError("Invalid saved floor")
    template = World(world.seed, level=world.level)
    # Snapshots from the five-floor build predate the void encounter field.
    if not hasattr(world, "void") and world.level <= 5:
        world.void = None
    if set(vars(world)) != set(vars(template)) - DERIVED_WORLD:
        raise ValueError("Incomplete saved world")
    if (not isinstance(world.player.pos, Vec) or not isinstance(world.player.inventory, Inventory)
            or world.player.current_level != world.level or world.state not in ("playing", "dead", "cleared", "won")
            or type(world.phase) is not int or not 1 <= world.phase <= 3):
        raise ValueError("Invalid saved simulation")
    for name in ("hp", "mana", "gold", "potions", "kills"):
        v = getattr(world.player, name)
        if type(v) not in (int, float) or not isfinite(v) or v < 0:
            raise ValueError("Invalid saved resources")
    for name, kind in (("enemies", "Enemy"), ("spawners", "Spawner"), ("projectiles", "Projectile"),
                       ("pickups", "Pickup"), ("hazards", "Hazard"), ("ice_patches", "IcePatch"),
                       ("rime_trails", "RimeTrail"), ("effects", "Effect")):
        values = getattr(world, name)
        if not isinstance(values, list) or any(not isinstance(v, types[kind]) or not isinstance(v.pos, Vec) for v in values):
            raise ValueError("Invalid saved actors")
    if world.keeper is not None and (not isinstance(world.keeper, types["KeeperFight"]) or world.keeper.world is not world):
        raise ValueError("Invalid saved encounter")
    if world.void is not None and (not isinstance(world.void, types["VoidFloor"]) or world.void.world is not world
            or not isinstance(world.void.zones, list)
            or any(not isinstance(z, types["GroundZone"]) or not isinstance(z.pos, Vec) for z in world.void.zones)):
        raise ValueError("Invalid saved void encounter")
    if world.level in (6, 7, 8, 9, 10) and world.void is None:
        raise ValueError("Missing void encounter")
    if world.level in (7, 8) and (not isinstance(world.void, types["VoidDepths"])
            or not isinstance(world.void.mechanics, list)
            or any(not isinstance(m, types["VoidMechanic"]) or not isinstance(m.pos, Vec)
                   for m in world.void.mechanics)):
        raise ValueError("Invalid saved deep void encounter")
    if world.level in (9, 10):
        if not isinstance(world.void, types["TemporalFloor"]):
            raise ValueError("Invalid saved temporal encounter")
        for name, kind in (("fields", "TemporalField"), ("echoes", "TemporalEcho"), ("portals", "TemporalPortal")):
            values = getattr(world.void, name)
            if not isinstance(values, list) or any(not isinstance(v, types[kind]) or not isinstance(v.pos, Vec) for v in values):
                raise ValueError("Invalid saved temporal mechanics")
    if world.level == 10:
        if (not isinstance(world.void, types["MawFloor"]) or not isinstance(world.void.arrivals, list)
                or any(not isinstance(a, types["VoidArrival"]) or not isinstance(a.pos, Vec)
                       for a in world.void.arrivals)):
            raise ValueError("Invalid saved final void encounter")
    if world.state == "won" and world.level < PLAYABLE_FLOORS:
        world.state = "cleared"
    world.telemetry = None
    world.level_data = level_for_depth(world.level)
    world.layout = world.level_data.layout
    world.walls = {(x, y) for y, row in enumerate(world.layout) for x, tile in enumerate(row) if tile == "#"}
    return world


class SaveSlots:
    def __init__(self, path=None):
        first = ProfileStore(path)
        self.stores = [first] + [ProfileStore(first.path.with_name(f"{first.path.stem}-slot-{i}{first.path.suffix}")) for i in range(2, SLOT_COUNT + 1)]
        self.error = ""

    def store(self, slot):
        if type(slot) is not int or not 1 <= slot <= SLOT_COUNT:
            raise ValueError("Choose a slot from 1 to 4")
        return self.stores[slot - 1]

    def summaries(self):
        rows = []
        for slot, store in enumerate(self.stores, 1):
            row = {"slot": slot, "occupied": store.path.exists(), "valid": False, "label": "Empty", "detail": ""}
            if row["occupied"]:
                try:
                    data = self.read(store)
                    player = ProfileStore(store.path).load()
                    if player is None:
                        raise ValueError("Invalid save")
                    if "game_state" in data:
                        decode_world(data["game_state"])
                    stamp = datetime.fromtimestamp(store.path.stat().st_mtime, timezone.utc).astimezone()
                    row.update(valid=True, label=f"Floor {player.current_level} / {player.gold:,} gold",
                               detail=stamp.strftime("%b %d, %Y  %I:%M %p") + (" / Legacy save" if "game_state" not in data else ""))
                except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, OverflowError):
                    row.update(label="Unreadable save", detail="Choose another slot, or explicitly overwrite this one.")
            rows.append(row)
        return rows

    @staticmethod
    def read(store):
        if store.path.stat().st_size > MAX_SAVE_BYTES:
            raise ValueError("Save too large")
        data = json.loads(store.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid save")
        return data

    def load(self, slot, *, seed=None, presentation=None):
        from .world import World
        store = self.store(slot)
        try:
            data = self.read(store)
            player = ProfileStore(store.path).load()
            if player is None:
                raise ValueError("Invalid saved player")
            world = decode_world(data["game_state"]) if "game_state" in data else World(seed, player=player, level=player.current_level, **(presentation or {}))
            store.writable = True
            self.error = ""
            return world
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, OverflowError):
            self.error = f"Slot {slot} could not be loaded. Its file has been preserved."
            return None

    def save(self, slot, world, *, overwrite=False):
        store = self.store(slot)
        if store.path.exists() and not overwrite:
            self.error = f"Confirm before overwriting Slot {slot}."
            return False
        # A new store permits an explicitly confirmed replacement of a corrupt save.
        writer = ProfileStore(store.path)
        try:
            from .codex import observe_items
            observe_items(world.player)
            snapshot = encode_world(world)
            if len(json.dumps(snapshot)) > MAX_SAVE_BYTES - 1024 * 1024:
                raise ValueError("Save too large")
            if not writer.save(world.player, snapshot=snapshot):
                self.error = writer.error
                return False
            self.stores[slot - 1] = writer
            self.error = ""
            return True
        except (ValueError, TypeError, RecursionError):
            self.error = f"Slot {slot} could not be saved. Its previous file has been preserved."
            return False
