"""The stationary void finale reuses the preceding floors' forces and creatures.

Temporal support is limited to the wardens' own portals, echoes and fields.
The Floor 9 lesson, reserved R and checkpoint never run in this encounter.
"""
from dataclasses import dataclass
from math import cos, sin

from .geometry import Vec
from .temporal import TemporalFloor
from .void_depths import FORCES
from .void import POPULATION_CAP

MAW_HEALTH = 3600
MAW_STATS = {"devourer": ("The Threshold Devourer", MAW_HEALTH, 0, 0)}
BOSS_POS = Vec(8.5, 5.5)
MINION_CAP = 6
ARRIVAL_CAP = 3
SUMMON_WARNING = 2.0
SUMMON_LIFE = 26
RECOVERY = 1.5
PULL_WARNING = 2.0
PULL_STRENGTHS = (1.25, 1.5, 1.75)
PULL_LIVES = (2.5, 3, 3.5)
SUMMON_ROSTER = ("voidling", "thrall", "gravity_adept", "binder", "lasher", "rift_warden",
                 "grasper", "star_fragment", "chronal_scholar", "anchor", "repulsor")
ARRIVAL_POINTS = tuple(Vec(x, y) for x, y in ((4.5, 5.5), (12.5, 5.5), (4.5, 9.5), (12.5, 9.5),
                                           (6.5, 11.5), (10.5, 11.5), (4.5, 12.5), (12.5, 12.5)))


@dataclass(slots=True)
class VoidArrival:
    pos: Vec
    kind: str
    owner: object
    warning: float = SUMMON_WARNING


class MawFloor(TemporalFloor):
    def __init__(self, world):
        super().__init__(world)
        self.arrivals = []
        self.summon_index = 0
        self.last_pattern = ""

    @property
    def checkpoint_active(self):
        return False

    @property
    def reserved_prison(self):
        return False

    def actor_defeated(self, actor):
        return False

    def activate_boss(self):
        if self.boss_started:
            return False
        w = self.world
        # Recall wave survivors rather than bury the opening tells under them.
        # Earned drops and the mage's remaining combat resources stay intact.
        w.enemies.clear()
        w.selected = None
        w.projectiles.clear()
        self.zones.clear()
        self.mechanics.clear()
        self.fields.clear()
        self.echoes.clear()
        self.portals.clear()
        self.root_owner, self.root_left = None, 0
        self.boss = w.make_enemy(BOSS_POS, "devourer", boss_role="boss", species_id="devourer",
                                 boss_name="The Threshold Devourer", spawn_phase=3, cooldown=2.5)
        w.phase, w.intermission, w._phase_resolved, w.boss_started = 3, 0, False, True
        self.stage_name = "devourer"
        w._record("phase_start", encounter=self.boss.name, spawner_count=0)
        w.announce(w.level_data.phase_lines[2])
        w.events.append("phase")
        return True

    def interrupt(self, owner):
        super().interrupt(owner)
        self.arrivals[:] = [a for a in self.arrivals if a.owner is not owner]
        if owner is self.boss:
            owner.recovery = max(owner.recovery, RECOVERY)
            owner.cooldown = max(owner.cooldown, RECOVERY)

    def _summon(self, boss):
        w = self.world
        if self.arrivals:
            return False
        available = min(ARRIVAL_CAP, MINION_CAP - sum(e.summoned for e in w.enemies),
                        POPULATION_CAP - len(w.enemies))
        if available <= 0:
            return False
        chosen = []
        for point in ARRIVAL_POINTS:
            if (w.walkable(point, .5) and (point - w.player.pos).length() >= 3
                    and all((point - e.pos).length() >= 1.5 for e in w.enemies)
                    and all(not z.contains(point, 1) for z in self.zones)):
                chosen.append(point)
                if len(chosen) == available:
                    break
        if not chosen:
            return False
        warning = max(SUMMON_WARNING, w.player.stasis + w.player.cast_time + 1)
        for point in chosen:
            kind = SUMMON_ROSTER[self.summon_index % len(SUMMON_ROSTER)]
            self.summon_index += 1
            self.arrivals.append(VoidArrival(point, kind, boss, warning))
        boss.cooldown = warning + RECOVERY
        w.announce("Breach Communion: marked portals are opening. Clear the arrivals before the next gravity draw.")
        w._record("maw_summon_warning", kinds=[a.kind for a in self.arrivals], warning_seconds=warning / boss.attack_rate)
        return True

    def boss_attack(self, boss):
        w = self.world
        if (self.arrivals or any(m.owner is boss or m.kind in FORCES for m in self.mechanics)
                or self.rooted):
            return
        attack = ("summon", "pull", "slam", "lash")[self.sequence % 4]
        started = False
        if attack == "summon":
            started = self._summon(boss)
            # A full population must not stall the boss's entire attack cycle.
            if not started:
                self.sequence += 1
                boss.cooldown = .5
        elif attack == "pull":
            started = self.warn("convergence", boss, boss.pos, PULL_WARNING,
                                PULL_LIVES[self.stage - 1], 14, strength=PULL_STRENGTHS[self.stage - 1])
            boss.cooldown = PULL_WARNING + PULL_LIVES[self.stage - 1] + RECOVERY
        elif attack == "slam":
            # Locked circles, not homing strikes. Later stages add offset hits.
            for i, offset in enumerate((Vec(), Vec(2.4, 0), Vec(-2.4, 0))[:self.stage]):
                point = w.player.pos + offset
                if w.walkable(point, 1.1):
                    started = self.warn("chorus", boss, point, 1.8 + .45 * i, .2, 1.1) or started
            boss.cooldown = 1.8 + .45 * (self.stage - 1) + .2 + RECOVERY
        else:
            direction = (w.player.pos - boss.pos).unit()
            offsets = (0,) if self.stage == 1 else (-.35, .35) if self.stage == 2 else (-.5, 0, .5)
            for i, angle in enumerate(offsets):
                rotated = Vec(direction.x * cos(angle) - direction.y * sin(angle),
                              direction.x * sin(angle) + direction.y * cos(angle))
                end = self.line_end(boss.pos, boss.pos + rotated, 9)
                started = self.warn("lash", boss, boss.pos, 1.8 + .3 * i, .2, .4, end=end) or started
            boss.cooldown = 1.8 + .3 * (len(offsets) - 1) + .2 + RECOVERY
        if started:
            self.sequence += 1
            self.last_pattern = attack
            w._record("maw_pattern", attack=attack, health_stage=self.stage)
        elif attack != "summon":
            boss.cooldown = .35

    def update_enemy(self, enemy, dt):
        if enemy is self.boss:
            if self.finished:
                return
            enemy.recovery = max(0, enemy.recovery - dt * enemy.attack_rate)
            self.stage = 1 + sum(enemy.hp / enemy.max_hp <= threshold for threshold in (2 / 3, 1 / 3))
            if enemy.recovery <= 0 and enemy.cooldown <= 0:
                self.boss_attack(enemy)
            return
        super().update_enemy(enemy, dt)

    def update(self, dt):
        super().update(dt)
        if self.finished or self.world.state != "playing":
            return
        for arrival in self.arrivals[:]:
            if arrival.owner not in self.world.enemies or arrival.owner.frozen > 0:
                self.arrivals.remove(arrival)
                continue
            arrival.warning -= dt * arrival.owner.attack_rate
            if arrival.warning <= 0:
                if sum(e.summoned for e in self.world.enemies) < MINION_CAP:
                    spawned = self.spawn_at(arrival.pos, arrival.kind, lifetime=SUMMON_LIFE)
                    if spawned:
                        self.world._record("maw_summon_arrival", kind=arrival.kind, position=self.world._point(arrival.pos))
                self.arrivals.remove(arrival)
                if not self.arrivals:
                    self.boss.recovery = max(self.boss.recovery, RECOVERY)

    def cleanup(self, clear_projectiles=True):
        super().cleanup(clear_projectiles)
        self.arrivals.clear()
