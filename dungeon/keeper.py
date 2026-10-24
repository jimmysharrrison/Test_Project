"""The Keeper's persistent mechanics, movement certificates, and stage scheduler.

Warnings reserve reachable floor, not just a pretty safe marker. The scheduler
counts warnings, active spills/vines, and living specimens as major mechanics.
"""
from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import floor

from .geometry import Vec
from .combat_values import KEEPER_DAMAGE
from .navigation import neighbors


@dataclass(frozen=True, slots=True)
class KeeperTuning:
    health: int = 3000
    thresholds: tuple = (2 / 3, 1 / 3)
    summon_cap: int = 4
    summon_life: float = 20
    freeze_cap: float = .45
    frost_resistance: float = 3
    vine_life: float = 7
    vine_speed: float = .55
    nova_suppression: float = 4
    spill_life: float = 3.5
    warning_min: float = 2
    warning_max: float = 5
    reaction_margin: float = .8
    opening_delay: float = 1.5
    intervals: tuple = (3.2, 2.8, 2.2)
    completion_gold: int = 2500


TUNING = KeeperTuning()
NAMES = {"repairs": "Structural Repairs", "vines": "Overgrowth",
         "cleaning": "Deep Cleaning", "specimens": "Escaped Specimens"}
ORDER = tuple(NAMES)
PAIRS = {frozenset(("repairs", "vines")), frozenset(("cleaning", "specimens"))}


@dataclass(slots=True)
class Mechanic:
    kind: str
    zones: tuple[Vec, ...]
    radius: float
    warning: float
    life: float
    safe: Vec | None = None
    route: tuple = ()
    check_in: float = .25
    suppressed: dict = field(default_factory=dict)
    elapsed: float = 0
    route_seconds: float = 0
    certified_speed: float = 0

    def contains(self, point, padding=0):
        return any((point - zone).length() < self.radius + padding for zone in self.zones)


class KeeperFight:
    def __init__(self, world, tuning=TUNING):
        self.world, self.tuning = world, tuning
        self.mechanics = []
        self.stage = 1
        self.next_cast = tuning.opening_delay
        self.sequence = 0
        # A warning alone does not complete a turn: cancelled duties must retry.
        # No duty repeats until every duty in this rotation has activated.
        self.pending_duties = set(ORDER)
        self.finished = False
        self.history = []
        self.boss = None
        if world.player.cleared_floor == 5:
            self.finished = True
            world.level_completed = world._phase_resolved = True
            world.floor_clear_notified = True
            world.message = "The Keeper is off duty. The upper tower continues beyond this section."
        else:
            self.boss = world.make_enemy(Vec(8.5, 5.5), "keeper", boss_role="keeper", boss_name="The Keeper")
            world.boss_started = True

    @property
    def live_summons(self):
        return [e for e in self.world.enemies if e.summoned and e.hp > 0]

    @property
    def active_kinds(self):
        kinds = {m.kind for m in self.mechanics}
        if self.live_summons:
            kinds.add("specimens")
        return kinds

    def can_start(self, kind):
        kinds = self.active_kinds
        if self.finished or kind in kinds or len(kinds) >= (1 if self.stage == 1 else 2):
            return False
        if self.stage == 2 and kinds and frozenset(kinds | {kind}) not in PAIRS:
            return False
        return True

    def slow_at(self, point, projected=None):
        for mechanic in self.mechanics + ([projected] if projected and projected.kind == "vines" else []):
            if mechanic.kind != "vines":
                continue
            for i, zone in enumerate(mechanic.zones):
                if mechanic.suppressed.get(i, 0) <= 0 and (point - zone).length() < mechanic.radius + .23:
                    # Existing warnings are also counted when certifying future movement.
                    if projected is not None or mechanic.warning <= 0:
                        return self.tuning.vine_speed
        return 1

    def suppress_vines(self, center, radius):
        for mechanic in self.mechanics:
            if mechanic.kind == "vines":
                for i, zone in enumerate(mechanic.zones):
                    if (zone - center).length() <= radius + mechanic.radius:
                        mechanic.suppressed[i] = self.tuning.nova_suppression

    def _segment_clear(self, start, end, candidate):
        delta = end - start
        steps = max(1, round(delta.length() / .12))
        for i in range(1, steps + 1):
            point = start + delta * (i / steps)
            if not self.world.walkable(point, .28):
                return False
            for enemy in self.world.enemies:
                clearance = .85 if enemy is self.boss else .7
                distance = (enemy.pos - point).length()
                initial = (enemy.pos - start).length()
                if distance < clearance and (initial >= clearance or distance < initial - .01 or delta.length() < .01):
                    return False
                if enemy.action in ("warning", "lunge") and enemy.kind in ("crystal", "predator"):
                    attack = enemy.attack_direction * (5.2 if enemy.kind == "crystal" else 2.3)
                    offset = point - enemy.attack_origin
                    fraction = max(0, min(1, (offset.x * attack.x + offset.y * attack.y) / max(.01, attack.length() ** 2)))
                    if (offset - attack * fraction).length() < .8:
                        return False
            for other in self.mechanics:
                if other is not candidate and other.kind in ("repairs", "cleaning") and other.contains(point, .35):
                    return False
        return True

    def _travel_time(self, start, end, candidate):
        midpoint = (start + end) * .5
        factor = min(self.slow_at(start, candidate), self.slow_at(midpoint, candidate), self.slow_at(end, candidate))
        return (end - start).length() / (max(.1, self.world.player.move_speed) * factor)

    def escape_plan(self, candidate):
        """Dijkstra on the actual arena with clearance, actor occupancy and vine cost.

        The whole route must avoid other damage mechanics. The destination is
        outside the new mechanic with enough clearance for the player's body.
        """
        start = self.world.player.pos
        tile = (floor(start.x), floor(start.y))
        distances, parents, points = {tile: 0.0}, {tile: None}, {tile: start}
        queue = [(0.0, tile)]
        while queue:
            travel, node = heappop(queue)
            if travel > distances[node] + 1e-8:
                continue
            point = points[node]
            if (self._segment_clear(point, point, candidate) and not candidate.contains(point, .5)
                    and all(not m.contains(point, .4) for m in self.mechanics
                            if m is not candidate and m.kind in ("repairs", "cleaning"))):
                route = []
                cursor = node
                while cursor is not None:
                    route.append(points[cursor])
                    cursor = parents[cursor]
                return tuple(reversed(route)), travel
            for adjacent in neighbors(node):
                x, y = adjacent
                if not (0 < x < 16 and 0 < y < 16):
                    continue
                target = Vec(x + .5, y + .5)
                if not self._segment_clear(point, target, candidate):
                    continue
                cost = travel + self._travel_time(point, target, candidate)
                if cost < distances.get(adjacent, float("inf")):
                    distances[adjacent], parents[adjacent], points[adjacent] = cost, node, target
                    heappush(queue, (cost, adjacent))
        return None

    def _certify(self, mechanic):
        plan = self.escape_plan(mechanic)
        if plan is None:
            return False
        route, travel = plan
        delay = travel + self.tuning.reaction_margin + self.world.player.cast_time + self.world.player.stasis
        if delay > self.tuning.warning_max:
            return False
        mechanic.route, mechanic.safe = route, route[-1]
        mechanic.route_seconds = travel
        mechanic.certified_speed = self.world.player.move_speed
        mechanic.warning = max(mechanic.warning, self.tuning.warning_min, delay)
        return True

    def _summon_positions(self):
        count = min(self.tuning.summon_cap - len(self.live_summons), self.stage + 1)
        positions = []
        # Authored entry points, then a deterministic fallback over clear arena.
        candidates = [Vec(4.5, 5.5), Vec(12.5, 5.5), Vec(5.5, 10.5), Vec(11.5, 10.5)]
        candidates += [Vec(x + .5, y + .5) for y in range(2, 15) for x in range(2, 15)]
        for point in candidates:
            if (self.world.walkable(point, .4) and (point - self.world.player.pos).length() >= 4
                    and all((point - e.pos).length() >= 1.5 for e in self.world.enemies)
                    and all((point - p).length() >= 2 for p in positions)
                    and all(not m.contains(point, 1) for m in self.mechanics)):
                positions.append(point)
                if len(positions) == count:
                    break
        return tuple(positions) if len(positions) == count and count > 0 else ()

    def start(self, kind):
        if kind not in NAMES or not self.can_start(kind):
            return False
        player = self.world.player.pos
        if kind == "repairs":
            direction = (player - self.boss.pos).unit()
            zones = []
            for i in range(1, 21):
                point = self.boss.pos + direction * (.7 * i)
                if not self.world.walkable(point, .3):
                    break
                zones.append(point)
            if not zones:
                return False
            mechanic = Mechanic(kind, tuple(zones), .62, 2, 1.5)
        elif kind == "vines":
            # Disjoint patches cannot create a solid arena-spanning barrier.
            zones = tuple(player + offset for offset in (Vec(1.3, 0), Vec(2.2, .6), Vec(-1.4, 1), Vec(-2.3, 1.5))
                          if self.world.walkable(player + offset, .4))
            if not zones:
                return False
            mechanic = Mechanic(kind, zones, .85, 2, self.tuning.vine_life)
        elif kind == "cleaning":
            zones = tuple(player + offset for offset in (Vec(), Vec(2.6, 0), Vec(0, -2.6))
                          if self.world.walkable(player + offset, .3))
            mechanic = Mechanic(kind, zones, 1.25, 2.2, self.tuning.spill_life)
        else:
            zones = self._summon_positions()
            if not zones:
                return False
            mechanic = Mechanic(kind, zones, .6, 1.4, .1)
        if not self._certify(mechanic):
            return False
        self.mechanics.append(mechanic)
        self.history.append((self.world.time, self.stage, kind, mechanic.warning, mechanic.safe))
        self.world._record("boss_attack", source="keeper", attack=NAMES[kind],
                           warning_seconds=mechanic.warning / self.boss.attack_rate,
                           safe_position=self.world._point(mechanic.safe), active_duties=sorted(self.active_kinds))
        instructions = {"repairs": "Step sideways from the stone line.",
                        "vines": "Avoid the growing patches. Frost Nova suppresses vines.",
                        "cleaning": "Reach the green safe marker before the splash.",
                        "specimens": "Unauthorized specimens must return to their enclosures!"}
        self.world.announce(f"{NAMES[kind]}: {instructions[kind]}")
        return True

    def _warning_still_safe(self, mechanic):
        if not mechanic.route:
            return False
        if self.world.player.move_speed < mechanic.certified_speed - .01:
            return False
        if any(not self._segment_clear(a, b, mechanic) for a, b in zip(mechanic.route, mechanic.route[1:])):
            return False
        if sum(self._travel_time(a, b, mechanic) for a, b in zip(mechanic.route, mechanic.route[1:])) > mechanic.route_seconds + .05:
            return False
        return self._segment_clear(mechanic.safe, mechanic.safe, mechanic)

    def update(self, dt):
        if self.finished:
            return
        self.world.refresh_patch_status(self.boss)
        ratio = self.boss.hp / self.boss.max_hp
        new_stage = 1 + sum(ratio <= threshold for threshold in self.tuning.thresholds)
        if new_stage != self.stage:
            self.stage = new_stage
            self.world.phase = new_stage
            self.world._record("boss_stage", stage=new_stage, boss_hp=self.boss.hp)
            self.world.announce(f"Keeper stage {new_stage}: 'I just cleaned that!' Two duties at once; watch the warnings.")
        for enemy in self.live_summons:
            enemy.summon_life -= dt
            if enemy.summon_life <= 0:
                self.world._record("summon_recalled", target=self.world._actor_info(enemy), reason="lifetime")
                self.world.enemies.remove(enemy)
                if self.world.selected is enemy:
                    self.world.selected = None
        for mechanic in self.mechanics[:]:
            for i in mechanic.suppressed:
                mechanic.suppressed[i] = max(0, mechanic.suppressed[i] - dt)
            if mechanic.warning > 0:
                mechanic.warning -= dt * self.boss.attack_rate
                mechanic.check_in -= dt
                if mechanic.check_in <= 0:
                    mechanic.check_in = .25
                    if not self._warning_still_safe(mechanic):
                        if not self._certify(mechanic):
                            self.mechanics.remove(mechanic)
                            self.world._record("hazard_cancelled", attack=NAMES[mechanic.kind], reason="no_safe_route")
                        continue
                if mechanic.warning > 0:
                    continue
                self.world._record("hazard_active", attack=NAMES[mechanic.kind], duration=mechanic.life,
                                   positions=[self.world._point(p) for p in mechanic.zones])
                if mechanic.kind == "specimens":
                    previous_count = len(self.live_summons)
                    # Revalidate all entry points after the telegraph. Never
                    # materialize a specimen in a player, terrain or hazard.
                    for i, point in enumerate(mechanic.zones):
                        if len(self.live_summons) >= self.tuning.summon_cap:
                            break
                        if (self.world.walkable(point, .4) and (point - self.world.player.pos).length() >= 2
                                and all((point - e.pos).length() >= 1 for e in self.world.enemies)):
                            enemy = self.world.make_enemy(point, ("crystal", "predator", "arcane")[i % 3],
                                                          summoned=True, summon_life=self.tuning.summon_life, cooldown=1.5)
                    if len(self.live_summons) > previous_count:
                        self.pending_duties.discard(mechanic.kind)
                    self.mechanics.remove(mechanic)
                    continue
                self.pending_duties.discard(mechanic.kind)
            mechanic.elapsed += dt
            mechanic.life -= dt
            if mechanic.kind == "cleaning" and mechanic.contains(self.world.player.pos, .23):
                self.world._hurt_player(KEEPER_DAMAGE["Deep Cleaning"], source="keeper", attack="Deep Cleaning", attacker=self.boss)
            elif mechanic.kind == "repairs":
                for i, point in enumerate(mechanic.zones):
                    if i * .055 <= mechanic.elapsed <= i * .055 + .45 and (point - self.world.player.pos).length() < .85:
                        self.world._hurt_player(KEEPER_DAMAGE["Structural Repairs"], source="keeper", attack="Structural Repairs", attacker=self.boss)
            if self.finished:
                return
            if mechanic.life <= 0:
                self.mechanics.remove(mechanic)
        if self.world.state != "playing" or self.finished:
            return
        self.next_cast -= dt * self.boss.attack_rate
        if self.next_cast <= 0 and self.boss.frozen <= 0:
            if not self.pending_duties:
                self.pending_duties.update(ORDER)
            for offset in range(len(ORDER)):
                index = (self.sequence + offset) % len(ORDER)
                if ORDER[index] in self.pending_duties and self.start(ORDER[index]):
                    self.sequence = (index + 1) % len(ORDER)
                    self.next_cast = self.tuning.intervals[self.stage - 1]
                    break
            else:
                self.next_cast = .35

    def cleanup(self):
        self.world._record("fight_cleanup", summons=len(self.live_summons), hazards=len(self.mechanics))
        self.finished = True
        self.mechanics.clear()
        self.world.enemies[:] = [e for e in self.world.enemies if not e.summoned]
        self.world.projectiles[:] = [p for p in self.world.projectiles if not p.hostile]
        if self.world.selected and getattr(self.world.selected, "summoned", False):
            self.world.selected = None

    def defeated(self):
        if self.finished:
            return
        self.cleanup()
        self.world.player.cleared_floor = 5
        first_victory = not self.world.player.frostweave_unlocked
        self.world.player.lower_tower_completed = True
        self.world.player.frostweave_unlocked = True
        self.world.player.gold += self.tuning.completion_gold
        self.world._record("gold_change", amount=self.tuning.completion_gold, source="keeper_reward")
        inventory = self.world.player.inventory
        if first_victory:
            inventory.add(inventory.create_template("frostweave:helm", 3, self.world.loot_rng, "reward"))
        self.world._complete_level()
        self.world.events.append("loot")
        self.world.announce(f"The Keeper is off duty! +{self.tuning.completion_gold} gold. Frostweave Rank 3 stock is unlocked. The upper tower awaits.")
