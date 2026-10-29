"""Action completion, assistance, armory integration, and desktop persistence boundaries."""

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from dungeon.armory import Armory
from dungeon.controls import Controls
from dungeon.geometry import Vec
from dungeon.profile import ProfileStore
from dungeon.tutorial import LESSONS, PracticeWorld, Tutorial
from dungeon.world import Player, World
import test_desktop as desktop
from test_desktop import click, key


class TutorialTests(unittest.TestCase):
    def setUp(self):
        self.normal = World(7)
        self.t = Tutorial(self.normal)
        self.w = self.t.world

    def lesson(self, name):
        self.t.index = next(i for i, step in enumerate(LESSONS) if step[0] == name)
        self.t.retry()

    def tick(self, seconds):
        for _ in range(round(seconds * 60)):
            self.w.update(1 / 60)
            self.t.observe()

    def test_move_requires_arrival_and_select_requires_target(self):
        self.assertFalse(self.t.next())
        self.w.request_move(self.t.mark)
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.tick(1)
        self.assertTrue(self.t.next())
        self.assertEqual(self.t.step, "select")
        Controls(self.w).left_world(self.t.targets[0].pos, self.t.targets[0])
        self.t.observe()
        self.assertTrue(self.t.ready)

    def test_bolt_requires_real_hit_not_press_or_miss(self):
        self.lesson("bolt")
        self.assertTrue(self.w.cast("q", Vec(4, 10)))
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.tick(1.2)
        self.assertFalse(self.t.ready)
        self.assertTrue(self.w.cast("q", self.t.targets[0].pos))
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.tick(.4)
        self.assertTrue(self.t.ready)
        self.assertGreater(self.t.targets[0].chilled, 0)
        self.assertEqual(self.t.targets[0].frozen, 0)

    def test_failures_show_real_reason_and_never_complete(self):
        for name, key_, reason in (("nova", "w", "Not enough mana."),
                                   ("patch", "e", "Not enough mana."),
                                   ("prison", "r", "Not enough mana.")):
            self.lesson(name)
            self.w.player.mana = 0
            self.assertFalse(self.w.cast(key_, self.t.mark))
            self.assertEqual(self.w.message, reason)
            self.t.observe()
            self.assertFalse(self.t.ready)
            self.t.retry()
            self.w.player.cooldowns[key_] = 5
            self.assertFalse(self.w.cast(key_, self.t.mark))
            self.assertIn("cooling down", self.w.message)
            self.t.observe()
            self.assertFalse(self.t.ready)
        self.lesson("patch")
        self.assertFalse(self.w.cast("e", Vec(1, 1)))
        self.assertIn("out of range", self.w.message)
        self.assertEqual(self.w.player.mana, 100)
        self.t.observe()
        self.assertFalse(self.t.ready)

    def test_nova_both_targets_and_retry_after_miss(self):
        self.lesson("nova")
        self.w.player.pos = Vec(3, 3)
        self.w.cast("w")
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.t.retry()
        self.w.cast("w")
        self.t.observe()
        self.assertTrue(self.t.ready)
        self.assertTrue(all(t.frozen > 0 for t in self.t.targets))

    def test_patch_requires_enemy_effect_and_mage_bonus(self):
        self.lesson("patch")
        self.w.player.pos = Vec(7, 9.5)
        self.w.cast("e", self.t.mark)
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.w.request_move(self.t.mark)
        self.tick(1)
        self.assertTrue(self.t.ready)

    def test_prison_requires_protection_and_release_then_resets_long_cooldown(self):
        self.lesson("prison")
        self.w.cast("r")
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.assertFalse(self.w.cast("q", self.t.mark))
        pos = self.w.player.pos
        self.w.request_move(Vec(12, 12))
        self.tick(2)
        self.assertEqual(self.w.player.pos, pos)
        self.assertTrue(self.t.protected)
        self.assertFalse(self.t.ready)
        self.tick(.6)
        self.assertTrue(self.t.ready)
        self.assertEqual(self.w.player.hp, self.w.player.max_hp)
        self.assertGreater(self.w.player.cooldowns["r"], 40)
        self.t.retry()
        self.assertEqual(self.w.player.cooldowns["r"], 0)
        self.assertEqual(self.w.player.stasis, 0)

    def test_heal_needs_consumed_potion_and_restored_health(self):
        self.lesson("heal")
        self.w.player.potions = 0
        self.w.use_potion()
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.t.retry()
        self.w.use_potion()
        self.t.observe()
        self.assertTrue(self.t.ready)
        self.assertEqual(self.w.player.potions, 2)
        self.assertEqual(self.w.player.hp, self.w.player.max_hp)

    def test_pickup_inspection_and_real_equip_button(self):
        self.lesson("pickup")
        self.w.request_move(self.t.mark)
        self.tick(1)
        self.assertTrue(self.t.ready)
        self.assertEqual(self.w.player.inventory.worn("helm").rank, 1)
        self.t.next()
        a = Armory()
        point = a.bag_rects[0].center
        self.t.observe("inventory", a, point)
        self.assertFalse(self.t.ready)
        a.click(self.w, point, "inventory")
        self.t.observe("playing", a, point)
        self.assertFalse(self.t.ready)
        self.t.observe("inventory", a, point)
        self.assertTrue(self.t.next())
        self.assertEqual(self.t.step, "equip")
        self.t.observe()
        self.assertFalse(self.t.ready)
        a.click(self.w, a.bag_rects[0].center, "inventory")
        a.click(self.w, a.equip_rect.center, "inventory")
        self.t.observe("inventory", a)
        self.assertTrue(self.t.ready)
        self.assertEqual(self.w.player.inventory.stats.damage, .20)
        self.assertIn(self.t.old_uid, [i.uid for i in self.w.player.inventory.backpack])

    def test_retry_restores_destroyed_item_and_clears_ui_independent_state(self):
        self.lesson("equip")
        self.w.destroy_item(self.t.item.uid)
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.t.retry()
        self.assertIsNotNone(self.w.player.inventory.get(self.t.item.uid))
        self.assertEqual(len(self.w.player.inventory.items), 2)
        self.assertEqual(self.w.player.inventory.stats.damage, .10)

    def test_skips_do_not_count_as_actions_and_final_requires_kills(self):
        self.assertTrue(self.t.next(skip=True))
        self.assertEqual(self.t.skipped, {"move"})
        self.assertFalse(self.t.completed)
        self.lesson("final")
        self.w.cast("q", Vec(1, 1))
        self.t.observe()
        self.assertFalse(self.t.ready)
        for target in self.w.enemies[:]:
            self.w._hit(target, 100)
        self.t.observe()
        self.assertTrue(self.t.next())
        self.assertEqual(self.t.step, "complete")
        self.assertFalse(self.t.next(skip=True))

    def test_practice_is_disposable_and_death_cannot_softlock(self):
        before = self.normal.player.inventory.to_dict()
        self.w.player.gold = 99999
        self.w.player.unlocked_level = 5
        self.w.state, self.w.player.hp = "dead", 0
        self.t.observe()
        self.assertEqual(self.w.state, "playing")
        self.assertEqual(self.w.player.hp, self.w.player.max_hp)
        self.assertEqual(self.normal.player.gold, 0)
        self.assertEqual(self.normal.player.unlocked_level, 1)
        self.assertEqual(self.normal.player.inventory.to_dict(), before)
        self.assertIs(self.t.normal_world, self.normal)

    def test_entire_tutorial_actions_without_skipping(self):
        self.w.request_move(self.t.mark)
        self.tick(1)
        self.assertTrue(self.t.next())
        Controls(self.w).left_world(self.t.targets[0].pos, self.t.targets[0])
        self.t.observe()
        self.assertTrue(self.t.next())
        self.w.cast("q", self.t.targets[0].pos)
        self.tick(.5)
        self.assertTrue(self.t.next())
        self.w.cast("w")
        self.t.observe()
        self.assertTrue(self.t.next())
        self.w.cast("e", self.t.mark)
        self.t.observe()
        self.assertFalse(self.t.ready)  # Walk into the bonus field as well.
        self.w.request_move(self.t.mark)
        self.tick(1)
        self.assertTrue(self.t.next())
        self.w.cast("r")
        self.tick(3)
        self.assertTrue(self.t.next())
        self.w.use_potion()
        self.t.observe()
        self.assertTrue(self.t.next())
        self.w.request_move(self.t.mark)
        self.tick(1)
        self.assertTrue(self.t.next())
        a = Armory()
        point = a.bag_rects[0].center
        a.click(self.w, point, "inventory")
        self.t.observe("inventory", a, point)
        self.assertTrue(self.t.next())
        a.click(self.w, point, "inventory")
        a.click(self.w, a.equip_rect.center, "inventory")
        self.t.observe("inventory", a)
        self.assertTrue(self.t.ready)
        self.w.unequip_item("helm")
        self.t.observe()
        self.assertFalse(self.t.ready)
        self.w.equip_item(self.t.item.uid)
        self.t.observe()
        self.assertTrue(self.t.next())
        self.t.observe()
        self.assertTrue(self.t.next())
        self.w.cast("r")
        self.tick(3)
        for _ in range(20):
            if not self.w.enemies:
                break
            self.w.cast("q", self.w.enemies[0].pos)
            self.tick(.5)
        self.assertTrue(self.t.next())
        self.assertEqual(self.t.step, "complete")
        self.assertEqual(len(self.t.completed), len(LESSONS) - 1)
        self.assertFalse(self.t.skipped)

    def test_callouts_scale_with_canvas_and_do_not_cover_targets_or_armory_controls(self):
        from dungeon.render import Renderer, WIDTH, HEIGHT, iso
        pygame.display.init()
        pygame.font.init()
        canvas = pygame.Surface((WIDTH, HEIGHT))
        r = Renderer(canvas, self.w)
        for i, (_, _, lines) in enumerate(LESSONS):
            self.t.index = i
            self.t.retry()
            self.assertTrue(all(r.font(12).size(line)[0] <= 1056 for line in lines))
            for target in self.t.targets:
                x, y = iso(target.pos)
                self.assertGreater(y - 40, 357)
            for mode in ("playing", "inventory"):
                r.draw(self.w, None, mode)
                self.t.draw(r, mode)
                for size in ((1024, 768), (1280, 800), (1440, 900), (1920, 1080)):
                    scale = min(size[0] / WIDTH, size[1] / HEIGHT)
                    scaled = pygame.transform.smoothscale(canvas, (round(WIDTH * scale), round(HEIGHT * scale)))
                    self.assertLessEqual(scaled.get_width(), size[0])
                    self.assertLessEqual(scaled.get_height(), size[1])
            header = pygame.Rect(318, 4, 1080, 94)
            self.assertFalse(header.colliderect(r.armory.close_rect))
            self.assertFalse(header.colliderect(r.armory.equip_rect))
        pygame.quit()


class TutorialDesktopTests(unittest.TestCase):
    def run_app(self, *args, **kwargs):
        return desktop.DesktopTests().run_app(*args, skip_offer=False, **kwargs)

    def test_offer_and_skip_without_forcing_returning_players(self):
        _, frames = self.run_app([[key(pygame.K_RETURN)], [click(1, (915, 554))]])
        self.assertEqual([m for m, _ in frames], ["tutorial_offer", "playing"])

    def test_existing_save_bytes_unchanged_during_exit_completion_and_abandon(self):
        for finish in ("exit", "complete", "abandon", "resume"):
            with self.subTest(finish=finish), TemporaryDirectory() as folder:
                path = Path(folder) / "profile.json"
                p = Player(gold=876, unlocked_level=3, current_level=2)
                p.inventory.add(p.inventory.create("boots", 3))
                ProfileStore(path).save(p)
                before = path.read_bytes()
                seen = []

                def observer(frame, world, renderer):
                    seen.append(world)
                    if isinstance(world, PracticeWorld):
                        world.player.gold = 9999
                        self.assertEqual(path.read_bytes(), before)

                script = [[click(1, (480, 749))], []]
                if finish in ("complete", "resume"):
                    script += [[click(1, (989, 881))] for _ in range(len(LESSONS) - 1)]
                    script += [[click(1, (449 if finish == "resume" else 719, 881))]]
                elif finish == "exit":
                    script += [[click(1, (1259, 881))]]
                worlds, frames = self.run_app(script, observer, path)
                # Resuming play also leaves a manual checkpoint unchanged.
                self.assertEqual(path.read_bytes(), before)
                self.assertIs(seen[0], seen[1])
                self.assertEqual(worlds[0].player.gold, 876)
                if finish != "abandon":
                    self.assertIs(seen[-1], worlds[0])
                    self.assertEqual(frames[-1][0], "playing" if finish == "resume" else "title")

    def test_new_game_tutorial_can_exit_without_creating_profile(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            _, frames = self.run_app([[key(pygame.K_RETURN)], [click(1, (525, 554))],
                                     [key(pygame.K_i)], [key(pygame.K_ESCAPE)],
                                     [click(1, (1259, 881))]], profile_path=path)
            self.assertEqual([m for m, _ in frames], ["tutorial_offer", "playing", "inventory", "playing", "title"])
            self.assertFalse(path.exists())

    def test_legacy_save_is_not_normalized_on_tutorial_exit(self):
        import json
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            ProfileStore(path).save(Player(gold=42))
            data = json.loads(path.read_text())
            for field in ("current_level", "cleared_floor", "lower_tower_completed"):
                del data[field]
            path.write_text(json.dumps(data))
            before = path.read_bytes()
            self.run_app([[click(1, (480, 749))], [click(1, (1259, 881))]], profile_path=path)
            self.assertEqual(path.read_bytes(), before)

    def test_retry_skip_and_rapid_next_do_not_complete_unfinished_actions(self):
        _, frames = self.run_app([[click(1, (480, 749))],
                                 [key(pygame.K_q), key(pygame.K_RETURN), key(pygame.K_RETURN)],
                                 [click(1, (719, 881))], [click(1, (989, 881))],
                                 [click(1, (1259, 881))]])
        self.assertEqual(frames[-1][0], "title")

    def test_inventory_stays_open_between_inspection_and_equipping(self):
        seen = []

        def observer(frame, world, renderer):
            seen.append((renderer.armory.selected_uid, world.player.inventory.stats.damage))

        script = [[click(1, (480, 749))]] + [[click(1, (989, 881))] for _ in range(8)]
        script += [[click(1, (1170, 127))], [click(1, (549, 303))],
                   [click(1, (449, 881))], [click(1, (783, 757))]]
        _, frames = self.run_app(script, observer)
        self.assertEqual([m for m, _ in frames[-4:]], ["inventory"] * 4)
        self.assertEqual(seen[-2], (2, .10))
        self.assertEqual(seen[-1], (2, .20))

    def test_start_game_after_new_game_lesson_discards_all_practice_rewards(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            script = [[key(pygame.K_RETURN)], [click(1, (525, 554))]]
            script += [[click(1, (989, 881))] for _ in range(len(LESSONS) - 1)]
            script += [[click(1, (449, 881))]]
            worlds, frames = self.run_app(script, profile_path=path)
            self.assertEqual(frames[-1][0], "playing")
            self.assertFalse(path.exists())  # Save Game selects a destination later.
            self.assertEqual(worlds[-1].player.gold, 0)
            self.assertEqual(worlds[-1].player.potions, 3)
            self.assertEqual(worlds[-1].player.inventory.items, [])
            self.assertEqual(worlds[-1].player.unlocked_level, 1)
            self.assertIsNot(worlds[-1], worlds[0])


if __name__ == "__main__":
    unittest.main()
