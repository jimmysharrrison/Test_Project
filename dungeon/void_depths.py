"""The Oracle and Astronomer share bounded, interruptible arena mechanics.

Forced movement uses the world's swept wall collision and never moves a player
inside Glacial Prison. A grasp restricts movement orders, not spells or potions.
"""
from dataclasses import dataclass
from math import atan2, cos, sin, pi

from .geometry import Vec
from .void import VoidFloor, GroundZone, POPULATION_CAP
from .combat_values import scaled_damage

DEPTH_STATS = {
    "lasher": ("Lashing Tentacle", 44, 0, 16),
    "grasper": ("Grasping Tentacle", 30, 0, 8),
    "anchor": ("Anchor Tentacle", 56, 0, 0),
    "thrall": ("Enthralled Wizard", 42, 1, 8),
    "oracle": ("The Many-Eyed Oracle", 2600, 0, 0),
    "gravity_adept": ("Gravity Adept", 48, 1, 12),
    "repulsor": ("Repulsion Construct", 64, 0, 0),
    "star_fragment": ("Orbiting Fragment", 28, 1.12, 14),
    "astronomer": ("The Fallen Astronomer", 2800, 0, 0),
}
BOSS_HEALTH = {kind: DEPTH_STATS[kind][1] for kind in ("oracle", "astronomer")}
MECHANIC_CAP = 3
ROOT_DURATION = 2.2
ORACLE_PROTECTION = .2
FORCES = {"tether", "well", "convergence", "rejection"}
DAMAGE = {"lash": 16, "grasp": 8, "chorus": 16, "gaze": 18,
          "well": 22, "convergence": 18, "orbit": 15, "fragment": 14}
NAMES = {"lash": "Lashing Strike", "grasp": "Grasping Strike", "tether": "Draw into Darkness",
         "chorus": "Grasping Chorus", "gaze": "Searching Gaze", "communion": "Thrall Communion",
         "call_anchor": "Draw into Darkness", "well": "Collapsing Star",
         "convergence": "Inward Convergence", "rejection": "Stellar Rejection", "orbit": "Orbiting Ruin"}


@dataclass(slots=True)
class VoidMechanic:
    kind: str
    owner: object
    pos: Vec
    warning: float
    life: float
    radius: float = .75
    end: Vec | None = None
    strength: float = 0
    elapsed: float = 0
    fired: bool = False
    points: tuple = ()

    def contains(self, point, padding=0):
        if self.end is not None:
            delta, offset = self.end - self.pos, point - self.pos
            along = max(0, min(1, (offset.x * delta.x + offset.y * delta.y) / max(.001, delta.length() ** 2)))
            return (offset - delta * along).length() < self.radius + padding
        return (point - self.pos).length() < self.radius + padding


def force_player(world, center, strength, dt, outward=False):
    """All void forces share the same wall-safe, Prison-resistant displacement."""
    if world.player.stasis > 0 or world.state != "playing" or world.level_completed:
        return
    offset = world.player.pos - center if outward else center - world.player.pos
    if offset.length() <= .001:
        return
    distance = strength * dt
    if not outward:
        distance = min(distance, offset.length())
    world.player.pos = world.move(world.player.pos, offset.unit() * distance)


def gaze_end(mechanic):
    direction = (mechanic.end - mechanic.pos).unit()
    angle = atan2(direction.y, direction.x) - .5 + min(1, mechanic.elapsed / 1.8)
    return mechanic.pos + Vec(cos(angle), sin(angle)) * 8


def orbit_points(mechanic):
    return tuple(mechanic.pos + Vec(cos(mechanic.elapsed * .85 + i * 2 * pi / 3),
                                     sin(mechanic.elapsed * .85 + i * 2 * pi / 3)) * mechanic.radius
                 for i in range(3))


class VoidDepths(VoidFloor):
    def __init__(self, world):
        super().__init__(world)
        self.mechanics = []
        self.root_owner = None
        self.root_left = 0
        self.guard_cycles = 0

    @property
    def rooted(self):
        return (self.root_left > 0 and self.root_owner in self.world.enemies
                and self.root_owner.hp > 0 and self.root_owner.frozen <= 0)

    @property
    def protected(self):
        return bool(self.boss and self.boss.kind == "oracle" and any(
            e.boss_role == "channeler" and e.hp > 0 and e.frozen <= 0
            and (e.pos - self.boss.pos).length() <= 8 for e in self.world.enemies))

    def interrupt(self, owner):
        self.mechanics[:] = [m for m in self.mechanics if not
                             (m.owner is owner and (m.warning > 0 or m.kind == "tether"))]
        if self.root_owner is owner:
            self.root_owner, self.root_left = None, 0

    def line_end(self, origin, target, length=7):
        direction = (target - origin).unit()
        end = origin
        for i in range(1, round(length / .1) + 1):
            point = origin + direction * (i * .1)
            if not self.world.walkable(point, .3):
                break
            end = point
        return end

    def warn(self, kind, owner, pos, warning=1.5, life=.2, radius=.75, end=None, strength=0, points=()):
        if self.finished or len(self.mechanics) >= MECHANIC_CAP or not self.world.walkable(pos, .25):
            return False
        if kind in FORCES and (self.rooted or any(m.kind in FORCES or m.kind == "grasp" for m in self.mechanics)):
            return False
        if kind == "grasp" and (self.rooted or any(m.kind in FORCES or m.kind == "grasp" for m in self.mechanics)
                                 or any(z.contains(pos, 1) for z in self.zones)):
            return False
        warning = max(warning, self.world.player.stasis + self.world.player.cast_time + 1)
        mechanic = VoidMechanic(kind, owner, pos, warning, life, radius, end, strength, points=points)
        self.mechanics.append(mechanic)
        self.world._record("void_mechanic_warning", attack=NAMES[kind], source=owner.kind,
                           warning_seconds=warning / owner.attack_rate, position=self.world._point(pos))
        if owner is self.boss:
            self.world.announce(NAMES[kind] + ": " + {
                "lash": "Sidestep the locked gold tentacle lanes.",
                "gaze": "Watch the beam sweep. Move out of its path.",
                "chorus": "Tentacles strike the marked circles in sequence.",
                "call_anchor": "Destroy the emerging anchor to stop its pull.",
                "communion": "Break or freeze the channeling wizards to expose the Oracle.",
                "convergence": "Move outward before the pull; avoid the central core.",
                "rejection": "Move inward before the outward pulse.",
                "orbit": "Step through the gaps between the orbiting fragments.",
                "well": "Leave the star before its final collapse.",
            }[kind])
        return True

    def spawn_at(self, point, kind, *, role="", lifetime=20):
        w = self.world
        if (len(w.enemies) >= POPULATION_CAP or not w.walkable(point, .45)
                or (point - w.player.pos).length() < 2
                or any((point - e.pos).length() < 1 for e in w.enemies)):
            return None
        return w.make_enemy(point, kind, spawn_phase=3, summoned=True, summon_life=lifetime,
                            cooldown=1.5, boss_role=role,
                            species_id="oracle_channeler" if role else kind,
                            boss_name="Oracle Channeler" if role else "")

    def activate_boss(self):
        w = self.world
        chosen = self.boss_arrival_positions()
        if len(chosen) < 3:
            return False
        w.phase, w.intermission, w._phase_resolved = 3, 0, False
        self.zones.clear()
        self.mechanics.clear()
        self.root_owner, self.root_left = None, 0
        kind = "oracle" if w.level == 7 else "astronomer"
        self.boss = w.make_enemy(chosen[0], kind, boss_role="boss", species_id=kind,
                                 boss_name=DEPTH_STATS[kind][0], spawn_phase=3, cooldown=2)
        w.boss_started = True
        if w.level == 7:
            for point in chosen[1:]:
                self.spawn_at(point, "thrall", role="channeler", lifetime=24)
            self.guard_cycles = 1
        w._record("phase_start", encounter=self.boss.name, spawner_count=0)
        w.announce(w.level_data.phase_lines[2])
        w.events.append("phase")
        return True

    def _remove(self, mechanic):
        if mechanic in self.mechanics:
            self.mechanics.remove(mechanic)
            if mechanic.owner is self.boss and not any(m.owner is self.boss for m in self.mechanics):
                self.boss.recovery = max(self.boss.recovery, 1.3)
                self.boss.cooldown = max(self.boss.cooldown, 1.3)

    def update(self, dt):
        super().update(dt)
        w = self.world
        if self.finished or w.state != "playing":
            return
        self.root_left = max(0, self.root_left - dt)
        if not self.rooted:
            self.root_owner, self.root_left = None, 0
        for m in self.mechanics[:]:
            if m not in self.mechanics:
                continue
            if m.owner not in w.enemies and not (m.kind == "well" and m.warning <= 0):
                self._remove(m)
                continue
            if self.rooted and m.kind in ("lash", "chorus", "gaze"):
                if m.kind == "gaze":
                    self._remove(m)
                else:
                    m.warning = max(m.warning, 1)
                continue
            if m.warning > 0:
                if m.owner.frozen > 0:
                    self._remove(m)
                    continue
                m.warning -= dt * m.owner.attack_rate
                if m.warning > 0:
                    continue
                w._record("void_mechanic_active", attack=NAMES[m.kind], duration=m.life)
            m.elapsed += dt
            m.life -= dt
            if m.kind in ("lash", "grasp", "chorus") and not m.fired:
                m.fired = True
                if (m.contains(w.player.pos, .23) and w._line_clear(m.pos, w.player.pos)
                        and w._line_clear(m.owner.pos, w.player.pos)):
                    hit = w._hurt_player(DAMAGE[m.kind], source=m.owner.kind, attack=NAMES[m.kind], attacker=m.owner)
                    if hit and m.kind == "grasp" and w.state == "playing":
                        self.root_owner, self.root_left = m.owner, ROOT_DURATION
                        w.selected = m.owner
                        w.announce("Grasped! Attack or freeze the grasping tentacle. You can still cast spells.")
            elif m.kind in FORCES:
                if m.contains(w.player.pos) and not self.rooted and w._line_clear(m.pos, w.player.pos):
                    force_player(w, m.pos, m.strength, dt, outward=m.kind == "rejection")
                if m.kind == "convergence" and (w.player.pos - m.pos).length() < 1.5:
                    w._hurt_player(DAMAGE["convergence"], source=m.owner.kind, attack=NAMES[m.kind], attacker=m.owner)
                if m.kind == "well" and m.life <= 0 and (w.player.pos - m.pos).length() < 1.3 and w._line_clear(m.pos, w.player.pos):
                    w._hurt_player(DAMAGE["well"], source=m.owner.kind, attack=NAMES[m.kind], attacker=m.owner)
            elif m.kind == "gaze":
                beam = VoidMechanic("gaze", m.owner, m.pos, 0, .1, .3, gaze_end(m))
                if beam.contains(w.player.pos, .23) and w._line_clear(m.pos, w.player.pos):
                    w._hurt_player(DAMAGE["gaze"], source=m.owner.kind, attack=NAMES[m.kind], attacker=m.owner)
            elif m.kind == "orbit":
                if any((p - w.player.pos).length() < .65 for p in orbit_points(m)):
                    w._hurt_player(DAMAGE["orbit"], source=m.owner.kind, attack=NAMES[m.kind], attacker=m.owner)
            elif m.kind in ("call_anchor", "communion") and not m.fired:
                m.fired = True
                for point in m.points or (m.pos,):
                    if m.kind == "communion":
                        if sum(e.boss_role == "channeler" for e in w.enemies) < 2:
                            self.spawn_at(point, "thrall", role="channeler", lifetime=24)
                    elif sum(e.kind == "anchor" and e.summoned for e in w.enemies) < 2:
                        self.spawn_at(point, "anchor", lifetime=16)
            if w.state == "dead":
                return
            if m.life <= 0:
                self._remove(m)

    def update_enemy(self, enemy, dt):
        w = self.world
        if self.finished:
            return
        if enemy.kind not in DEPTH_STATS:
            return super().update_enemy(enemy, dt)
        enemy.recovery = max(0, enemy.recovery - dt * enemy.attack_rate)
        if enemy.recovery > 0:
            return
        if enemy is self.boss:
            self.stage = 1 + sum(enemy.hp / enemy.max_hp <= value for value in (2 / 3, 1 / 3))
            if enemy.cooldown <= 0:
                self.boss_attack(enemy)
            return
        distance = (w.player.pos - enemy.pos).length()
        if enemy.kind == "star_fragment":
            if enemy.action != "orbit":
                enemy.action, enemy.action_time = "orbit", 0
                enemy.attack_origin = enemy.pos - Vec(1.4, 0)
            normal_patch = .5 if enemy.patch_time > 0 else 1
            speed = enemy.move_speed / normal_patch * w.enemy_move_factor(enemy) * (.6 if enemy.chilled > 0 else 1)
            enemy.action_time += dt * speed / 1.4
            point = enemy.attack_origin + Vec(cos(enemy.action_time), sin(enemy.action_time)) * 1.4
            if w.walkable(point, .3):
                enemy.pos = point
            if (enemy.pos - w.player.pos).length() < .6:
                w._hurt_player(DAMAGE["fragment"], source=enemy.kind, attack="Orbiting Fragment", attacker=enemy)
            return
        if enemy.kind == "thrall":
            if enemy.action == "bolt_warning":
                enemy.action_time -= dt * enemy.attack_rate
                if enemy.action_time <= 0:
                    if w._line_clear(enemy.pos, enemy.attack_origin):
                        w.enemy_bolt(enemy, (enemy.attack_origin - enemy.pos).unit(), 3.8, "arcane", 3)
                    enemy.action, enemy.cooldown = "", 3.2
            elif (enemy.cooldown <= 0 and distance <= 7 and w._line_clear(enemy.pos, w.player.pos)
                  and sum(e.action == "bolt_warning" for e in w.enemies) < 2):
                enemy.action, enemy.action_time, enemy.attack_origin = "bolt_warning", .95, w.player.pos
            elif enemy.boss_role != "channeler":
                if distance > 5:
                    w._move_enemy(enemy, dt)
                elif distance < 2.5:
                    w._move_enemy(enemy, dt, (enemy.pos - w.player.pos).unit())
            return
        if enemy.cooldown > 0 or distance > 7 or not w._line_clear(enemy.pos, w.player.pos):
            if enemy.kind == "gravity_adept" and distance > 5:
                w._move_enemy(enemy, dt)
            return
        started = False
        if enemy.kind == "lasher":
            started = self.warn("lash", enemy, enemy.pos, 1.4, .2, .4,
                                self.line_end(enemy.pos, w.player.pos))
        elif enemy.kind == "grasper":
            started = self.warn("grasp", enemy, w.player.pos, 1.5, .2, .75)
        elif enemy.kind == "anchor":
            if not any(m.owner is enemy for m in self.mechanics):
                started = self.warn("tether", enemy, enemy.pos, 1.6, 4, 7, strength=.9)
                if started:
                    self.add_darkness(enemy.pos, enemy, warning=1.6, life=4.5, radius=.8)
        elif enemy.kind == "gravity_adept":
            started = self.warn("well", enemy, w.player.pos, 1.6, 2.4, 2.2, strength=.85)
        elif enemy.kind == "repulsor":
            started = self.warn("rejection", enemy, enemy.pos, 1.6, .8, 5, strength=1.5)
        if started:
            enemy.cooldown = 7 if enemy.kind in ("anchor", "gravity_adept") else 5

    def boss_attack(self, boss):
        w = self.world
        # Finish a major pattern before starting another. Recovery leaves a
        # neutral interval; ordinary enemies still have their own readable casts.
        if any(m.owner is boss for m in self.mechanics):
            return
        if boss.kind == "oracle":
            if self.stage > self.guard_cycles and not any(e.boss_role == "channeler" for e in w.enemies):
                points = (boss.pos + Vec(-3, 1), boss.pos + Vec(3, 1))
                if self.warn("communion", boss, boss.pos, 1.8, .2, points=points):
                    self.guard_cycles += 1
                    boss.cooldown = 3.5
                return
            attack = ("gaze", "chorus", "call_anchor")[self.sequence % 3]
            if attack == "gaze":
                if self.rooted:
                    return
                started = self.warn(attack, boss, boss.pos, 1.7, 1.8, .3,
                                    self.line_end(boss.pos, w.player.pos, 8))
            elif attack == "chorus":
                if self.mechanics or self.rooted:
                    return
                started = False
                for i, offset in enumerate((Vec(), Vec(2.2, 0), Vec(-2.2, 0))):
                    point = w.player.pos + offset
                    if w.walkable(point, .8):
                        started = self.warn(attack, boss, point, 1.5 + i * .6, .2, .8) or started
            else:
                candidates = (Vec(4.5, 8.5), Vec(12.5, 8.5), Vec(8.5, 11.5))
                point = next((p for p in candidates if w.walkable(p, .5)
                              and (p - w.player.pos).length() >= 3
                              and all((p - e.pos).length() >= 1.2 for e in w.enemies)), None)
                started = point is not None and self.warn(attack, boss, point, 1.8, .2)
            if started:
                self.sequence += 1
                boss.cooldown = 5
        else:
            if any(m.kind in FORCES for m in self.mechanics):
                return
            attack = ("convergence", "rejection", "orbit", "well")[self.sequence % 4]
            if attack == "well":
                started = self.warn(attack, boss, w.player.pos, 1.8, 2.5, 2.2, strength=.9)
                duration = 4.3
            elif attack == "orbit":
                started = self.warn(attack, boss, boss.pos, 1.8, 4.5, 3.5)
                duration = 6.3
            else:
                life = 3 if attack == "convergence" else 1.2
                started = self.warn(attack, boss, boss.pos, 1.8, life, 14,
                                    strength=1.35 if attack == "convergence" else 2.2)
                duration = 1.8 + life
                if started and self.stage >= 2 and not any(m.kind == "orbit" for m in self.mechanics):
                    self.warn("orbit", boss, boss.pos, 2.1, life, 3.5)
                    duration = max(duration, 2.1 + life)
            if started:
                self.sequence += 1
                boss.cooldown = duration + 1.3

    def cleanup(self, clear_projectiles=True):
        super().cleanup(clear_projectiles)
        self.mechanics.clear()
        self.root_owner, self.root_left = None, 0
