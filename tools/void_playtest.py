"""Repeatable Floor 6 spell/movement playtests, with no direct damage or R use.

This checks completion and resource pressure, not human judgment of the fight.
Run with .venv/Scripts/python.exe tools/void_playtest.py.
"""
import json
from math import cos, sin, pi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dungeon.geometry import Vec
from dungeon.void import in_sweep, LUNGE_REACH
from dungeon.world import World


def danger(world, point):
    score = 0
    for zone in world.void.zones:
        if zone.contains(point, .55):
            score += 20 if zone.kind == "darkness" else 8
    for enemy in world.enemies:
        distance = (point - enemy.pos).length()
        score += max(0, 2 - distance) * 4 if enemy.kind != "binder" else 0
        if enemy.kind == "voidwalker":
            if enemy.action in ("lunge_warning", "lunge"):
                offset = point - enemy.attack_origin
                direction = enemy.attack_direction
                fraction = max(0, min(LUNGE_REACH, offset.x * direction.x + offset.y * direction.y))
                if (offset - direction * fraction).length() < 1.1:
                    score += 30
            elif enemy.action == "sweep" and in_sweep(enemy.attack_origin, enemy.attack_direction, point, .65):
                score += 30
    return score


def order(world):
    p = world.player
    if p.hp < p.max_hp * .6 and p.potions:
        world.use_potion()
    if world.level_completed:
        world.request_move(world.exit, marker=False)
        return
    targets = world.spawners or ([world.void.boss] if world.void.boss in world.enemies else world.enemies)
    target = min(targets, key=lambda t: (t.pos - p.pos).length(), default=None)
    if sum((e.pos - p.pos).length() < 2.5 for e in world.enemies) >= 2:
        world.cast("w", feedback=False)
    if target and p.mana > 55:
        world.cast("e", p.pos, feedback=False)
    if target and (target.pos - p.pos).length() < 8 and world._line_clear(p.pos, target.pos):
        world.cast("q", target.pos, feedback=False)
    if world.time % .2 >= 1 / 60:
        return
    if danger(world, p.pos) > 1:
        candidates = [p.pos + Vec(cos(i * pi / 8), sin(i * pi / 8)) * d
                      for d in (1.5, 3) for i in range(16)]
        clear = [point for point in candidates if world.walkable(point, .3) and world._line_clear(p.pos, point)]
        if clear:
            world.request_move(min(clear, key=lambda point: danger(world, point) +
                ((point - target.pos).length() * .08 if target else 0)), marker=False)
    elif target and ((target.pos - p.pos).length() > 5.5 or not world._line_clear(p.pos, target.pos)):
        world.request_move(target.pos, marker=False)
    elif not world.path:
        world.stop()


def run(seed, loadout="frostweave"):
    world = World(seed, level=6)
    inv = world.player.inventory
    for slot in ("helm", "chest", "legs", "gloves", "boots"):
        template = "frostweave:" + slot if loadout == "frostweave" or slot == "helm" else "standard:" + slot
        rank = 3 if template.startswith("frostweave:") else 2
        item = inv.create_template(template, rank, world.loot_rng, "shop")
        inv.add(item)
        inv.equip(item.uid)
    world.player.hp = world.player.max_hp
    world.player.frostweave_unlocked = True
    peak_enemies = peak_darkness = 0
    damage = []

    class Recorder:
        def event(self, current, event, **data):
            if event == "player_damage":
                damage.append(data)
        def tick(self, current, dt):
            pass

    world.telemetry = Recorder()
    for _ in range(300 * 60):
        order(world)
        world.update(1 / 60)
        peak_enemies = max(peak_enemies, len(world.enemies))
        peak_darkness = max(peak_darkness, sum(z.kind == "darkness" for z in world.void.zones))
        if world.state in ("dead", "won", "cleared"):
            break
    return dict(seed=seed, loadout=loadout, state=world.state, seconds=round(world.time, 2),
                phase=world.phase, hp=round(world.player.hp, 2), potions=world.player.potions,
                boss_hp=world.void.boss.hp if world.void.boss else None,
                pillars_broken=world.void.broken_pillars, peak_enemies=peak_enemies,
                peak_darkness=peak_darkness, damage_events=len(damage),
                damage_sources=sorted({d["attack"] for d in damage}), used_glacial_prison=False)


if __name__ == "__main__":
    results = [run(seed, loadout) for loadout in ("frostweave", "keeper_reward") for seed in (3, 7, 19)]
    print(json.dumps(results, indent=2))
    Path("docs/void-playtest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
