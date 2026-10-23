"""Exercise mouse, keyboard, and rendering through SDL's virtual display."""

import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from dungeon import app
from dungeon.render import Renderer, iso
from dungeon.world import World


def key(code):
    return pygame.event.Event(pygame.KEYDOWN, key=code)


def click(button, point):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=button,
                              pos=(round(point[0] * 8 / 9), round(point[1] * 8 / 9)))


class DesktopTests(unittest.TestCase):
    def run_app(self, script, observer=None):
        worlds, frames = [], []
        pointer = [800, 480]
        buttons = [False, False, False]
        index = 0

        def new_world(seed):
            world = World(seed)
            worlds.append(world)
            return world

        class RecordingRenderer(Renderer):
            def draw(self, world, mouse=None, mode="playing"):
                super().draw(world, mouse, mode)
                frames.append((mode, world.time))
                if observer:
                    observer(len(frames), world, self)

        def events():
            nonlocal index
            items = script[index]
            index += 1
            for event in items:
                if hasattr(event, "pos"):
                    pointer[:] = event.pos
                if event.type == pygame.MOUSEBUTTONDOWN:
                    buttons[event.button - 1] = True
                if event.type == pygame.MOUSEBUTTONUP:
                    buttons[event.button - 1] = False
            return items

        class NoKeys:
            def __getitem__(self, code):
                return False

        with (
            patch.object(sys, "argv", ["main.py", "--frames", str(len(script)), "--seed", "7"]),
            patch("dungeon.app.World", side_effect=new_world),
            patch("dungeon.render.Renderer", RecordingRenderer),
            patch("pygame.event.get", side_effect=events),
            patch("pygame.key.get_pressed", return_value=NoKeys()),
            patch("pygame.mouse.get_pos", side_effect=lambda: tuple(pointer)),
            patch("pygame.mouse.get_pressed", side_effect=lambda: tuple(buttons)),
        ):
            app.main()
        return worlds, frames

    def test_ultimate_pause_focus_resume_and_enter_restart(self):
        def observer(frame, world, renderer):
            if frame == 7:
                world.state = "won"
        script = [
            [key(pygame.K_RETURN)], [key(pygame.K_r)], [key(pygame.K_ESCAPE)],
            [key(pygame.K_ESCAPE)], [pygame.event.Event(pygame.WINDOWFOCUSLOST)],
            [click(1, (852, 554))], [], [key(pygame.K_r)], [key(pygame.K_RETURN)],
        ]
        worlds, frames = self.run_app(script, observer)
        self.assertEqual([mode for mode, _ in frames], [
            "playing", "playing", "paused", "playing", "paused", "playing", "playing", "playing", "playing",
        ])
        self.assertEqual(frames[1][1], frames[2][1])
        self.assertEqual(frames[3][1], frames[4][1])
        self.assertEqual(len(worlds), 2)
        self.assertEqual(worlds[1].state, "playing")
        self.assertGreater(worlds[0].player.cooldowns["r"], 40)
        self.assertGreater(worlds[0].player.stasis, 0)

    def test_spell_button_target_selection_and_held_right_movement(self):
        from dungeon.geometry import Vec
        target = iso(Vec(7.5, 5.5))
        body = (target[0], target[1] - 20)
        first_goal, next_goal = iso(Vec(4.5, 14.5)), iso(Vec(8.5, 14.5))
        script = [
            [key(pygame.K_RETURN)], [click(1, (627, 823))], [click(1, body)],
            [click(1, body)], [], [click(3, first_goal)],
            [pygame.event.Event(pygame.MOUSEMOTION, pos=(round(next_goal[0] * 8 / 9), round(next_goal[1] * 8 / 9)))],
        ] + [[] for _ in range(7)] + [[pygame.event.Event(pygame.MOUSEBUTTONUP, button=3)]]
        snapshots = []
        def observer(frame, world, renderer):
            snapshots.append((renderer.armed, len(world.projectiles)))
        worlds, _ = self.run_app(script, observer)
        world = worlds[0]
        self.assertEqual(snapshots[1], ("q", 0))
        self.assertEqual(snapshots[2], (None, 1))
        self.assertEqual(len(world.projectiles), 1)  # Holding LMB never repeats an attack.
        self.assertIs(world.selected, world.enemies[0])
        self.assertGreater(world.player.pos.x, 3.5)
        self.assertLess((world.destination - Vec(8.5, 14.5)).length(), 0.1)

    def test_clickable_self_cast_and_cancelled_wall_targeting(self):
        script = [[key(pygame.K_RETURN)], [click(1, (840, 823))]]
        script += [[] for _ in range(13)]
        script += [[click(1, (1054, 823))], [click(3, (900, 650))]]
        worlds, _ = self.run_app(script)
        world = worlds[0]
        self.assertLess(world.player.mana, 80)
        self.assertGreater(world.player.cooldowns["w"], 0)
        self.assertEqual(world.player.cooldowns["e"], 0)
        self.assertEqual(world.ice_walls, [])
        self.assertIsNone(world.destination)


if __name__ == "__main__":
    unittest.main()
