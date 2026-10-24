"""Check the rendered warning, healing reset, and equipment-aware health threshold."""

import os
import unittest

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from dungeon.render import HEIGHT, WIDTH, Renderer
from dungeon.world import World


class HealthWarningTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_mode((1, 1))
        self.world = World(7)
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.renderer = Renderer(self.canvas, self.world)

    def tearDown(self):
        pygame.quit()

    def render_at(self, hp, mode="playing"):
        self.world.player.hp = hp
        self.renderer.draw(self.world, mode=mode)
        return self.canvas.copy()

    def test_warning_intensifies_as_health_falls_and_leaves_hud_readable(self):
        healthy = self.render_at(100)
        mild = self.render_at(25)
        critical = self.render_at(5)
        edge = (1400, 450)
        self.assertLess(critical.get_at(edge).g, mild.get_at(edge).g)
        self.assertLess(mild.get_at(edge).g, healthy.get_at(edge).g)
        # A central floor pixel and an ability button are not tinted.
        for point in ((720, 450), (530, 795)):
            self.assertEqual(healthy.get_at(point), critical.get_at(point))

    def test_healing_removes_warning_without_leaving_a_cached_red_overlay(self):
        self.world.player.hp = 20
        self.renderer.draw(self.world)
        red_edge = self.canvas.get_at((1400, 450))
        self.world.use_potion()
        self.renderer.draw(self.world)
        healed_edge = self.canvas.get_at((1400, 450))
        self.assertGreater(healed_edge.g, red_edge.g)
        healthy = self.render_at(100).get_at((1400, 450))
        self.assertEqual(healthy, healed_edge)
        self.assertEqual(self.render_at(35).get_at((1400, 450)), healthy)

    def test_health_percentage_uses_equipped_maximum_and_warning_is_hidden_in_menus(self):
        without_chest = self.render_at(50).get_at((1400, 450))
        inv = self.world.player.inventory
        inv.add(inv.create("chest", 3))  # 160 maximum health: 50 HP is now low.
        with_chest = self.render_at(50).get_at((1400, 450))
        self.assertLess(with_chest.g, without_chest.g)
        for mode in ("inventory", "shop", "paused"):
            low = self.render_at(5, mode).get_at((1400, 450))
            full = self.render_at(160, mode).get_at((1400, 450))
            self.assertEqual(low, full)


if __name__ == "__main__":
    unittest.main()
