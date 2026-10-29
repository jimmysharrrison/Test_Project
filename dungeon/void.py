"""Reusable void ground zones and the first breach's authored combat.

Warnings belong to a caster and can be interrupted. Released darkness is an
independent, expiring field. All damage uses the normal armor/Prison rules.
"""
from dataclasses import dataclass
from math import cos

from .geometry import Vec
from .combat_values import scaled_damage

VOID_KINDS = ("voidling", "binder", "voidwalker", "lasher", "grasper", "anchor", "thrall",
              "oracle", "gravity_adept", "repulsor", "star_fragment", "astronomer",
              "rift_warden", "chronal_scholar", "dimensional_anchor", "hourless_breach", "devourer")
VOID_HEALTH = 2200
VOID_FREEZE_CAP = .55
VOID_FROST_RESISTANCE = 3.5
ZONE_CAP = 4
POPULATION_CAP = 12
SUMMON_CAP = 4
DARK_DAMAGE = 10
DARK_GRACE = .35
BINDER_WARNING = 1.5
BINDER_INTERVAL = 5.5
LUNGE_DAMAGE = 24
SWEEP_DAMAGE = 20
LUNGE_REACH = 5.5
LUNGE_SPEED = 7
LUNGE_WARNING = 1.2
SWEEP_RADIUS = 2.4
SWEEP_WARNING = 1.3
SWEEP_COSINE = cos(1.05)
DISCHARGE_DAMAGE = 18
DISCHARGE_ENEMY_DAMAGE = 30
PILLARS = (Vec(5.5, 4.5), Vec(11.5, 4.5))


@dataclass(slots=True)
class GroundZone:
    pos: Vec
    owner: object
    warning: float = BINDER_WARNING
    life: float = 4
    radius: float = 1
    kind: str = "darkness"
    exposure: float = 0
    end: Vec | None = None

    def contains(self, point, padding=0):
        if self.end is not None:
            delta, offset = self.end - self.pos, point - self.pos
            fraction = max(0, min(1, (offset.x * delta.x + offset.y * delta.y) / max(.001, delta.length() ** 2)))
            return (offset - delta * fraction).length() < self.radius + padding
        return (point - self.pos).length() < self.radius + padding


def in_sweep(origin, direction, point, padding=0):
    offset = point - origin
    distance = offset.length()
    return distance < SWEEP_RADIUS + padding and (distance < .25 or
        (offset.x * direction.x + offset.y * direction.y) / distance >= SWEEP_COSINE)


def interrupt_void(world, enemy):
    """Freezing cancels a committed attack; active darkness keeps its lifetime."""
    if enemy.action and enemy.kind != "star_fragment":
        enemy.action = ""
        enemy.action_time = 0
        enemy.cooldown = max(enemy.cooldown, 1.5)
        enemy.recovery = max(enemy.recovery, .8)
    if world.void:
        world.void.zones[:] = [z for z in world.void.zones if not (z.owner is enemy and z.warning > 0)]
        if hasattr(world.void, "interrupt"):
            world.void.interrupt(enemy)


class VoidFloor:
    def __init__(self, world):
        self.world = world
        self.zones = []
        self.boss = None
        self.stage = 1
        self.broken_pillars = 0
        self.sequence = 0
        self.finished = False
        self.rage_hits = set()
        self.discharge_in = 5
        self.discharge_index = 0

    def add_darkness(self, pos, owner, *, warning=BINDER_WARNING, life=4, radius=1):
        world = self.world
        fields = [z for z in self.zones if z.kind == "darkness"]
        if (len(fields) >= ZONE_CAP or not world.walkable(pos, radius + .25)
                or any((pos - z.pos).length() < radius + z.radius + .6 for z in fields)):
            return False
        # Small separated circles in this open room leave lanes on every side.
        # Account for an already committed player cast/Prison before activation.
        warning = max(warning, world.player.cast_time + world.player.stasis + .8)
        self.zones.append(GroundZone(pos, owner, warning, life, radius))
        world._record("void_zone_warning", source=owner.kind, position=world._point(pos), warning_seconds=warning)
        return True

    def boss_arrival_positions(self):
        world = self.world
        if len(world.enemies) >= POPULATION_CAP:
            return []
        candidates = [Vec(x + .5, y + .5) for y in range(2, 15) for x in range(2, 15)]
        candidates.sort(key=lambda p: ((p - Vec(8.5, 5.5)).length(), p.x, p.y))
        chosen = []
        for point in candidates:
            if (world.walkable(point, .55) and (point - world.player.pos).length() >= 3
                    and all((point - e.pos).length() >= 1 for e in world.enemies)
                    and all((point - p).length() >= 2 for p in chosen)
                    and all(not z.contains(point, .7) for z in self.zones)):
                chosen.append(point)
                if len(chosen) == 3:
                    break
        return chosen

    def activate_boss(self):
        world = self.world
        chosen = self.boss_arrival_positions()
        if len(chosen) < 3:
            return False
        world.phase, world.intermission, world._phase_resolved = 3, 0, False
        self.zones[:] = [z for z in self.zones if z.kind != "discharge"]
        world.boss_started = True
        self.boss = world.make_enemy(chosen[0], "voidwalker", boss_role="boss",
                                     boss_name="The Unbound Voidwalker", species_id="voidwalker",
                                     spawn_phase=3, cooldown=1.5)
        for point in chosen[1:]:
            if len(world.enemies) < POPULATION_CAP:
                world.make_enemy(point, "binder", spawn_phase=3, cooldown=2)
        world._record("phase_start", encounter=self.boss.name, spawner_count=0)
        world.announce("The Unbound Voidwalker: sidestep its marked lunge; leave the sweep. It attacks its binders too!")
        world.events.append("phase")
        return True

    def update(self, dt):
        world = self.world
        if not self.finished and world.level == 6 and world.phase < 3:
            self.discharge_in -= dt
            if self.discharge_in <= 0:
                origin = PILLARS[self.discharge_index % len(PILLARS)]
                direction = (Vec(8.5, 10.5) - origin).unit()
                end = origin
                for i in range(1, 61):
                    point = origin + direction * (i * .1)
                    if not world.walkable(point, .4):
                        break
                    end = point
                self.zones.append(GroundZone(origin, None, 1.6 + world.player.stasis,
                                             .35, .4, "discharge", end=end))
                self.discharge_index += 1
                self.discharge_in = 8
                world.announce("Containment discharge: leave the gold lane. The beam can hit escaped creatures too!")
                world._record("containment_discharge", origin=world._point(origin), end=world._point(end))
        for zone in self.zones[:]:
            if zone not in self.zones:
                continue
            if zone.warning > 0:
                if zone.owner is not None and (zone.owner not in world.enemies or zone.owner.frozen > 0):
                    self.zones.remove(zone)
                    continue
                if zone.owner is not None:
                    world.refresh_patch_status(zone.owner)
                zone.warning -= dt * (zone.owner.attack_rate if zone.owner is not None else 1)
                if zone.warning > 0:
                    continue
                world._record("void_zone_active", kind=zone.kind, position=world._point(zone.pos), duration=zone.life)
                if zone.kind == "discharge":
                    if zone.contains(world.player.pos, .23):
                        world._hurt_player(DISCHARGE_DAMAGE, source="containment", attack="containment_discharge")
                    if world.state == "dead":
                        return
                    for enemy in world.enemies[:]:
                        if zone.contains(enemy.pos, .3):
                            world._hit(enemy, DISCHARGE_ENEMY_DAMAGE, spell="containment_discharge", environmental=True)
                if zone.kind == "summon":
                    if (sum(e.summoned for e in world.enemies) < SUMMON_CAP
                            and len(world.enemies) < POPULATION_CAP
                            and world.walkable(zone.pos, .4)
                            and (zone.pos - world.player.pos).length() >= 2
                            and all((zone.pos - e.pos).length() >= .8 for e in world.enemies)):
                        world.make_enemy(zone.pos, "voidling", spawn_phase=3, summoned=True,
                                         summon_life=18, cooldown=1)
                    self.zones.remove(zone)
                    continue
            zone.life -= dt
            if zone.kind == "darkness" and zone.contains(world.player.pos, .23):
                zone.exposure += dt
                if zone.exposure >= DARK_GRACE:
                    world._hurt_player(DARK_DAMAGE, source="void", attack="darkness")
                    if world.state == "dead":
                        return
            else:
                zone.exposure = 0
            if zone.life <= 0:
                self.zones.remove(zone)
        for enemy in world.enemies[:]:
            if enemy.summoned:
                enemy.summon_life -= dt
                if enemy.summon_life <= 0:
                    world.enemies.remove(enemy)
                    if world.selected is enemy:
                        world.selected = None

    def begin_attack(self, enemy, attack, target):
        world = self.world
        self.rage_hits.clear()
        enemy.action = attack
        enemy.attack_origin = enemy.pos
        enemy.attack_direction = (target - enemy.pos).unit()
        enemy.action_time = LUNGE_WARNING if attack == "lunge_warning" else SWEEP_WARNING
        if attack == "shatter":
            enemy.attack_origin = PILLARS[self.broken_pillars]
            enemy.action_time = 1.6
            for offset in (Vec(-1.5, 1), Vec(1.5, 1)):
                point = enemy.attack_origin + offset
                if world.walkable(point, .4):
                    self.zones.append(GroundZone(point, enemy, 1.6, .1, .55, "summon"))
        world._record("boss_attack", source=enemy.kind, attack=attack,
                     warning_seconds=enemy.action_time / enemy.attack_rate)
        world.announce({"lunge_warning": "Rift Lunge: sidestep the gold lane!",
                        "sweep": "Rending Sweep: leave the marked fan!",
                        "shatter": "Shatter the Chains: the pillar is breaking. Watch the summon rings!"}[attack])

    def update_enemy(self, enemy, dt):
        world = self.world
        if self.finished:
            return
        enemy.recovery = max(0, enemy.recovery - dt * enemy.attack_rate)
        if enemy.recovery > 0:
            return
        distance = (world.player.pos - enemy.pos).length()
        if enemy.kind == "binder":
            if enemy.cooldown <= 0 and distance <= 7 and world._line_clear(enemy.pos, world.player.pos):
                if self.add_darkness(world.player.pos, enemy):
                    enemy.cooldown = BINDER_INTERVAL
                    world._record("enemy_attack", source="binder", attack="binding_darkness", stage="warning")
            elif distance > 4:
                world._move_enemy(enemy, dt)
            elif distance < 2.5:
                world._move_enemy(enemy, dt, (enemy.pos - world.player.pos).unit())
            return
        if enemy.kind == "voidling":
            if distance > .5:
                world._move_enemy(enemy, dt)
            elif enemy.cooldown <= 0 and world._hurt_player(scaled_damage(8, enemy.level), source=enemy.kind, attack="claw", attacker=enemy):
                enemy.cooldown = 1.1
            return
        if self.finished:
            return
        self.stage = 1 + sum(enemy.hp / enemy.max_hp <= threshold for threshold in (2 / 3, 1 / 3))
        if enemy.action:
            rate = world.enemy_move_factor(enemy) * (.6 if enemy.chilled > 0 else 1) if enemy.action == "lunge" else enemy.attack_rate
            enemy.action_time -= dt * rate
            if enemy.action == "lunge":
                travel = min(LUNGE_SPEED * dt * rate, max(0, LUNGE_REACH - (enemy.pos - enemy.attack_origin).length()))
                blocked = False
                while travel > 1e-8:
                    step = min(.1, travel)
                    candidate = enemy.pos + enemy.attack_direction * step
                    if not world.walkable(candidate, .4):
                        blocked = True
                        break
                    enemy.pos = candidate
                    if (enemy.pos - world.player.pos).length() < .75:
                        world._hurt_player(LUNGE_DAMAGE, source=enemy.kind, attack="Rift Lunge", attacker=enemy)
                    self.hurt_binders(enemy, lambda p: (p - enemy.pos).length() < .8, LUNGE_DAMAGE)
                    travel -= step
                if blocked or enemy.action_time <= 0 or (enemy.pos - enemy.attack_origin).length() >= LUNGE_REACH - .01:
                    if self.stage >= 2 and (enemy.pos - world.player.pos).length() > 1.3:
                        self.add_darkness(enemy.pos, enemy, warning=.8, life=3.5, radius=.65)
                    self.recover(enemy, 2)
                return
            if enemy.action_time > 0:
                return
            if enemy.action == "lunge_warning":
                enemy.action, enemy.action_time = "lunge", LUNGE_REACH / LUNGE_SPEED
                return
            if enemy.action == "sweep":
                contains = lambda p: in_sweep(enemy.attack_origin, enemy.attack_direction, p, .23)
                if contains(world.player.pos) and world._line_clear(enemy.pos, world.player.pos):
                    world._hurt_player(SWEEP_DAMAGE, source=enemy.kind, attack="Rending Sweep", attacker=enemy)
                self.hurt_binders(enemy, contains, SWEEP_DAMAGE)
            elif enemy.action == "shatter":
                self.broken_pillars += 1
                self.add_darkness(enemy.attack_origin, enemy, warning=.8, life=3, radius=1.1)
                world._record("containment_pillar_broken", count=self.broken_pillars)
            self.recover(enemy, 1.6 if self.stage == 3 else 2)
            return
        if self.broken_pillars < self.stage - 1:
            self.begin_attack(enemy, "shatter", world.player.pos)
            return
        binders = [e for e in world.enemies if e.kind == "binder" and world._line_clear(enemy.pos, e.pos)]
        target = min([world.player, *binders], key=lambda e: (e.pos - enemy.pos).length())
        target_distance = (target.pos - enemy.pos).length()
        if enemy.cooldown <= 0 and world._line_clear(enemy.pos, target.pos):
            # Alternate when close so both attacks remain represented.
            attack = "sweep" if target_distance < SWEEP_RADIUS and self.sequence % 2 else "lunge_warning"
            self.sequence += 1
            self.begin_attack(enemy, attack, target.pos)
        elif target_distance > 1:
            world._move_enemy(enemy, dt, (target.pos - enemy.pos).unit() if target is not world.player else None)

    def hurt_binders(self, boss, contains, damage):
        for other in self.world.enemies[:]:
            if other.kind == "binder" and other not in self.rage_hits and contains(other.pos) and self.world._line_clear(boss.pos, other.pos):
                self.rage_hits.add(other)
                self.world._hit(other, damage, spell="voidwalker_rage", environmental=True)

    def recover(self, enemy, duration):
        enemy.action, enemy.action_time = "", 0
        enemy.recovery = duration
        enemy.cooldown = 1.5 if self.stage < 3 else 1

    def cleanup(self, clear_projectiles=True):
        self.finished = True
        self.zones.clear()
        if self.boss:
            self.boss.action = ""
        self.world.enemies[:] = [e for e in self.world.enemies if not e.summoned]
        if clear_projectiles:
            self.world.projectiles[:] = [p for p in self.world.projectiles if not p.hostile]
        if self.world.selected and getattr(self.world.selected, "summoned", False):
            self.world.selected = None
