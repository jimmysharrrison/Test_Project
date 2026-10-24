"""Display-independent combat, navigation, and status simulation for the Ice Mage."""

from collections import deque
from dataclasses import dataclass, field
from math import ceil, floor
from random import Random

from .abilities import ABILITIES
from .geometry import Vec
from .items import BLANK_COST, Inventory, Item, SLOTS
from .navigation import find_path, flood, neighbors

LAYOUT = (
    "#################",
    "#...............#",
    "#...##..........#",
    "#...##....##....#",
    "#.........##....#",
    "#...............#",
    "#..##...........#",
    "#..##.....##....#",
    "#.........##....#",
    "#...............#",
    "#.....##........#",
    "#.....##....##..#",
    "#...........##..#",
    "#...............#",
    "#...............#",
    "#...............#",
    "#################",
)


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
    invincible: float = 0
    flash: float = 0
    inventory: Inventory = field(default_factory=Inventory)
    first_clear_rewarded: bool = False
    unlocked_level: int = 1

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

    @property
    def max_hp(self):
        base = 26 if self.kind == "skitter" else 44
        return round(base * (1 + .15 * (self.level - 1)))

    @property
    def name(self):
        return "Ember Skitter" if self.kind == "skitter" else "Molten Skeleton"

    @property
    def statuses(self):
        return [(name, time) for name, time in (("Frozen", self.frozen), ("Chilled", self.chilled)) if time > 0]


@dataclass(slots=True, eq=False)
class Spawner:
    pos: Vec
    hp: int = 176
    timer: float = 6
    flash: float = 0
    level: int = 1

    @property
    def max_hp(self):
        return round(176 * (1 + .15 * (self.level - 1)))

    @property
    def name(self):
        return "Molten Rift"

    @property
    def statuses(self):
        return []


@dataclass(slots=True)
class IceWall:
    cells: tuple
    life: float = 6


@dataclass(slots=True)
class Projectile:
    pos: Vec
    velocity: Vec
    life: float = 1.05
    damage: int = 24


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
        self.rng = Random(seed)
        self.combat_rng = Random(seed)
        self.loot_rng = Random(None if seed is None else seed + 1937)
        self.player = player if player is not None else Player()
        self.level = level
        self.level_completed = False
        self.walls = {(x, y) for y, row in enumerate(LAYOUT) for x, tile in enumerate(row) if tile == "#"}
        self.ice_walls = []
        self._ice_cells = set()
        self.spawners = [
            Spawner(Vec(4.5, 4.5), timer=5), Spawner(Vec(13.5, 4.5), timer=8),
            Spawner(Vec(12.5, 13.5), timer=11),
        ]
        self.enemies = [Enemy(Vec(7.5, 5.5)), Enemy(Vec(12.5, 5.5)),
                        Enemy(Vec(10.5, 12.5), "skitter", 26)]
        self.pickups = [Pickup(Vec(7.5, 13.5), "food", 25), Pickup(Vec(12.5, 8.5), "food", 25),
                        Pickup(Vec(8.5, 6.5), "gold", 25), Pickup(Vec(5.5, 9.5), "gold", 25)]
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
        self.message = "Right click to move. QWER to cast. Seal the three rifts."
        self.message_time = 7.0
        self.selected = None
        self.path = []
        self.destination = None
        self._path_tile = None
        self._distances = {}

    def gold_value(self, base):
        return round(base * (1 + .15 * (self.level - 1)))

    @property
    def blocked(self):
        return self.walls | self._ice_cells

    @property
    def exit_open(self):
        return not self.spawners

    def walkable(self, pos, radius=0.23):
        if not (0 <= pos.x < 17 and 0 <= pos.y < 17):
            return False
        for x in range(floor(pos.x - radius), floor(pos.x + radius) + 1):
            for y in range(floor(pos.y - radius), floor(pos.y + radius) + 1):
                if (x, y) in self.walls or (x, y) in self._ice_cells:
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
        distance = self.player.move_speed * dt
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
        self._ice_cells = {cell for wall in self.ice_walls for cell in wall.cells}
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
            self.events.append("heal")
            self.effects.append(Effect(player.pos, "heal", 0.8, 0.8, f"+{restored}"))
        else:
            self.announce("No potions left. Look for food.")

    def can_cast(self, key):
        player = self.player
        if self.state != "playing":
            return "The descent has ended."
        if player.stasis > 0:
            return "Encased in ice. Wait for the shatter."
        if player.cooldowns[key] > 0:
            return f"{ABILITIES[key].name} is cooling down."
        if player.cast_time > 0:
            return "Finishing a spell."
        if player.mana < ABILITIES[key].mana:
            return "Not enough mana."
        return ""

    def wall_preview(self, target):
        """Return candidate cells and a failure reason; never mutate the world."""
        x, y = floor(target.x), floor(target.y)
        center = Vec(x + 0.5, y + 0.5)
        direction = center - self.player.pos
        cells = tuple((x, y + i) if abs(direction.x) >= abs(direction.y) else (x + i, y)
                      for i in (-1, 0, 1))
        if direction.length() > ABILITIES["e"].range:
            return cells, "Ice Wall is out of range (5 tiles)."
        if any(not (0 < cx < 16 and 0 < cy < 16) or (cx, cy) in self.blocked for cx, cy in cells):
            return cells, "Ice Wall needs three clear floor tiles."
        if not self._line_clear(self.player.pos, center):
            return cells, "Cannot place Ice Wall through an obstacle."
        for actor in [self.player] + self.enemies + self.spawners:
            for cx, cy in cells:
                closest = Vec(max(cx, min(actor.pos.x, cx + 1)), max(cy, min(actor.pos.y, cy + 1)))
                if (actor.pos - closest).length() < (0.6 if isinstance(actor, Spawner) else 0.35):
                    return cells, "Cannot place Ice Wall through a character or rift."
        if (floor(self.exit.x), floor(self.exit.y)) in cells:
            return cells, "Keep the escape gate clear."
        start = (floor(self.player.pos.x), floor(self.player.pos.y))
        before = flood(start, self.blocked)
        after = flood(start, self.blocked | set(cells))
        if not before.difference(cells).issubset(after):
            return cells, "That wall would seal off part of the glade."
        return cells, ""

    def cast(self, key, target=None, feedback=True):
        reason = self.can_cast(key)
        target = target if target is not None else self.player.pos + self.player.facing * 4
        cells = ()
        if not reason and key == "e":
            cells, reason = self.wall_preview(target)
        if not reason and key == "q" and (target - self.player.pos).length() < 0.1:
            reason = "Aim Ice Bolt away from yourself."
        if reason:
            if feedback:
                self.announce(reason)
            return False
        player = self.player
        ability = ABILITIES[key]
        player.mana -= ability.mana
        player.cooldowns[key] = player.cooldown_for(key)
        player.cast_time = 0.1 if key == "q" else 0.18
        if key == "q":
            direction = (target - player.pos).unit()
            player.facing = direction
            self.projectiles.append(Projectile(player.pos + direction * 0.35, direction * 10, damage=ability.damage))
            self.effects.append(Effect(player.pos + direction * 0.4, "cast", 0.2, 0.2))
            self.events.append("bolt")
        elif key == "w":
            self._aoe(player.pos, ability.range, ability.damage, ability.freeze)
            self.effects.append(Effect(player.pos, "nova", 0.6, 0.6, radius=ability.range))
            self.events.append("nova")
        elif key == "e":
            self.ice_walls.append(IceWall(cells, life=ability.duration))
            self._navigation_changed()
            self.events.append("wall")
            self.announce("Ice Wall raised. It will melt in 6 seconds.")
        elif key == "r":
            player.stasis = ability.duration
            self.events.append("prison")
            self.announce("Glacial Prison: invulnerable. Shatter in 2.5 seconds.")
        return True

    def _aoe(self, pos, radius, damage, freeze):
        for target in (self.enemies + self.spawners)[:]:
            if (target.pos - pos).length() <= radius and self._line_clear(pos, target.pos):
                self._hit(target, damage)
                if isinstance(target, Enemy) and target.hp > 0:
                    target.frozen = max(target.frozen, freeze)

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

    def _hit(self, target, damage):
        critical = self.combat_rng.random() < self.player.crit_chance
        amount = damage * (1 + self.player.inventory.stats.damage)
        if critical:
            amount *= self.player.crit_multiplier
        damage = max(1, round(amount))
        target.hp = max(0, target.hp - damage)
        target.flash = 0.12
        self.events.append("hit")
        self.effects.append(Effect(target.pos, "critical" if critical else "hit", 0.5, 0.5, str(damage) + ("!" if critical else "")))
        if target.hp <= 0:
            self.effects.append(Effect(target.pos, "burst", 0.7, 0.7))
            if self.selected is target:
                self.selected = None
            if isinstance(target, Spawner):
                self.spawners.remove(target)
                self.events.append("break")
                self.pickups.append(Pickup(target.pos, "gold", self.gold_value(75)))
                self._drop_equipment(target.pos, guaranteed=True)
                self.announce(f"Rift sealed. {len(self.spawners)} remaining.")
                if not self.spawners:
                    self._complete_level()
            else:
                self.enemies.remove(target)
                self.player.kills += 1
                self._drop_equipment(target.pos)
                self.pickups.append(Pickup(target.pos, "gold", self.gold_value(10)))
                if self.rng.random() < 0.12:
                    self.pickups.append(Pickup(target.pos + Vec(0.3, 0), "food", 15))

    def _projectiles(self, dt):
        for shot in self.projectiles[:]:
            shot.life -= dt
            steps = max(1, ceil(shot.velocity.length() * dt / 0.1))
            for _ in range(steps):
                shot.pos = shot.pos + shot.velocity * (dt / steps)
                if not self.walkable(shot.pos, 0.06):
                    shot.life = 0
                    self.effects.append(Effect(shot.pos, "spark", 0.2, 0.2))
                    break
                target = next((item for item in self.enemies + self.spawners
                               if (item.pos - shot.pos).length() < (0.55 if isinstance(item, Spawner) else 0.38)), None)
                if target is not None:
                    self._hit(target, shot.damage)
                    if isinstance(target, Enemy) and target.hp > 0:
                        target.chilled = max(target.chilled, ABILITIES["q"].duration)
                    shot.life = 0
                    break
            if shot.life <= 0:
                self.projectiles.remove(shot)

    def _spawn(self, dt):
        for spawner in self.spawners:
            spawner.flash = max(0, spawner.flash - dt)
            spawner.timer -= dt
            if spawner.timer <= 0:
                spawner.timer = self.rng.uniform(4.5, 6.5)
                if len(self.enemies) >= 40:
                    continue
                options = [Vec(0.8, 0), Vec(-0.8, 0), Vec(0, 0.8), Vec(0, -0.8)]
                self.rng.shuffle(options)
                for offset in options:
                    pos = spawner.pos + offset
                    if self.walkable(pos):
                        skitter = self.rng.random() < 0.35
                        enemy = Enemy(pos, "skitter" if skitter else "husk", level=self.level)
                        enemy.hp = enemy.max_hp
                        self.enemies.append(enemy)
                        self.effects.append(Effect(pos, "spawn", 0.6, 0.6))
                        break

    def update(self, dt, aim=None):
        if self.state != "playing":
            return
        dt = min(max(dt, 0), 1 / 30)
        self.time += dt
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
                self._aoe(player.pos, ultimate.range, ultimate.damage, ultimate.freeze)
                self.effects.append(Effect(player.pos, "shatter", 0.9, 0.9, radius=ultimate.range))
                self.events.append("shatter")
        elif player.cast_time <= 0:
            self._follow_path(dt)
        if aim is not None and (aim - player.pos).length() > 0.1:
            player.facing = (aim - player.pos).unit()
        for effect in self.effects:
            effect.life -= dt
        self.effects = [effect for effect in self.effects if effect.life > 0]
        changed = False
        for wall in self.ice_walls:
            wall.life -= dt
            if wall.life <= 0:
                changed = True
        if changed:
            self.ice_walls = [wall for wall in self.ice_walls if wall.life > 0]
            self._navigation_changed()
        self._update_distances()
        self._spawn(dt)
        for enemy in self.enemies:
            enemy.flash = max(0, enemy.flash - dt)
            enemy.cooldown = max(0, enemy.cooldown - dt)
            enemy.phase += dt
            was_frozen = enemy.frozen > 0
            enemy.frozen = max(0, enemy.frozen - dt)
            enemy.chilled = max(0, enemy.chilled - dt)
            if was_frozen:
                continue
            distance = (player.pos - enemy.pos).length()
            if distance > 0.5:
                direction = self._enemy_direction(enemy)
                separation = Vec()
                for other in self.enemies:
                    offset = enemy.pos - other.pos
                    length = offset.length()
                    if other is not enemy and 0 < length < 0.5:
                        separation = separation + offset.unit() * ((0.5 - length) * 2)
                direction = (direction + separation).unit()
                speed = (1.65 if enemy.kind == "skitter" else 1.05) * ((1 - ABILITIES["q"].slow) if enemy.chilled > 0 else 1)
                enemy.pos = self.move(enemy.pos, direction * speed * dt)
            elif enemy.cooldown <= 0 and player.invincible <= 0 and player.stasis <= 0:
                base_damage = 6 if enemy.kind == "skitter" else 10
                damage = max(1, round(base_damage * (1 + .12 * (enemy.level - 1))) - player.inventory.stats.armor)
                player.hp = max(0, player.hp - damage)
                player.invincible = 0.65
                player.flash = 0.2
                self.events.append("hurt")
                enemy.cooldown = 0.9
                self.effects.append(Effect(player.pos, "hurt", 0.4, 0.4))
                if player.hp <= 0:
                    self.state = "dead"
                    self.events.append("dead")
                    return
        self._projectiles(dt)
        for pickup in self.pickups[:]:
            if (pickup.pos - player.pos).length() < 0.65:
                if pickup.kind == "food":
                    if player.hp >= player.max_hp:
                        continue
                    restored = min(pickup.value, player.max_hp - player.hp)
                    player.hp += restored
                    self.events.append("heal")
                    self.effects.append(Effect(player.pos, "heal", 0.7, 0.7, f"+{restored}"))
                elif pickup.kind == "item":
                    player.inventory.add(pickup.item)
                    self.events.append("loot")
                    self.announce(f"Found {pickup.item.name} — Rank {pickup.item.rank}. I opens inventory.")
                else:
                    player.gold += pickup.value
                    self.events.append("gold")
                    self.effects.append(Effect(pickup.pos, "gold", 0.6, 0.6, f"+{pickup.value}"))
                self.pickups.remove(pickup)
        if self.exit_open:
            self._complete_level()
            if (player.pos - self.exit).length() < 0.8:
                self.state = "cleared"
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
        player.unlocked_level = max(player.unlocked_level, self.level + 1)
        if self.level == 1 and not player.first_clear_rewarded:
            reward = player.inventory.create("boots", 1, "reward")
            player.inventory.add(reward)
            player.first_clear_rewarded = True
            self.announce("Level 1 cleared! Everfrost Treads awarded. The gate is open. I opens gear.")
            self.events.append("loot")
        else:
            self.announce(f"Level {self.level} cleared! The gate is open. Your loot has been collected.")
        self._collect_remaining_rewards()

    def _collect_remaining_rewards(self):
        # Never leave an earned equipment drop behind on a level transition.
        for pickup in self.pickups[:]:
            if pickup.kind == "item":
                self.player.inventory.add(pickup.item)
                self.pickups.remove(pickup)
            elif pickup.kind == "gold":
                self.player.gold += pickup.value
                self.pickups.remove(pickup)

    def next_level(self):
        if self.state != "cleared":
            return False
        player = self.player
        player.pos = Vec(3.5, 13.5)
        player.hp, player.mana = player.max_hp, 100
        player.stasis = player.cast_time = player.flash = 0
        player.invincible = 1
        player.cooldowns = dict.fromkeys(ABILITIES, 0.0)
        seed = None if self.seed is None else self.seed + 1
        fresh = World(seed, player=player, level=self.level + 1)
        self.__dict__.update(fresh.__dict__)
        self.announce(f"Depth {self.level}. Your equipment and gold carry forward.")
        return True

    def _can_manage_gear(self):
        if self.state == "dead" or self.player.hp <= 0:
            self.announce("Return to the glade before changing equipment.")
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
        self.player.inventory.upgrade(uid)
        self.announce(f"{item.name} enchanted to Rank {item.rank + 1}.")
        self.events.append("loot")
        return True
