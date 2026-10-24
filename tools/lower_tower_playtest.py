"""Repeatable spell-and-movement playthroughs; not a substitute for human play.

Run with .venv/Scripts/python.exe tools/lower_tower_playtest.py.
Uses rank-3 Frostweave gear, normal HP/mana/cooldowns/damage and no direct kills.
The bot reads telegraphs and the displayed Keeper escape route. --realtime
renders a normal-speed run for observing animation and warning timing.
"""
import argparse
import json
from math import cos, sin, pi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dungeon.geometry import Vec
from dungeon.world import World


def danger(world, point):
    score = 0
    for enemy in world.enemies:
        if enemy.kind == "keeper":
            continue
        distance = (point - enemy.pos).length()
        score += max(0, 2 - distance) * 3
        if enemy.action in ("warning", "lunge") and enemy.kind in ("crystal", "predator"):
            end = enemy.attack_origin + enemy.attack_direction * (5.2 if enemy.kind == "crystal" else 2.3)
            delta = end - enemy.attack_origin
            offset = point - enemy.attack_origin
            fraction = max(0, min(1, (offset.x * delta.x + offset.y * delta.y) / max(.01, delta.length() ** 2)))
            score += 10 if (offset - delta * fraction).length() < .85 else 0
    for shot in world.projectiles:
        if shot.hostile and (point - shot.pos).length() < 1.2:
            score += 7
    if world.keeper:
        score += sum(20 for m in world.keeper.mechanics if m.kind in ("cleaning", "repairs") and m.contains(point, .4))
    return score


def order(world):
    p = world.player
    if p.hp < p.max_hp * .55 and p.potions:
        world.use_potion()
    close = [e for e in world.enemies if e.kind != "keeper" and (e.pos - p.pos).length() < 2.5]
    if close or (world.keeper and world.keeper.slow_at(p.pos) < 1):
        world.cast("w", feedback=False)
    if len(close) >= 3 and p.hp < p.max_hp * .7:
        world.cast("r", feedback=False)
    targets = world.spawners + world.enemies
    if world.keeper:
        target = world.keeper.boss if not world.keeper.finished else None
    else:
        threats = [e for e in close if e.frozen <= 0]
        target = min(threats or targets, key=lambda t: (t.pos - p.pos).length(), default=None)
    if target and p.mana >= 55 and p.cooldowns["e"] <= 0:
        world.cast("e", p.pos, feedback=False)
    if target and (target.pos - p.pos).length() < 8.5 and world._line_clear(p.pos, target.pos):
        world.cast("q", target.pos, feedback=False)
    if world.keeper:
        warning = next((m for m in world.keeper.mechanics if m.warning > 0 and m.contains(p.pos, .5)), None)
        if warning:
            plan = world.keeper.escape_plan(warning)
            if plan:
                world.path = list(plan[0][1:])
                world.destination = world.path[-1] if world.path else None
                return
    if world.time % .15 >= 1 / 60:
        return
    if danger(world, p.pos) > 1:
        candidates = [p.pos + Vec(cos(i * pi / 8), sin(i * pi / 8)) * 2 for i in range(16)]
        clear = [v for v in candidates if world.walkable(v) and world._line_clear(p.pos, v)]
        if clear:
            world.request_move(min(clear, key=lambda v: danger(world, v)), marker=False)
    elif target and ((target.pos - p.pos).length() > 6 or not world._line_clear(p.pos, target.pos)):
        world.request_move(target.pos, marker=False)
    else:
        world.stop()


def run(seed, render=None, clock=None, seconds=240):
    world = World(seed, level=4)
    inv = world.player.inventory
    for slot in ("helm", "chest", "legs", "gloves", "boots"):
        item = inv.create(slot, 3, "shop")
        inv.add(item)
        inv.equip(item.uid)
    world.player.hp = world.player.max_hp
    results = []
    for level in (4, 5):
        peak = 0
        for frame in range(seconds * 60):
            if clock:
                clock.tick(60)
                import pygame
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return results
            order(world)
            world.update(1 / 60)
            if world.keeper:
                peak = max(peak, len(world.keeper.active_kinds))
                assert peak <= 2
                assert len(world.keeper.live_summons) <= 4
            if render:
                render(world)
            if world.state == "dead" or world.exit_open:
                break
        results.append({"seed": seed, "floor": level, "cleared": world.exit_open,
                        "seconds": round(world.time, 2), "hp": world.player.hp,
                        "kills": world.player.kills, "peak_mechanics": peak,
                        "stages": sorted({row[1] for row in world.keeper.history}) if world.keeper else [],
                        "attacks": sorted({row[2] for row in world.keeper.history}) if world.keeper else []})
        if not world.exit_open:
            break
        if level == 4:
            world.player.pos = world.exit
            world.update(1 / 60)
            assert world.next_level()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--seeds", nargs="+", type=int, default=(3, 7, 19, 41))
    args = parser.parse_args()
    render, clock = None, None
    if args.realtime:
        import pygame
        from dungeon.render import Renderer, WIDTH, HEIGHT
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Frost Mage - normal-speed scripted playtest")
        renderer = Renderer(screen, World(7, level=4))
        clock = pygame.time.Clock()

        def render(world):
            renderer.draw(world)
            pygame.display.flip()
    report = []
    for seed in args.seeds:
        result = run(seed, render, clock)
        report.extend(result)
        print(json.dumps(result), flush=True)
    Path("docs/lower-tower-playtest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
