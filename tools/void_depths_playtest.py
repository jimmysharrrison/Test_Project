"""Normal-resource automated clears of floors 7 and 8; no direct kills or R.

The policy reads warning geometry, so this is completion/resource verification,
not a measure of human reaction time or final encounter difficulty.
"""
import json
from math import cos, sin, pi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dungeon.geometry import Vec
from dungeon.void_depths import VoidMechanic, gaze_end, FORCES
from dungeon.world import World
from void_playtest import danger as base_danger


def danger(world, point):
    score = base_danger(world, point)
    for m in world.void.mechanics:
        if m.kind in ("lash", "grasp", "chorus") and m.contains(point, .6):
            score += 30
        elif m.kind == "gaze":
            beam = VoidMechanic("gaze", m.owner, m.pos, 0, .1, 1, gaze_end(m))
            if beam.contains(point, .4):
                score += 30
        elif m.kind in ("convergence", "well") and (point - m.pos).length() < (2.8 if m.kind == "convergence" else 2):
            score += 30
        elif m.kind == "orbit" and abs((point - m.pos).length() - m.radius) < 1.1:
            score += 22
    return score


def order(world):
    p, fight = world.player, world.void
    if p.hp < p.max_hp * .6 and p.potions:
        world.use_potion()
    if world.level_completed:
        world.request_move(world.exit, marker=False)
        return
    if fight.rooted:
        targets = [fight.root_owner]
        world.cast("w", feedback=False)
    elif fight.protected:
        targets = [e for e in world.enemies if e.boss_role == "channeler" and e.frozen <= 0]
    else:
        targets = world.spawners or ([fight.boss] if fight.boss in world.enemies else world.enemies)
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
                               ((v - target.pos).length() * .08 if target else 0)), marker=False)
    elif target and ((target.pos - p.pos).length() > 5.5 or not world._line_clear(p.pos, target.pos)):
        world.request_move(target.pos, marker=False)
    elif not world.path:
        world.stop()


def run(level, seed, loadout="keeper_reward"):
    world = World(seed, level=level)
    inv = world.player.inventory
    for slot in ("helm", "chest", "legs", "gloves", "boots"):
        template = "frostweave:" + slot if loadout == "frostweave" or slot == "helm" else "standard:" + slot
        item = inv.create_template(template, 3 if template.startswith("frostweave:") else 2, world.loot_rng, "shop")
        inv.add(item)
        inv.equip(item.uid)
    world.player.hp = world.player.max_hp
    world.player.frostweave_unlocked = True
    damage, attacks = [], set()
    peak = forces = hazards = 0

    class Recorder:
        def event(self, current, event, **data):
            if event == "player_damage":
                damage.append(data)
            if event == "void_mechanic_active":
                attacks.add(data["attack"])
        def tick(self, current, dt):
            pass

    world.telemetry = Recorder()
    for _ in range(240 * 60):
        order(world)
        world.update(1 / 60)
        peak = max(peak, len(world.enemies))
        hazards = max(hazards, len(world.void.mechanics))
        forces = max(forces, sum(m.kind in FORCES for m in world.void.mechanics))
        if world.state in ("dead", "cleared", "won"):
            break
    return dict(level=level, seed=seed, loadout=loadout, state=world.state, seconds=round(world.time, 2),
                phase=world.phase, hp=round(world.player.hp, 2), potions=world.player.potions,
                boss_hp=world.void.boss.hp if world.void.boss else None, peak_enemies=peak,
                peak_mechanics=hazards, peak_force_fields=forces, damage_events=len(damage),
                active_attacks=sorted(attacks), used_glacial_prison=False)


if __name__ == "__main__":
    results = [run(level, seed, loadout) for level in (7, 8)
               for loadout in ("keeper_reward", "frostweave") for seed in (3, 7, 19)]
    Path("docs/void-depths-playtest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
