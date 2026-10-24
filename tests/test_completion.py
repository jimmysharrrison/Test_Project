"""Completion transactions and nonblocking presentation timing."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from dungeon.profile import ProfileStore

from dungeon.geometry import Vec
from dungeon.world import Effect, Projectile, World
from dungeon.keeper import TUNING


class CompletionTests(unittest.TestCase):
    def keeper(self, **kwargs):
        world = World(7, level=5, **kwargs)
        world.keeper.next_cast = 100
        return world

    def defeat(self, world):
        world._in_tick = True
        world._hit(world.keeper.boss, 10000)
        world.update(1 / 60)

    def test_same_tick_projectile_deaths_prefer_player_death_in_either_order(self):
        for reverse in (False, True):
            world = self.keeper()
            world.player.hp = 1
            shots = [Projectile(world.keeper.boss.pos, Vec(), damage=10000),
                     Projectile(world.player.pos, Vec(), damage=10000, hostile=True)]
            world.projectiles = shots[::-1] if reverse else shots
            world.update(1 / 60)
            self.assertEqual(world.state, "dead")
            self.assertFalse(world.level_completed)
            self.assertFalse(world.player.lower_tower_completed)
            self.assertEqual(world.player.gold, 0)
            self.assertFalse(world.completion_pending)
            self.assertNotIn("keeper_victory", world.events)

    def test_delay_uses_elapsed_time_at_different_frame_rates_and_keeps_effects(self):
        for fps in (20, 30, 60, 144):
            world = self.keeper()
            self.defeat(world)
            world.effects.append(Effect(Vec(), "burst", 2, 2))
            timer = world.time
            for _ in range(round(fps * 1.4)):
                world.update(1 / fps)
            self.assertFalse(world.floor_clear_notice)
            self.assertLess(world.effects[-1].life, 1)
            self.assertFalse(world._hurt_player(10000))
            world.update(.11)
            self.assertTrue(world.floor_clear_notice)
            self.assertEqual(world.time, timer)
            self.assertEqual(world.state, "playing")
            self.assertEqual(world.player.gold, TUNING.completion_gold)

    def test_repeated_events_commit_rewards_and_telemetry_once(self):
        world = self.keeper(completion_delay_ms=25)
        with patch.object(world, "_record") as record:
            self.defeat(world)
            gear = world.player.inventory.to_dict()
            world._hit(world.keeper.boss, 10000)
            world.keeper.defeated()
            world._complete_level()
            world.update(.03)
            world.update(.03)
            self.assertEqual(world.player.inventory.to_dict(), gear)
            self.assertEqual(world.player.gold, TUNING.completion_gold)
            self.assertEqual(sum(c.args[0] == "floor_cleared" for c in record.call_args_list), 1)
            self.assertTrue(world.floor_clear_notice)

    def test_miniboss_notice_with_survivors_and_combined_floor_notice(self):
        for survivors in (False, True):
            world = World(7, miniboss_delay_ms=20, completion_delay_ms=50)
            world.enemies.clear()
            world.spawners.clear()
            world._activate_boss()
            boss = next(e for e in world.enemies if e.boss_role == "boss")
            if not survivors:
                world.enemies[:] = [boss]
            world._in_tick = True
            world._hit(boss, 10000)
            world.update(.01)
            if survivors:
                self.assertFalse(world.level_completed)
                self.assertFalse(world.player.first_clear_rewarded)
                world.update(.02)
                self.assertIn("defeated!", world.message)
                self.assertFalse(world.floor_clear_notice)
                self.assertTrue(world._hurt_player(1))
            else:
                self.assertTrue(world.level_completed)
                self.assertIsNone(world._miniboss_notice)
                world.update(.051)
                self.assertTrue(world.floor_clear_notice)

    def test_new_encounter_discards_pending_presentation_and_retains_settings(self):
        world = self.keeper(completion_delay_ms=17)
        self.defeat(world)
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder) / "character.json")
            self.assertTrue(store.save(world.player))
            fresh = World(7, player=store.load(), level=5)
        self.assertFalse(fresh.completion_pending)
        self.assertTrue(fresh.floor_clear_notified)
        self.assertEqual(fresh.player.gold, TUNING.completion_gold)
        world = World(7, completion_delay_ms=17, miniboss_delay_ms=23)
        world.state = "cleared"
        self.assertTrue(world.next_level())
        self.assertEqual((world.completion_delay_ms, world.miniboss_delay_ms), (17, 23))
        self.assertFalse(world.completion_pending)
