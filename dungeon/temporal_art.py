"""Headless-safe procedural presentation for the Fractured Hour's tells."""
from math import cos, sin, pi
from types import SimpleNamespace

import pygame

from .geometry import Vec
from .tower_art import iso
from .temporal import TemporalFloor, TEMPORAL_STATS, SURVIVAL_PULL
from .void_art import VIOLET, PALE, GOLD, DARK

CYAN = (132, 217, 245)


def decorate(r):
    s = r.floor
    x, y = iso(Vec(8.5, 7.5))
    for radius in (65, 105, 150):
        pygame.draw.arc(s, (90, 106, 148), (x - radius, y - radius / 2, radius * 2, radius), .15, 5.8, 2)
    for i in range(12):
        a = i * pi / 6
        pygame.draw.line(s, (139, 139, 169), (x + cos(a) * 120, y + sin(a) * 60),
                         (x + cos(a) * 136, y + sin(a) * 68), 2)
    pygame.draw.lines(s, (153, 137, 177), False, [(x - 85, y + 25), (x - 22, y - 5),
                                               (x + 16, y + 14), (x + 100, y - 32)], 3)


def elf(r, pos, color, time, scholar=False):
    x, y = iso(pos)
    s = r.screen
    pygame.draw.polygon(s, (40, 51, 89), [(x, y - 46), (x - 17, y), (x + 17, y)])
    pygame.draw.lines(s, color, False, [(x - 13, y - 3), (x, y - 40), (x + 13, y - 3)], 2)
    pygame.draw.circle(s, (187, 200, 209), (x, y - 46), 7)
    for side in (-1, 1):
        pygame.draw.polygon(s, color, [(x + side * 5, y - 48), (x + side * 14, y - 52), (x + side * 7, y - 42)])
        pygame.draw.line(s, color, (x + side * 7, y - 31), (x + side * 20, y - 19), 3)
    pygame.draw.line(s, color, (x - 8, y - 51), (x + 9, y - 51), 2)
    if scholar:
        pygame.draw.ellipse(s, GOLD, (x + 13, y - 35, 18, 22), 2)
        pygame.draw.line(s, CYAN, (x + 22, y - 32), (x + 22, y - 17), 2)
    else:
        pygame.draw.line(s, color, (x + 20, y - 37), (x + 20, y + 1), 2)
        pygame.draw.polygon(s, PALE, [(x + 20, y - 47), (x + 25, y - 36), (x + 20, y - 29), (x + 15, y - 36)], 1)


def enemy(r, e, time):
    if e.kind not in TEMPORAL_STATS:
        return False
    x, y = iso(e.pos)
    color = (240, 245, 250) if e.flash > 0 else CYAN if e.frozen > 0 else VIOLET
    if e.kind in ("rift_warden", "chronal_scholar"):
        elf(r, e.pos, color, time, e.kind == "chronal_scholar")
    elif e.kind == "dimensional_anchor":
        r.glow(x, y - 27, CYAN, 44, 32)
        pygame.draw.polygon(r.screen, (45, 48, 89), [(x, y - 65), (x + 21, y - 29), (x, y), (x - 21, y - 29)])
        pygame.draw.polygon(r.screen, color, [(x, y - 65), (x + 21, y - 29), (x, y), (x - 21, y - 29)], 3)
        pygame.draw.line(r.screen, PALE, (x, y - 54), (x, y - 10), 3)
        pygame.draw.ellipse(r.screen, GOLD, (x - 30, y - 42, 60, 24), 2)
    else:
        r.glow(x, y - 35, VIOLET, 70, 30)
        pygame.draw.ellipse(r.screen, (14, 12, 30), (x - 35, y - 81, 70, 86))
        pygame.draw.ellipse(r.screen, color, (x - 36, y - 82, 72, 88), 3)
        pygame.draw.arc(r.screen, GOLD, (x - 45, y - 91, 90, 106), .3, 5.8, 3)
        for i in range(8):
            a = i * pi / 4
            pygame.draw.line(r.screen, PALE, (x + cos(a) * 38, y - 38 + sin(a) * 46),
                             (x + cos(a) * 45, y - 38 + sin(a) * 53), 2)
        pygame.draw.lines(r.screen, VIOLET, False, [(x - 14, y - 63), (x + 10, y - 39), (x - 8, y - 16)], 3)
    return True


def portal(r, point, warning):
    x, y = iso(point)
    r.radius(point, .85, GOLD, 2)
    pygame.draw.ellipse(r.screen, VIOLET, (x - 15, y - 47, 30, 49), 2)
    r.text(f"PORTAL / {max(0, warning):.1f}s", x, y + 15, 9, GOLD, center=True)


def telegraphs(r, world):
    t = world.void
    if not isinstance(t, TemporalFloor):
        return
    previous = r.screen.get_clip()
    r.screen.set_clip(pygame.Rect(300, 166, 1140, 610))
    for e in world.enemies:
        if e.action == "rift_warning":
            portal(r, e.attack_origin, e.action_time / e.attack_rate)
            r.radius(e.pos, .65, VIOLET, 2)
        elif e.action == "time_shot":
            pygame.draw.line(r.screen, GOLD, iso(e.pos), iso(e.attack_origin), 2)
    for arrival in t.portals:
        portal(r, arrival.pos, arrival.warning)
    for f in t.fields:
        color = GOLD if f.warning > 0 else CYAN
        r.radius(f.pos, f.radius, color, 3)
        x, y = iso(f.pos)
        label = f"STASIS IN {f.warning:.1f}s" if f.warning > 0 else f"SHOTS PAUSED / RELEASE {f.life:.1f}s"
        r.text(label, x, y + 23, 9, color, center=True)
        if f.warning <= 0 and f.life < .5:
            r.radius(f.pos, f.radius * .85, GOLD, 2)
    for echo in t.echoes:
        x, y = iso(echo.pos)
        pygame.draw.polygon(r.screen, PALE, [(x, y - 46), (x - 14, y), (x + 14, y)], 1)
        pygame.draw.circle(r.screen, PALE, (x, y - 49), 6, 1)
        pygame.draw.line(r.screen, PALE, (x, y - 15), iso(echo.pos + echo.direction * 5), 1)
        r.text(f"ECHO / {echo.warning:.1f}s", x, y + 13, 9, PALE, center=True)
    if t.stage_name == "demonstration":
        point = Vec(6.5, 10.5)
        elf(r, point, PALE, t.scene_time)
        x, y = iso(point)
        if t.stage_left < 2.7:
            r._prison_shell(SimpleNamespace(stasis=2.5), x, y, 1)
        r.text("WARDEN: ICE HOLDS AGAINST THE VOID", x, y + 15, 10, PALE, center=True)
    if t.stopped:
        x, y = iso(t.boss.pos)
        r.radius(t.boss.pos, 1.6, VIOLET, 3)
        if t.stage_left < SURVIVAL_PULL:
            for i in range(10):
                a = i * pi / 5
                near = t.boss.pos + Vec(cos(a), sin(a)) * 2
                far = t.boss.pos + Vec(cos(a), sin(a)) * 3
                pygame.draw.line(r.screen, PALE, iso(far), iso(near), 2)
        anchored = world.player.stasis > 0
        r.text("TIME STOPPED / " + ("ANCHORED IN ICE" if anchored else "PRESS R NOW"), 850, 664, 23,
               CYAN if anchored else GOLD, bold=True, center=True)
        r.text(f"{'Safe practice' if t.stage_name == 'practice' else 'Breach pulse'} / {t.stage_left:.2f}s", 850, 699, 13, PALE, center=True)
    elif t.stage_name == "retry":
        r.text(f"CHECKPOINT RESTORES IN {t.stage_left:.1f}s", 850, 664, 21, GOLD, center=True)
    r.screen.set_clip(previous)
