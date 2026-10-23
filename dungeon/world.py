"""Real-time dungeon simulation. No window or renderer is required."""

from collections import deque
from dataclasses import dataclass, field
from math import ceil, floor
from random import Random

from .geometry import Vec

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
    potions: int = 3
    gold: int = 0
    kills: int = 0
    facing: Vec = field(default_factory=lambda: Vec(1, -1).unit())
    attack_cooldown: float = 0
    dash_cooldown: float = 0
    dash_time: float = 0
    dash_direction: Vec = field(default_factory=Vec)
    invincible: float = 0
    flash: float = 0


@dataclass(slots=True)
class Enemy:
    pos: Vec
    kind: str = "husk"
    hp: int = 44
    cooldown: float = 0
    flash: float = 0
    phase: float = 0

    @property
    def max_hp(self):
        return 26 if self.kind == "skitter" else 44


@dataclass(slots=True)
class Spawner:
    pos: Vec
    hp: int = 176
    timer: float = 6
    flash: float = 0


@dataclass(slots=True)
class Projectile:
    pos: Vec
    velocity: Vec
    life: float = 1.15
    damage: int = 22


@dataclass(slots=True)
class Pickup:
    pos: Vec
    kind: str = "gold"
    value: int = 10


@dataclass(slots=True)
class Effect:
    pos: Vec
    kind: str
    life: float = 0.4
    duration: float = 0.4
    text: str = ""


class World:
    def __init__(self, seed=None):
        self.rng = Random(seed)
        self.player = Player()
        self.walls = {
            (x, y) for y, row in enumerate(LAYOUT)
            for x, tile in enumerate(row) if tile == "#"
        }
        self.spawners = [
            Spawner(Vec(4.5, 4.5), timer=5),
            Spawner(Vec(13.5, 4.5), timer=8),
            Spawner(Vec(12.5, 13.5), timer=11),
        ]
        self.enemies = [
            Enemy(Vec(7.5, 5.5)), Enemy(Vec(12.5, 5.5)),
            Enemy(Vec(10.5, 12.5), "skitter", 26),
        ]
        self.pickups = [
            Pickup(Vec(7.5, 13.5), "food", 25),
            Pickup(Vec(12.5, 8.5), "food", 25),
            Pickup(Vec(8.5, 6.5), "gold", 25),
            Pickup(Vec(5.5, 9.5), "gold", 25),
        ]
        self.projectiles = []
        self.effects = []
        self.events = []
        self.exit = Vec(8.5, 1.5)
        self.state = "playing"
        self.time = 0.0
        self.message = "Destroy the three rifts. Leave nothing behind."
        self.message_time = 6.0
        self._path_tile = None
        self._distances = {}

    @property
    def exit_open(self):
        return not self.spawners and not self.enemies

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
        # Substeps prevent fast dashes from tunneling through a wall.
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

    def announce(self, message):
        self.message, self.message_time = message, 3.5

    def use_potion(self):
        player = self.player
        if self.state != "playing":
            return
        if player.hp >= 100:
            self.announce("Already at full health. Save your potions.")
        elif player.potions > 0:
            player.potions -= 1
            restored = min(40, 100 - player.hp)
            player.hp += restored
            self.events.append("heal")
            self.effects.append(Effect(player.pos, "heal", 0.8, 0.8, f"+{restored}"))
            self.announce("A little more fight in you.")
        else:
            self.announce("No potions left. Look for food.")

    def dash(self, direction):
        player = self.player
        if self.state == "playing" and player.dash_cooldown <= 0:
            player.dash_direction = direction.unit() if direction.length() else player.facing
            player.dash_time = 0.19
            self.events.append("dash")
            player.dash_cooldown = 1.4
            player.invincible = max(player.invincible, 0.25)
            self.effects.append(Effect(player.pos, "dash", 0.35, 0.35))

    def attack(self, target):
        player = self.player
        direction = (target - player.pos).unit()
        if self.state != "playing" or player.attack_cooldown > 0 or not direction.length():
            return
        player.facing = direction
        player.attack_cooldown = 0.28
        self.events.append("throw")
        self.projectiles.append(Projectile(player.pos + direction * 0.35, direction * 9))
        self.effects.append(Effect(player.pos + direction * 0.4, "swing", 0.18, 0.18))

    def _update_distances(self):
        tile = (floor(self.player.pos.x), floor(self.player.pos.y))
        if tile == self._path_tile:
            return
        self._path_tile = tile
        self._distances = {tile: 0}
        queue = deque([tile])
        while queue:
            x, y = queue.popleft()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                nx, ny = neighbor
                if (0 < nx < 16 and 0 < ny < 16 and neighbor not in self.walls
                        and neighbor not in self._distances):
                    self._distances[neighbor] = self._distances[(x, y)] + 1
                    queue.append(neighbor)

    def _line_clear(self, start, end):
        delta = end - start
        steps = max(1, ceil(delta.length() / 0.15))
        return all(self.walkable(start + delta * (i / steps)) for i in range(1, steps + 1))

    def _enemy_direction(self, enemy):
        target = self.player.pos
        if not self._line_clear(enemy.pos, target):
            x, y = floor(enemy.pos.x), floor(enemy.pos.y)
            neighbors = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
            best = min(neighbors, key=lambda cell: self._distances.get(cell, 999))
            target = Vec(best[0] + 0.5, best[1] + 0.5)
        return (target - enemy.pos).unit()

    def _hit(self, target, damage):
        target.hp -= damage
        self.events.append("hit")
        target.flash = 0.12
        self.effects.append(Effect(target.pos, "hit", 0.5, 0.5, str(damage)))
        if target.hp <= 0:
            self.effects.append(Effect(target.pos, "burst", 0.7, 0.7))
            if isinstance(target, Spawner):
                self.spawners.remove(target)
                self.events.append("break")
                self.pickups.append(Pickup(target.pos, "gold", 75))
                self.announce(f"Rift sealed. {len(self.spawners)} remaining.")
            else:
                self.enemies.remove(target)
                self.player.kills += 1
                self.pickups.append(Pickup(target.pos, "gold", 10))
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
                        self.enemies.append(Enemy(pos, "skitter" if skitter else "husk", 26 if skitter else 44))
                        self.effects.append(Effect(pos, "spawn", 0.6, 0.6))
                        break

    def update(self, dt, movement=Vec(), aim=None, attacking=False):
        if self.state != "playing":
            return
        # A paused/minimized window should never jump the simulation ahead.
        dt = min(max(dt, 0), 1 / 30)
        self.time += dt
        self.message_time = max(0, self.message_time - dt)
        player = self.player
        for attr in ("attack_cooldown", "dash_cooldown", "dash_time", "invincible", "flash"):
            setattr(player, attr, max(0, getattr(player, attr) - dt))
        delta = (player.dash_direction * 11 if player.dash_time > 0 else movement.unit() * 3.1) * dt
        player.pos = self.move(player.pos, delta)
        if aim is not None and (aim - player.pos).length() > 0.1:
            player.facing = (aim - player.pos).unit()
        if attacking and aim is not None:
            self.attack(aim)
        for effect in self.effects:
            effect.life -= dt
        self.effects = [effect for effect in self.effects if effect.life > 0]
        self._update_distances()
        self._spawn(dt)
        for enemy in self.enemies:
            enemy.flash = max(0, enemy.flash - dt)
            enemy.cooldown = max(0, enemy.cooldown - dt)
            enemy.phase += dt
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
                speed = 1.65 if enemy.kind == "skitter" else 1.05
                enemy.pos = self.move(enemy.pos, direction * speed * dt)
            elif enemy.cooldown <= 0 and player.invincible <= 0:
                player.hp = max(0, player.hp - (6 if enemy.kind == "skitter" else 10))
                player.invincible = 0.65
                self.events.append("hurt")
                player.flash = 0.2
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
                    if player.hp >= 100:
                        continue
                    restored = min(pickup.value, 100 - player.hp)
                    player.hp += restored
                    self.events.append("heal")
                    self.effects.append(Effect(player.pos, "heal", 0.7, 0.7, f"+{restored}"))
                else:
                    player.gold += pickup.value
                    self.events.append("gold")
                    self.effects.append(Effect(pickup.pos, "gold", 0.6, 0.6, f"+{pickup.value}"))
                self.pickups.remove(pickup)
        if self.exit_open:
            if self.message != "The way is clear. Reach the northern gate.":
                self.announce("The way is clear. Reach the northern gate.")
            if (player.pos - self.exit).length() < 0.8:
                self.state = "won"
                self.events.append("win")
