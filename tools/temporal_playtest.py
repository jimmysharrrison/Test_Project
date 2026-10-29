"""Background-only Floor 9 clears using real movement, spells and resources.

The bot reads warning geometry. These runs verify completion and resource flow,
not human reaction time or live visual readability. No direct kills or god mode.
"""
import json
from math import cos, sin, pi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dungeon.geometry import Vec
from dungeon.temporal import SURVIVAL_SECONDS
from dungeon.world import World


def in_lane(point, origin, direction, length=7, width=.65):
    offset = point - origin
    along = max(0, min(length, offset.x * direction.x + offset.y * direction.y))
    return (offset - direction * along).length() < width


def danger(world, point):
    score = 0
    for enemy in world.enemies:
        if enemy.kind == "hourless_breach":
            continue
        score += max(0, 2 - (point - enemy.pos).length()) * 3
        if enemy.action == "time_shot" and in_lane(point, enemy.pos, (enemy.attack_origin - enemy.pos).unit()):
            score += 20
        if enemy.action == "rift_warning" and (point - enemy.attack_origin).length() < 1.5:
            score += 10
    for echo in world.void.echoes:
        if in_lane(point, echo.pos, echo.direction):
            score += 20
    for shot in world.projectiles:
        if shot.hostile and in_lane(point, shot.pos, shot.velocity.unit(), length=3):
            score += 25
    for field in world.void.fields:
        if field.contains(point):
            score += 5
    return score


def order(world, delay, deliberately_fail=False):
    p, fight = world.player, world.void
    if world.level_completed:
        world.request_move(world.exit, marker=False)
        return
    if fight.stopped:
        if not deliberately_fail and SURVIVAL_SECONDS - fight.stage_left >= delay:
            world.cast("r", feedback=False)
        return
    if fight.stage_name in ("demonstration", "practice_reset", "lesson_passed", "retry", "recovery"):
        return
    if p.hp < p.max_hp * .6 and p.potions:
        world.use_potion()
    targets = ([fight.active_anchor] if fight.active_anchor else world.spawners or
               [e for e in world.enemies if e.kind != "hourless_breach"])
    target = min(targets, key=lambda t: (t.pos - p.pos).length(), default=None)
    if sum((e.pos - p.pos).length() < 2.6 for e in world.enemies) >= 2:
        world.cast("w", feedback=False)
    if target and p.mana > 55:
        world.cast("e", p.pos, feedback=False)
    if target and (target.pos - p.pos).length() < 8 and world._line_clear(p.pos, target.pos):
        world.cast("q", target.pos, feedback=False)
    if world.time % .15 >= 1 / 60:
        return
    if danger(world, p.pos) > 1:
        candidates = [p.pos + Vec(cos(i * pi / 8), sin(i * pi / 8)) * d
                      for d in (1.5, 3) for i in range(16)]
        clear = [v for v in candidates if world.walkable(v, .3) and world._line_clear(p.pos, v)]
        if clear:
            world.request_move(min(clear, key=lambda v: danger(world, v) +
                               ((v - target.pos).length() * .15 if target else 0)), marker=False)
    elif target and ((target.pos - p.pos).length() > 5.5 or not world._line_clear(p.pos, target.pos)):
        world.request_move(target.pos, marker=False)


def run(seed, loadout="keeper_reward", delay=0, fail_once=False):
    world = World(seed, level=9, completion_delay_ms=0)
    inv = world.player.inventory
    for slot in ("helm", "chest", "legs", "gloves", "boots"):
        template = "frostweave:" + slot if loadout == "frostweave" or slot == "helm" else "standard:" + slot
        item = inv.create_template(template, 3 if template.startswith("frostweave:") else 2, world.loot_rng, "shop")
        inv.add(item)
        inv.equip(item.uid)
    world.player.hp = world.player.max_hp
    world.player.frostweave_unlocked = True
    events, damage = {}, []
    peak = fields = echoes = 0

    class Recorder:
        def event(self, current, event, **data):
            events[event] = events.get(event, 0) + 1
            if event == "player_damage":
                damage.append(data)
        def tick(self, current, dt):
            pass

    world.telemetry = Recorder()
    for _ in range(240 * 60):
        fail = (fail_once and world.void.failures == 0 and world.void.completed_anchors == 1
                and world.void.stage_name == "stopped_hour")
        order(world, delay, fail)
        world.update(1 / 60)
        peak = max(peak, len(world.enemies))
        fields = max(fields, len(world.void.fields))
        echoes = max(echoes, len(world.void.echoes))
        if world.state in ("dead", "cleared", "won"):
            break
    return dict(level=9, seed=seed, loadout=loadout, r_delay_seconds=delay,
                deliberate_failure=fail_once, state=world.state, seconds=round(world.time, 2),
                phase=world.phase, hp=round(world.player.hp, 2), potions=world.player.potions,
                stage=world.void.stage_name, lesson_attempts=world.void.practice_attempts,
                anchors_sealed=world.void.completed_anchors, failures=world.void.failures,
                peak_enemies=peak, peak_fields=fields, peak_echoes=echoes,
                damage_events=len(damage), events=events)


if __name__ == "__main__":
    results = [run(seed, loadout, delay) for loadout in ("keeper_reward", "frostweave")
               for seed, delay in ((3, 0), (7, .5), (19, 1))]
    results.append(run(7, delay=.5, fail_once=True))
    Path("docs/temporal-playtest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    raise SystemExit(any(r["state"] not in ("cleared", "won") or r["anchors_sealed"] != 3 for r in results))
