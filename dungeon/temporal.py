"""The Fractured Hour: portal tells, single echoes, stasis and an R survival puzzle.

The reserved Prison charge ignores mana/cooldown/cast recovery only during its
explicit cue. A prompt cast always covers the entire pulse. Checkpoint retries
bank prior loot and never refund shops or generate attempt-specific loot.
"""
from dataclasses import dataclass

from .abilities import ABILITIES
from .geometry import Vec
from .combat_values import scaled_damage
from .void_depths import VoidDepths, force_player

TEMPORAL_STATS = {
    "rift_warden": ("Time-Displaced Warden", 46, 1.2, 9),
    "chronal_scholar": ("Chronal Scholar", 42, 1, 0),
    "dimensional_anchor": ("Dimensional Anchor", 300, 0, 0),
    "hourless_breach": ("The Hourless Breach", 3, 0, 0),
}
FIXED_HEALTH = {kind: TEMPORAL_STATS[kind][1] for kind in ("dimensional_anchor", "hourless_breach")}
PORTAL_WARNING = 1.3
SHOT_WARNING = .95
ECHO_WARNING = 1.3
FIELD_WARNING = 1.3
FIELD_LIFE = 2
FIELD_RADIUS = 1.6
FIELD_CAP = 2
ECHO_CAP = 4
SURVIVAL_WARNING = .45
SURVIVAL_PULL = 1.1
SURVIVAL_SECONDS = SURVIVAL_WARNING + SURVIVAL_PULL
CHECKPOINT_POS = Vec(8.5, 12.5)
ANCHORS = (Vec(5.5, 6.5), Vec(11.5, 6.5), Vec(8.5, 8.5))
ARRIVALS = (Vec(4.5, 5.5), Vec(12.5, 5.5), Vec(4.5, 9.5), Vec(12.5, 9.5))


@dataclass(slots=True)
class TemporalField:
    pos: Vec
    owner: object
    warning: float = FIELD_WARNING
    life: float = FIELD_LIFE
    radius: float = FIELD_RADIUS

    def contains(self, point):
        return (point - self.pos).length() <= self.radius


@dataclass(slots=True)
class TemporalEcho:
    pos: Vec
    direction: Vec
    damage: int
    warning: float = ECHO_WARNING


@dataclass(slots=True)
class TemporalPortal:
    pos: Vec
    kind: str = "rift_warden"
    warning: float = PORTAL_WARNING


class TemporalFloor(VoidDepths):
    def __init__(self, world):
        super().__init__(world)
        self.fields = []
        self.echoes = []
        self.portals = []
        self.stage_name = "waves"
        self.stage_left = 0.0
        self.completed_anchors = 0
        self.active_anchor = None
        self.lesson_complete = False
        self.practice_attempts = 0
        self.failures = 0
        self.free_prison = False
        self.frozen_scene_time = 0.0
        self.checkpoint_potions = 0

    @property
    def stopped(self):
        return self.stage_name in ("practice", "stopped_hour")

    @property
    def scene_time(self):
        return self.frozen_scene_time if self.stopped else self.world.time

    @property
    def checkpoint_active(self):
        return self.boss_started and not self.finished

    @property
    def boss_started(self):
        return self.boss is not None

    @property
    def harmless(self):
        return self.stage_name in ("demonstration", "practice", "practice_reset", "retry")

    @property
    def reserved_prison(self):
        return self.stopped and self.free_prison and not self.finished

    @property
    def protected(self):
        # The environmental encounter uses its own anchor progress display.
        return False

    def can_damage(self, target, spell):
        if target.kind == "hourless_breach":
            return spell == "seal_breach" and self.completed_anchors == 3
        if target.kind == "dimensional_anchor":
            return target is self.active_anchor and self.stage_name == "exposure"
        return not self.harmless

    def shot_stopped(self, shot):
        return self.stopped or self.stage_name in ("demonstration", "practice_reset", "retry") or any(
            f.warning <= 0 and f.life > 0 and f.contains(shot.pos) for f in self.fields)

    def interrupt(self, owner):
        super().interrupt(owner)
        self.fields[:] = [f for f in self.fields if not (f.owner is owner and f.warning > 0)]
        if owner.kind in ("rift_warden", "chronal_scholar"):
            owner.signature_timer = max(owner.signature_timer, 2)

    def _clear_attempt(self):
        w = self.world
        self.fields.clear()
        self.echoes.clear()
        self.portals.clear()
        self.zones.clear()
        self.mechanics.clear()
        self.root_owner, self.root_left = None, 0
        w.enemies[:] = [self.boss] if self.boss and self.boss.hp > 0 else []
        w.projectiles.clear()
        w.ice_patches.clear()
        w.rime_trails.clear()
        w._prison_patch = None
        w.selected = None
        w.stop()
        self.active_anchor = None

    def _restore_resources(self):
        p = self.world.player
        p.pos = CHECKPOINT_POS
        p.hp, p.mana = p.max_hp, p.max_mana
        p.potions = self.checkpoint_potions
        p.cooldowns = dict.fromkeys(ABILITIES, 0.0)
        p.stasis = p.cast_time = p.slow_time = p.slow_pulse = 0
        p.stasis_frost_multiplier = 1
        p.invincible = 1
        self.world._record("temporal_resources_restored", hp=p.hp, mana=p.mana, potions=p.potions)

    def activate_boss(self):
        w = self.world
        if self.boss_started:
            return False
        if SURVIVAL_SECONDS >= ABILITIES["r"].duration:
            raise ValueError("Stopped Hour must be shorter than Glacial Prison")
        # Bank already-earned wave loot before establishing a repeatable boss
        # checkpoint; later portal enemies/anchors award no attempt loot.
        w._collect_remaining_rewards()
        w.pickups.clear()
        self.checkpoint_potions = w.player.potions
        self.boss = w.make_enemy(Vec(8.5, 4.5), "hourless_breach", boss_role="boss",
                                 boss_name="The Hourless Breach", species_id="hourless_breach", spawn_phase=3)
        self._clear_attempt()
        self._restore_resources()
        w.phase, w.intermission, w._phase_resolved = 3, 0, False
        w.boss_started = True
        self.stage_name, self.stage_left = "demonstration", 3.2
        w.announce("A warden anchors in ice. When time stops, R / Glacial Prison protects you from the breach.")
        w._record("temporal_checkpoint", potions=self.checkpoint_potions, position=w._point(CHECKPOINT_POS))
        w._record("phase_start", encounter=self.boss.name, spawner_count=0)
        w.events.append("phase")
        return True

    def _prime_prison(self, practice=False):
        w, p = self.world, self.world.player
        p.cooldowns["r"] = 0
        p.mana = min(p.max_mana, max(p.mana, p.mana_cost_for("r")))
        p.cast_time = 0
        p.slow_time = p.slow_pulse = 0
        # A Prison cast just before the cue is also a valid answer: extend it
        # to a full duration rather than forcing another key press mid-stasis.
        self.free_prison = p.stasis <= 0
        if p.stasis > 0:
            p.stasis = max(p.stasis, ABILITIES["r"].duration)
        self.stage_name = "practice" if practice else "stopped_hour"
        self.stage_left = SURVIVAL_SECONDS
        self.frozen_scene_time = w.time
        w.announce(("SAFE PRACTICE" if practice else "STOPPED HOUR") +
                   ": R restored. Cast Glacial Prison NOW to anchor yourself! Reserved cast costs no mana.")
        w._record("prison_charge_restored", practice=practice, pulse_seconds=SURVIVAL_SECONDS,
                  prison_seconds=ABILITIES["r"].duration, already_anchored=p.stasis > 0)

    def _start_cycle(self):
        w = self.world
        self.stage_name, self.stage_left = "fracture", 4.2
        self.free_prison = False
        self.active_anchor = None
        # Previous-cycle guards are recalled, never counted as fresh deaths.
        w.enemies[:] = [e for e in w.enemies if not e.summoned]
        self.echoes.clear()
        self.fields.clear()
        self.portals = [TemporalPortal(ARRIVALS[(self.completed_anchors + i) % len(ARRIVALS)],
                                      "chronal_scholar" if i == 2 else "rift_warden")
                        for i in range(2 + (self.completed_anchors > 0))]
        w.announce(f"Fracture {self.completed_anchors + 1}/3: watch the portal exits. The next anchor opens shortly.")

    def fail(self, reason):
        if not self.checkpoint_active or self.stage_name == "retry":
            return
        w = self.world
        self.failures += 1
        w.player.achievement_run.retry()
        w.player.achievement_run.deaths += 1
        w.player.timing.eligible = False
        self._clear_attempt()
        w.player.hp = max(1, w.player.hp)
        w.player.stasis = 0
        self.free_prison = False
        self.stage_name, self.stage_left = "retry", 2
        w.announce("The breach takes the unanchored. Returning to the nearby boss checkpoint; resources will be restored.")
        w._record("temporal_checkpoint_failure", reason=reason, failures=self.failures)

    def actor_defeated(self, actor):
        if actor is self.active_anchor:
            self.active_anchor = None
            self.stage_name = "stop_pending"
            self.world.announce("Anchor broken. The hour is stopping — prepare Glacial Prison!")
            return True
        # Attempt-specific enemies cannot be farmed for gold, equipment or food.
        return self.checkpoint_active and actor is not self.boss

    def _pulse_update(self, dt):
        w = self.world
        self.stage_left = max(0, self.stage_left - dt)
        if self.stage_left < SURVIVAL_PULL:
            force_player(w, self.boss.pos, 4.5, dt)
        if self.stage_left > 1e-8:
            return
        anchored = w.player.stasis > 0
        self.free_prison = False
        if self.stage_name == "practice":
            self.practice_attempts += 1
            if anchored:
                self.lesson_complete = True
                self._clear_attempt()
                self._restore_resources()
                self.stage_name, self.stage_left = "lesson_passed", 1.5
                w.announce("Anchored! Glacial Prison defeats the pull. The checkpoint is ready; three real cycles remain.")
                w._record("temporal_lesson_passed", attempts=self.practice_attempts)
            else:
                w.player.pos = CHECKPOINT_POS
                w.projectiles.clear()
                self.stage_name, self.stage_left = "practice_reset", 1.3
                w.announce("Safe reset — no life lost. When the next cue appears, press R immediately to anchor in ice.")
                w._record("temporal_lesson_retry", attempts=self.practice_attempts)
        elif anchored:
            self.completed_anchors += 1
            self.boss.hp = max(1, 3 - self.completed_anchors)
            w._record("stopped_hour_survived", anchors=self.completed_anchors)
            if self.completed_anchors == 3:
                w._hit(self.boss, 3, spell="seal_breach", environmental=True)
            else:
                self.stage_name, self.stage_left = "recovery", 2
                w.announce(f"Stopped Hour survived — {self.completed_anchors}/3 anchors sealed. Reposition before the next fracture.")
        else:
            self.fail("unanchored_stopped_hour")

    def update(self, dt):
        w = self.world
        if self.finished:
            return
        if self.stopped:
            self._pulse_update(dt)
            return
        if self.stage_name in ("demonstration", "practice_reset", "lesson_passed", "retry", "recovery"):
            self.stage_left = max(0, self.stage_left - dt)
            if self.stage_left <= 1e-8:
                if self.stage_name in ("demonstration", "practice_reset"):
                    self._prime_prison(practice=True)
                elif self.stage_name == "retry":
                    self._clear_attempt()
                    self._restore_resources()
                    self.completed_anchors = 0
                    self.boss.hp = self.boss.max_hp
                    self._start_cycle()
                    w._record("temporal_checkpoint_restart", failures=self.failures)
                else:
                    self._start_cycle()
            return
        if self.stage_name == "stop_pending":
            self._prime_prison()
            return
        super().update(dt)
        if self.stage_name == "fracture":
            self.stage_left = max(0, self.stage_left - dt)
            if self.stage_left <= 1e-8:
                pos = ANCHORS[self.completed_anchors]
                self.active_anchor = w.make_enemy(pos, "dimensional_anchor", boss_role="anchor",
                                                  boss_name="Dimensional Anchor", species_id="dimensional_anchor", spawn_phase=3)
                self.stage_name = "exposure"
                w.selected = self.active_anchor
                w.announce("Dimensional Anchor exposed. Break it, then use R when Stopped Hour begins.")
        for portal in self.portals[:]:
            portal.warning -= dt
            if portal.warning <= 0:
                self.spawn_at(portal.pos, portal.kind, lifetime=25)
                self.portals.remove(portal)
        for field in self.fields[:]:
            if field.warning > 0:
                if field.owner not in w.enemies or field.owner.frozen > 0:
                    self.fields.remove(field)
                    continue
                field.warning -= dt * field.owner.attack_rate
            else:
                field.life -= dt
                if field.life <= 0:
                    self.fields.remove(field)
        for echo in self.echoes[:]:
            echo.warning -= dt
            if echo.warning <= 0:
                from .world import Projectile
                w.projectiles.append(Projectile(echo.pos + echo.direction * .4, echo.direction * 3.8,
                                               life=3, damage=echo.damage, hostile=True, spell="arcane", source="temporal_echo"))
                w._record("temporal_echo_release", position=w._point(echo.pos))
                self.echoes.remove(echo)

    def portal_destination(self, enemy):
        w = self.world
        points = ARRIVALS[enemy.telemetry_id % 4:] + ARRIVALS[:enemy.telemetry_id % 4]
        return next((p for p in points if (p - enemy.pos).length() >= 2 and w.walkable(p, .4)
                     and (p - w.player.pos).length() >= 3
                     and all(e is enemy or (p - e.pos).length() >= 1 for e in w.enemies)), None)

    def update_enemy(self, enemy, dt):
        if self.finished or self.stopped or self.harmless or self.stage_name == "lesson_passed":
            return
        if enemy.kind in FIXED_HEALTH:
            return
        if enemy.kind not in TEMPORAL_STATS:
            return super().update_enemy(enemy, dt)
        w = self.world
        distance = (w.player.pos - enemy.pos).length()
        enemy.signature_timer -= dt * enemy.attack_rate
        if enemy.action == "rift_warning":
            enemy.action_time -= dt * enemy.attack_rate
            if enemy.action_time <= 0:
                dest = enemy.attack_origin
                if (w.walkable(dest, .4) and (dest - w.player.pos).length() >= 2
                        and all(e is enemy or (dest - e.pos).length() >= 1 for e in w.enemies)):
                    enemy.pos = dest
                    w._record("warden_portal_arrival", target=w._actor_info(enemy))
                enemy.action, enemy.signature_timer, enemy.cooldown = "", 8, 1
            return
        if enemy.action == "time_shot":
            enemy.action_time -= dt * enemy.attack_rate
            if enemy.action_time <= 0:
                if w._line_clear(enemy.pos, enemy.attack_origin):
                    direction = (enemy.attack_origin - enemy.pos).unit()
                    w.enemy_bolt(enemy, direction, 3.8, "arcane", 3)
                    if len(self.echoes) < ECHO_CAP:
                        self.echoes.append(TemporalEcho(enemy.pos, direction,
                                                       scaled_damage(TEMPORAL_STATS["rift_warden"][3], w.level)))
                enemy.action, enemy.cooldown = "", 3.2
            return
        if enemy.signature_timer <= 0 and distance <= 8:
            point = self.portal_destination(enemy)
            if point is not None:
                enemy.action, enemy.action_time, enemy.attack_origin = "rift_warning", PORTAL_WARNING, point
                return
        if enemy.cooldown <= 0 and distance <= 7 and w._line_clear(enemy.pos, w.player.pos):
            if enemy.kind == "rift_warden":
                enemy.action, enemy.action_time, enemy.attack_origin = "time_shot", SHOT_WARNING, w.player.pos
            elif len(self.fields) < FIELD_CAP:
                self.fields.append(TemporalField(w.player.pos, enemy))
                enemy.cooldown = 6.5
            return
        if distance > 5:
            w._move_enemy(enemy, dt)
        elif distance < 2.5:
            w._move_enemy(enemy, dt, (enemy.pos - w.player.pos).unit())

    def cleanup(self, clear_projectiles=True):
        super().cleanup(clear_projectiles)
        self.fields.clear()
        self.echoes.clear()
        self.portals.clear()
        self.free_prison = False
        self.active_anchor = None
        self.stage_name = "complete"
