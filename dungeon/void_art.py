"""The breach's procedural art and geometry-matched, unobscured warnings."""
from math import atan2, cos, sin

import pygame

from .geometry import Vec
from .tower_art import iso
from .void import LUNGE_REACH, SWEEP_RADIUS, PILLARS

VIOLET = (185, 121, 238)
PALE = (164, 236, 210)
GOLD = (240, 193, 104)
DARK = (46, 30, 69)


def decorate(renderer):
    surface = renderer.floor
    for point, size in ((Vec(8.5, 7.5), 130), (Vec(4.5, 5.5), 42), (Vec(12.5, 5.5), 42)):
        x, y = iso(point)
        for radius in (size, size * .78):
            pygame.draw.arc(surface, (122, 87, 159), (x - radius, y - radius / 2, radius * 2, radius), .3, 5.5, 2)
        for i in range(9):
            a = i * .7
            px, py = x + cos(a) * size * .9, y + sin(a) * size * .45
            pygame.draw.lines(surface, (157, 121, 173), False,
                              [(px - 4, py - 4), (px + 3, py + 2), (px + 6, py - 3)], 1)
    x, y = iso(Vec(8.5, 7.5))
    pygame.draw.lines(surface, (24, 16, 37), False,
                      [(x - 150, y + 20), (x - 90, y + 2), (x - 35, y + 15),
                       (x, y - 10), (x + 40, y - 4), (x + 100, y - 33)], 5)
    # Discarded robes and snapped chains, kept below actors and warning lines.
    for point in (Vec(6.5, 4.5), Vec(12.5, 11.5)):
        x, y = iso(point)
        pygame.draw.polygon(surface, (65, 48, 83), [(x - 20, y), (x - 4, y - 9), (x + 22, y + 3), (x, y + 7)])
        for i in range(5):
            pygame.draw.ellipse(surface, (133, 122, 145), (x + i * 8 - 15, y - 3 + i % 2 * 3, 9, 5), 1)


def pillar(renderer, point, broken=False):
    x, y = iso(point)
    s = renderer.screen
    if broken:
        pygame.draw.polygon(s, (85, 69, 102), [(x - 19, y), (x - 8, y - 12), (x + 3, y - 5), (x + 18, y - 2), (x + 7, y + 7)])
        return
    pygame.draw.polygon(s, (84, 73, 110), [(x - 12, y), (x - 12, y - 43), (x, y - 53), (x + 12, y - 43), (x + 12, y), (x, y + 6)])
    pygame.draw.lines(s, PALE, False, [(x - 6, y - 37), (x + 4, y - 30), (x - 4, y - 20), (x + 4, y - 12)], 2)
    pygame.draw.ellipse(s, VIOLET, (x - 18, y - 6, 36, 16), 2)


def enemy(renderer, actor, time):
    if actor.kind not in ("voidling", "binder", "voidwalker"):
        return False
    x, y = iso(actor.pos)
    s = renderer.screen
    color = (235, 240, 250) if actor.flash > 0 else (139, 216, 248) if actor.frozen > 0 else VIOLET
    bob = 0 if actor.frozen > 0 else round(sin(time * 3 + actor.phase) * 3)
    if actor.kind == "binder":
        pygame.draw.polygon(s, (75, 48, 105), [(x, y - 48), (x - 18, y + 1), (x - 5, y - 4), (x + 4, y + 2), (x + 17, y)])
        pygame.draw.polygon(s, color, [(x - 11, y - 35), (x, y - 53), (x + 11, y - 35)], 2)
        pygame.draw.ellipse(s, (19, 20, 32), (x - 6, y - 42, 12, 12))
        pygame.draw.line(s, PALE, (x - 4, y - 37), (x + 4, y - 37), 2)
        pygame.draw.line(s, (145, 123, 169), (x + 19, y - 5), (x + 19, y - 53), 3)
        pygame.draw.circle(s, color, (x + 19, y - 55), 5, 2)
    elif actor.kind == "voidling":
        pygame.draw.ellipse(s, DARK, (x - 12, y - 29 + bob, 24, 26))
        for i in range(4):
            dx = (i - 1.5) * 8
            pygame.draw.lines(s, color, False, [(x + dx, y - 15 + bob),
                              (x + dx * 1.6, y - 3), (x + dx * 1.8 + sin(time * 4 + i) * 4, y + 3)], 2)
        pygame.draw.circle(s, PALE, (x, y - 19 + bob), 4)
        pygame.draw.circle(s, DARK, (x, y - 19 + bob), 2)
    else:
        renderer.glow(x, y - 35, VIOLET, 65, 28)
        pygame.draw.polygon(s, DARK, [(x - 28, y - 54), (x - 18, y - 78), (x + 18, y - 78),
                                    (x + 28, y - 54), (x + 20, y - 12), (x - 20, y - 12)])
        pygame.draw.lines(s, color, False, [(x - 26, y - 52), (x - 39, y - 31), (x - 47, y - 12)], 7)
        pygame.draw.lines(s, color, False, [(x + 26, y - 52), (x + 39, y - 31), (x + 47, y - 12)], 7)
        for side in (-1, 1):
            pygame.draw.lines(s, color, False, [(x + side * 13, y - 72), (x + side * 27, y - 87), (x + side * 21, y - 65)], 4)
            for i in range(3):
                pygame.draw.line(s, PALE, (x + side * 43, y - 17), (x + side * (47 + i * 4), y - 5 + i * 3), 2)
            pygame.draw.circle(s, PALE, (x + side * 8, y - 64), 4)
            pygame.draw.ellipse(s, (164, 148, 181), (x + side * 32 - 7, y - 30, 14, 10), 2)
        for i in range(5):
            dx = (i - 2) * 10
            pygame.draw.lines(s, color, False, [(x + dx, y - 20), (x + dx * 1.3, y - 4),
                              (x + dx * 1.5 + sin(time * 3 + i) * 6, y + 5)], 3)
        pygame.draw.lines(s, PALE, False, [(x - 6, y - 53), (x + 4, y - 44), (x - 4, y - 35)], 2)
    if actor.kind == "voidwalker" and actor.recovery > 0:
        renderer.text("RECOVERING / +35% DAMAGE", x, y - 117, 10, PALE, center=True)
    return True


def telegraphs(renderer, world):
    fight = world.void
    if not fight:
        return
    s = renderer.screen
    for zone in fight.zones:
        warning = zone.warning > 0
        color = GOLD if warning else VIOLET
        if zone.end is not None:
            direction = (zone.end - zone.pos).unit()
            normal = Vec(-direction.y, direction.x) * (zone.radius + .23)
            pygame.draw.polygon(s, GOLD if warning else PALE,
                                [iso(zone.pos + normal), iso(zone.end + normal),
                                 iso(zone.end - normal), iso(zone.pos - normal)], 2 if warning else 4)
            x, y = iso((zone.pos + zone.end) * .5)
            renderer.text("CONTAINMENT DISCHARGE", x, y + 12, 9, color, center=True)
            continue
        renderer.radius(zone.pos, zone.radius, color, 2 if warning else 4)
        if not warning:
            # Sparse interior rings leave ice, the mage, and other warnings visible.
            renderer.radius(zone.pos, zone.radius * .66, (108, 68, 153), 2)
        x, y = iso(zone.pos)
        label = "VOIDLING" if zone.kind == "summon" else "DARKNESS"
        renderer.text(f"{label} {max(0, zone.warning):.1f}s" if warning else label,
                      x, y + 12, 9, color, center=True)
    boss = fight.boss
    if not boss or not boss.action:
        return
    if boss.action in ("lunge_warning", "lunge"):
        end = boss.attack_origin
        for i in range(1, round(LUNGE_REACH / .1) + 1):
            point = boss.attack_origin + boss.attack_direction * (i * .1)
            if not world.walkable(point, .4):
                break
            end = point
        normal = Vec(-boss.attack_direction.y, boss.attack_direction.x) * .75
        pygame.draw.polygon(s, GOLD, [iso(boss.attack_origin + normal), iso(end + normal),
                                    iso(end - normal), iso(boss.attack_origin - normal)], 2)
        label = "RIFT LUNGE"
    elif boss.action == "sweep":
        angle = atan2(boss.attack_direction.y, boss.attack_direction.x)
        points = [iso(boss.attack_origin)] + [iso(boss.attack_origin + Vec(cos(a), sin(a)) * (SWEEP_RADIUS + .23))
                  for a in (angle - 1.05 + i * 2.1 / 32 for i in range(33))]
        pygame.draw.polygon(s, GOLD, points, 3)
        label = "RENDING SWEEP"
    else:
        renderer.radius(boss.attack_origin, 1.35, GOLD, 3)
        pygame.draw.line(s, GOLD, iso(boss.pos), iso(boss.attack_origin), 2)
        label = "SHATTER THE CHAINS"
    x, y = iso(boss.pos)
    renderer.text(label, x, y + 18, 10, GOLD, center=True)
