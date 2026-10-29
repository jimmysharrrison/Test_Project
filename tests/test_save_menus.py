"""Drive save/load menus through actual desktop keyboard and mouse events."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pygame
import test_desktop as desktop
from test_desktop import click, key
from dungeon.saves import SaveSlots
from dungeon.world import World


class SaveMenuTests(unittest.TestCase):
    def run_app(self, *args, **kwargs):
        return desktop.DesktopTests().run_app(*args, **kwargs)

    def test_save_paused_game_to_empty_slot_and_load_next_session(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            def prepare(frame, world, renderer):
                if frame == 1:
                    world.player.gold = 321
                    world.player.hp = 38
                    world.player.mana = 27
                    world.player.cooldowns['w'] = 2.5
            _, frames = self.run_app([[key(pygame.K_RETURN)], [key(pygame.K_ESCAPE)],
                                      [click(1, (570, 487))], [click(1, (720, 393))]], prepare, path)
            self.assertEqual([mode for mode, _ in frames], ['playing', 'paused', 'save_slots', 'paused'])
            slots = SaveSlots(path)
            self.assertFalse(path.exists())
            self.assertTrue(slots.store(2).path.exists())
            saved = slots.load(2)
            self.assertEqual((saved.player.gold, saved.player.hp, saved.player.mana), (321, 38, 27))
            self.assertEqual(saved.player.cooldowns['w'], 2.5)
            seen = []
            _, frames = self.run_app([[click(1, (970, 364))], [click(1, (720, 393))]],
                                      lambda f, w, r: seen.append(w), path)
            self.assertEqual([mode for mode, _ in frames], ['load_slots', 'playing'])
            self.assertEqual(seen[-1].player.gold, 321)
            self.assertEqual(seen[-1].player.hp, 38)

    def test_new_game_and_overwrite_cancel_preserve_old_bytes_then_confirm_replaces(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            slots = SaveSlots(path)
            original = World(7)
            original.player.gold = 987
            slots.save(1, original)
            before = path.read_bytes()
            checked = []
            def observe(frame, world, renderer):
                if frame in (2, 7):
                    checked.append(path.read_bytes())
                if frame == 2:
                    world.player.gold = 42
            script = [[key(pygame.K_RETURN)], [click(1, (915, 554))],
                      [key(pygame.K_ESCAPE)], [click(1, (570, 487))],
                      [click(1, (720, 302))], [key(pygame.K_ESCAPE)],
                      [click(1, (720, 302))], [click(1, (915, 554))]]
            _, frames = self.run_app(script, observe, path)
            self.assertEqual(checked, [before, before])
            self.assertEqual([m for m, _ in frames][-4:], ['confirm_overwrite', 'save_slots', 'confirm_overwrite', 'paused'])
            self.assertEqual(SaveSlots(path).load(1).player.gold, 42)

    def test_empty_load_slots_are_disabled_and_escape_returns(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            slots = SaveSlots(path)
            slots.save(3, World(7))
            _, frames = self.run_app([[click(1, (970, 364))], [click(1, (720, 302))],
                                      [key(pygame.K_ESCAPE)]], profile_path=path)
            self.assertEqual([m for m, _ in frames], ['load_slots', 'load_slots', 'title'])

    def test_load_during_play_requires_confirmation_and_cancel_keeps_world(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            slots = SaveSlots(path)
            world = World(7)
            world.player.gold = 987
            slots.save(2, world)
            captured = []
            def observer(frame, world, renderer):
                if frame == 1:
                    world.player.gold = 42
                    renderer.armory.selected_uid = 99
                    renderer.armory.enchant_uid = 99
                captured.append((world, world.player.gold, renderer.armory.selected_uid, renderer.armory.enchant_uid))
            script = [[key(pygame.K_RETURN)], [key(pygame.K_ESCAPE)],
                      [click(1, (1125, 487))], [click(1, (720, 393))],
                      [key(pygame.K_ESCAPE)], [click(1, (720, 393))], [click(1, (915, 554))]]
            _, frames = self.run_app(script, observer, path)
            self.assertEqual([m for m, _ in frames][-4:], ['confirm_load', 'load_slots', 'confirm_load', 'playing'])
            self.assertIs(captured[0][0], captured[-2][0])
            self.assertEqual(captured[-2][1], 42)
            self.assertEqual(captured[-1][1:], (987, None, None))

    def test_save_slots_pause_time_and_keyboard_defaults_to_cancel(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            slots = SaveSlots(path)
            slots.save(2, World(7))
            before = slots.store(2).path.read_bytes()
            script = [[key(pygame.K_RETURN)], [key(pygame.K_ESCAPE)],
                      [click(1, (570, 487))], [key(pygame.K_DOWN), key(pygame.K_RETURN)],
                      [key(pygame.K_RETURN)], [key(pygame.K_ESCAPE)]]
            _, frames = self.run_app(script, profile_path=path)
            self.assertEqual([m for m, _ in frames], ['playing', 'paused', 'save_slots', 'confirm_overwrite', 'save_slots', 'paused'])
            self.assertEqual(len({time for _, time in frames}), 1)
            self.assertEqual(slots.store(2).path.read_bytes(), before)

    def test_quitting_new_unslotted_game_never_replaces_old_save(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            slots = SaveSlots(path)
            slots.save(1, World(7))
            before = path.read_bytes()
            self.run_app([[key(pygame.K_RETURN)], [click(1, (915, 554))], []], profile_path=path)
            self.assertEqual(path.read_bytes(), before)

    def test_no_save_disables_buttons_and_tutorial_never_writes_slots(self):
        observed = []
        def observer(frame, world, renderer):
            observed.append([b.enabled for b in renderer.menu.buttons(world, 'paused') if b.action == 'save_game'][0])
        self.run_app([[key(pygame.K_RETURN)], [key(pygame.K_ESCAPE)]], observer)
        self.assertEqual(observed, [False, False])
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            self.run_app([[click(1, (480, 749))], [key(pygame.K_ESCAPE)],
                          [click(1, (570, 487))]], observer, path)
            self.assertFalse(any(path.parent.glob('*.json')))
            self.assertFalse(observed[-1])
