"""An oversized tentacled torso emerging from a floor rupture; no locomotion."""
from math import cos, sin, pi

import pygame

from .geometry import Vec
from .tower_art import iso
from .maw import BOSS_POS, MawFloor, MINION_CAP
from .void_art import GOLD, PALE, VIOLET

FLESH = (67, 81, 91)
EDGE = (142, 104, 169)
EYE = (151, 240, 191)


def decorate(r):
    s = r.floor
    x, y = iso(BOSS_POS)
    for radius in (82, 121, 165):
        pygame.draw.ellipse(s, (89, 64, 113), (x - radius, y - radius / 2, radius * 2, radius), 2)
    for i in range(12):
        a = i * pi / 6
        pygame.draw.lines(s, (74, 56, 98), False,
                          [(x + cos(a) * 90, y + sin(a) * 45),
                           (x + cos(a + .1) * 154, y + sin(a + .1) * 77),
                           (x + cos(a) * 210, y + sin(a) * 105)], 3)
    for point in (Vec(4.5, 6.5), Vec(12.5, 6.5), Vec(8.5, 11.5)):
        px, py = iso(point)
        pygame.draw.ellipse(s, (105, 103, 127), (px - 18, py - 8, 36, 16), 2)
        pygame.draw.line(s, (128, 106, 146), (px - 6, py + 3), (px + 7, py - 5), 2)


def enemy(r, e, time):
    if e.kind != "devourer":
        return False
    x, y = iso(e.pos)
    s = r.screen
    color = (226, 243, 248) if e.flash > 0 else (144, 209, 237) if e.frozen > 0 else EDGE
    motion = 0 if e.frozen > 0 else time
    r.glow(x, y - 42, VIOLET, 155, 48)
    # A flat aperture and its foreground lip make the missing lower half clear.
    pygame.draw.ellipse(s, (8, 8, 23), (x - 130, y - 37, 260, 78))
    pygame.draw.ellipse(s, color, (x - 130, y - 37, 260, 78), 3)
    for side in (-1, 1):
        for limb in range(4):
            points = []
            for i in range(25):
                t = i / 24
                px = x + side * (41 + t * (76 + limb * 15))
                py = y - 95 + limb * 18 + t * (57 - limb * 3)
                py += sin(t * pi * 2 + limb * .8 + motion * .85) * (8 + t * 11)
                points.append((round(px), round(py)))
            pygame.draw.lines(s, (35, 40, 65), False, points, 19 - limb * 3)
            pygame.draw.lines(s, color, False, points, 3)
            for i in (10, 15, 20):
                pygame.draw.circle(s, (103, 148, 151), points[i], 3)
    pygame.draw.ellipse(s, FLESH, (x - 67, y - 166, 134, 170))
    pygame.draw.ellipse(s, color, (x - 67, y - 166, 134, 170), 3)
    pygame.draw.polygon(s, (45, 53, 76), [(x - 62, y - 83), (x - 78, y - 28),
                                        (x - 48, y + 17), (x + 48, y + 17),
                                        (x + 78, y - 28), (x + 62, y - 83)])
    # Alien brows and an uneven cluster of eyes above the facial tentacles.
    for dx, dy, radius in ((-29, -127, 9), (28, -126, 10), (0, -143, 6), (-44, -104, 5), (44, -104, 5)):
        pygame.draw.circle(s, (15, 17, 34), (x + dx, y + dy), radius + 4)
        pygame.draw.circle(s, EYE if e.frozen <= 0 else PALE, (x + dx, y + dy), radius)
        pygame.draw.line(s, (10, 15, 27), (x + dx, y + dy - radius + 1), (x + dx, y + dy + radius - 1), 3)
    pygame.draw.ellipse(s, (9, 8, 23), (x - 24, y - 94, 48, 63))
    for i in range(7):
        a = i * pi / 3.5
        pygame.draw.polygon(s, PALE, [(x + cos(a) * 23, y - 64 + sin(a) * 29),
                                      (x + cos(a + .18) * 21, y - 64 + sin(a + .18) * 28),
                                      (x + cos(a + .09) * 12, y - 64 + sin(a + .09) * 16)])
    for i in range(7):
        dx = (i - 3) * 10
        points = [(round(x + dx + sin(j * .4 + i + motion) * j * .7),
                   round(y - 99 + j * 4)) for j in range(19)]
        pygame.draw.lines(s, (42, 64, 73), False, points, 8)
        pygame.draw.lines(s, color, False, points, 2)
    # Broken floor plates hide the torso below the aperture's front edge.
    pygame.draw.arc(s, (16, 14, 34), (x - 130, y - 37, 260, 78), pi, 2 * pi, 9)
    pygame.draw.arc(s, color, (x - 130, y - 37, 260, 78), pi, 2 * pi, 3)
    for dx in (-111, -77, 66, 102):
        pygame.draw.polygon(s, (63, 66, 84), [(x + dx - 13, y + 14), (x + dx, y + 3),
                                            (x + dx + 18, y + 22), (x + dx - 7, y + 28)])
    return True


def telegraphs(r, world):
    f = world.void
    if not isinstance(f, MawFloor):
        return
    clip = r.screen.get_clip()
    r.screen.set_clip(pygame.Rect(300, 166, 1140, 610))
    for arrival in f.arrivals:
        r.radius(arrival.pos, .9, GOLD, 3)
        x, y = iso(arrival.pos)
        pygame.draw.ellipse(r.screen, VIOLET, (x - 15, y - 49, 30, 48), 2)
        r.text(arrival.kind.replace("_", " ").upper(), x, y - 61, 9, GOLD, center=True)
        r.text(f"ARRIVAL / {max(0, arrival.warning / arrival.owner.attack_rate):.1f}s", x, y + 18, 9, GOLD, center=True)
    if f.boss and not f.finished:
        r.text(f"BREACH SUMMONS / {sum(e.summoned for e in world.enemies)} / {MINION_CAP}",
               850, 749, 10, PALE, center=True)
    r.screen.set_clip(clip)
