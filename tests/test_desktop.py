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


def motion(point):
    return pygame.event.Event(pygame.MOUSEMOTION, pos=click(1, point).pos)


def release(button, point):
    return pygame.event.Event(pygame.MOUSEBUTTONUP, button=button, pos=click(button, point).pos)


class DesktopTests(unittest.TestCase):
    def run_app(self, script, observer=None, profile_path=None, extra_args=()):
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
        args += list(extra_args)
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

    def test_launch_waits_on_splash_and_does_not_create_save_or_accept_gameplay_input(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        script = [[], [key(pygame.K_q), key(pygame.K_i), key(pygame.K_b), click(3, (900, 500))], []]
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            worlds, frames = self.run_app(script, profile_path=path)
            self.assertFalse(path.exists())
        self.assertEqual(frames, [("title", 0)] * 3)
        self.assertEqual(worlds[0].projectiles, [])
        self.assertEqual(worlds[0].path, [])

    def test_splash_with_saved_forest_waits_for_continue(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from dungeon.profile import ProfileStore
        from dungeon.world import Player
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            ProfileStore(path).save(Player(current_level=2, unlocked_level=2, gold=99))
            worlds, frames = self.run_app([[], [], [click(1, (970, 364))]], profile_path=path)
        self.assertEqual(frames[:2], [("title", 0)] * 2)
        self.assertEqual(frames[2][0], "playing")
        self.assertEqual(worlds[0].level, 2)
        self.assertEqual(worlds[0].player.gold, 99)

    def test_howto_returns_to_title_and_keyboard_can_start_game(self):
        script = [[click(1, (970, 488))], [key(pygame.K_q), key(pygame.K_i)],
                  [key(pygame.K_RETURN)], [key(pygame.K_RETURN)]]
        worlds, frames = self.run_app(script)
        self.assertEqual([mode for mode, _ in frames], ["howto", "howto", "title", "playing"])
        self.assertEqual([time for _, time in frames[:3]], [0, 0, 0])
        self.assertEqual(worlds[0].level, 1)
        self.assertEqual(worlds[0].projectiles, [])

    def test_start_over_can_be_cancelled_then_resets_character_and_save(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from dungeon.profile import ProfileStore
        from dungeon.world import Player
        snapshots = []
        def observer(frame, world, renderer):
            snapshots.append((world.level, world.player.gold, world.player.unlocked_level,
                              len(world.player.inventory.items)))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            player = Player(current_level=2, unlocked_level=2, gold=999, kills=20, potions=0,
                            first_clear_rewarded=True)
            player.inventory.add(player.inventory.create("helm", 3))
            ProfileStore(path).save(player)
            script = [[click(1, (970, 302))], [key(pygame.K_RETURN)],
                      [click(1, (970, 302))], [key(pygame.K_ESCAPE)],
                      [click(1, (970, 302))], [click(1, (915, 554))]]
            worlds, frames = self.run_app(script, observer, path)
            saved = ProfileStore(path).load()
        self.assertEqual([mode for mode, _ in frames],
                         ["confirm_new", "title", "confirm_new", "title", "confirm_new", "playing"])
        self.assertEqual(snapshots[:5], [(2, 999, 2, 1)] * 5)
        self.assertEqual(snapshots[5], (1, 0, 1, 0))
        self.assertEqual((saved.current_level, saved.unlocked_level, saved.gold, saved.kills, saved.potions),
                         (1, 1, 0, 0, 3))
        self.assertFalse(saved.first_clear_rewarded)
        self.assertEqual(len(worlds), 2)

    def test_locked_level_cannot_be_clicked_or_selected_with_keyboard(self):
        script = [[click(1, (970, 426))], [click(1, (720, 351))],
                  [key(pygame.K_DOWN)], [key(pygame.K_RETURN)]]
        worlds, frames = self.run_app(script)
        self.assertEqual([mode for mode, _ in frames], ["levels", "levels", "levels", "title"])
        self.assertTrue(all(time == 0 for _, time in frames))
        self.assertEqual(len(worlds), 1)
        self.assertEqual(worlds[0].player.unlocked_level, 1)

    def test_cli_level_cannot_bypass_locked_destination_in_interactive_game(self):
        notices = []
        def observer(frame, world, renderer):
            notices.append(renderer.menu.notice)
        worlds, frames = self.run_app([[], [click(1, (970, 426))], [click(1, (720, 351))]],
                                     observer, extra_args=("--level", "2"))
        self.assertEqual(worlds[0].level, 1)
        self.assertIn("locked", notices[0])
        self.assertEqual(frames[-1][0], "levels")

    def test_unlocked_level_replay_keeps_gear_and_highest_unlock_across_reload(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from dungeon.profile import ProfileStore
        from dungeon.world import Player
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            player = Player(current_level=2, unlocked_level=2, gold=444, first_clear_rewarded=True)
            player.inventory.add(player.inventory.create("boots", 2))
            ProfileStore(path).save(player)
            worlds, frames = self.run_app([[click(1, (970, 426))], [click(1, (720, 283))]], profile_path=path)
            saved = ProfileStore(path).load()
            reload_worlds, reload_frames = self.run_app([[], [click(1, (970, 364))]], profile_path=path)
        replay = worlds[-1]
        self.assertEqual((replay.level, saved.current_level, saved.unlocked_level, saved.gold), (1, 1, 2, 444))
        self.assertEqual(saved.inventory.worn("boots").rank, 2)
        self.assertTrue(saved.first_clear_rewarded)
        self.assertEqual(frames[1][0], "playing")
        self.assertEqual(reload_frames[0], ("title", 0))
        self.assertEqual(reload_worlds[0].level, 1)

    def test_first_portal_arrival_unlocks_forest_for_level_select(self):
        snapshots = []
        def observer(frame, world, renderer):
            snapshots.append((world.level, world.player.unlocked_level))
            if frame == 1:
                world.spawners.clear()
                world.player.pos = world.exit
        script = [[key(pygame.K_RETURN)], [], [key(pygame.K_RETURN)],
                  [key(pygame.K_ESCAPE)], [click(1, (852, 614))],
                  [click(1, (970, 426))], [click(1, (720, 351))]]
        worlds, frames = self.run_app(script, observer)
        self.assertEqual(snapshots[:2], [(1, 1), (1, 1)])
        self.assertEqual(snapshots[2], (2, 2))
        self.assertEqual(frames[4][0], "title")
        self.assertEqual(frames[5][0], "levels")
        self.assertEqual(frames[6][0], "playing")
        self.assertEqual(worlds[-1].level, 2)

    def test_pause_help_main_menu_and_continue_do_not_tick_simulation(self):
        script = [[key(pygame.K_RETURN)], [key(pygame.K_ESCAPE)],
                  [click(1, (852, 487))], [key(pygame.K_ESCAPE)],
                  [click(1, (852, 614))], [], [click(1, (970, 364))]]
        worlds, frames = self.run_app(script)
        self.assertEqual([mode for mode, _ in frames],
                         ["playing", "paused", "howto", "paused", "title", "title", "playing"])
        self.assertEqual(len({time for _, time in frames[:6]}), 1)
        self.assertGreater(frames[-1][1], frames[0][1])
        self.assertEqual(len(worlds), 1)

    def test_death_retries_current_level_instead_of_highest_unlocked_level(self):
        def observer(frame, world, renderer):
            if frame == 1:
                world.player.unlocked_level = 2
                world.state = "dead"
                world.player.hp = 0
        worlds, _ = self.run_app([[key(pygame.K_RETURN)], [key(pygame.K_RETURN)]], observer)
        self.assertEqual(worlds[-1].level, 1)
        self.assertEqual(worlds[-1].player.unlocked_level, 2)
        self.assertEqual(worlds[-1].player.hp, worlds[-1].player.max_hp)

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
            worlds, frames = self.run_app([[], [click(1, (970, 364))]], profile_path=profile)
            self.assertEqual(worlds[0].player.gold, 321)
            self.assertEqual(worlds[0].player.inventory.worn("helm").rank, 3)
            self.assertEqual(worlds[0].level, 1)
            self.assertEqual(worlds[0].player.unlocked_level, 2)
            self.assertEqual(frames[0], ("title", 0))
            self.assertEqual(frames[1][0], "playing")


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

    def test_upgrade_first_grid_click_equips_correct_item_and_updates_markers(self):
        snapshots = []
        def observer(frame, world, renderer):
            inv = world.player.inventory
            if frame == 1:
                inv.add(inv.create("helm", 1))
                for _ in range(18):
                    inv.add(inv.create("helm", 1), auto_equip=False)
                inv.add(inv.create("helm", 3), auto_equip=False)
            if frame in (2, 4):
                snapshots.append([(item.uid, inv.is_upgrade(item)) for item in renderer.armory.bag_page(world)])
        script = [[key(pygame.K_RETURN)], [key(pygame.K_i)],
                  [click(1, (550, 300))], [click(1, (780, 757))]]
        worlds, _ = self.run_app(script, observer)
        inv = worlds[0].player.inventory
        self.assertTrue(snapshots[0][0][1])
        self.assertEqual(inv.worn("helm").uid, snapshots[0][0][0])
        self.assertEqual(inv.worn("helm").rank, 3)
        self.assertFalse(any(upgrade for _, upgrade in snapshots[1]))
        self.assertEqual(len(inv.backpack), 19)

    def test_bulk_confirmation_escape_tab_switch_and_confirm_persist_across_reload(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from dungeon.profile import ProfileStore
        pending, gold = [], []
        sold = []
        def observer(frame, world, renderer):
            if frame == 1:
                inv = world.player.inventory
                inv.add(inv.create("chest", 2))
                for i in range(21):
                    item = inv.create("helm" if i % 2 else "boots", 2)
                    inv.add(item, auto_equip=False)
                    sold.append(item)
                inv.add(inv.create("gloves", 3), auto_equip=False)
            pending.append(len(renderer.armory.pending_sale_items))
            gold.append(world.player.gold)
        script = [[key(pygame.K_RETURN)], [key(pygame.K_i)],
                  [click(1, (324, 683))], [click(1, (350, 747))],
                  [key(pygame.K_ESCAPE)], [click(1, (350, 747))],
                  [key(pygame.K_b)], [click(1, (350, 747))], [click(1, (830, 515))]]
        with TemporaryDirectory() as folder:
            profile = Path(folder) / "profile.json"
            _, frames = self.run_app(script, observer, profile)
            player = ProfileStore(profile).load()
        self.assertEqual(pending[3:9], [21, 0, 21, 0, 21, 0])
        self.assertEqual(frames[4][0], "inventory")
        self.assertEqual(frames[6][0], "shop")
        self.assertTrue(all(value == 0 for value in gold[:-1]))
        self.assertEqual(player.gold, sum(item.sell_value for item in sold))
        self.assertEqual(player.inventory.worn("chest").rank, 2)
        self.assertEqual([(item.slot, item.rank) for item in player.inventory.backpack], [("gloves", 3)])

    def test_drag_equipped_gear_to_enchant_slot_then_enchant_through_desktop_events(self):
        snapshots = []
        def observer(frame, world, renderer):
            if frame == 1:
                world.player.gold = 1000
                inv = world.player.inventory
                inv.add(inv.create("helm", 0, "shop"))
            snapshots.append((renderer.armory.dragging, renderer.armory.enchant_uid,
                              world.player.gold, world.player.inventory.worn("helm").rank))
        slot, target, upgrade = (350, 298), (1061, 308), (1060, 597)
        script = [[key(pygame.K_RETURN)], [key(pygame.K_b)], [click(1, slot)],
                  [motion(target)], [release(1, target)], [click(1, upgrade)], [release(1, upgrade)]]
        worlds, frames = self.run_app(script, observer)
        self.assertTrue(snapshots[3][0])
        self.assertEqual(snapshots[4][1:], (1, 1000, 0))
        self.assertEqual(snapshots[5][1:], (1, 950, 1))
        self.assertTrue(all(time == frames[0][1] for _, time in frames))
        self.assertEqual(len(worlds[0].player.inventory.items), 1)
        self.assertEqual(worlds[0].player.inventory.worn("helm").set_id, "frostweave")

    def test_drag_from_inventory_over_enchanter_tab_to_target_preserves_backpack_ownership(self):
        targets = []
        def observer(frame, world, renderer):
            if frame == 1:
                world.player.gold = 123
                inv = world.player.inventory
                inv.add(inv.create("helm", 1), auto_equip=False)
            targets.append(renderer.armory.enchant_uid)
        target = (1061, 308)
        script = [[key(pygame.K_RETURN)], [key(pygame.K_i)], [click(1, (550, 300))],
                  [motion((505, 190))], [motion(target)], [release(1, target)]]
        worlds, frames = self.run_app(script, observer)
        self.assertEqual(frames[2][0], "inventory")
        self.assertEqual(frames[3][0], "shop")
        self.assertEqual(targets[-1], 1)
        inv = worlds[0].player.inventory
        self.assertIsNone(inv.worn("helm"))
        self.assertEqual(len(inv.backpack), 1)
        self.assertEqual(worlds[0].player.gold, 123)

    def test_escape_and_focus_loss_cancel_drags_without_loading_or_losing_items(self):
        state = []
        def observer(frame, world, renderer):
            if frame == 1:
                inv = world.player.inventory
                inv.add(inv.create("helm", 3, "shop"))
            state.append((renderer.armory.dragging, renderer.armory.enchant_uid))
        slot, target = (350, 298), (1061, 308)
        script = [[key(pygame.K_RETURN)], [key(pygame.K_b)],
                  [click(1, slot)], [motion(target)], [key(pygame.K_ESCAPE)], [release(1, target)],
                  [click(1, slot)], [motion(target)], [pygame.event.Event(pygame.WINDOWFOCUSLOST)],
                  [release(1, target)]]
        worlds, frames = self.run_app(script, observer)
        self.assertEqual(state[3], (True, None))
        self.assertEqual(state[4], (False, None))
        self.assertEqual(state[7], (True, None))
        self.assertEqual(state[8], (False, None))
        self.assertTrue(all(mode == "shop" for mode, _ in frames[1:]))
        self.assertEqual(len(worlds[0].player.inventory.items), 1)
        self.assertEqual(worlds[0].player.inventory.worn("helm").rank, 3)


if __name__ == "__main__":
    unittest.main()
