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
    def run_app(self, script, observer=None, profile_path=None):
        worlds, frames = [], []
        pointer = [800, 480]
        buttons = [False, False, False]
        index = 0

        def new_world(seed, **kwargs):
            world = World(seed, **kwargs)
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

        args = ["main.py", "--frames", str(len(script)), "--seed", "7"]
        args += ["--profile", str(profile_path)] if profile_path is not None else ["--no-save"]
        with (
            patch.object(sys, "argv", args),
            patch("dungeon.app.World", side_effect=new_world),
            patch("dungeon.render.Renderer", RecordingRenderer),
            patch("pygame.event.get", side_effect=events),
            patch("pygame.key.get_pressed", return_value=NoKeys()),
            patch("pygame.mouse.get_pos", side_effect=lambda: tuple(pointer)),
            patch("pygame.mouse.get_pressed", side_effect=lambda: tuple(buttons)),
        ):
            app.main()
        return worlds, frames

    def test_entering_portal_loads_forest_floor_and_resets_input(self):
        layouts, floors = [], []
        def observer(frame, world, renderer):
            layouts.append(world.layout)
            floors.append(pygame.image.tobytes(renderer.floor, "RGBA"))
            if frame == 1:
                world.spawners.clear()
                world.player.pos = world.exit
        script = [[key(pygame.K_RETURN)], [], [key(pygame.K_RETURN)],
                  [click(1, (1054, 823))], [key(pygame.K_ESCAPE)], [key(pygame.K_i)], [key(pygame.K_ESCAPE)]]
        worlds, frames = self.run_app(script, observer)
        world = worlds[0]
        self.assertEqual(world.level, 2)
        self.assertEqual(world.level_data.name, "Thornveil Forest")
        self.assertNotEqual(layouts[0], layouts[2])
        self.assertNotEqual(floors[0], floors[2])
        self.assertEqual(floors[2], floors[-1])
        self.assertEqual(frames[5][0], "inventory")
        self.assertEqual(frames[-1][0], "playing")

    def test_ultimate_pause_focus_resume_and_enter_restart(self):
        ultimate_seen = []
        def observer(frame, world, renderer):
            if frame == 2:
                ultimate_seen.append(world.player.stasis)
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
        self.assertGreater(ultimate_seen[0], 0)

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


    def test_inventory_pauses_combat_and_shop_buy_enchant_equip_work(self):
        def observer(frame, world, renderer):
            if frame == 1:
                world.player.gold = 1000
        script = [
            [key(pygame.K_RETURN)], [key(pygame.K_i)],
            [key(pygame.K_q), click(3, (900, 500))],
            [key(pygame.K_b), pygame.event.Event(pygame.MOUSEBUTTONUP, button=3)],
            [click(1, (800, 295))], [click(1, (1060, 597))],
            [key(pygame.K_i)], [click(1, (780, 757))],
            [click(1, (780, 757))], [key(pygame.K_ESCAPE)],
        ]
        worlds, frames = self.run_app(script, observer)
        world = worlds[0]
        self.assertEqual([mode for mode, _ in frames], [
            "playing", "inventory", "inventory", "shop", "shop", "shop",
            "inventory", "inventory", "inventory", "playing",
        ])
        self.assertTrue(all(time == frames[0][1] for _, time in frames[1:9]))
        self.assertEqual(world.player.gold, 910)
        self.assertEqual(world.player.inventory.worn("helm").rank, 1)
        self.assertEqual(world.player.inventory.stats.damage, .1)
        self.assertEqual(world.projectiles, [])
        self.assertIsNone(world.destination)

    def test_gate_transition_preserves_player_and_opens_next_depth(self):
        def observer(frame, world, renderer):
            if frame == 1:
                world.spawners.clear()
                world.player.pos = world.exit
                world.player.gold = 250
        worlds, _ = self.run_app([[key(pygame.K_RETURN)], [], [key(pygame.K_RETURN)]], observer)
        self.assertEqual(len(worlds), 1)
        self.assertEqual(worlds[0].level, 2)
        self.assertEqual(worlds[0].state, "playing")
        self.assertTrue(worlds[0].player.first_clear_rewarded)
        self.assertEqual(worlds[0].player.inventory.worn("boots").rank, 1)
        self.assertGreaterEqual(worlds[0].player.gold, 250)

    def test_backpack_paging_renders_and_keeps_all_items_accessible(self):
        observed_pages = []
        def observer(frame, world, renderer):
            if frame == 1:
                for _ in range(33):
                    inv = world.player.inventory
                    inv.add(inv.create("helm", 1), auto_equip=False)
            elif frame in (2, 3, 4):
                observed_pages.append([i.uid for i in renderer.armory.bag_page(world)])
        script = [[key(pygame.K_RETURN)], [key(pygame.K_i)],
                  [click(1, (829, 646))], [click(1, (829, 646))]]
        worlds, _ = self.run_app(script, observer)
        self.assertEqual([len(page) for page in observed_pages], [16, 16, 1])
        self.assertEqual(len(set(uid for page in observed_pages for uid in page)), 33)
        self.assertEqual(len(worlds[0].player.inventory.items), 33)

    def test_desktop_profile_survives_close_and_loads_next_session(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        def observer(frame, world, renderer):
            inv = world.player.inventory
            inv.add(inv.create("helm", 3))
            world.player.gold = 321
            world.player.unlocked_level = 2
            world.player.first_clear_rewarded = True
        with TemporaryDirectory() as folder:
            profile = Path(folder) / "profile.json"
            self.run_app([[key(pygame.K_RETURN)]], observer, profile)
            self.assertTrue(profile.exists())
            worlds, _ = self.run_app([[key(pygame.K_RETURN)]], profile_path=profile)
            self.assertEqual(worlds[0].player.gold, 321)
            self.assertEqual(worlds[0].player.inventory.worn("helm").rank, 3)
            self.assertEqual(worlds[0].level, 2)


    def test_sell_and_destroy_confirmation_cancel_then_confirm(self):
        pending = []
        def observer(frame, world, renderer):
            if frame == 1:
                inv = world.player.inventory
                inv.add(inv.create("helm", 1), auto_equip=False)
                inv.add(inv.create("boots", 2), auto_equip=False)
            pending.append(renderer.armory.pending_destroy_uid)
        script = [
            [key(pygame.K_RETURN)], [key(pygame.K_i)],
            [click(1, (551, 757))],  # Sell the selected spare helm.
            [click(1, (648, 757))],  # Request destruction of the remaining boots.
            [click(1, (551, 757))],  # Underlying Sell button is blocked by the modal.
            [key(pygame.K_ESCAPE)], # Cancel; inventory remains open.
            [click(1, (648, 757))], [click(1, (830, 515))],
        ]
        worlds, frames = self.run_app(script, observer)
        world = worlds[0]
        self.assertEqual(world.player.gold, 22)
        self.assertEqual(world.player.inventory.items, [])
        self.assertIsNotNone(pending[3])
        self.assertEqual(pending[3], pending[4])
        self.assertIsNone(pending[5])
        self.assertEqual(frames[5][0], "inventory")
        self.assertIsNone(pending[-1])

    def test_shop_supports_selling_and_destroy_cancel_button(self):
        def observer(frame, world, renderer):
            if frame == 1:
                inv = world.player.inventory
                inv.add(inv.create("helm", 1), auto_equip=False)
                inv.add(inv.create("boots", 2), auto_equip=False)
        script = [
            [key(pygame.K_RETURN)], [key(pygame.K_b)], [click(1, (551, 757))],
            [click(1, (648, 757))], [click(1, (590, 515))], [click(1, (551, 757))],
        ]
        worlds, frames = self.run_app(script, observer)
        self.assertEqual(worlds[0].player.inventory.items, [])
        self.assertEqual(worlds[0].player.gold, 122)
        self.assertTrue(all(mode == "shop" for mode, _ in frames[1:]))


if __name__ == "__main__":
    unittest.main()
