"""Exercise the actual desktop loop through SDL's virtual display."""

import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from dungeon import app
from dungeon.render import Renderer
from dungeon.world import World


class DesktopTests(unittest.TestCase):
    def test_start_dash_pause_focus_resume_and_restart(self):
        worlds = []
        frames = []

        def new_world(seed):
            world = World(seed)
            worlds.append(world)
            return world

        class RecordingRenderer(Renderer):
            def draw(self, world, mouse=None, mode="playing"):
                super().draw(world, mouse, mode)
                frames.append((mode, world.time))
                if len(frames) == 6:
                    world.state = "won"

        class MovementKeys:
            def __getitem__(self, key):
                return key == pygame.K_d

        def key(code):
            return pygame.event.Event(pygame.KEYDOWN, key=code)

        events = [
            [key(pygame.K_RETURN)],
            [key(pygame.K_SPACE), key(pygame.K_e), key(pygame.K_m)],
            [key(pygame.K_ESCAPE)],
            [key(pygame.K_ESCAPE)],
            [pygame.event.Event(pygame.WINDOWFOCUSLOST)],
            [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
            [key(pygame.K_r)],
            [pygame.event.Event(pygame.QUIT)],
        ]
        with (
            patch.object(sys, "argv", ["main.py", "--frames", "8", "--seed", "7"]),
            patch("dungeon.app.World", side_effect=new_world),
            patch("dungeon.render.Renderer", RecordingRenderer),
            patch("pygame.event.get", side_effect=events),
            patch("pygame.key.get_pressed", return_value=MovementKeys()),
            patch("pygame.mouse.get_pos", return_value=(757, 492)),
            patch("pygame.mouse.get_pressed", return_value=(False, False, False)),
        ):
            app.main()
        self.assertEqual([mode for mode, _ in frames], [
            "playing", "playing", "paused", "playing",
            "paused", "playing", "playing", "playing",
        ])
        self.assertEqual(frames[1][1], frames[2][1])
        self.assertEqual(frames[3][1], frames[4][1])
        self.assertEqual(len(worlds), 2)
        self.assertEqual(worlds[1].state, "playing")
        self.assertGreater(worlds[0].player.dash_cooldown, 0)
        self.assertEqual(worlds[0].player.potions, 3)
        self.assertGreater(worlds[0].player.pos.x, 3.5)


if __name__ == "__main__":
    unittest.main()
