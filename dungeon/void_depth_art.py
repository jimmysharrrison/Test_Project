"""Readable tentacle and cosmic arenas, actors, and shared mechanic warnings."""
from math import cos, sin, pi

import pygame

from .geometry import Vec, project
from .tower_art import iso
from .void_art import VIOLET, PALE, GOLD, DARK
from .void_depths import DEPTH_STATS, VoidDepths, NAMES, gaze_end, orbit_points

SKY = (126, 195, 245)
RED = (244, 128, 135)


def decorate(r, world):
    s = r.floor
    if world.level == 7:
        for origin, end in ((Vec(1.5, 3.5), Vec(6.5, 6.5)), (Vec(15.5, 4.5), Vec(11.5, 7.5)),
                            (Vec(2.5, 14.5), Vec(6.5, 11.5)), (Vec(14.5, 14.5), Vec(11.5, 11.5))):
            points = [iso(origin + (end - origin) * (i / 20) + Vec(0, sin(i * .45) * .35)) for i in range(21)]
            pygame.draw.lines(s, (56, 34, 74), False, points, 14)
            pygame.draw.lines(s, (99, 65, 117), False, points, 3)
        x, y = iso(Vec(8.5, 7.5))
        pygame.draw.ellipse(s, (99, 70, 121), (x - 107, y - 31, 214, 62), 2)
        pygame.draw.ellipse(s, (118, 119, 151), (x - 21, y - 24, 42, 48), 2)
        pygame.draw.ellipse(s, (76, 138, 133), (x - 7, y - 18, 14, 36), 2)
    else:
        x, y = iso(Vec(8.5, 7.5))
        for radius in (62, 92, 128, 160):
            pygame.draw.arc(s, (87, 113, 145), (x - radius, y - radius / 2, radius * 2, radius), .3, 5.65, 2)
        for i in range(12):
            a = i * pi / 6
            px, py = x + cos(a) * 145, y + sin(a) * 72
            pygame.draw.circle(s, SKY, (round(px), round(py)), 2)
            pygame.draw.line(s, (70, 95, 126), (px, py), (x + cos(a + .5) * 90, y + sin(a + .5) * 45), 1)
        for point in (Vec(4.5, 5.5), Vec(12.5, 5.5), Vec(8.5, 12.5)):
            px, py = iso(point)
            pygame.draw.lines(s, (123, 141, 165), False,
                              [(px - 18, py - 4), (px, py + 8), (px + 25, py - 7), (px + 8, py - 16)], 2)


def enemy(r, e, time):
    if e.kind not in DEPTH_STATS:
        return False
    x, y = iso(e.pos)
    s = r.screen
    color = (238, 242, 250) if e.flash > 0 else SKY if e.frozen > 0 else VIOLET if e.kind in ("lasher", "grasper", "anchor", "thrall", "oracle") else SKY
    sway = 0 if e.frozen > 0 else sin(time * 2 + e.pos.x) * 4
    if e.kind in ("lasher", "grasper", "anchor"):
        height = 54 if e.kind == "lasher" else 40 if e.kind == "grasper" else 47
        pygame.draw.ellipse(s, DARK, (x - 19, y - 8, 38, 16))
        points = [(x - 13, y), (x - 10, y - 20), (x + 4 + sway, y - height + 8),
                  (x + 17 + sway, y - height), (x + 24 + sway, y - height + 11)]
        pygame.draw.lines(s, (83, 49, 105), False, points, 12 if e.kind == "anchor" else 8)
        pygame.draw.lines(s, color, False, points, 2)
        if e.kind == "grasper":
            for i in range(3):
                pygame.draw.line(s, GOLD, points[-1], (x + 24 + sway - i * 6, y - height + 23 + i * 2), 3)
        elif e.kind == "anchor":
            r.radius(e.pos, .7, PALE, 2)
            pygame.draw.circle(s, PALE, (round(x + 15 + sway), y - height + 9), 6, 2)
    elif e.kind in ("thrall", "gravity_adept"):
        pygame.draw.polygon(s, (65, 48, 91) if e.kind == "thrall" else (36, 58, 93),
                            [(x, y - 50), (x - 18, y), (x + 18, y)])
        pygame.draw.circle(s, (177, 167, 187), (x, y - 45), 7)
        pygame.draw.polygon(s, color, [(x - 12, y - 46), (x, y - 64), (x + 12, y - 46)], 2)
        pygame.draw.line(s, PALE if e.kind == "thrall" else SKY, (x - 4, y - 46), (x + 4, y - 46), 3)
        for side in (-1, 1):
            pygame.draw.line(s, color, (x, y - 28), (x + side * 22, y - 20), 4)
            pygame.draw.circle(s, color, (x + side * 22, y - 23), 4, 1)
        if e.boss_role == "channeler":
            r.radius(e.pos, .65, GOLD, 2)
            r.text("CHANNELER", x, y + 12, 9, GOLD, center=True)
        if e.kind == "gravity_adept":
            pygame.draw.ellipse(s, SKY, (x - 17, y - 37, 34, 13), 1)
    elif e.kind in ("repulsor", "star_fragment"):
        size = 17 if e.kind == "repulsor" else 10
        cy = y - 24 + round(sway)
        pygame.draw.polygon(s, (55, 75, 120), [(x, cy - size), (x + size, cy), (x, cy + size), (x - size, cy)])
        pygame.draw.polygon(s, color, [(x, cy - size), (x + size, cy), (x, cy + size), (x - size, cy)], 2)
        if e.kind == "repulsor":
            pygame.draw.ellipse(s, SKY, (x - 27, cy - 7, 54, 14), 2)
        else:
            pygame.draw.line(s, PALE, (x, cy - 9), (x, cy + 9), 2)
    elif e.kind == "oracle":
        cy = y - 48 + round(sway)
        r.glow(x, cy, VIOLET, 65, 30)
        pygame.draw.ellipse(s, DARK, (x - 40, cy - 25, 80, 52))
        pygame.draw.ellipse(s, color, (x - 35, cy - 18, 70, 36), 3)
        pygame.draw.circle(s, PALE, (x, cy), 15)
        pygame.draw.ellipse(s, DARK, (x - 4, cy - 13, 8, 26))
        for i in range(7):
            a = i * 2 * pi / 7
            px, py = round(x + cos(a) * 45), round(cy + sin(a) * 30)
            pygame.draw.circle(s, color, (px, py), 5, 2)
        for side in (-1, 1):
            pygame.draw.lines(s, color, False, [(x + side * 25, cy + 20), (x + side * 38, y - 10),
                                               (x + side * 25 + sway, y + 5)], 4)
    else:
        cy = y - 45 + round(sway)
        r.glow(x, cy, SKY, 65, 26)
        for rect, start, end in (((x - 48, cy - 42, 96, 78), .2, 5.7),
                                 ((x - 57, cy - 18, 114, 37), .5, 5.9),
                                 ((x - 23, cy - 48, 46, 96), .25, 5.8)):
            pygame.draw.arc(s, GOLD, rect, start, end, 3)
        pygame.draw.polygon(s, (58, 65, 119), [(x, cy - 15), (x - 19, cy + 31), (x + 19, cy + 31)])
        pygame.draw.circle(s, (203, 208, 224), (x, cy - 23), 8)
        pygame.draw.line(s, SKY, (x - 5, cy - 24), (x + 5, cy - 24), 3)
        for i in range(4):
            a = time * .7 + i * pi / 2
            pygame.draw.circle(s, SKY, (round(x + cos(a) * 48), round(cy + sin(a) * 30)), 4)
    return True


def arrow(r, start, end, color):
    a, b = Vec(*iso(start)), Vec(*iso(end))
    d = (b - a).unit()
    n = Vec(-d.y, d.x)
    pygame.draw.line(r.screen, color, (a.x, a.y), (b.x, b.y), 2)
    pygame.draw.polygon(r.screen, color, [(b.x, b.y),
        (b.x - d.x * 8 + n.x * 4, b.y - d.y * 8 + n.y * 4),
        (b.x - d.x * 8 - n.x * 4, b.y - d.y * 8 - n.y * 4)])


def telegraphs(r, world):
    fight = world.void
    if not isinstance(fight, VoidDepths):
        return
    s = r.screen
    previous_clip = s.get_clip()
    s.set_clip(pygame.Rect(300, 166, 1140, 610))
    for e in world.enemies:
        if e.action == "bolt_warning":
            pygame.draw.line(s, GOLD, iso(e.pos), iso(e.attack_origin), 2)
            r.radius(e.attack_origin, .35, GOLD)
        if e.kind == "star_fragment" and e.action == "orbit":
            r.radius(e.attack_origin, 1.4, (69, 112, 151))
        if e.boss_role == "channeler" and fight.boss and e.frozen <= 0:
            pygame.draw.line(s, (118, 91, 143), iso(e.pos), iso(fight.boss.pos), 2)
    label_rows = {}
    for m in fight.mechanics:
        warning = m.warning > 0
        color = GOLD if warning else RED if m.kind in ("lash", "grasp", "chorus", "gaze") else SKY
        if m.kind in ("lash", "gaze"):
            end = fight.line_end(m.pos, gaze_end(m), 8) if m.kind == "gaze" else m.end
            normal = Vec(-(end - m.pos).unit().y, (end - m.pos).unit().x) * (m.radius + .23)
            pygame.draw.polygon(s, color, [iso(m.pos + normal), iso(end + normal), iso(end - normal), iso(m.pos - normal)], 2 if warning else 4)
            if m.kind == "gaze" and warning:
                r.radius(m.pos, 8, (84, 72, 105))
        elif m.kind == "orbit":
            r.radius(m.pos, m.radius, color, 2)
            for p in orbit_points(m):
                r.radius(p, .65, color, 1)
                if not warning:
                    x, y = iso(p)
                    pygame.draw.circle(s, SKY, (x, y - 12), 7)
        elif m.kind in ("convergence", "rejection", "tether", "well"):
            r.radius(m.pos, m.radius, color, 2)
            if m.kind in ("convergence", "well"):
                r.radius(m.pos, 1.5 if m.kind == "convergence" else 1.3,
                         RED if not warning and (m.kind == "convergence" or m.life < .8) else GOLD, 3)
            for i in range(8):
                a = i * pi / 4
                radial = Vec(cos(a), sin(a))
                near = m.pos + radial * min(3, m.radius * .45)
                far = near + radial * .8
                arrow(r, near if m.kind == "rejection" else far, far if m.kind == "rejection" else near, color)
            if m.kind == "tether":
                pygame.draw.line(s, PALE, iso(m.pos), iso(world.player.pos), 2)
        elif m.kind == "communion":
            for p in m.points:
                r.radius(p, .65, color, 2)
        else:
            r.radius(m.pos, m.radius, color, 3)
        x, y = iso(m.pos)
        clock = m.warning / m.owner.attack_rate if warning else max(0, m.life)
        row = label_rows.get((x, y), 0)
        label_rows[x, y] = row + 1
        r.text(f"{NAMES[m.kind]} / {clock:.1f}s", x, y + 20 + row * 13, 9, color, center=True)
    if fight.rooted:
        r.radius(world.player.pos, .6, GOLD, 3)
        pygame.draw.line(s, GOLD, iso(fight.root_owner.pos), iso(world.player.pos), 3)
        x, y = iso(world.player.pos)
        r.text("GRASPED / BREAK OR FREEZE THE LIMB", x, y - 88, 10, GOLD, center=True)
    s.set_clip(previous_clip)
