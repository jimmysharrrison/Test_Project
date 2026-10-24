"""Procedural Menagerie and maintenance-station art in the existing isometric style."""
from math import sin, cos, pi

import pygame

from .geometry import Vec, project
from .keeper import NAMES

GOLD, ICE, TEAL = (214, 180, 113), (139, 216, 248), (100, 212, 189)
RED, VINE, POTION = (245, 112, 90), (133, 194, 108), (207, 117, 220)


def iso(point):
    v = project(point, Vec(857, 226))
    return round(v.x), round(v.y)


def decorate_floor(renderer, world):
    surface = renderer.floor
    if world.level_data.menagerie:
        for center in (Vec(4.5, 5.5), Vec(12.5, 5.5), Vec(4.5, 10.5), Vec(12.5, 10.5)):
            x, y = iso(center)
            pygame.draw.ellipse(surface, (90, 118, 139), (x - 53, y - 25, 106, 50), 2)
            for i in range(5):
                dx, dy = cos(i * 1.2) * 43, sin(i * 1.2) * 20
                pygame.draw.lines(surface, (138, 119, 166), False,
                                  [(x + dx - 4, y + dy), (x + dx, y + dy - 5), (x + dx + 6, y + dy + 3)], 2)
        for point in (Vec(2.5, 7.5), Vec(14.5, 7.5), Vec(8.5, 14.5)):
            x, y = iso(point)
            pygame.draw.ellipse(surface, (133, 119, 84), (x - 12, y - 5, 24, 10), 2)
            pygame.draw.ellipse(surface, (65, 101, 117), (x - 8, y - 3, 16, 6))
        x, y = iso(Vec(8.5, 8.5))
        pygame.draw.lines(surface, (90, 72, 119), False, [(x - 50, y), (x - 12, y - 9), (x, y + 8), (x + 46, y - 5)], 2)
    elif world.keeper:
        for r in (60, 78, 103):
            x, y = iso(Vec(8.5, 8.5))
            pygame.draw.ellipse(surface, (81, 85, 79), (x - r, y - r // 2, 2 * r, r), 1)
        for point in (Vec(2.5, 3.5), Vec(14.5, 3.5), Vec(2.5, 11.5), Vec(14.5, 11.5)):
            x, y = iso(point)
            pygame.draw.lines(surface, GOLD, False, [(x - 12, y), (x, y - 6), (x + 12, y)], 2)


def low_enclosure(renderer, tile, keeper=False):
    x, y = iso(Vec(tile[0] + .5, tile[1] + .5))
    surface = renderer.screen
    pygame.draw.polygon(surface, (70, 83, 97), [(x - 26, y - 9), (x, y - 22), (x + 26, y - 9), (x, y + 4)])
    pygame.draw.lines(surface, (158, 134, 99), False, [(x - 26, y - 9), (x, y + 4), (x + 26, y - 9)], 2)
    for dx in (-17, 12):
        pygame.draw.line(surface, (139, 158, 170), (x + dx, y - 8), (x + dx - 4, y - 32), 3)
    pygame.draw.line(surface, GOLD if keeper else ICE, (x - 21, y - 31), (x - 4, y - 23), 2)
    if keeper:
        pygame.draw.circle(surface, POTION, (x + 3, y - 16), 5)
        pygame.draw.lines(surface, VINE, False, [(x, y), (x + 8, y - 10), (x + 12, y - 4)], 3)


def containment(renderer, spawner, time):
    x, y = iso(spawner.pos)
    screen = renderer.screen
    pulse = ICE if spawner.flash <= 0 else (245, 245, 245)
    renderer.radius(spawner.pos, .65, pulse, 2)
    for side in (-1, 1):
        pygame.draw.lines(screen, (135, 151, 176), False,
                          [(x + side * 23, y), (x + side * 23, y - 38), (x + side * 11, y - 50)], 4)
    pygame.draw.polygon(screen, (83, 60, 119), [(x, y - 53), (x + 11, y - 27), (x, y - 9), (x - 11, y - 27)])
    pygame.draw.lines(screen, pulse, False, [(x, y - 48), (x - 5, y - 31), (x + 6, y - 29), (x, y - 14)], 2)
    pygame.draw.line(screen, pulse, (x - 22, y - 31), (x - 8 + sin(time * 15) * 4, y - 25), 2)
    renderer.bar(x - 25, y - 65, 50, 3, spawner.hp / spawner.max_hp, ICE)


def new_enemy(renderer, enemy, time):
    if enemy.kind not in ("crystal", "predator", "arcane", "keeper"):
        return False
    x, y = iso(enemy.pos)
    s = renderer.screen
    color = (232, 240, 245) if enemy.flash > 0 else ICE if enemy.frozen > 0 else (129, 151, 178)
    if enemy.kind == "crystal":
        pygame.draw.ellipse(s, (71, 89, 117), (x - 23, y - 25, 46, 25))
        for dx in (-15, 13):
            pygame.draw.line(s, color, (x + dx, y - 8), (x + dx, y + 3), 5)
        for dx, h in ((-15, 17), (-3, 30), (10, 22)):
            pygame.draw.polygon(s, color, [(x + dx - 7, y - 20), (x + dx, y - 20 - h), (x + dx + 8, y - 20)])
        pygame.draw.circle(s, GOLD, (x + 21, y - 15), 3)
    elif enemy.kind == "predator":
        pygame.draw.ellipse(s, color, (x - 12, y - 19, 25, 14))
        pygame.draw.lines(s, color, False, [(x - 10, y - 9), (x - 26, y - 20), (x - 21, y - 25)], 3)
        for dx in (-7, 8):
            pygame.draw.line(s, color, (x + dx, y - 8), (x + dx + 7, y + 2), 3)
        pygame.draw.polygon(s, (168, 120, 191), [(x + 7, y - 14), (x + 8, y - 31), (x + 18, y - 17)])
        pygame.draw.circle(s, TEAL, (x + 12, y - 15), 2)
    elif enemy.kind == "arcane":
        bob = 0 if enemy.frozen > 0 else sin(time * 4 + enemy.pos.x) * 4
        cy = round(y - 30 + bob)
        renderer.glow(x, cy, POTION, 38, 30)
        pygame.draw.circle(s, (75, 64, 120), (x, cy), 13)
        pygame.draw.circle(s, color, (x, cy), 13, 2)
        pygame.draw.circle(s, GOLD, (x, cy), 5)
        for side in (-1, 1):
            pygame.draw.lines(s, color, False, [(x + side * 11, cy + 6), (x + side * 23, cy + 14), (x + side * 17, cy + 24)], 2)
    else:
        # Heavy brass construct, work apron, hanging keys, vines, flasks and broom.
        for side in (-1, 1):
            pygame.draw.line(s, (104, 120, 125), (x + side * 13, y - 18), (x + side * 18, y + 2), 10)
        pygame.draw.polygon(s, (100, 125, 131), [(x - 25, y - 61), (x + 25, y - 61), (x + 20, y - 15), (x - 20, y - 15)])
        pygame.draw.polygon(s, (124, 88, 58), [(x - 15, y - 53), (x + 15, y - 53), (x + 21, y - 13), (x - 21, y - 13)])
        pygame.draw.circle(s, color, (x, y - 75), 16)
        pygame.draw.rect(s, GOLD, (x - 21, y - 91, 42, 8), border_radius=3)
        for dx in (-7, 7):
            pygame.draw.rect(s, TEAL, (x + dx - 3, y - 79, 6, 5))
        for side in (-1, 1):
            pygame.draw.line(s, color, (x + side * 22, y - 51), (x + side * 35, y - 26), 8)
        pygame.draw.line(s, (155, 119, 76), (x + 38, y - 91), (x + 43, y - 5), 5)
        pygame.draw.polygon(s, GOLD, [(x + 32, y - 18), (x + 52, y - 19), (x + 61, y + 4), (x + 26, y + 4)])
        for dx in range(31, 56, 5):
            pygame.draw.line(s, (106, 76, 47), (x + 42, y - 17), (x + dx, y + 2), 1)
        pygame.draw.circle(s, GOLD, (x - 22, y - 29), 8, 2)
        for dx in (-28, -22, -16):
            pygame.draw.line(s, GOLD, (x + dx, y - 26), (x + dx, y - 12), 2)
            pygame.draw.line(s, GOLD, (x + dx, y - 13), (x + dx + 4, y - 13), 2)
        pygame.draw.lines(s, VINE, False, [(x - 18, y - 61), (x - 29, y - 50), (x - 19, y - 40)], 3)
        for dx, color in ((-9, POTION), (8, TEAL)):
            pygame.draw.circle(s, color, (x + dx, y - 28), 5)
    if enemy.recovery > 0:
        renderer.text("STAGGERED" if enemy.kind == "crystal" else "RECOVERING", x, y - 67, 9, TEAL, center=True)
    return True


def telegraphs(renderer, world):
    s = renderer.screen
    for enemy in world.enemies:
        if enemy.kind not in ("crystal", "predator", "arcane") or enemy.action not in ("warning", "lunge"):
            continue
        reach = 5.2 if enemy.kind == "crystal" else 2.3 if enemy.kind == "predator" else 6
        end = enemy.attack_origin
        for i in range(1, round(reach / .1) + 1):
            point = enemy.attack_origin + enemy.attack_direction * (.1 * i)
            if not world.walkable(point, .3):
                break
            end = point
        color = GOLD if enemy.action == "warning" else RED
        pygame.draw.line(s, color, iso(enemy.attack_origin), iso(end), 3)
        renderer.radius(end, .45, color, 2)
        x, y = iso(enemy.pos)
        renderer.text("CHARGE" if enemy.kind == "crystal" else "POUNCE" if enemy.kind == "predator" else "BOLT", x, y - 62, 10, color, center=True)
    if not world.keeper:
        return
    for mechanic in world.keeper.mechanics:
        warning = mechanic.warning > 0
        color = GOLD if warning else VINE if mechanic.kind == "vines" else POTION if mechanic.kind == "cleaning" else RED
        if warning and mechanic.kind == "cleaning":
            t = max(0, min(1, 1 - mechanic.warning / 2.2))
            point = world.keeper.boss.pos * (1 - t) + mechanic.zones[0] * t
            bx, by = iso(point)
            by -= round(30 + sin(t * pi) * 60)
            pygame.draw.circle(s, POTION, (bx, by), 6)
            pygame.draw.rect(s, GOLD, (bx - 2, by - 10, 4, 5))
        for i, point in enumerate(mechanic.zones):
            x, y = iso(point)
            if mechanic.kind == "vines" and mechanic.suppressed.get(i, 0) > 0:
                renderer.radius(point, mechanic.radius, ICE, 1)
                continue
            renderer.radius(point, mechanic.radius, color, 2 if warning else 3)
            if not warning and mechanic.kind == "vines":
                pygame.draw.lines(s, VINE, False, [(x - 15, y), (x - 4, y - 8), (x + 4, y), (x + 15, y - 6)], 3)
            elif not warning and mechanic.kind == "repairs" and i * .055 <= mechanic.elapsed <= i * .055 + .45:
                pygame.draw.polygon(s, (168, 155, 135), [(x - 9, y), (x - 3, y - 24), (x + 9, y)])
            elif not warning and mechanic.kind == "cleaning":
                rx, ry = round(mechanic.radius * 39.6), round(mechanic.radius * 19.8)
                pygame.draw.ellipse(s, (97, 55, 110), (x - rx, y - ry, rx * 2, ry * 2))
                renderer.radius(point, mechanic.radius, POTION, 3)
                pygame.draw.circle(s, POTION, (x + 4, y - 2), 3, 1)
        if mechanic.safe is not None and (warning or mechanic.kind == "cleaning"):
            renderer.radius(mechanic.safe, .6, TEAL, 3)
            x, y = iso(mechanic.safe)
            renderer.text("SAFE", x, y + 18, 10, TEAL, center=True)
            if warning and len(mechanic.route) > 1:
                pygame.draw.lines(s, TEAL, False, [iso(p) for p in mechanic.route], 2)
def duty_status(renderer, world):
    """Draw after scene objects so the back wall cannot hide duty names."""
    if not world.keeper:
        return
    summary = "   |   ".join(f"{NAMES[m.kind]} {m.warning / world.keeper.boss.attack_rate:.1f}s" if m.warning > 0 else NAMES[m.kind] for m in world.keeper.mechanics)
    if summary:
        renderer.text(summary, 820, 238, 11, GOLD, center=True)
