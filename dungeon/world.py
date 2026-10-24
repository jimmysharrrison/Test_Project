"""Display-independent combat, navigation, phases, and status simulation for Frost Mage."""

from collections import deque
from dataclasses import dataclass, field
from math import ceil, floor
from random import Random

from .abilities import (ABILITIES, ICE_PATCH_RADIUS, ICE_PATCH_MOVE_FACTOR,
                        ICE_PATCH_ATTACK_FACTOR, ICE_PATCH_FROST_BONUS)
from .encounters import BOSSES, signature, update_hazards
from .creatures import KINDS, interrupt, update_creature
from .keeper import KeeperFight, TUNING
from .geometry import Vec
from .items import BLANK_COST, FROSTWEAVE_FREEZE, Inventory, Item, SLOTS
from .levels import FROSTFALL, PHASE_DELAY, PHASE_SPEEDS, PLAYABLE_FLOORS, level_for_depth
from .navigation import find_path, flood, neighbors

LAYOUT = FROSTFALL.layout
ENEMY_STATS = {
    "husk": ("Molten Skeleton", 44, 1.05, 10),
    "skitter": ("Ember Skitter", 26, 1.65, 6),
    "tree": ("Darkroot Treant", 44, 1.05, 10),
    "spider": ("Thornwood Spider", 26, 1.65, 6),
    "archer": ("Briarbone Archer", 34, 1.15, 8),
    "armor": ("Bewitched Armor", 58, .90, 12),
    "grimoire": ("Runaway Grimoire", 30, 1.45, 7),
    "fairy": ("Potion-Maddened Fairy", 28, 1.60, 7),
    "crystal": ("Crystalback Beast", 66, .85, 18),
    "predator": ("Runeclaw Prowler", 32, 1.5, 11),
    "arcane": ("Arcane Drifter", 38, 1.0, 12),
    "keeper": ("The Keeper", TUNING.health, 0, 0),
}
ARCHER_RANGE = 7.5
ARCHER_WINDUP = .65
ARCHER_COOLDOWN = 2.8


@dataclass(slots=True)
class Player:
    pos: Vec = field(default_factory=lambda: Vec(3.5, 13.5))
    hp: int = 100
    mana: float = 100
    potions: int = 3
    gold: int = 0
    kills: int = 0
    facing: Vec = field(default_factory=lambda: Vec(1, -1).unit())
    cooldowns: dict = field(default_factory=lambda: dict.fromkeys(ABILITIES, 0.0))
    cast_time: float = 0
    stasis: float = 0
    stasis_frost_multiplier: float = 1
    stasis_cast_id: int = 0
    invincible: float = 0
    flash: float = 0
    inventory: Inventory = field(default_factory=Inventory)
    first_clear_rewarded: bool = False
    unlocked_level: int = 1
    current_level: int = 1
    cleared_floor: int = 0
    lower_tower_completed: bool = False

    @property
    def max_hp(self):
        return 100 + self.inventory.stats.health

    @property
    def move_speed(self):
        return 3.1 * (1 + self.inventory.stats.speed)

    @property
    def crit_chance(self):
        return .05 + self.inventory.stats.crit_chance

    @property
    def crit_multiplier(self):
        return 2 + self.inventory.stats.crit_damage

    def cooldown_for(self, key):
        return ABILITIES[key].cooldown * (1 - self.inventory.stats.cooldown)


@dataclass(slots=True, eq=False)
class Enemy:
    pos: Vec
    kind: str = "husk"
    hp: int = 44
    cooldown: float = 0
    flash: float = 0
    phase: float = 0
    chilled: float = 0
    frozen: float = 0
    level: int = 1
    windup: float = 0
    shot_target: Vec | None = None
    spawn_phase: int = 1

    boss_role: str = ""
    boss_name: str = ""
    signature_timer: float = 3
    recovery: float = 0
    action: str = ""
    action_time: float = 0
    attack_direction: Vec = Vec()
    attack_origin: Vec = Vec()
    frost_resistance: float = 0
    summoned: bool = False
    summon_life: float = 0
    patch_time: float = 0
    telemetry_id: int = 0

    @property
    def max_hp(self):
        if self.kind == "keeper":
            return TUNING.health
        base = 380 if self.boss_role == "boss" else 85 if self.boss_role else ENEMY_STATS[self.kind][1]
        return round(base * (1 + .15 * (self.level - 1)))

    @property
    def name(self):
        return self.boss_name or ENEMY_STATS[self.kind][0]

    @property
    def move_speed(self):
        return ENEMY_STATS[self.kind][2] * PHASE_SPEEDS[self.spawn_phase - 1] * (ICE_PATCH_MOVE_FACTOR if self.patch_time > 0 else 1)

    @property
    def attack_rate(self):
        return ICE_PATCH_ATTACK_FACTOR if self.patch_time > 0 else 1

    @property
    def statuses(self):
        return [(name, time) for name, time in (("Frozen", self.frozen), ("Chilled", self.chilled), ("Frost resistance", self.frost_resistance), ("Ice Patch", self.patch_time)) if time > 0]


@dataclass(slots=True, eq=False)
class Spawner:
    pos: Vec
    hp: int = 176
    timer: float = 6
    flash: float = 0
    level: int = 1
    forest: bool = False
    alchemist: bool = False
    menagerie: bool = False
    spawn_phase: int = 1
    telemetry_id: int = 0

    @property
    def max_hp(self):
        return round(176 * (1 + .15 * (self.level - 1)))

    @property
    def name(self):
        return "Containment Device" if self.menagerie else "Unstable Alembic" if self.alchemist else "Blighted Heart" if self.forest else "Molten Rift"

    @property
    def statuses(self):
        return []


@dataclass(slots=True)
class IcePatch:
    pos: Vec
    radius: float = ICE_PATCH_RADIUS
    life: float = 6

    def contains(self, pos):
        return self.life > 0 and (pos - self.pos).length() <= self.radius


@dataclass(slots=True)
class Projectile:
    pos: Vec
    velocity: Vec
    life: float = 1.05
    damage: int = 24
    hostile: bool = False
    spell: str = "q"
    frost_multiplier: float = 1
    cast_id: int = 0
    source: str = "unknown"


@dataclass(slots=True)
class Pickup:
    pos: Vec
    kind: str = "gold"
    value: int = 10
    item: Item | None = None


@dataclass(slots=True)
class Effect:
    pos: Vec
    kind: str
    life: float = 0.4
    duration: float = 0.4
    text: str = ""
    radius: float = 0


class World:
    def __init__(self, seed=None, player=None, level=1):
        self.seed = seed
        self.telemetry = None
        self.telemetry_reason = "continue"
        self._next_actor_id = 1
        self._cast_sequence = 0
        self.rng = Random(seed)
        self.combat_rng = Random(seed)
        self.proc_rng = Random(None if seed is None else seed + 8727)
        self.loot_rng = Random(None if seed is None else seed + 1937)
        self.player = player if player is not None else Player()
        self.level_data = level_for_depth(level)
        self.level = level
        self.player.current_level = level
        self.player.unlocked_level = max(self.player.unlocked_level, level)
        self.layout = self.level_data.layout
        self.level_completed = False
        self.hazards = []
        self.boss_started = False
        self.phase = 1
        self.intermission = 0.0
        self.spawners_defeated = 0
        self._phase_resolved = False
        self.walls = {(x, y) for y, row in enumerate(self.layout) for x, tile in enumerate(row) if tile == "#"}
        self.ice_patches = []
        self.spawners = []
        self.enemies = [Enemy(Vec(x, y), kind, cooldown=1 + i * .25 if kind in ("archer", "fairy") else 0)
                        for i, (x, y, kind) in enumerate(self.level_data.enemies)]
        self.pickups = [Pickup(Vec(x, y), kind, value) for x, y, kind, value in self.level_data.pickups]
        for actor in self.enemies + self.spawners:
            actor.level = level
            actor.hp = actor.max_hp
        for pickup in self.pickups:
            if pickup.kind == "gold":
                pickup.value = self.gold_value(pickup.value)
        self.projectiles = []
        self.effects = []
        self.events = []
        self.exit = Vec(8.5, 1.5)
        self.state = "playing"
        self.time = 0.0
        self.message = self.level_data.phase_lines[0]
        self.message_time = 7.0
        self.selected = None
        self.path = []
        self.destination = None
        self._path_tile = None
        self._distances = {}
        self.keeper = KeeperFight(self) if self.level_data.keeper else None
        if not self.keeper:
            self._activate_phase(1, initial=True)

    @staticmethod
    def _point(pos):
        return [round(pos.x, 3), round(pos.y, 3)]

    def _actor_info(self, actor):
        if not actor.telemetry_id:
            actor.telemetry_id = self._next_actor_id
            self._next_actor_id += 1
        return {"id": actor.telemetry_id, "kind": "spawner" if isinstance(actor, Spawner) else actor.kind,
                "name": actor.name, "role": getattr(actor, "boss_role", ""),
                "summoned": getattr(actor, "summoned", False), "spawn_phase": actor.spawn_phase,
                "position": self._point(actor.pos), "hp": actor.hp, "max_hp": actor.max_hp}

    def _record(self, event, **data):
        if self.telemetry:
            self.telemetry.event(self, event, **data)

    def make_enemy(self, pos, kind, **kwargs):
        enemy = Enemy(pos, kind, level=self.level, **kwargs)
        enemy.hp = enemy.max_hp
        self.enemies.append(enemy)
        self._record("enemy_spawn", target=self._actor_info(enemy))
        return enemy

    def enemy_bolt(self, enemy, direction, speed, spell, life):
        damage = round(ENEMY_STATS[enemy.kind][3] * (1 + .12 * (enemy.level - 1)))
        self._record("enemy_attack", source=enemy.kind, attack=spell, stage="release")
        self.projectiles.append(Projectile(enemy.pos + direction * .4, direction * speed,
                                           life=life, damage=damage, hostile=True, spell=spell, source=enemy.kind))

    def _freeze(self, enemy, duration):
        if enemy.kind == "keeper":
            if enemy.frost_resistance > 0:
                self._record("freeze_resisted", target=self._actor_info(enemy))
                return False
            duration = min(duration, TUNING.freeze_cap)
            enemy.frost_resistance = TUNING.frost_resistance
            self.effects.append(Effect(enemy.pos, "freeze", .7, .7, "BRIEF FREEZE / RESISTANCE"))
        enemy.frozen = max(enemy.frozen, duration)
        self._record("freeze_applied", target=self._actor_info(enemy), duration=duration)
        return True

    def gold_value(self, base):
        return round(base * (1 + .15 * (self.level - 1)))

    @property
    def blocked(self):
        return self.walls

    @property
    def exit_open(self):
        return self.level_completed

    @property
    def phase_spawner_count(self):
        return self.level_data.phase_counts[self.phase - 1]

    def _activate_phase(self, phase, initial=False):
        if phase == 3 and not self.level_data.menagerie:
            return self._activate_boss()
        reached = flood((floor(self.player.pos.x), floor(self.player.pos.y)), self.blocked)
        reserved = []
        for x, y in self.level_data.phase_spawners[phase - 1]:
            preferred = Vec(x, y)
            candidates = sorted((Vec(cx + .5, cy + .5) for cx, cy in reached),
                                key=lambda point: ((point - preferred).length(), point.x, point.y))
            position = next((point for point in candidates if self.walkable(point, .55)
                             and (point - self.player.pos).length() >= 1
                             and all((point - enemy.pos).length() >= .8 for enemy in self.enemies)
                             and all((point - other).length() >= 1.25 for other in reserved)), None)
            if position is None:
                # Defer an occupied phase; never materialize inside an actor.
                return False
            reserved.append(position)
        self.phase, self.intermission, self._phase_resolved = phase, 0.0, False
        self.spawners = [Spawner(pos, timer=(5 + i * 3) if initial else (2 + i), level=self.level,
                                 forest=self.level_data.forest, alchemist=self.level_data.alchemist, menagerie=self.level_data.menagerie,
                                 spawn_phase=phase) for i, pos in enumerate(reserved)]
        for spawner in self.spawners:
            spawner.hp = spawner.max_hp
            if not initial:
                self.effects.append(Effect(spawner.pos, "spawn", .8, .8))
        if not initial:
            self._record("phase_start", spawner_count=len(self.spawners))
            self.announce(f"Phase {phase}/3: {self.level_data.phase_lines[phase - 1]}")
            self.events.append("phase")
        return True

    def _activate_boss(self):
        name, kind, move = BOSSES[self.level]
        reached = flood((floor(self.player.pos.x), floor(self.player.pos.y)), self.blocked)
        positions = sorted((Vec(x + .5, y + .5) for x, y in reached),
                           key=lambda p: ((p - Vec(8.5, 5.5)).length(), p.x, p.y))
        chosen = []
        for point in positions:
            if (self.walkable(point, .55) and (point - self.player.pos).length() >= 3
                    and all((point - e.pos).length() >= 1 for e in self.enemies)
                    and all((point - p).length() >= 2 for p in chosen)):
                chosen.append(point)
                if len(chosen) == 3:
                    break
        if len(chosen) < 3:
            return False
        self.phase, self.intermission, self._phase_resolved = 3, 0, False
        self.boss_started = True
        support_kind = {1: "armor", 2: "tree", 3: "fairy"}[self.level]
        support_name = {1: "Animated Shield", 2: "Thorn Tender", 3: "Volatile Duplicate"}[self.level]
        for i, point in enumerate(chosen):
            enemy = Enemy(point, kind if i == 0 else support_kind, level=self.level, spawn_phase=3,
                          boss_role="boss" if i == 0 else "duplicate" if self.level == 3 else "support",
                          boss_name=name if i == 0 else support_name)
            enemy.hp = enemy.max_hp
            self.enemies.append(enemy)
            self._record("enemy_spawn", target=self._actor_info(enemy))
            self.effects.append(Effect(point, "spawn", .8, .8))
        self._record("phase_start", encounter=name, spawner_count=0)
        self.announce(f"Final encounter: {name}. Signature: {move}!")
        self.events.append("phase")
        return True

    def _phase_cleared(self):
        if self.keeper:
            return
        if self.spawners or self._phase_resolved:
            return
        if self.phase == 3 and not self.level_data.menagerie and (not self.boss_started or any(e.boss_role for e in self.enemies)):
            return
        self._phase_resolved = True
        self._record("phase_cleared", enemies_remaining=len(self.enemies))
        if self.phase < 3:
            self.intermission = PHASE_DELAY
            self.announce(f"Phase {self.phase}/3 cleared. Next phase in {PHASE_DELAY:g} seconds. Reposition and prepare!")
            self.events.append("phase_clear")
        else:
            self._complete_level()

    def walkable(self, pos, radius=0.23):
        if not (0 <= pos.x < 17 and 0 <= pos.y < 17):
            return False
        for x in range(floor(pos.x - radius), floor(pos.x + radius) + 1):
            for y in range(floor(pos.y - radius), floor(pos.y + radius) + 1):
                if (x, y) in self.walls:
                    closest = Vec(max(x, min(pos.x, x + 1)), max(y, min(pos.y, y + 1)))
                    if (pos - closest).length() < radius:
                        return False
        return True

    def move(self, pos, delta, radius=0.23):
        steps = max(1, ceil(delta.length() / 0.12))
        step = delta * (1 / steps)
        for _ in range(steps):
            candidate = Vec(pos.x + step.x, pos.y)
            if self.walkable(candidate, radius):
                pos = candidate
            candidate = Vec(pos.x, pos.y + step.y)
            if self.walkable(candidate, radius):
                pos = candidate
        return pos

    def _line_clear(self, start, end):
        delta = end - start
        steps = max(1, ceil(delta.length() / 0.15))
        return all(self.walkable(start + delta * (i / steps)) for i in range(1, steps + 1))

    def request_move(self, target, marker=True):
        if self.state != "playing":
            return
        self.path = find_path(self.player.pos, target, self.blocked, self.walkable, self._line_clear)
        self.destination = self.path[-1] if self.path else None
        if marker and self.destination is not None:
            self.effects.append(Effect(self.destination, "destination", 0.6, 0.6))

    def stop(self):
        self.path.clear()
        self.destination = None

    def _follow_path(self, dt):
        distance = self.player.move_speed * dt * (self.keeper.slow_at(self.player.pos) if self.keeper else 1)
        while self.path and distance > 0:
            delta = self.path[0] - self.player.pos
            length = delta.length()
            if length < 0.025:
                self.path.pop(0)
                continue
            step = delta.unit() * min(distance, length)
            self.player.pos = self.move(self.player.pos, step)
            distance -= step.length()
            if (self.path[0] - self.player.pos).length() < 0.025:
                self.path.pop(0)
        if not self.path:
            self.destination = None

    def _navigation_changed(self):
        self._path_tile = None
        if self.destination is not None:
            self.request_move(self.destination, marker=False)

    def announce(self, message):
        self.message, self.message_time = message, 3.5

    def use_potion(self):
        player = self.player
        if self.state != "playing" or player.stasis > 0:
            return
        if player.hp >= player.max_hp:
            self.announce("Already at full health. Save your potions.")
        elif player.potions > 0:
            player.potions -= 1
            restored = min(40, player.max_hp - player.hp)
            player.hp += restored
            self._record("healing", source="potion", hp_restored=restored, potions_left=player.potions)
            self.events.append("heal")
            self.effects.append(Effect(player.pos, "heal", 0.8, 0.8, f"+{restored}"))
        else:
            self.announce("No potions left. Look for food.")

    def can_cast(self, key):
        player = self.player
        if self.state != "playing":
            return "This ascent has ended."
        if player.stasis > 0:
            return "Encased in ice. Wait for the shatter."
        if player.cooldowns[key] > 0:
            return f"{ABILITIES[key].name} is cooling down."
        if player.cast_time > 0:
            return "Finishing a spell."
        if player.mana < ABILITIES[key].mana:
            return "Not enough mana."
        return ""

    def patch_time_at(self, pos):
        return max((patch.life for patch in self.ice_patches if patch.contains(pos)), default=0)

    @property
    def frost_multiplier(self):
        return 1 + ICE_PATCH_FROST_BONUS if self.patch_time_at(self.player.pos) > 0 else 1

    def refresh_patch_status(self, enemy):
        enemy.patch_time = self.patch_time_at(enemy.pos)

    def enemy_move_factor(self, enemy):
        self.refresh_patch_status(enemy)
        return ICE_PATCH_MOVE_FACTOR if enemy.patch_time > 0 else 1

    def patch_preview(self, target):
        if (target - self.player.pos).length() > ABILITIES["e"].range:
            return target, "Ice Patch is out of range (5 tiles)."
        if not self.walkable(target, .05):
            return target, "Ice Patch needs clear floor."
        if not self._line_clear(self.player.pos, target):
            return target, "Cannot place Ice Patch through an obstacle."
        return target, ""

    def cast(self, key, target=None, feedback=True):
        reason = self.can_cast(key)
        target = target if target is not None else self.player.pos + self.player.facing * 4
        center = target
        if not reason and key == "e":
            center, reason = self.patch_preview(target)
        if not reason and key == "q" and (target - self.player.pos).length() < 0.1:
            reason = "Aim Frost Bolt away from yourself."
        if reason:
            if feedback:
                self._record("spell_rejected", spell=key, reason=reason)
                self.announce(reason)
            return False
        player = self.player
        frost_multiplier = self.frost_multiplier
        ability = ABILITIES[key]
        player.mana -= ability.mana
        self._cast_sequence += 1
        cast_id = self._cast_sequence
        self._record("spell_cast", spell=key, cast_id=cast_id, mana_spent=ability.mana,
                     mana_remaining=round(player.mana, 2), frost_multiplier=frost_multiplier,
                     position=self._point(player.pos), target=self._point(target), cooldown=player.cooldown_for(key))
        player.cooldowns[key] = player.cooldown_for(key)
        player.cast_time = 0.1 if key == "q" else 0.18
        if key == "q":
            direction = (target - player.pos).unit()
            player.facing = direction
            self.projectiles.append(Projectile(player.pos + direction * 0.35, direction * 10, damage=ability.damage, frost_multiplier=frost_multiplier, cast_id=cast_id, source="mage"))
            self.effects.append(Effect(player.pos + direction * 0.4, "cast", 0.2, 0.2))
            self.events.append("bolt")
        elif key == "w":
            self._aoe(player.pos, ability.range, ability.damage, ability.freeze, frost_multiplier, spell="w", cast_id=cast_id)
            if self.keeper:
                self.keeper.suppress_vines(player.pos, ability.range)
            self.effects.append(Effect(player.pos, "nova", 0.6, 0.6, radius=ability.range))
            self.events.append("nova")
        elif key == "e":
            self.ice_patches.append(IcePatch(center, life=ability.duration))
            for enemy in self.enemies:
                self.refresh_patch_status(enemy)
            self._record("spell_resolved", spell="e", cast_id=cast_id, reason="field_placed",
                         targets_hit=sum(self.ice_patches[-1].contains(enemy.pos) for enemy in self.enemies))
            self.events.append("patch")
            self.announce("Ice Patch: enemies move and attack slower. Stand inside for +30% frost damage.")
        elif key == "r":
            player.stasis = ability.duration
            player.stasis_frost_multiplier = frost_multiplier
            player.stasis_cast_id = cast_id
            self.events.append("prison")
            self.announce("Glacial Prison: invulnerable. Shatter in 2.5 seconds.")
        return True

    def _aoe(self, pos, radius, damage, freeze, frost_multiplier=1, spell="unknown", cast_id=0):
        targets_hit = 0
        for target in (self.enemies + self.spawners)[:]:
            # A boss kill can recall living summons during this same blast.
            # Revalidate the snapshot before damaging or freezing each target.
            if target not in self.enemies and target not in self.spawners:
                continue
            if (target.pos - pos).length() <= radius and self._line_clear(pos, target.pos):
                was_alive = target.hp > 0
                self._hit(target, damage, frost_multiplier, spell=spell, cast_id=cast_id)
                targets_hit += int(was_alive)
                if isinstance(target, Enemy) and target.hp > 0:
                    self._freeze(target, freeze)
        self._record("spell_resolved", spell=spell, cast_id=cast_id, targets_hit=targets_hit, reason="area")

    def _update_distances(self):
        tile = (floor(self.player.pos.x), floor(self.player.pos.y))
        if tile == self._path_tile:
            return
        self._path_tile = tile
        self._distances = {tile: 0}
        queue = deque([tile])
        blocked = self.blocked
        while queue:
            cell = queue.popleft()
            for neighbor in neighbors(cell):
                x, y = neighbor
                if 0 < x < 16 and 0 < y < 16 and neighbor not in blocked and neighbor not in self._distances:
                    self._distances[neighbor] = self._distances[cell] + 1
                    queue.append(neighbor)

    def _enemy_direction(self, enemy):
        target = self.player.pos
        if not self._line_clear(enemy.pos, target):
            choices = neighbors((floor(enemy.pos.x), floor(enemy.pos.y)))
            best = min(choices, key=lambda cell: self._distances.get(cell, 999))
            if best not in self._distances:
                return Vec()
            target = Vec(best[0] + 0.5, best[1] + 0.5)
        return (target - enemy.pos).unit()

    def _move_enemy(self, enemy, dt, direction=None):
        self.refresh_patch_status(enemy)
        if direction is None:
            direction = self._enemy_direction(enemy)
        separation = Vec()
        for other in self.enemies:
            offset = enemy.pos - other.pos
            length = offset.length()
            if other is not enemy and 0 < length < .5:
                separation = separation + offset.unit() * ((.5 - length) * 2)
        direction = (direction + separation).unit()
        speed = enemy.move_speed
        if enemy.chilled > 0:
            speed *= 1 - ABILITIES["q"].slow
        enemy.pos = self.move(enemy.pos, direction * speed * dt)

    def _archer(self, enemy, dt):
        fairy = enemy.kind == "fairy"
        if enemy.windup > 0:
            # Aim locks at draw time: arrows never home in on a moving player.
            if not self._line_clear(enemy.pos, enemy.shot_target):
                enemy.windup, enemy.shot_target = 0, None
                enemy.cooldown = .4
                return
            enemy.windup = max(0, enemy.windup - dt * enemy.attack_rate)
            if enemy.windup == 0:
                direction = (enemy.shot_target - enemy.pos).unit()
                damage = round(ENEMY_STATS[enemy.kind][3] * (1 + .12 * (enemy.level - 1)))
                self.projectiles.append(Projectile(enemy.pos + direction * .4, direction * (4.4 if fairy else 5.5),
                                                   life=1.7, damage=damage, hostile=True,
                                                   spell="potion" if fairy else "arrow", source=enemy.kind))
                enemy.shot_target = None
                enemy.cooldown = 2.3 if fairy else ARCHER_COOLDOWN
                self._record("enemy_attack", source=enemy.kind, attack="potion" if fairy else "arrow", stage="release")
                self.events.append("potion_cast" if fairy else "arrow")
            return
        distance = (self.player.pos - enemy.pos).length()
        if distance <= (6.5 if fairy else ARCHER_RANGE) and self._line_clear(enemy.pos, self.player.pos):
            if enemy.cooldown <= 0:
                enemy.shot_target = self.player.pos
                enemy.windup = .8 if fairy else ARCHER_WINDUP
                self._record("enemy_attack", source=enemy.kind, attack="potion" if fairy else "arrow",
                             stage="warning", warning_seconds=enemy.windup / enemy.attack_rate)
            elif distance < 2.6:
                self._move_enemy(enemy, dt, (enemy.pos - self.player.pos).unit() if distance else Vec(1, 0))
        else:
            self._move_enemy(enemy, dt)

    def _hurt_player(self, amount, source="unknown", attack="contact"):
        player = self.player
        if self.state != "playing" or player.invincible > 0 or player.stasis > 0:
            return False
        damage = max(1, amount - player.inventory.stats.armor)
        previous_hp = player.hp
        player.hp = max(0, player.hp - damage)
        self._record("player_damage", source=source, attack=attack, raw_damage=amount,
                     effective_damage=previous_hp - player.hp, armor=player.inventory.stats.armor,
                     hp_remaining=player.hp, position=self._point(player.pos))
        player.invincible = .65
        player.flash = .2
        self.events.append("hurt")
        self.effects.append(Effect(player.pos, "hurt", .4, .4))
        if player.hp <= 0:
            self.state = "dead"
            self._record("player_died", source=source, attack=attack)
            if self.keeper:
                self.keeper.cleanup()
            self.hazards.clear()
            self.ice_patches.clear()
            for enemy in self.enemies:
                enemy.patch_time = 0
            self.events.append("dead")
        return True

    def _hit(self, target, damage, frost_multiplier=1, spell="unknown", cast_id=0):
        active_targets = self.spawners if isinstance(target, Spawner) else self.enemies
        if target.hp <= 0 or target not in active_targets:
            return
        critical = self.combat_rng.random() < self.player.crit_chance
        amount = damage * (1 + self.player.inventory.stats.damage) * frost_multiplier
        if isinstance(target, Enemy) and target.boss_role == "boss":
            if target.recovery > 0:
                amount *= 1.35
            elif self.level == 1 and any(e.boss_role == "support" and e.frozen <= 0 for e in self.enemies):
                amount *= .65
        if critical:
            amount *= self.player.crit_multiplier
        damage = max(1, round(amount))
        previous_hp = target.hp
        target.hp = max(0, target.hp - damage)
        self._record("target_damage", target=self._actor_info(target), spell=spell, cast_id=cast_id,
                     effective_damage=previous_hp - target.hp, rolled_damage=damage, critical=critical,
                     frost_multiplier=frost_multiplier)
        target.flash = 0.12
        self.events.append("hit")
        self.effects.append(Effect(target.pos, "critical" if critical else "hit", 0.5, 0.5, str(damage) + ("!" if critical else "")))
        if target.hp <= 0:
            self.effects.append(Effect(target.pos, "burst", 0.7, 0.7))
            if self.selected is target:
                self.selected = None
            if isinstance(target, Spawner):
                self._record("spawner_destroyed", target=self._actor_info(target), spell=spell)
                self.spawners.remove(target)
                self.spawners_defeated += 1
                self.events.append("break")
                self.pickups.append(Pickup(target.pos, "gold", self.gold_value(75)))
                self._drop_equipment(target.pos, guaranteed=True)
                label = "Alembic shattered" if target.alchemist else "Blighted Heart purged" if target.forest else "Rift sealed"
                self.announce(f"{label}. {len(self.spawners)} remaining.")
                if not self.spawners:
                    self._phase_cleared()
            else:
                self._record("enemy_defeated", target=self._actor_info(target), spell=spell)
                self.enemies.remove(target)
                self.player.kills += 1
                if target.kind == "keeper":
                    self.keeper.defeated()
                    return
                self._drop_equipment(target.pos, guaranteed=bool(target.boss_role))
                self.pickups.append(Pickup(target.pos, "gold", self.gold_value(150 if target.boss_role == "boss" else 10)))
                if self.rng.random() < 0.12:
                    self.pickups.append(Pickup(target.pos + Vec(0.3, 0), "food", 15))
                if target.boss_role:
                    self._phase_cleared()

    def _projectiles(self, dt):
        if dt <= 0:
            return
        for shot in self.projectiles[:]:
            if shot not in self.projectiles:
                continue
            travel = min(dt, max(0, shot.life))
            shot.life -= dt
            if travel == 0:
                self.projectiles.remove(shot)
                continue
            steps = max(1, ceil(shot.velocity.length() * travel / 0.1))
            resolved = False
            for _ in range(steps):
                shot.pos = shot.pos + shot.velocity * (travel / steps)
                if not self.walkable(shot.pos, 0.06):
                    shot.life = 0
                    if not shot.hostile:
                        resolved = True
                        self._record("spell_resolved", spell=shot.spell, cast_id=shot.cast_id, targets_hit=0, reason="terrain")
                    splash = shot.hostile and shot.spell == "potion"
                    self.effects.append(Effect(shot.pos, "potion_splash" if splash else "spark", .3, .3))
                    break
                if shot.hostile:
                    if (self.player.pos - shot.pos).length() < .32:
                        self._hurt_player(shot.damage, source=shot.source, attack=shot.spell)
                        if shot.spell == "potion":
                            self.effects.append(Effect(shot.pos, "potion_splash", .4, .4))
                        shot.life = 0
                        break
                    continue
                target = next((item for item in self.enemies + self.spawners
                               if (item.pos - shot.pos).length() < (0.55 if isinstance(item, Spawner) else 0.38)), None)
                if target is not None:
                    self._hit(target, shot.damage, shot.frost_multiplier, spell=shot.spell, cast_id=shot.cast_id)
                    resolved = True
                    self._record("spell_resolved", spell=shot.spell, cast_id=shot.cast_id, targets_hit=1, reason="hit")
                    if isinstance(target, Enemy) and target.hp > 0:
                        target.chilled = max(target.chilled, ABILITIES["q"].duration)
                        chance = self.player.inventory.stats.frostweave_freeze_chance if shot.spell == "q" else 0
                        if chance and self.proc_rng.random() < chance:
                            applied = self._freeze(target, FROSTWEAVE_FREEZE)
                            target.windup, target.shot_target = 0, None
                            self.effects.append(Effect(target.pos, "freeze", .5, .5, "FROZEN!" if applied else "FROST RESISTED"))
                            if applied:
                                self.events.append("freeze")
                    shot.life = 0
                    break
            if shot.life <= 0:
                if not shot.hostile and not resolved:
                    self._record("spell_resolved", spell=shot.spell, cast_id=shot.cast_id, targets_hit=0, reason="expired")
                self.projectiles.remove(shot)
            if self.state == "dead":
                return

    def _spawn(self, dt):
        for spawner in self.spawners:
            spawner.flash = max(0, spawner.flash - dt)
            spawner.timer -= dt
            if spawner.timer <= 0:
                spawner.timer = self.rng.uniform(4.5, 6.5)
                if len(self.enemies) >= (14 if self.level_data.menagerie else 40):
                    continue
                options = [Vec(0.8, 0), Vec(-0.8, 0), Vec(0, 0.8), Vec(0, -0.8)]
                self.rng.shuffle(options)
                for offset in options:
                    pos = spawner.pos + offset
                    if self.walkable(pos):
                        if self.level_data.forest or self.level_data.alchemist or self.level_data.menagerie:
                            kind = self.rng.choices(self.level_data.spawn_kinds,
                                                    weights=self.level_data.spawn_weights)[0]
                        else:
                            kind = "skitter" if self.rng.random() < .35 else "husk"
                        enemy = Enemy(pos, kind, level=self.level, cooldown=1 if kind in ("archer", "fairy") else 0,
                                      spawn_phase=spawner.spawn_phase)
                        enemy.hp = enemy.max_hp
                        self.enemies.append(enemy)
                        self._record("enemy_spawn", target=self._actor_info(enemy))
                        self.effects.append(Effect(pos, "spawn", 0.6, 0.6))
                        break

    def update(self, dt, aim=None):
        if self.state != "playing":
            return
        dt = min(max(dt, 0), 1 / 30)
        if self.telemetry:
            self.telemetry.tick(self, dt)
        self.time += dt
        if self.intermission > 0:
            self.intermission = max(0, self.intermission - dt)
            if self.intermission <= 1e-8:
                if not self._activate_phase(self.phase + 1):
                    self.intermission = .2
        self.message_time = max(0, self.message_time - dt)
        player = self.player
        player.mana = min(100, player.mana + 8 * dt)
        for key in player.cooldowns:
            player.cooldowns[key] = max(0, player.cooldowns[key] - dt)
        for attr in ("cast_time", "invincible", "flash"):
            setattr(player, attr, max(0, getattr(player, attr) - dt))
        if player.stasis > 0:
            player.stasis = max(0, player.stasis - dt)
            if player.stasis == 0:
                ultimate = ABILITIES["r"]
                self._aoe(player.pos, ultimate.range, ultimate.damage, ultimate.freeze, player.stasis_frost_multiplier, spell="r", cast_id=player.stasis_cast_id)
                player.stasis_frost_multiplier = 1
                self.effects.append(Effect(player.pos, "shatter", 0.9, 0.9, radius=ultimate.range))
                self.events.append("shatter")
        elif player.cast_time <= 0:
            self._follow_path(dt)
        if aim is not None and (aim - player.pos).length() > 0.1:
            player.facing = (aim - player.pos).unit()
        for effect in self.effects:
            effect.life -= dt
        self.effects = [effect for effect in self.effects if effect.life > 0]
        for patch in self.ice_patches:
            patch.life -= dt
        self.ice_patches = [patch for patch in self.ice_patches if patch.life > 1e-8]
        for enemy in self.enemies:
            self.refresh_patch_status(enemy)
        self._update_distances()
        self._spawn(dt)
        update_hazards(self, dt)
        if self.keeper:
            self.keeper.update(dt)
        if self.state == "dead":
            return
        for enemy in self.enemies[:]:
            self.refresh_patch_status(enemy)
            enemy.flash = max(0, enemy.flash - dt)
            enemy.cooldown = max(0, enemy.cooldown - dt * enemy.attack_rate)
            enemy.phase += dt
            enemy.frost_resistance = max(0, enemy.frost_resistance - dt)
            was_frozen = enemy.frozen > 0
            enemy.frozen = max(0, enemy.frozen - dt)
            enemy.chilled = max(0, enemy.chilled - dt)
            if was_frozen:
                enemy.windup, enemy.shot_target = 0, None
                if enemy.kind in KINDS:
                    interrupt(enemy)
                continue
            if enemy.kind == "keeper":
                continue
            if enemy.kind in KINDS:
                update_creature(self, enemy, dt)
                if self.state == "dead":
                    return
                continue
            if enemy.boss_role == "boss":
                enemy.recovery = max(0, enemy.recovery - dt * enemy.attack_rate)
                if enemy.recovery > 0 or any(h.owner is enemy for h in self.hazards):
                    continue
                enemy.signature_timer -= dt * enemy.attack_rate
                if enemy.signature_timer <= 0:
                    signature(self, enemy)
                    continue
                if self.level == 2:
                    for tender in self.enemies:
                        if tender.boss_role == "support" and tender.frozen <= 0 and (tender.pos - enemy.pos).length() < 5:
                            enemy.hp = min(enemy.max_hp, enemy.hp + 5 * dt)
                    continue
            if enemy.kind in ("archer", "fairy"):
                self._archer(enemy, dt)
                continue
            distance = (player.pos - enemy.pos).length()
            if distance > 0.5:
                self._move_enemy(enemy, dt)
            elif enemy.cooldown <= 0:
                base_damage = ENEMY_STATS[enemy.kind][3]
                if self._hurt_player(round(base_damage * (1 + .12 * (enemy.level - 1))), source=enemy.kind, attack="melee"):
                    enemy.cooldown = .9
                    self._record("enemy_attack", source=enemy.kind, attack="melee", stage="hit")
                if self.state == "dead":
                    return
        for enemy in self.enemies:
            self.refresh_patch_status(enemy)
        self._projectiles(dt)
        if self.state == "dead":
            return
        for pickup in self.pickups[:]:
            if (pickup.pos - player.pos).length() < 0.65:
                if pickup.kind == "food":
                    if player.hp >= player.max_hp:
                        continue
                    restored = min(pickup.value, player.max_hp - player.hp)
                    player.hp += restored
                    self._record("healing", source="food", hp_restored=restored)
                    self.events.append("heal")
                    self.effects.append(Effect(player.pos, "heal", 0.7, 0.7, f"+{restored}"))
                elif pickup.kind == "item":
                    player.inventory.add(pickup.item)
                    self._record("loot_collected", slot=pickup.item.slot, rank=pickup.item.rank, set=pickup.item.set_id)
                    self.events.append("loot")
                    self.announce(f"Found {pickup.item.name} — Rank {pickup.item.rank}. I opens inventory.")
                else:
                    player.gold += pickup.value
                    self._record("gold_change", amount=pickup.value, source="pickup")
                    self.events.append("gold")
                    self.effects.append(Effect(pickup.pos, "gold", 0.6, 0.6, f"+{pickup.value}"))
                self.pickups.remove(pickup)
        if not self.spawners:
            self._phase_cleared()
        if self.exit_open:
            if (player.pos - self.exit).length() < 0.8:
                self.state = "won" if self.level == PLAYABLE_FLOORS else "cleared"
                self.stop()
                # Collect remaining earned drops before the room is discarded.
                self._collect_remaining_rewards()
                self.events.append("win")

    def _drop_equipment(self, pos, guaranteed=False):
        if self.loot_rng.random() < .005:
            slot = "boots"
        elif guaranteed or self.loot_rng.random() < .12:
            slot = self.loot_rng.choice(SLOTS[:-1])
        else:
            return
        rank = self.loot_rng.choices((1, 2, 3), weights=(70, 25, 5))[0]
        item = self.player.inventory.create(slot, rank)
        self.pickups.append(Pickup(pos, "item", 0, item))

    def _complete_level(self):
        if self.level_completed:
            return
        self.level_completed = True
        player = self.player
        if self.level == 1 and not player.first_clear_rewarded:
            reward = player.inventory.create("boots", 1, "reward")
            player.inventory.add(reward)
            player.first_clear_rewarded = True
            self.announce("Ground floor cleared! Everfrost Treads awarded. The stair portal is open. I opens gear.")
            self.events.append("loot")
        else:
            self.announce(f"Floor {self.level} cleared! All three phases defeated. The stair portal is open.")
        if self.level_data.keeper:
            self.announce("The lower five floors are complete. The upper tower continues beyond the sealed stair.")
        self.hazards.clear()
        self._record("floor_cleared", hp_remaining=player.hp, gold=player.gold)

    def _collect_remaining_rewards(self):
        # Never leave an earned equipment drop behind on a level transition.
        for pickup in self.pickups[:]:
            if pickup.kind == "item":
                self.player.inventory.add(pickup.item)
                self.pickups.remove(pickup)
            elif pickup.kind == "gold":
                self.player.gold += pickup.value
                self._record("gold_change", amount=pickup.value, source="portal_collection")
                self.pickups.remove(pickup)

    def next_level(self):
        if self.state != "cleared" or self.level >= PLAYABLE_FLOORS:
            return False
        recorder = self.telemetry
        if recorder:
            recorder.end_attempt(self, "next_floor")
        player = self.player
        player.cleared_floor = 0
        player.stasis_frost_multiplier = 1
        player.pos = Vec(3.5, 13.5)
        player.hp, player.mana = player.max_hp, 100
        player.stasis = player.cast_time = player.flash = 0
        player.invincible = 1
        player.cooldowns = dict.fromkeys(ABILITIES, 0.0)
        seed = None if self.seed is None else self.seed + 1
        fresh = World(seed, player=player, level=self.level + 1)
        self.__dict__.update(fresh.__dict__)
        if recorder:
            recorder.attach(self, "next_floor")
        if self.keeper:
            self.keeper.world = self
        self.announce(f"Floor {self.level}: {self.level_data.phase_lines[0]}")
        return True

    def _can_manage_gear(self):
        if self.state == "dead" or self.player.hp <= 0:
            self.announce("Return to The Tower before changing equipment.")
            return False
        if self.player.stasis > 0:
            self.announce("Close the armory and wait for Glacial Prison to shatter before changing gear.")
            return False
        return True

    def equip_item(self, uid):
        if not self._can_manage_gear() or not self.player.inventory.equip(uid):
            return False
        self.player.hp = min(self.player.hp, self.player.max_hp)
        self.announce("Equipment changed. Maximum health changes do not heal you.")
        return True

    def unequip_item(self, slot):
        if not self._can_manage_gear() or not self.player.inventory.unequip(slot):
            return False
        self.player.hp = min(self.player.hp, self.player.max_hp)
        return True

    def buy_item(self, slot):
        if slot not in SLOTS or not self._can_manage_gear():
            return False
        cost = BLANK_COST[slot]
        if self.player.gold < cost:
            self.announce(f"Need {cost:,} gold for this unranked {slot}.")
            return False
        self.player.gold -= cost
        self._record("gold_change", amount=-cost, source="shop")
        item = self.player.inventory.create(slot, 0, "shop")
        self.player.inventory.add(item)
        self.announce(f"Bought {item.name}. Select it to enchant.")
        self.events.append("loot")
        return item

    def enchant_item(self, uid):
        if not self._can_manage_gear():
            return False
        item = self.player.inventory.get(uid)
        if item is None:
            return False
        if item.next_cost is None:
            self.announce("Rank 5 is the maximum enchantment.")
            return False
        if self.player.gold < item.next_cost:
            self.announce(f"Need {item.next_cost:,} gold to reach Rank {item.rank + 1}.")
            return False
        self.player.gold -= item.next_cost
        self._record("gold_change", amount=-item.next_cost, source="enchant")
        self.player.inventory.upgrade(uid)
        self.announce(f"{item.name} enchanted to Rank {item.rank + 1}.")
        self.events.append("loot")
        return True

    def _discardable_item(self, uid):
        if not self._can_manage_gear():
            return None
        item = self.player.inventory.get(uid)
        if item is None:
            self.announce("Select an item from your backpack first.")
            return None
        if uid in self.player.inventory.equipped.values():
            self.announce("Unequip this item before selling or destroying it.")
            return None
        return item

    def sell_item(self, uid):
        item = self._discardable_item(uid)
        return self.sell_items((item,)) if item is not None else False

    def quote_sale(self, rank):
        if type(rank) is not int or not 0 <= rank <= 5:
            return ()
        return tuple(item for item in self.player.inventory.backpack if item.rank == rank)

    def sell_items(self, quoted_items):
        """Validate the entire quoted snapshot before removing or paying for anything."""
        if not self._can_manage_gear():
            return False
        items = tuple(quoted_items)
        inventory = self.player.inventory
        if not items:
            self.announce("No backpack equipment matches this sale.")
            return False
        if (len({item.uid for item in items}) != len(items)
                or any(inventory.get(item.uid) != item or item.uid in inventory.equipped.values()
                       for item in items)):
            self.announce("Equipment changed. Review the items and request a new sale.")
            return False
        total = sum(item.sell_value for item in items)
        for item in items:
            inventory.remove(item.uid)
        self.player.gold += total
        self._record("gold_change", amount=total, source="sale")
        if len(items) == 1:
            item = items[0]
            self.announce(f"Sold Rank {item.rank} {item.name} for {total:,} gold.")
        else:
            self.announce(f"Sold {len(items)} backpack items for {total:,} gold.")
        self.events.append("gold")
        return True

    def destroy_item(self, uid):
        item = self._discardable_item(uid)
        if item is None or self.player.inventory.remove(uid) is None:
            return False
        self.announce(f"Destroyed Rank {item.rank} {item.name}. No gold received.")
        self.events.append("break")
        return True
