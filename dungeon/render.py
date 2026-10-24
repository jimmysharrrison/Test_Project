"""Procedural isometric art and interface; no external art assets required."""

from math import cos, pi, sin
from random import Random

import pygame

from .abilities import ABILITIES
from .armory import Armory, item_icon
from .items import RANK_COLORS
from .menus import FRONTEND_MODES, Menus
from .geometry import Vec, project

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
VIOLET = (240, 136, 91)
ICE = (139, 216, 248)
SILVER = (203, 219, 229)
LEAF = (130, 191, 104)
BLIGHT = (177, 111, 214)
LOW_HEALTH_THRESHOLD = 0.35


def iso(pos):
    point = project(pos, ORIGIN)
    return round(point.x), round(point.y)


class Renderer:
    def __init__(self, screen, world):
        self.screen = screen
        self.fonts = {}
        self.glows = {}
        self.sound_enabled = True
        self.armory = Armory()
        self.menu = Menus()
        self.gear_button = pygame.Rect(1109, 113, 137, 28)
        self.profile_notice = ""
        self.armed = None
        self.aim = world.player.pos + world.player.facing * 4
        self.bolt_aim = self.aim
        self.ability_rects = {key: pygame.Rect(526 + i * 215, 794, 202, 68)
                              for i, key in enumerate(ABILITIES)}
        self.potion_rect = pygame.Rect(48, 437, 210, 31)
        self.button = pygame.Rect(669, 529, 366, 51)
        self.floor = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self._build_floor(world)
        self.foliage = self._build_foliage()
        self.health_vignette = self._build_health_vignette()
        rng = Random(21)
        self.dust = [(rng.uniform(340, 1395), rng.uniform(190, 760), rng.uniform(0, 6)) for _ in range(45)]

    @staticmethod
    def _build_health_vignette():
        # Build a small gradient once, then scale it; no per-pixel work during play.
        mask = pygame.Surface((180, 112), pygame.SRCALPHA)
        for y in range(mask.get_height()):
            for x in range(mask.get_width()):
                edge = max(abs(2 * x / (mask.get_width() - 1) - 1),
                           abs(2 * y / (mask.get_height() - 1) - 1))
                falloff = max(0, (edge - .25) / .75) ** 1.6
                mask.set_at((x, y), (95, 0, 12, round(220 * falloff)))
        return pygame.transform.smoothscale(mask, (WIDTH, HEIGHT))

    def low_health_warning(self, player):
        fraction = player.hp / max(1, player.max_hp)
        if fraction >= LOW_HEALTH_THRESHOLD:
            return
        strength = min(1, max(0, (LOW_HEALTH_THRESHOLD - fraction) / LOW_HEALTH_THRESHOLD))
        self.health_vignette.set_alpha(round(255 * strength))
        self.screen.blit(self.health_vignette, (0, 0))

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
        self.floor.fill((0, 0, 0, 0))
        self.floor_key = (world.layout, world.level_data.theme)
        forest = world.level_data.forest
        rng = Random(42)
        corners = [iso(Vec(0, 0)), iso(Vec(17, 0)), iso(Vec(17, 17)), iso(Vec(0, 17))]
        for drop in range(30, 0, -1):
            pygame.draw.polygon(self.floor, (15 + drop // 6, 21 + drop // 5, 27 + drop // 5),
                                [(x, y + drop) for x, y in corners])
        for y, row in enumerate(world.layout):
            for x, _ in enumerate(row):
                polygon = [iso(Vec(x, y)), iso(Vec(x + 1, y)), iso(Vec(x + 1, y + 1)), iso(Vec(x, y + 1))]
                noise = rng.randrange(-5, 6)
                path = abs(x - (3 + (14 - y) * .42)) < 1.4
                base = ((56 + noise, 56 + noise, 39 + noise) if path else
                        (34 + noise, 54 + noise, 37 + noise)) if forest else (40 + noise, 51 + noise, 59 + noise)
                if (x, y) in world.walls:
                    base = (25, 39, 28) if forest else (28, 37, 45)
                pygame.draw.polygon(self.floor, base, polygon)
                pygame.draw.polygon(self.floor, (32, 46, 31) if forest else (26, 36, 44), polygon, 1)
                if forest and (x, y) not in world.walls:
                    px, py = iso(Vec(x + rng.uniform(.15, .85), y + rng.uniform(.15, .85)))
                    for i in range(3):
                        pygame.draw.line(self.floor, (57, 86 + i * 9, 46),
                                         (px + i * 3, py), (px - 3 + i * 5, py - 4 - i), 1)
                    if rng.random() < .3:
                        pygame.draw.ellipse(self.floor, (123, 111, 60), (px + 7, py + 2, 5, 2))
                    if (x + y) % 11 == 0:
                        for i in range(3):
                            pygame.draw.line(self.floor, (125, 124, 97), (px + i * 4, py), (px + i * 4, py - 4), 1)
                            pygame.draw.ellipse(self.floor, (162, 114, 159), (px - 2 + i * 4, py - 6, 5, 3))
                if rng.random() < 0.15 and (x, y) not in world.walls:
                    px, py = iso(Vec(x + 0.5, y + 0.5))
                    pygame.draw.lines(self.floor, (30, 41, 48), False,
                                      [(px - 9, py - 4), (px - 2, py), (px - 5, py + 4)], 1)
                if (x, y) not in world.walls and rng.random() < 0.12:
                    px, py = iso(Vec(x + 0.18, y + 0.72))
                    pygame.draw.lines(self.floor, (48, 69, 62), False,
                                      [(px - 7, py), (px - 2, py - 2), (px + 4, py + 1)], 2)
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
        if world.level_data.forest:
            self.forest_obstacle(tile, world)
            return
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

    @staticmethod
    def _build_foliage():
        surface = pygame.Surface((88, 104), pygame.SRCALPHA)
        for dx, dy, radius in ((-12, 9, 15), (12, 5, 18), (0, -8, 19), (-3, 5, 20)):
            pygame.draw.circle(surface, (24 + (dx % 7), 55 + (dy % 8), 35), (44 + dx, 40 + dy), radius)
            pygame.draw.arc(surface, (57, 91, 48), (44 + dx - radius, 40 + dy - radius, radius * 2, radius * 2), .5, 2.4, 1)
        return surface

    def forest_obstacle(self, tile, world):
        tx, ty = tile
        x, y = iso(Vec(tx + .5, ty + .5))
        front = tx == 16 or ty == 16
        self.shadow(x, y, 38)
        for side in (-1, 1):
            pygame.draw.lines(self.screen, (72, 64, 43), False,
                              [(x, y - 8), (x + side * 11, y - 1), (x + side * 23, y + 3)], 3)
        height = 13 if front else 45 + (tx * 7 + ty * 3) % 17
        pygame.draw.polygon(self.screen, (66, 58, 40),
                            [(x - 9, y), (x - 6, y - height), (x + 6, y - height), (x + 11, y + 2)])
        pygame.draw.line(self.screen, (103, 88, 53), (x - 3, y - height + 4), (x - 1, y - 6), 2)
        if front:
            pygame.draw.ellipse(self.screen, (113, 100, 61), (x - 6, y - height - 3, 13, 6))
            return
        canopy = pygame.Rect(x - 34, y - height - 28, 68, 67)
        obscures_actor = False
        for actor in [world.player] + world.enemies + world.spawners:
            if actor.pos.x + actor.pos.y < tx + ty + 1:
                ax, ay = iso(actor.pos)
                if canopy.colliderect(pygame.Rect(ax - 15, ay - 46, 30, 48)):
                    obscures_actor = True
                    break
        self.foliage.set_alpha(85 if obscures_actor else 255)
        self.screen.blit(self.foliage, (x - 44, y - height - 40))
        pygame.draw.lines(self.screen, (88, 68, 112), False,
                          [(x + 6, y - 5), (x + 2, y - 17), (x + 8, y - 27)], 2)

    def player(self, player, time, at=None, scale=1):
        x, y = at or iso(player.pos)
        def p(dx, dy):
            return round(x + dx * scale), round(y + dy * scale)
        def poly(color, points):
            pygame.draw.polygon(self.screen, color, [p(dx, dy) for dx, dy in points])
        self.shadow(x, y, round(29 * scale))
        self.glow(x, y - round(19 * scale), ICE, round(32 * scale), 27)
        sway = sin(time * 3) * 1.5
        blue = WHITE if player.flash > 0 else (47, 92, 145)
        poly((21, 39, 70), [(-10, -25), (9, -25), (13 + sway, 1), (0, -2), (-13 + sway, 1)])
        poly(blue, [(-9, -25), (7, -26), (9 + sway, -1), (0, 2), (-11 + sway, -1)])
        pygame.draw.lines(self.screen, SILVER, False, [p(-9, -24), p(-11 + sway, -1), p(0, 2), p(9 + sway, -1)], max(1, round(scale)))
        poly((29, 61, 106), [(0, -27), (8, -24), (7, -12), (0, -8)])
        # Pale fur collar, silver hair, and an original 'forever frozen' glyph.
        for dx, dy in ((-10, -26), (-6, -28), (-2, -27), (3, -27), (8, -26)):
            pygame.draw.circle(self.screen, (212, 222, 225), p(dx, dy), max(1, round(3 * scale)))
        pygame.draw.circle(self.screen, (226, 198, 184) if player.flash <= 0 else WHITE, p(0, -34), round(6 * scale))
        poly((171, 201, 220), [(-6, -35), (-3, -41), (4, -40), (7, -34), (5, -26), (3, -35), (-3, -37), (-4, -27)])
        pygame.draw.line(self.screen, (30, 49, 75), p(-3, -33), p(2, -33), max(1, round(scale)))
        pygame.draw.line(self.screen, SILVER, p(-4, -18), p(3, -18), max(1, round(scale)))
        pygame.draw.lines(self.screen, ICE, False, [p(-4, -18), p(0, -23), p(3, -18), p(0, -13), p(-4, -18)], max(1, round(scale)))
        pygame.draw.line(self.screen, ICE, p(0, -22), p(0, -10), max(1, round(scale)))
        pygame.draw.line(self.screen, (151, 179, 194), p(13, -34), p(13, 1), max(1, round(2 * scale)))
        poly(ICE, [(13, -45), (18, -35), (13, -29), (8, -35)])
        poly((226, 248, 255), [(13, -45), (13, -29), (9, -35)])
        if scale == 1:
            pygame.draw.ellipse(self.screen, ICE, (x - 13, y - 4, 26, 12), 1)
        if player.stasis > 0:
            self.glow(x, y - round(22 * scale), ICE, round(54 * scale), 60)
            shell = [p(-17, -3), p(-18, -32), p(-7, -51), p(9, -52), p(20, -28), p(17, 0), p(0, 8)]
            left, top = min(px for px, _ in shell), min(py for _, py in shell)
            width = max(px for px, _ in shell) - left + 1
            height = max(py for _, py in shell) - top + 1
            glass = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.polygon(glass, (130, 217, 251, 80), [(px - left, py - top) for px, py in shell])
            self.screen.blit(glass, (left, top))
            pygame.draw.polygon(self.screen, ICE, shell, max(1, round(scale)))
            pygame.draw.lines(self.screen, (211, 246, 255), False, [p(-7, -51), p(-3, -22), p(17, 0)], max(1, round(scale)))
            if scale == 1:
                self.text(f"{player.stasis:.1f}s", x, y - 72, 12, ICE, center=True)

    def enemy(self, enemy, time):
        x, y = iso(enemy.pos)
        self.shadow(x, y, 24)
        frozen = enemy.frozen > 0
        forest = enemy.kind in ("tree", "spider", "archer")
        ember = ICE if frozen or enemy.chilled > 0 else BLIGHT if enemy.kind == "tree" else LEAF if forest else (245, 120, 61)
        color = WHITE if enemy.flash > 0 else (150, 178, 193) if frozen else (133, 104, 93)
        self.glow(x, y - 15, ember, 30, 24)
        if enemy.kind == "tree":
            self.treant(enemy, time, ember)
        elif enemy.kind == "spider":
            self.spider(enemy, time, ember)
        elif enemy.kind == "archer":
            self.archer(enemy, time, ember)
        elif enemy.kind == "skitter":
            for side in (-1, 1):
                for leg in range(3):
                    wave = 0 if frozen else sin(time * 14 + leg) * 2
                    pygame.draw.lines(self.screen, color, False,
                                      [(x + side * 3, y - 7), (x + side * (10 + leg), y - 13 + leg * 4),
                                       (x + side * (15 + wave), y - 8 + leg * 4)], 2)
            pygame.draw.ellipse(self.screen, color, (x - 8, y - 18, 16, 17))
            pygame.draw.line(self.screen, ember, (x, y - 16), (x + 1, y - 3), 2)
            pygame.draw.circle(self.screen, ember, (x - 3, y - 11), 2)
            pygame.draw.circle(self.screen, ember, (x + 3, y - 11), 2)
        else:
            bob = 0 if frozen else round(sin(time * 6 + enemy.pos.x) * 1.5)
            pygame.draw.line(self.screen, color, (x - 3, y - 10), (x - 6, y), 3)
            pygame.draw.line(self.screen, color, (x + 3, y - 10), (x + 7, y), 3)
            pygame.draw.line(self.screen, ember, (x, y - 24 + bob), (x, y - 9), 3)
            for rib in range(3):
                pygame.draw.lines(self.screen, color, False,
                                  [(x - 7, y - 23 + rib * 4 + bob), (x, y - 20 + rib * 4 + bob),
                                   (x + 7, y - 23 + rib * 4 + bob)], 2)
            pygame.draw.circle(self.screen, color, (x, y - 30 + bob), 6)
            pygame.draw.circle(self.screen, ember, (x - 2, y - 31 + bob), 1)
            pygame.draw.circle(self.screen, ember, (x + 2, y - 31 + bob), 1)
            pygame.draw.lines(self.screen, color, False, [(x - 5, y - 33), (x - 10, y - 41), (x - 9, y - 32)], 2)
            pygame.draw.lines(self.screen, color, False, [(x + 5, y - 33), (x + 10, y - 41), (x + 9, y - 32)], 2)
            pygame.draw.line(self.screen, color, (x - 7, y - 21), (x - 11, y - 12), 3)
            pygame.draw.line(self.screen, color, (x + 7, y - 21), (x + 13, y - 10), 3)
            pygame.draw.line(self.screen, (87, 73, 66), (x + 13, y - 4), (x + 13, y - 28), 2)
            pygame.draw.polygon(self.screen, ember, [(x + 13, y - 35), (x + 9, y - 26), (x + 16, y - 26)])
        if frozen:
            pygame.draw.polygon(self.screen, ICE, [(x - 13, y + 1), (x - 15, y - 24), (x, y - 44), (x + 15, y - 20), (x + 13, y + 2)], 1)
            self.snowflake(x, y - 52, 5, ICE)
        elif enemy.chilled > 0:
            pygame.draw.ellipse(self.screen, ICE, (x - 15, y - 5, 30, 14), 1)
        if enemy.hp < enemy.max_hp:
            self.bar(x - 15, y - (62 if enemy.kind == "tree" else 49 if enemy.kind == "archer" else 44),
                     30, 3, enemy.hp / enemy.max_hp, ember)

    def treant(self, enemy, time, magic):
        x, y = iso(enemy.pos)
        frozen = enemy.frozen > 0
        bark = WHITE if enemy.flash > 0 else (132, 171, 182) if frozen else (110, 85, 57)
        sway = 0 if frozen else round(sin(time * 3 + enemy.phase) * 2)
        for side in (-1, 1):
            pygame.draw.lines(self.screen, bark, False,
                              [(x + side * 5, y - 13), (x + side * 9, y - 2), (x + side * 17, y + 2)], 5)
            pygame.draw.lines(self.screen, bark, False,
                              [(x + side * 7, y - 31), (x + side * 20, y - 25 + sway),
                               (x + side * 26, y - 39 + sway)], 4)
            pygame.draw.lines(self.screen, bark, False,
                              [(x + side * 23, y - 31 + sway), (x + side * 31, y - 33 + sway),
                               (x + side * 32, y - 40 + sway)], 2)
        pygame.draw.polygon(self.screen, bark, [(x - 10, y - 4), (x - 12, y - 34),
                             (x - 6, y - 48), (x + 8, y - 47), (x + 13, y - 30), (x + 10, y - 3)])
        pygame.draw.lines(self.screen, (58, 48, 44), False,
                          [(x - 5, y - 43), (x - 2, y - 29), (x - 5, y - 8)], 2)
        pygame.draw.lines(self.screen, magic, False,
                          [(x + 4, y - 41), (x + 1, y - 26), (x + 7, y - 16), (x + 3, y - 5)], 2)
        for side in (-1, 1):
            pygame.draw.polygon(self.screen, magic, [(x + side * 2, y - 34), (x + side * 9, y - 37), (x + side * 6, y - 31)])
            pygame.draw.lines(self.screen, bark, False,
                              [(x + side * 5, y - 45), (x + side * 14, y - 54), (x + side * 12, y - 61)], 3)
            pygame.draw.ellipse(self.screen, (70, 108, 71) if frozen else (57, 87, 44),
                                (x + side * 13 - 8, y - 58, 15, 8))
        pygame.draw.lines(self.screen, magic, False, [(x - 6, y - 25), (x - 2, y - 28), (x + 2, y - 24), (x + 7, y - 27)], 2)

    def spider(self, enemy, time, magic):
        x, y = iso(enemy.pos)
        frozen = enemy.frozen > 0
        body = WHITE if enemy.flash > 0 else (135, 168, 186) if frozen else (70, 51, 83)
        legs = (139, 173, 187) if frozen else (133, 109, 135)
        for side in (-1, 1):
            for leg in range(4):
                wave = 0 if frozen else sin(time * 13 + leg * 1.6) * 2
                pygame.draw.lines(self.screen, legs, False,
                                  [(x + side * 4, y - 10), (x + side * (15 + leg), y - 19 + leg * 6),
                                   (x + side * (24 + wave), y - 12 + leg * 5)], 2)
        pygame.draw.ellipse(self.screen, body, (x - 10, y - 26, 20, 18))
        pygame.draw.ellipse(self.screen, (107, 78, 118) if not frozen else body, (x - 7, y - 14, 14, 12))
        pygame.draw.polygon(self.screen, magic, [(x, y - 22), (x + 4, y - 17), (x, y - 12), (x - 4, y - 17)], 1)
        for dx in (-4, -1, 2, 5):
            pygame.draw.circle(self.screen, magic, (x + dx, y - 7), 1)
        for side in (-1, 1):
            pygame.draw.line(self.screen, SILVER, (x + side * 3, y - 3), (x + side * 5, y + 2), 1)

    def archer(self, enemy, time, magic):
        x, y = iso(enemy.pos)
        bone = WHITE if enemy.flash > 0 else (158, 192, 204) if enemy.frozen > 0 else (192, 193, 153)
        cloak = (79, 118, 130) if enemy.frozen > 0 else (44, 78, 49)
        pygame.draw.polygon(self.screen, cloak, [(x - 9, y - 28), (x + 6, y - 27), (x + 10, y - 3), (x - 12, y)])
        for side in (-1, 1):
            pygame.draw.line(self.screen, bone, (x + side * 3, y - 10), (x + side * 6, y), 3)
            pygame.draw.line(self.screen, bone, (x + side * 3, y - 25), (x + side * 8, y - 18), 2)
        pygame.draw.line(self.screen, bone, (x, y - 28), (x, y - 9), 2)
        for rib in range(3):
            pygame.draw.lines(self.screen, bone, False, [(x - 5, y - 24 + rib * 4),
                              (x, y - 22 + rib * 4), (x + 5, y - 24 + rib * 4)], 1)
        pygame.draw.polygon(self.screen, cloak, [(x - 9, y - 30), (x - 6, y - 42), (x + 3, y - 45), (x + 9, y - 32)])
        pygame.draw.circle(self.screen, bone, (x, y - 33), 6)
        for side in (-1, 1):
            pygame.draw.circle(self.screen, magic, (x + side * 2, y - 34), 1)
            pygame.draw.lines(self.screen, (113, 103, 70), False,
                              [(x + side * 6, y - 39), (x + side * 12, y - 48), (x + side * 9, y - 51)], 2)
            pygame.draw.ellipse(self.screen, LEAF, (x + side * 10 - 3, y - 45, 7, 3))
        # A drawn bow and visible arrow distinguish the ranged skeleton at a glance.
        pull = 4 if enemy.windup > 0 else 0
        pygame.draw.lines(self.screen, (163, 130, 76), False,
                          [(x + 12, y - 37), (x + 19, y - 28), (x + 20, y - 19), (x + 12, y - 9)], 2)
        pygame.draw.lines(self.screen, GOLD, False,
                          [(x + 12, y - 37), (x + 10 - pull, y - 23), (x + 12, y - 9)], 1)
        pygame.draw.line(self.screen, bone, (x + 6, y - 25), (x + 16, y - 23), 2)
        pygame.draw.line(self.screen, LEAF, (x + 5 - pull, y - 23), (x + 25, y - 23), 1)
        pygame.draw.polygon(self.screen, magic, [(x + 29, y - 23), (x + 23, y - 26), (x + 23, y - 20)])

    def archer_aim(self, enemy):
        if enemy.windup <= 0 or enemy.shot_target is None or enemy.frozen > 0:
            return
        start, end = Vec(*iso(enemy.pos)), Vec(*iso(enemy.shot_target))
        delta = end - start
        length = delta.length()
        direction = delta.unit()
        color = GOLD if enemy.windup < .25 else (139, 132, 81)
        for offset in range(15, round(length), 12):
            a, b = start + direction * offset, start + direction * min(offset + 6, length)
            pygame.draw.line(self.screen, color, (a.x, a.y - 15), (b.x, b.y - 15), 1)
        pygame.draw.circle(self.screen, color, (round(end.x), round(end.y - 15)), 7, 1)

    def spawner(self, spawner, time):
        if spawner.forest:
            self.blighted_heart(spawner, time)
            return
        x, y = iso(spawner.pos)
        pulse = sin(time * 3 + spawner.pos.x)
        self.glow(x, y - 22, VIOLET, 65, 56)
        pygame.draw.ellipse(self.screen, (110, 59, 43), (x - 29, y - 12, 58, 27), 1)
        for i in range(6):
            angle = i * pi / 3 + time * 0.35
            px, py = x + cos(angle) * 28, y + sin(angle) * 12
            pygame.draw.circle(self.screen, (214, 132, 89), (round(px), round(py)), 2)
        pygame.draw.polygon(self.screen, (53, 36, 35), [(x - 20, y), (x, y + 10), (x + 20, y), (x + 20, y - 9), (x - 20, y - 9)])
        pygame.draw.polygon(self.screen, (89, 65, 57), [(x - 20, y - 9), (x, y - 19), (x + 20, y - 9), (x, y + 1)])
        color = WHITE if spawner.flash else VIOLET
        for side in (-1, 1):
            sx = x + side * 17
            pygame.draw.polygon(self.screen, (86, 57, 51), [(sx - 5, y - 9), (sx - 4, y - 36), (sx + 1, y - 43), (sx + 5, y - 11)])
            pygame.draw.line(self.screen, (177, 109, 77), (sx, y - 38), (sx, y - 19), 1)
        pygame.draw.ellipse(self.screen, color, (x - 9, y - 48 + pulse * 2, 18, 34), 2)
        pygame.draw.ellipse(self.screen, (255, 214, 160), (x - 3, y - 43 + pulse * 2, 6, 25))
        self.bar(x - 25, y - 61, 50, 3, spawner.hp / spawner.max_hp, VIOLET)

    def blighted_heart(self, spawner, time):
        x, y = iso(spawner.pos)
        magic = WHITE if spawner.flash > 0 else BLIGHT
        pulse = round(sin(time * 3 + spawner.pos.x) * 2)
        self.glow(x, y - 22, BLIGHT, 65, 56)
        pygame.draw.ellipse(self.screen, (115, 75, 137), (x - 29, y - 12, 58, 27), 1)
        for side in (-1, 1):
            pygame.draw.lines(self.screen, (109, 85, 60), False,
                              [(x + side * 28, y + 5), (x + side * 14, y - 3),
                               (x + side * 17, y - 25), (x + side * 7, y - 45)], 7)
            pygame.draw.lines(self.screen, magic, False,
                              [(x + side * 26, y + 3), (x + side * 12, y - 6), (x + side * 15, y - 26)], 1)
        pygame.draw.polygon(self.screen, (77, 64, 49), [(x - 12, y), (x - 11, y - 34), (x + 7, y - 39), (x + 14, y - 1)])
        pygame.draw.ellipse(self.screen, magic, (x - 8, y - 37 + pulse, 16, 25))
        pygame.draw.ellipse(self.screen, (230, 186, 248), (x - 3, y - 31 + pulse, 6, 13))
        for dx, dy in ((-19, -29), (14, -38), (-7, -43)):
            pygame.draw.ellipse(self.screen, (67, 104, 52), (x + dx - 7, y + dy, 15, 6))
        self.bar(x - 25, y - 58, 50, 3, spawner.hp / spawner.max_hp, BLIGHT)

    def wisp(self, pos, time):
        x, y = iso(pos)
        bob = round(sin(time * 2 + pos.x) * 4)
        self.glow(x, y - 15 + bob, LEAF, 53, 27)
        pygame.draw.circle(self.screen, LEAF, (x, y - 15 + bob), 3)
        pygame.draw.circle(self.screen, (219, 239, 171), (x, y - 16 + bob), 1)

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
        if world.level_data.forest:
            for side in (-1, 1):
                pygame.draw.lines(self.screen, (83, 112, 63), False,
                                  [(x + side * 29, y - 4), (x + side * 20, y - 23),
                                   (x + side * 27, y - 44), (x + side * 19, y - 59)], 3)
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
        if pickup.kind == "item":
            color = RANK_COLORS[pickup.item.rank]
            self.glow(x, y - 8, color, 34, 35)
            pygame.draw.polygon(self.screen, color, [(x, y - 29), (x + 15, y - 12), (x, y + 1), (x - 15, y - 12)], 1)
            item_icon(self.screen, pickup.item.slot, (x, y - 13 + bob), color, .42)
        elif pickup.kind == "gold":
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
        direction = project(shot.velocity).unit()
        side = Vec(-direction.y, direction.x)
        if shot.hostile:
            tail, tip = Vec(x, y - 15) - direction * 15, Vec(x, y - 15) + direction * 7
            pygame.draw.line(self.screen, GOLD, (tail.x, tail.y), (tip.x, tip.y), 2)
            pygame.draw.polygon(self.screen, LEAF, [(tip.x + direction.x * 5, tip.y + direction.y * 5),
                                (tip.x + side.x * 3, tip.y + side.y * 3),
                                (tip.x - side.x * 3, tip.y - side.y * 3)])
            for sign in (-1, 1):
                feather = tail - direction * 4 + side * (sign * 4)
                pygame.draw.line(self.screen, SILVER, (tail.x + direction.x * 3, tail.y + direction.y * 3),
                                 (feather.x, feather.y), 1)
            return
        self.glow(x, y - 15, ICE, 28, 44)
        pygame.draw.line(self.screen, (76, 139, 183), (x - direction.x * 22, y - 15 - direction.y * 22), (x, y - 15), 3)
        pygame.draw.polygon(self.screen, ICE, [(x + direction.x * 12, y - 15 + direction.y * 12),
                            (x + side.x * 5 - direction.x * 5, y - 15 + side.y * 5 - direction.y * 5),
                            (x - direction.x * 9, y - 15 - direction.y * 9),
                            (x - side.x * 5 - direction.x * 5, y - 15 - side.y * 5 - direction.y * 5)])
        pygame.draw.line(self.screen, WHITE, (x, y - 15), (x + direction.x * 10, y - 15 + direction.y * 10), 2)

    def radius(self, pos, radius, color, width=1):
        x, y = iso(pos)
        rx, ry = round(radius * 39.6), round(radius * 19.8)
        pygame.draw.ellipse(self.screen, color, (x - rx, y - ry, rx * 2, ry * 2), width)

    def snowflake(self, x, y, size, color):
        for angle in (0, pi / 3, 2 * pi / 3):
            dx, dy = cos(angle) * size, sin(angle) * size
            pygame.draw.line(self.screen, color, (x - dx, y - dy), (x + dx, y + dy), 1)
            for side in (-1, 1):
                ex, ey = x + dx * side * 0.65, y + dy * side * 0.65
                for branch in (-1, 1):
                    turn = angle + pi + branch * pi / 3
                    pygame.draw.line(self.screen, color, (ex, ey), (ex + cos(turn) * size * 0.28 * side, ey + sin(turn) * size * 0.28 * side), 1)

    def icewall(self, cell, time):
        x, y = cell
        corners = [iso(Vec(x, y)), iso(Vec(x + 1, y)), iso(Vec(x + 1, y + 1)), iso(Vec(x, y + 1))]
        roof = [(px, py - (32 if i % 2 else 42)) for i, (px, py) in enumerate(corners)]
        pygame.draw.polygon(self.screen, (49, 100, 136), [roof[1], roof[2], corners[2], corners[1]])
        pygame.draw.polygon(self.screen, (75, 140, 173), [roof[2], roof[3], corners[3], corners[2]])
        pygame.draw.polygon(self.screen, (153, 217, 239), roof)
        pygame.draw.polygon(self.screen, ICE, [roof[1], roof[2], corners[2], corners[1]], 1)
        pygame.draw.lines(self.screen, (207, 241, 250), False, [roof[3], roof[0], roof[1]], 1)
        self.snowflake(corners[2][0] - 10, corners[2][1] - 19, 6, SILVER)

    def effect(self, effect):
        x, y = iso(effect.pos)
        age = 1 - effect.life / effect.duration
        color = TEAL if effect.kind == "heal" else GOLD if effect.kind in ("gold", "critical") else VIOLET if effect.kind in ("spawn", "burst") else RED if effect.kind == "hurt" else ICE
        if effect.kind in ("nova", "shatter"):
            self.radius(effect.pos, effect.radius * min(1, age * 1.5), ICE, 2)
            self.radius(effect.pos, effect.radius * age * 0.8, (80, 140, 177))
            for i in range(14):
                angle = i * pi / 7
                rr = effect.radius * age
                px, py = iso(effect.pos + Vec(cos(angle), sin(angle)) * rr)
                pygame.draw.line(self.screen, ICE, (px, py - 4), (px + cos(angle) * 4, py - 12 - sin(angle) * 5), 2)
        if effect.kind in ("burst", "spawn", "heal", "cast", "hurt", "destination"):
            radius = round(8 + age * 29)
            pygame.draw.ellipse(self.screen, color, (x - radius, y - radius / 2, radius * 2, radius), 1)
        if effect.kind in ("hit", "critical", "spark", "burst"):
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

    @staticmethod
    def world_area(point):
        return 308 <= point[0] <= 1410 and 166 <= point[1] < 773

    def ability_at(self, point):
        return next((key for key, rect in self.ability_rects.items() if rect.collidepoint(point)), None)

    def pick_target(self, world, point):
        targets = []
        for target in world.enemies + world.spawners:
            x, y = iso(target.pos)
            width, height = ((52, 68) if target in world.spawners else
                             (60, 63) if target.kind == "tree" else
                             (50, 30) if target.kind == "spider" else
                             (34, 52) if target.kind == "archer" else (34, 46))
            if pygame.Rect(x - width // 2, y - height, width, height + 9).collidepoint(point):
                targets.append(target)
        return max(targets, key=lambda target: target.pos.x + target.pos.y, default=None)

    def target_frame(self, world):
        self.spaced("SELECTED TARGET", 48, 502, 10)
        target = world.selected
        if target is None:
            self.text("Left click an enemy", 48, 534, 13, MUTED)
            self.text("to inspect its health", 48, 559, 11, MUTED)
            self.text("and active effects.", 48, 581, 11, MUTED)
            return
        self.text(target.name, 48, 530, 16, WHITE, serif=True)
        self.bar(48, 563, 210, 6, target.hp / target.max_hp, VIOLET)
        self.text(f"{target.hp} / {target.max_hp} health", 48, 576, 11, MUTED)
        for i, (name, seconds) in enumerate(target.statuses):
            self.snowflake(55, 606 + i * 21, 5, ICE)
            self.text(f"{name}  {seconds:.1f}s", 68, 598 + i * 21, 11, ICE)
        if not target.statuses:
            self.text("No active effects", 48, 604, 10, MUTED)
        if getattr(target, "windup", 0) > 0:
            self.text(f"Drawing bow  {target.windup:.1f}s", 48, 625, 10, GOLD)

    def hud(self, world):
        player = world.player
        pygame.draw.rect(self.screen, PANEL, (24, 24, 259, 852), border_radius=12)
        pygame.draw.rect(self.screen, LINE, (24, 24, 259, 852), 1, border_radius=12)
        self.spaced("EMBERVAULT", 47, 49, 21, SILVER, 1)
        self.spaced("THE FROZEN DESCENT", 49, 84, 10, ICE, 1)
        pygame.draw.line(self.screen, LINE, (47, 119), (259, 119))
        self.spaced("YOUR CHAMPION", 48, 140, 10)
        pygame.draw.circle(self.screen, (26, 41, 59), (153, 217), 49)
        pygame.draw.circle(self.screen, (74, 108, 132), (153, 217), 49, 1)
        self.player(player, world.time, (153, 253), 1.8)
        self.text("The Ice Mage", 153, 280, 24, WHITE, serif=True, center=True)
        self.spaced("FOREVER FROZEN", 87, 318, 9, ICE, 1)
        self.spaced("VITALITY", 48, 346, 10)
        self.text(f"{player.hp} / {player.max_hp}", 193, 343, 12, WHITE)
        self.bar(48, 370, 210, 7, player.hp / player.max_hp, RED)
        self.spaced("MANA", 48, 389, 10)
        self.text(f"{int(player.mana)} / 100", 193, 386, 12, ICE)
        self.bar(48, 414, 210, 7, player.mana / 100, (84, 151, 216))
        pygame.draw.rect(self.screen, (31, 43, 51), self.potion_rect, border_radius=4)
        self.key("1", 53, 440, 23)
        self.text("Healing potion", 86, 445, 11, WHITE)
        self.text(f"×{player.potions}", 230, 442, 14, GOLD)
        pygame.draw.line(self.screen, LINE, (47, 485), (259, 485))
        self.target_frame(world)
        pygame.draw.line(self.screen, LINE, (47, 648), (259, 648))
        self.spaced("THE OBJECTIVE", 48, 667, 10)
        total = len(world.level_data.spawners)
        objectives = [("Purge the hearts" if world.level_data.forest else "Seal the rifts",
                       f"{total - len(world.spawners)} / {total}", not world.spawners),
                      ("Survivors (optional)", str(len(world.enemies)), not world.enemies),
                      ("Reach the gate", "OPEN" if world.exit_open else "SEALED", world.exit_open)]
        for i, (label, value, done) in enumerate(objectives):
            yy = 696 + i * 27
            pygame.draw.circle(self.screen, TEAL if done else (83, 94, 100), (53, yy + 7), 3, 0 if done else 1)
            self.text(label, 66, yy, 11, WHITE if done else MUTED)
            self.text(value, 217 if i < 2 else 209, yy, 10, TEAL if done else GOLD)
        pygame.draw.line(self.screen, LINE, (47, 788), (259, 788))
        self.text(f"{player.gold:04d}", 48, 802, 25, GOLD, serif=True)
        self.text("GOLD", 49, 840, 9, MUTED)
        self.text(f"{player.kills:02d}", 178, 802, 25, WHITE, serif=True)
        self.text("SLAIN", 179, 840, 9, MUTED)

    def spell_icon(self, key, x, y):
        if key == "q":
            pygame.draw.polygon(self.screen, ICE, [(x + 13, y - 11), (x + 5, y + 5), (x - 12, y + 11), (x - 5, y - 6)], 2)
            pygame.draw.line(self.screen, SILVER, (x - 12, y + 11), (x + 13, y - 11), 1)
        elif key == "w":
            self.snowflake(x, y, 15, ICE)
            pygame.draw.circle(self.screen, (72, 123, 164), (x, y), 19, 1)
        elif key == "e":
            for dx in (-11, 0, 11):
                pygame.draw.polygon(self.screen, ICE, [(x + dx - 4, y + 12), (x + dx - 5, y - 5), (x + dx, y - 13), (x + dx + 5, y - 2), (x + dx + 4, y + 12)], 1)
        else:
            pygame.draw.polygon(self.screen, ICE, [(x - 12, y + 8), (x - 13, y - 6), (x, y - 18), (x + 13, y - 6), (x + 12, y + 8), (x, y + 17)], 2)
            self.snowflake(x, y, 7, SILVER)

    def spellbar(self, world, mouse):
        pygame.draw.rect(self.screen, PANEL, (323, 784, 1073, 92), border_radius=8)
        pygame.draw.rect(self.screen, LINE, (323, 784, 1073, 92), 1, border_radius=8)
        self.spaced("ICE MAGIC", 345, 801, 10, ICE, 2)
        if world.player.stasis > 0:
            self.text(f"ICEBOUND  {world.player.stasis:.1f}s", 345, 826, 12, ICE)
        elif self.armed:
            self.text(f"{self.armed.upper()} / Choose target", 345, 826, 12, ICE)
        else:
            self.text("RMB move · LMB select", 345, 826, 11, MUTED)
        self.text("Right click cancels" if self.armed else "I gear · B shop · S stop", 345, 851, 10, MUTED)
        hover = None
        for key, rect in self.ability_rects.items():
            ability = ABILITIES[key]
            cooldown = world.player.cooldowns[key]
            disabled = cooldown > 0 or world.player.mana < ability.mana or world.player.stasis > 0
            hovered = mouse is not None and rect.collidepoint(mouse)
            if hovered:
                hover = key
            color = (31, 54, 72) if self.armed == key or hovered else (25, 37, 48)
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            pygame.draw.rect(self.screen, ICE if self.armed == key or hovered else (57, 79, 96), rect, 1, border_radius=5)
            self.spell_icon(key, rect.x + 29, rect.y + 29)
            self.text(key.upper(), rect.x + 12, rect.y + 48, 10, SILVER, bold=True)
            self.text(ability.name, rect.x + 59, rect.y + 10, 13, MUTED if disabled else WHITE)
            if cooldown > 0:
                self.text(f"{cooldown:.1f}s", rect.x + 59, rect.y + 37, 17, ICE)
                self.bar(rect.x + 59, rect.y + 61, 130, 2, 1 - cooldown / world.player.cooldown_for(key), ICE)
            else:
                self.text(f"{int(ability.mana)} MANA" if ability.mana else "FREE · HOLD Q", rect.x + 59, rect.y + 42, 10, RED if world.player.mana < ability.mana else ICE)
        if hover:
            ability = ABILITIES[hover]
            rect = self.ability_rects[hover]
            x = min(rect.x, 980)
            box = pygame.Rect(x, 665, 406, 106)
            pygame.draw.rect(self.screen, (20, 33, 46), box, border_radius=6)
            pygame.draw.rect(self.screen, (75, 111, 138), box, 1, border_radius=6)
            self.text(f"{hover.upper()}  {ability.name}", x + 14, 679, 17, ICE, serif=True)
            # Wrap the short description using the same font as the rendered text.
            words, line, yy = ability.description.split(), "", 710
            for word in words:
                candidate = (line + " " + word).strip()
                if self.font(11).size(candidate)[0] > 376:
                    self.text(line, x + 14, yy, 11, WHITE)
                    line, yy = word, yy + 18
                else:
                    line = candidate
            self.text(line, x + 14, yy, 11, WHITE)
            self.text(f"{world.player.cooldown_for(hover):.2f}s cooldown · {int(ability.mana)} mana", x + 14, 748, 10, MUTED)

    def pine(self, x, y, size, forest=False):
        pygame.draw.line(self.screen, (27, 36, 34), (x, y - size * 0.2), (x, y + 10), 5)
        for i in range(4):
            top = y - size + i * size * 0.2
            spread = size * (0.18 + i * 0.07)
            color = (20 + i * 2, 42 + i * 4, 28 + i * 2) if forest else (19 + i * 2, 36 + i * 3, 38 + i * 2)
            pygame.draw.polygon(self.screen, color,
                                [(x, top), (x + spread, top + size * 0.48), (x - spread, top + size * 0.48)])
            pygame.draw.line(self.screen, (40, 62, 63), (x, top), (x - spread, top + size * 0.48), 1)

    def targeting(self, world, mouse):
        if world.destination is not None:
            x, y = iso(world.destination)
            pygame.draw.ellipse(self.screen, (92, 155, 176), (x - 12, y - 6, 24, 12), 1)
            pygame.draw.circle(self.screen, ICE, (x, y), 2)
        if self.armed and mouse and self.world_area(mouse):
            if self.armed == "e":
                cells, reason = world.wall_preview(self.aim)
                color = RED if reason else ICE
                for x, y in cells:
                    polygon = [iso(Vec(x, y)), iso(Vec(x + 1, y)), iso(Vec(x + 1, y + 1)), iso(Vec(x, y + 1))]
                    pygame.draw.polygon(self.screen, color, polygon, 2)
                if reason:
                    self.text(reason, 861, 748, 11, RED, center=True)
            else:
                start, end = iso(world.player.pos), iso(self.bolt_aim)
                pygame.draw.line(self.screen, (93, 166, 207), (start[0], start[1] - 15), (end[0], end[1] - 15), 1)

    def draw(self, world, mouse=None, mode="playing"):
        if mode in FRONTEND_MODES:
            self.menu.draw(self, world, mouse, mode)
            return
        if self.floor_key != (world.layout, world.level_data.theme):
            self._build_floor(world)
        forest = world.level_data.forest
        self.screen.fill(INK)
        pygame.draw.ellipse(self.screen, (17, 30, 23) if forest else (15, 27, 32), (340, 166, 1060, 600))
        self.screen.set_clip(pygame.Rect(300, 166, 1140, 610))
        for x, y, size in ((365, 400, 150), (434, 260, 104), (537, 228, 80), (1240, 235, 95),
                           (1358, 350, 156), (1403, 568, 152), (1307, 730, 100), (382, 712, 125)):
            self.pine(x, y, size, forest)
        self.screen.set_clip(None)
        self.spaced(world.level_data.chapter, 324, 39, 10, LEAF if forest else ICE, 2)
        self.text(world.level_data.name, 320, 64, 36, WHITE, serif=True)
        self.text(world.level_data.subtitle, 323, 116, 13, MUTED)
        self.text("DEPTH", 1302, 49, 10, MUTED)
        self.text(f"{world.level:02d}", 1299, 65, 36, SILVER, serif=True)
        Armory.button(self, self.gear_button, "I GEAR / B SHOP")
        self.text("M / SOUND " + ("ON" if self.sound_enabled else "OFF"), 1266, 121, 10, MUTED)
        pygame.draw.line(self.screen, LINE, (324, 155), (1396, 155))
        self.screen.blit(self.floor, (0, 0))
        if world.selected:
            self.radius(world.selected.pos, 0.55, GOLD, 2)
        for spawner in world.spawners:
            x, y = iso(spawner.pos)
            self.glow(x, y, BLIGHT if forest else VIOLET, 95, 35)
        for enemy in world.enemies:
            if enemy.kind == "archer":
                self.archer_aim(enemy)
        objects = [(x + y + 1, "wall", (x, y)) for x, y in world.walls]
        objects += [(x + y + 1, "icewall", (x, y)) for wall in world.ice_walls for x, y in wall.cells]
        objects += [(p.pos.x + p.pos.y, "pickup", p) for p in world.pickups]
        objects += [(s.pos.x + s.pos.y, "spawner", s) for s in world.spawners]
        objects += [(e.pos.x + e.pos.y, "enemy", e) for e in world.enemies]
        objects += [(p.pos.x + p.pos.y, "projectile", p) for p in world.projectiles]
        objects.append((world.player.pos.x + world.player.pos.y, "player", world.player))
        objects.append((world.exit.x + world.exit.y, "gate", None))
        objects += [(p.x + p.y, "wisp" if forest else "torch", p)
                    for p in (Vec(2.5, 7.5), Vec(7.5, 2.5), Vec(14.5, 10.5), Vec(8.5, 14.5))]
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
            pygame.draw.circle(self.screen, (140, 169, 88) if forest else (92, 122, 131), (px, py), 1)
        if mode == "playing" and world.state == "playing":
            self.low_health_warning(world.player)
        self.targeting(world, mouse)
        self.hud(world)
        self.spellbar(world, mouse)
        self.text(world.message if world.message_time > 0 else "Right click or hold to move. Left click selects. QWER casts at the cursor.", 325, 759, 11, MUTED)
        if mouse and mode == "playing" and world.state == "playing" and self.world_area(mouse):
            x, y = mouse
            color = ICE if self.armed else SILVER
            pygame.draw.circle(self.screen, color, (x, y), 8, 1)
            pygame.draw.circle(self.screen, color, (x, y), 2)
        if self.profile_notice:
            self.text(self.profile_notice, 325, 735, 10, GOLD)
        if mode in ("inventory", "shop"):
            self.armory.draw(self, world, mouse, mode)
        elif mode == "paused":
            self.menu.draw(self, world, mouse, mode)
        elif mode != "playing" or world.state != "playing":
            self.overlay(world, mode)
        elif mouse and self.world_area(mouse):
            for pickup in reversed(world.pickups):
                if pickup.kind == "item":
                    x, y = iso(pickup.pos)
                    if pygame.Rect(x - 18, y - 32, 36, 38).collidepoint(mouse):
                        self.armory.tooltip(self, pickup.item, mouse,
                                            current=world.player.inventory.worn(pickup.item.slot))
                        break

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
            action = "ENTER  /  TRY AGAIN"
        elif world.state == "cleared":
            kicker, title = "THE GATE IS OPEN", f"Depth {world.level} complete."
            subtitle = ("Thornveil Forest awaits. Your equipment and gold carry forward." if world.level == 1 else
                        "Your equipment and gold will carry into the next level.")
            action = "ENTER  /  NEXT DEPTH"
        elif world.state == "won":
            kicker, title, subtitle = "THE GLADE IS SILENT", "You made it out.", f"{world.player.kills} enemies slain. {world.player.gold} gold recovered."
            action = "ENTER  /  DESCEND AGAIN"
        elif mode == "paused":
            kicker, title, subtitle = "TAKE A BREATH", "The descent can wait.", "Your adventure is paused."
            action = "ESC  /  RESUME"
        else:
            kicker, title = "YOUR NEXT DESCENT", f"Enter {world.level_data.name}."
            subtitle = ("Darkroot trees. Thornwood spiders. Beware the archers." if world.level_data.forest else
                        "A frozen oath. Three molten rifts. A forest worth saving.")
            action = "ENTER  /  BEGIN DESCENT"
        self.text(kicker, center, 294, 11, GOLD, center=True)
        self.text(title, center, 333, 35, WHITE, serif=True, center=True)
        self.text(subtitle, center, 393, 14, MUTED, center=True)
        self.text("Right click or hold to move   ·   Left click to select enemies", center, 438, 12, WHITE, center=True)
        self.text("Q Ice Bolt   ·   W Frost Nova   ·   E Ice Wall   ·   R Glacial Prison", center, 465, 12, WHITE, center=True)
        self.button = pygame.Rect(center - 183, 529, 366, 51)
        pygame.draw.rect(self.screen, (64, 77, 69), self.button, border_radius=4)
        pygame.draw.rect(self.screen, GOLD, self.button, 1, border_radius=4)
        self.text(action, center, 546, 12, GOLD, bold=True, center=True)
        self.text("I inventory   ·   B shop & enchantments   ·   1 potion   ·   Esc pause", center, 606, 11, MUTED, center=True)
