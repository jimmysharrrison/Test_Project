"""Procedural isometric art and interface; no external art assets required."""

from math import cos, pi, sin
from random import Random

import pygame

from .geometry import Vec, project
from .world import LAYOUT

WIDTH, HEIGHT = 1440, 900
ORIGIN = Vec(857, 226)
INK = (12, 17, 23)
PANEL = (19, 26, 33)
LINE = (48, 57, 64)
GOLD = (214, 180, 113)
WHITE = (232, 230, 217)
MUTED = (130, 146, 152)
TEAL = (100, 212, 189)
RED = (215, 96, 99)
VIOLET = (183, 124, 233)


def iso(pos):
    point = project(pos, ORIGIN)
    return round(point.x), round(point.y)


class Renderer:
    def __init__(self, screen, world):
        self.screen = screen
        self.fonts = {}
        self.glows = {}
        self.sound_enabled = True
        self.floor = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._build_floor(world)
        rng = Random(21)
        self.dust = [(rng.uniform(340, 1395), rng.uniform(190, 760), rng.uniform(0, 6)) for _ in range(45)]

    def font(self, size, serif=False, bold=False):
        key = (size, serif, bold)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont("dejavuserif" if serif else "dejavusans", size, bold=bold)
        return self.fonts[key]

    def text(self, text, x, y, size=15, color=WHITE, serif=False, bold=False, center=False):
        surface = self.font(size, serif, bold).render(str(text), True, color)
        rect = surface.get_rect(midtop=(x, y)) if center else surface.get_rect(topleft=(x, y))
        self.screen.blit(surface, rect)
        return rect

    def spaced(self, text, x, y, size=11, color=MUTED, spacing=2):
        for letter in text:
            rect = self.text(letter, x, y, size, color)
            x += rect.width + spacing

    def glow(self, x, y, color, radius=50, strength=38):
        key = (color, radius, strength)
        if key not in self.glows:
            surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for r in range(radius, 0, -3):
                alpha = round(strength * (1 - r / radius) ** 1.6)
                pygame.draw.circle(surface, (*color, alpha), (radius, radius), r)
            self.glows[key] = surface
        self.screen.blit(self.glows[key], (x - radius, y - radius))

    def _build_floor(self, world):
        rng = Random(42)
        corners = [iso(Vec(0, 0)), iso(Vec(17, 0)), iso(Vec(17, 17)), iso(Vec(0, 17))]
        for drop in range(30, 0, -1):
            pygame.draw.polygon(self.floor, (15 + drop // 6, 21 + drop // 5, 27 + drop // 5),
                                [(x, y + drop) for x, y in corners])
        for y, row in enumerate(LAYOUT):
            for x, _ in enumerate(row):
                polygon = [iso(Vec(x, y)), iso(Vec(x + 1, y)), iso(Vec(x + 1, y + 1)), iso(Vec(x, y + 1))]
                noise = rng.randrange(-5, 6)
                base = (40 + noise, 51 + noise, 59 + noise)
                if (x, y) in world.walls:
                    base = (28, 37, 45)
                pygame.draw.polygon(self.floor, base, polygon)
                pygame.draw.polygon(self.floor, (26, 36, 44), polygon, 1)
                if rng.random() < 0.15 and (x, y) not in world.walls:
                    px, py = iso(Vec(x + 0.5, y + 0.5))
                    pygame.draw.lines(self.floor, (30, 41, 48), False,
                                      [(px - 9, py - 4), (px - 2, py), (px - 5, py + 4)], 1)
                if x in (1, 15) or y in (1, 15):
                    px, py = iso(Vec(x + 0.5, y + 0.5))
                    pygame.draw.line(self.floor, (76, 74, 62), (px - 4, py), (px + 4, py), 1)
        # The entrance is picked out in brass rather than a separate image asset.
        for pos in (Vec(2.5, 13.5), Vec(3.5, 13.5), Vec(4.5, 13.5)):
            px, py = iso(pos)
            pygame.draw.polygon(self.floor, (108, 103, 77), [(px, py - 6), (px + 12, py), (px, py + 6), (px - 12, py)], 1)

    def shadow(self, x, y, width=26):
        pygame.draw.ellipse(self.screen, (22, 29, 35), (x - width // 2, y - 4, width, 10))

    def wall(self, tile, world):
        x, y = tile
        front = x == 16 or y == 16
        height = 9 if front else 38 if x in (0, 16) or y in (0, 16) else 31
        ground = [iso(Vec(x, y)), iso(Vec(x + 1, y)), iso(Vec(x + 1, y + 1)), iso(Vec(x, y + 1))]
        roof = [(px, py - height) for px, py in ground]
        pygame.draw.polygon(self.screen, (36, 47, 56), [roof[1], roof[2], ground[2], ground[1]])
        pygame.draw.polygon(self.screen, (47, 58, 66), [roof[2], roof[3], ground[3], ground[2]])
        pygame.draw.polygon(self.screen, (68, 79, 86) if not front else (61, 71, 76), roof)
        pygame.draw.lines(self.screen, (85, 95, 99), False, [roof[3], roof[0], roof[1]], 1)
        pygame.draw.lines(self.screen, (29, 39, 47), False, [ground[3], ground[2], ground[1]], 1)
        if height > 20:
            middle = height // 2
            pygame.draw.lines(self.screen, (29, 40, 49), False,
                              [(ground[3][0], ground[3][1] - middle), (ground[2][0], ground[2][1] - middle),
                               (ground[1][0], ground[1][1] - middle)], 1)

    def player(self, player, time, at=None, scale=1):
        x, y = at or iso(player.pos)
        s = scale
        def p(dx, dy):
            return round(x + dx * s), round(y + dy * s)
        def poly(color, points):
            pygame.draw.polygon(self.screen, color, [p(dx, dy) for dx, dy in points])
        self.shadow(x, y, round(28 * s))
        if player.dash_time > 0:
            self.glow(x, y - 12, TEAL, 45, 55)
        flash = player.flash > 0
        cape = WHITE if flash else (27, 113, 120)
        sway = sin(time * 5) * 2
        poly((13, 51, 67), [(-10, -23), (8, -23), (13 + sway, 0), (-12 + sway, -4)])
        poly(cape, [(-9, -25), (6, -25), (7 + sway, -1), (-11 + sway, -5)])
        pygame.draw.line(self.screen, (19, 29, 40), p(-4, -5), p(-5, 1), max(1, round(5 * s)))
        pygame.draw.line(self.screen, (19, 29, 40), p(5, -5), p(6, 0), max(1, round(5 * s)))
        poly(WHITE if flash else (123, 148, 151), [(-8, -27), (7, -27), (9, -14), (0, -9), (-9, -14)])
        poly((57, 84, 94), [(0, -25), (7, -25), (8, -14), (0, -11)])
        pygame.draw.line(self.screen, GOLD, p(-8, -13), p(8, -13), max(1, round(2 * s)))
        poly(GOLD, [(-13, -26), (-6, -30), (-3, -23), (-11, -20)])
        poly((157, 136, 95), [(5, -29), (12, -26), (11, -20), (5, -22)])
        pygame.draw.circle(self.screen, (192, 195, 178) if not flash else WHITE, p(0, -34), round(7 * s))
        poly((63, 86, 99), [(-7, -35), (1, -40), (7, -35), (6, -30), (-6, -30)])
        pygame.draw.line(self.screen, GOLD, p(-4, -33), p(4, -33), max(1, round(s)))
        pygame.draw.line(self.screen, (207, 218, 213), p(0, -40), p(0, -28), max(1, round(s)))
        pygame.draw.line(self.screen, (94, 79, 64), p(13, -27), p(13, -8), max(1, round(2 * s)))
        poly((204, 214, 206), [(13, -28), (20, -31), (21, -22), (13, -20)])
        pygame.draw.line(self.screen, WHITE, p(20, -30), p(21, -23), max(1, round(s)))
        if scale == 1:
            pygame.draw.polygon(self.screen, TEAL, [p(0, 6), p(4, 9), p(0, 12), p(-4, 9)])

    def enemy(self, enemy, time):
        x, y = iso(enemy.pos)
        self.shadow(x, y, 24)
        flash = enemy.flash > 0
        if enemy.kind == "skitter":
            color = WHITE if flash else (121, 154, 140)
            for side in (-1, 1):
                for leg in range(3):
                    wave = sin(time * 14 + leg) * 2
                    pygame.draw.lines(self.screen, (79, 119, 116), False,
                                      [(x + side * 3, y - 7), (x + side * (10 + leg), y - 13 + leg * 4),
                                       (x + side * (15 + wave), y - 8 + leg * 4)], 2)
            pygame.draw.ellipse(self.screen, color, (x - 8, y - 18, 16, 17))
            pygame.draw.circle(self.screen, (220, 132, 110), (x - 3, y - 11), 2)
            pygame.draw.circle(self.screen, (220, 132, 110), (x + 3, y - 11), 2)
        else:
            bob = round(sin(time * 6 + enemy.pos.x) * 1.5)
            color = WHITE if flash else (125, 77, 94)
            pygame.draw.polygon(self.screen, (68, 43, 65), [(x - 7, y - 22 + bob), (x + 7, y - 22 + bob), (x + 11, y), (x - 10, y)])
            pygame.draw.polygon(self.screen, color, [(x, y - 29 + bob), (x + 10, y - 20 + bob), (x + 7, y - 7), (x - 8, y - 8), (x - 10, y - 20 + bob)])
            pygame.draw.circle(self.screen, WHITE if flash else (173, 164, 147), (x, y - 28 + bob), 6)
            pygame.draw.line(self.screen, (231, 113, 94), (x - 3, y - 28 + bob), (x + 3, y - 28 + bob), 2)
            pygame.draw.line(self.screen, (87, 73, 66), (x + 12, y - 4), (x + 12, y - 28), 2)
            pygame.draw.polygon(self.screen, (150, 158, 149), [(x + 12, y - 35), (x + 8, y - 26), (x + 15, y - 26)])
        if enemy.hp < enemy.max_hp:
            self.bar(x - 15, y - 42, 30, 3, enemy.hp / enemy.max_hp, RED)

    def spawner(self, spawner, time):
        x, y = iso(spawner.pos)
        pulse = sin(time * 3 + spawner.pos.x)
        self.glow(x, y - 22, VIOLET, 65, 56)
        pygame.draw.ellipse(self.screen, (83, 57, 105), (x - 29, y - 12, 58, 27), 1)
        for i in range(6):
            angle = i * pi / 3 + time * 0.35
            px, py = x + cos(angle) * 28, y + sin(angle) * 12
            pygame.draw.circle(self.screen, (159, 112, 193), (round(px), round(py)), 2)
        pygame.draw.polygon(self.screen, (42, 33, 61), [(x - 20, y), (x, y + 10), (x + 20, y), (x + 20, y - 9), (x - 20, y - 9)])
        pygame.draw.polygon(self.screen, (75, 62, 91), [(x - 20, y - 9), (x, y - 19), (x + 20, y - 9), (x, y + 1)])
        color = WHITE if spawner.flash else VIOLET
        for side in (-1, 1):
            sx = x + side * 17
            pygame.draw.polygon(self.screen, (71, 59, 87), [(sx - 5, y - 9), (sx - 4, y - 36), (sx + 1, y - 43), (sx + 5, y - 11)])
            pygame.draw.line(self.screen, (150, 114, 174), (sx, y - 38), (sx, y - 19), 1)
        pygame.draw.ellipse(self.screen, color, (x - 9, y - 48 + pulse * 2, 18, 34), 2)
        pygame.draw.ellipse(self.screen, (220, 190, 250), (x - 3, y - 43 + pulse * 2, 6, 25))
        self.bar(x - 25, y - 61, 50, 3, spawner.hp / 176, VIOLET)

    def torch(self, pos, time):
        x, y = iso(pos)
        self.glow(x, y - 20, (242, 163, 81), 88, 39)
        self.shadow(x, y, 20)
        pygame.draw.polygon(self.screen, (77, 68, 55), [(x - 7, y), (x + 7, y), (x + 4, y - 22), (x - 4, y - 22)])
        pygame.draw.ellipse(self.screen, (156, 118, 67), (x - 10, y - 26, 20, 9))
        sway = sin(time * 9 + pos.x) * 3
        pygame.draw.polygon(self.screen, (238, 147, 67), [(x - 7, y - 24), (x + sway, y - 45), (x + 7, y - 24)])
        pygame.draw.polygon(self.screen, (255, 218, 135), [(x - 3, y - 24), (x - sway, y - 37), (x + 3, y - 24)])

    def gate(self, world, time):
        x, y = iso(world.exit)
        color = TEAL if world.exit_open else (110, 118, 129)
        self.glow(x, y - 20, TEAL if world.exit_open else (87, 110, 145), 70, 35)
        pygame.draw.ellipse(self.screen, color, (x - 27, y - 10, 54, 23), 1)
        for side in (-1, 1):
            sx = x + 23 * side
            pygame.draw.rect(self.screen, (67, 80, 86), (sx - 5, y - 55, 10, 55))
            pygame.draw.rect(self.screen, (92, 104, 106), (sx - 7, y - 57, 14, 7))
            pygame.draw.line(self.screen, color, (sx, y - 45), (sx, y - 13), 2)
        pygame.draw.arc(self.screen, color, (x - 24, y - 77, 48, 49), 0, pi, 4)
        if world.exit_open:
            for i in range(5):
                yy = y - 8 - ((time * 25 + i * 10) % 50)
                pygame.draw.circle(self.screen, TEAL, (round(x + sin(i * 4 + time) * 12), round(yy)), 1)
        else:
            pygame.draw.polygon(self.screen, GOLD, [(x, y - 38), (x + 6, y - 30), (x, y - 22), (x - 6, y - 30)], 1)

    def pickup(self, pickup, time):
        x, y = iso(pickup.pos)
        bob = round(sin(time * 3 + pickup.pos.x) * 2)
        self.shadow(x, y, 16)
        if pickup.kind == "gold":
            self.glow(x, y - 4, GOLD, 25, 28)
            for dx, dy in ((-4, 0), (3, -2), (0, -5)):
                pygame.draw.ellipse(self.screen, (142, 110, 57), (x + dx - 4, y + dy - 5 + bob, 8, 6))
                pygame.draw.ellipse(self.screen, GOLD, (x + dx - 4, y + dy - 6 + bob, 8, 4))
        else:
            pygame.draw.ellipse(self.screen, (171, 119, 72), (x - 8, y - 11 + bob, 16, 10))
            pygame.draw.line(self.screen, (239, 204, 151), (x - 3, y - 9 + bob), (x + 1, y - 6 + bob), 2)
            pygame.draw.line(self.screen, (239, 204, 151), (x + 2, y - 10 + bob), (x + 5, y - 7 + bob), 2)
            self.text("+", x + 9, y - 20, 14, TEAL)

    def projectile(self, shot, time):
        x, y = iso(shot.pos)
        velocity = project(shot.velocity)
        direction = velocity.unit()
        pygame.draw.line(self.screen, (109, 126, 114), (x - direction.x * 16, y - 15 - direction.y * 16), (x, y - 15), 2)
        points = []
        for i in range(4):
            angle = time * 28 + i * pi / 2
            radius = 8 if i % 2 == 0 else 4
            points.append((x + cos(angle) * radius, y - 15 + sin(angle) * radius))
        pygame.draw.polygon(self.screen, (222, 220, 184), points)
        pygame.draw.circle(self.screen, GOLD, (x, y - 15), 2)

    def effect(self, effect):
        x, y = iso(effect.pos)
        age = 1 - effect.life / effect.duration
        color = TEAL if effect.kind in ("heal", "dash") else GOLD if effect.kind in ("gold", "swing", "spark") else VIOLET if effect.kind in ("spawn", "burst") else RED
        if effect.kind in ("burst", "spawn", "heal", "dash", "swing", "hurt"):
            radius = round(8 + age * 29)
            pygame.draw.ellipse(self.screen, color, (x - radius, y - radius / 2, radius * 2, radius), 1)
        if effect.kind in ("hit", "spark", "burst"):
            for i in range(6):
                angle = i * pi / 3
                distance = age * 27
                pygame.draw.circle(self.screen, color, (round(x + cos(angle) * distance), round(y - 15 + sin(angle) * distance * 0.7)), 2 if age < 0.6 else 1)
        if effect.text:
            self.text(effect.text, x, y - 42 - age * 22, 15, color, bold=True, center=True)

    def bar(self, x, y, width, height, fraction, color):
        pygame.draw.rect(self.screen, (34, 39, 46), (x, y, width, height), border_radius=min(2, height // 2))
        if fraction > 0:
            pygame.draw.rect(self.screen, color, (x, y, round(width * min(1, fraction)), height), border_radius=min(2, height // 2))

    def key(self, text, x, y, width=28):
        pygame.draw.rect(self.screen, (34, 44, 51), (x, y, width, 25), border_radius=4)
        pygame.draw.rect(self.screen, (65, 76, 82), (x, y, width, 25), 1, border_radius=4)
        self.text(text, x + width / 2, y + 4, 11, WHITE, center=True)

    def hud(self, world):
        player = world.player
        pygame.draw.rect(self.screen, PANEL, (24, 24, 259, 852), border_radius=12)
        pygame.draw.rect(self.screen, LINE, (24, 24, 259, 852), 1, border_radius=12)
        self.spaced("EMBERVAULT", 47, 49, 21, GOLD, 1)
        self.spaced("THE FIRST DESCENT", 49, 84, 10, MUTED, 2)
        pygame.draw.line(self.screen, LINE, (47, 119), (259, 119))
        self.spaced("YOUR CHAMPION", 48, 141, 10)
        pygame.draw.circle(self.screen, (28, 43, 50), (153, 229), 55)
        pygame.draw.circle(self.screen, (65, 85, 87), (153, 229), 55, 1)
        self.glow(153, 229, TEAL, 58, 24)
        self.player(player, world.time, (153, 267), 1.85)
        self.text("The Warden", 153, 292, 23, WHITE, serif=True, center=True)
        self.text("IRON WILL. SHARP STEEL.", 153, 328, 10, MUTED, center=True)
        self.spaced("VITALITY", 48, 366, 10)
        self.text(f"{player.hp} / 100", 197, 362, 12, WHITE)
        self.bar(48, 390, 210, 8, player.hp / 100, RED)
        self.key("E", 48, 417)
        self.text("Healing potion", 86, 419, 12, WHITE)
        self.text(f"×{player.potions}", 232, 417, 16, GOLD)
        self.key("SPC", 48, 454, 35)
        self.text("Dash", 94, 457, 12, WHITE)
        self.text("READY" if player.dash_cooldown <= 0 else f"{player.dash_cooldown:.1f}s", 211, 458, 10, TEAL if player.dash_cooldown <= 0 else MUTED)
        self.bar(94, 479, 164, 3, 1 - player.dash_cooldown / 1.4, TEAL)
        pygame.draw.line(self.screen, LINE, (47, 507), (259, 507))
        self.spaced("THE OBJECTIVE", 48, 531, 10)
        objectives = [
            (f"Seal the rifts", f"{3 - len(world.spawners)} / 3", not world.spawners),
            ("Clear the chamber", str(len(world.enemies)), not world.enemies),
            ("Reach the gate", "OPEN" if world.exit_open else "SEALED", world.exit_open),
        ]
        for i, (label, value, done) in enumerate(objectives):
            yy = 562 + i * 33
            pygame.draw.circle(self.screen, TEAL if done else (83, 94, 100), (53, yy + 7), 3, 0 if done else 1)
            self.text(label, 66, yy, 11, WHITE if done else MUTED)
            self.text(value, 217 if i < 2 else 209, yy, 10, TEAL if done else GOLD)
        pygame.draw.line(self.screen, LINE, (47, 678), (259, 678))
        self.spaced("THIS DESCENT", 48, 702, 10)
        self.text(f"{player.gold:04d}", 48, 730, 27, GOLD, serif=True)
        self.text("GOLD", 50, 769, 10, MUTED)
        self.text(f"{player.kills:02d}", 178, 730, 27, WHITE, serif=True)
        self.text("SLAIN", 179, 769, 10, MUTED)
        self.text("A Gauntlet-inspired adventure", 153, 835, 10, MUTED, center=True)

    def draw(self, world, mouse=None, mode="playing"):
        self.screen.fill(INK)
        pygame.draw.circle(self.screen, (16, 24, 31), (875, 468), 375)
        self.spaced("CHAPTER I    /    THE FORSAKEN DEPTHS", 324, 39, 10, GOLD, 2)
        self.text("The Hollow Sanctum", 320, 64, 36, WHITE, serif=True)
        self.text("Break the rifts. Hold your ground. Find the way out.", 323, 116, 13, MUTED)
        self.text("DEPTH", 1302, 49, 10, MUTED)
        self.text("01", 1299, 65, 36, GOLD, serif=True)
        self.text("M / SOUND " + ("ON" if self.sound_enabled else "OFF"), 1266, 121, 10, MUTED)
        pygame.draw.line(self.screen, LINE, (324, 155), (1396, 155))
        self.screen.blit(self.floor, (0, 0))
        for spawner in world.spawners:
            x, y = iso(spawner.pos)
            self.glow(x, y, VIOLET, 95, 35)
        # Render all solid objects in their world depth, including the hero.
        objects = [(x + y + 1, "wall", (x, y)) for x, y in world.walls]
        objects += [(p.pos.x + p.pos.y, "pickup", p) for p in world.pickups]
        objects += [(s.pos.x + s.pos.y, "spawner", s) for s in world.spawners]
        objects += [(e.pos.x + e.pos.y, "enemy", e) for e in world.enemies]
        objects += [(p.pos.x + p.pos.y, "projectile", p) for p in world.projectiles]
        objects.append((world.player.pos.x + world.player.pos.y, "player", world.player))
        objects.append((world.exit.x + world.exit.y, "gate", None))
        torches = (Vec(2.5, 7.5), Vec(7.5, 2.5), Vec(14.5, 10.5), Vec(8.5, 14.5))
        objects += [(p.x + p.y, "torch", p) for p in torches]
        for _, kind, obj in sorted(objects, key=lambda item: (item[0], item[1])):
            if kind == "wall":
                self.wall(obj, world)
            elif kind == "player":
                self.player(obj, world.time)
            elif kind == "gate":
                self.gate(world, world.time)
            else:
                getattr(self, kind)(obj, world.time)
        for effect in world.effects:
            self.effect(effect)
        for x, y, phase in self.dust:
            px = round(x + sin(world.time * 0.15 + phase) * 10)
            py = round(y - (world.time * 3 + phase * 10) % 40)
            pygame.draw.circle(self.screen, (78, 79, 69), (px, py), 1)
        self.hud(world)
        pygame.draw.rect(self.screen, PANEL, (323, 787, 1073, 89), border_radius=8)
        pygame.draw.rect(self.screen, LINE, (323, 787, 1073, 89), 1, border_radius=8)
        self.key("WASD", 345, 806, 51)
        self.text("Move", 407, 811, 12, WHITE)
        self.key("LMB", 489, 806, 42)
        self.text("Throw axe", 541, 811, 12, WHITE)
        self.key("SPACE", 666, 806, 55)
        self.text("Dash", 731, 811, 12, WHITE)
        self.key("E", 809, 806)
        self.text("Heal", 848, 811, 12, WHITE)
        self.key("ESC", 922, 806, 40)
        self.text("Pause", 974, 811, 12, WHITE)
        elapsed = int(world.time)
        self.text(f"{elapsed // 60:02d}:{elapsed % 60:02d}", 1310, 807, 17, GOLD)
        self.text(world.message if world.message_time > 0 else "Keep moving. The rifts will keep calling them back.", 345, 847, 11, MUTED)
        if mouse and mode == "playing" and world.state == "playing" and mouse[0] > 300:
            x, y = mouse
            pygame.draw.circle(self.screen, GOLD, (x, y), 9, 1)
            pygame.draw.circle(self.screen, GOLD, (x, y), 2)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                pygame.draw.line(self.screen, GOLD, (x + dx * 12, y + dy * 12), (x + dx * 16, y + dy * 16), 1)
        if mode != "playing" or world.state != "playing":
            self.overlay(world, mode)

    def overlay(self, world, mode):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((5, 10, 16, 182))
        self.screen.blit(veil, (0, 0))
        rect = pygame.Rect(477, 254, 750, 392)
        pygame.draw.rect(self.screen, (20, 29, 36), rect, border_radius=12)
        pygame.draw.rect(self.screen, (110, 100, 75), rect, 1, border_radius=12)
        center = rect.centerx
        if world.state == "dead":
            kicker, title, subtitle = "THE DUNGEON ENDURES", "Your watch has ended.", "Another descent. Another chance."
            action = "R  /  TRY AGAIN"
        elif world.state == "won":
            kicker, title, subtitle = "THE SANCTUM IS SILENT", "You made it out.", f"{world.player.kills} enemies slain. {world.player.gold} gold recovered."
            action = "R  /  DESCEND AGAIN"
        elif mode == "paused":
            kicker, title, subtitle = "TAKE A BREATH", "The descent can wait.", "Your adventure is paused."
            action = "ESC  /  RESUME"
        else:
            kicker, title, subtitle = "YOUR FIRST DESCENT", "Enter the Embervault.", "Three rifts feed the darkness. Seal them. Survive. Escape."
            action = "ENTER  /  BEGIN DESCENT"
        self.text(kicker, center, 294, 11, GOLD, center=True)
        self.text(title, center, 333, 35, WHITE, serif=True, center=True)
        self.text(subtitle, center, 393, 14, MUTED, center=True)
        self.text("WASD to move   ·   Mouse to aim   ·   Hold left click to throw", center, 438, 12, WHITE, center=True)
        self.text("Space to dash through danger   ·   E to heal", center, 465, 12, WHITE, center=True)
        self.button = pygame.Rect(center - 183, 529, 366, 51)
        pygame.draw.rect(self.screen, (64, 77, 69), self.button, border_radius=4)
        pygame.draw.rect(self.screen, GOLD, self.button, 1, border_radius=4)
        self.text(action, center, 546, 12, GOLD, bold=True, center=True)
        self.text("ESC to pause during play   ·   Close the window to quit", center, 606, 11, MUTED, center=True)
