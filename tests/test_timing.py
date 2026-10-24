"""Active gameplay timing, persistence, eligibility and completion boundaries."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from dungeon.profile import ProfileStore
from dungeon.timing import Timing, RULES, display
from dungeon.tutorial import PracticeWorld
from dungeon.world import World


class TimingTests(unittest.TestCase):
    def quiet(self):
        world = World(7)
        world.enemies.clear()
        world.spawners.clear()
        return world

    def test_frame_rate_and_pause_resume(self):
        for fps in (20, 30, 60, 144):
            world = self.quiet()
            with patch.object(world, '_update_simulation'):
                for _ in range(fps * 3):
                    world.update(1 / fps)
                self.assertAlmostEqual(world.player.timing.floor_seconds, 3)
                # Paused frontend/overlays do not call World.update.
                world.update(.5)
                self.assertAlmostEqual(world.player.timing.total_seconds, 3.5)

    def test_clear_delay_duplicate_and_previous_best(self):
        world = self.quiet()
        timer = world.player.timing
        timer.records[timer.key()] = 10
        world.update(.4)
        world._complete_level()
        self.assertEqual(timer.previous_best, 10)
        self.assertTrue(timer.new_best)
        records = timer.records.copy()
        for _ in range(20):
            world.update(1)
            world._complete_level()
        self.assertEqual(timer.floor_seconds, .4)
        self.assertGreaterEqual(timer.total_seconds, .4)
        self.assertEqual(timer.records, records)
        self.assertEqual(timer.cleared, [1])

    def test_delay_excluded_but_active_loot_collection_counts_for_run(self):
        world = self.quiet()
        world.update(.25)
        world._complete_level()
        world.update(.1)  # Starts presentation without adding floor time.
        before = world.player.timing.total_seconds
        world.update(.5)
        self.assertEqual(world.player.timing.total_seconds, before)
        world.update(2)  # Finishes the presentation; still excluded.
        self.assertEqual(world.player.timing.total_seconds, before)
        world.update(.4)  # World active again, collecting loot.
        self.assertAlmostEqual(world.player.timing.total_seconds, before + .4)
        self.assertEqual(world.player.timing.floor_seconds, .25)

    def test_failed_run_never_changes_records(self):
        world = self.quiet()
        timer = world.player.timing
        timer.records[timer.key()] = 50
        world.update(.1)
        world._hurt_player(10000)
        world.update(10)
        timer.clear()
        self.assertEqual(timer.best(), 50)
        self.assertFalse(timer.eligible)
        self.assertEqual(timer.total_seconds, .1)

    def test_restart_and_practice_separation(self):
        timer = Timing()
        timer.advance(20)
        timer.clear()
        timer.restart(1, campaign=False)
        timer.advance(1)
        timer.clear()
        self.assertEqual(len(timer.records), 2)
        timer.restart(campaign=True)
        self.assertEqual(timer.total_seconds, 0)
        self.assertEqual(timer.best(), 20)

    def test_only_complete_campaign_sets_first_five(self):
        for campaign in (True, False):
            timer = Timing()
            timer.restart(campaign=campaign)
            for floor in range(1, 6):
                timer.begin_floor(floor)
                timer.advance(floor)
                timer.clear()
            key = f'{RULES}/campaign/first-five'
            self.assertEqual(timer.records.get(key), 15 if campaign else None)
        timer = Timing()
        timer.begin_floor(5)
        timer.advance(1)
        timer.clear()
        self.assertNotIn(key, timer.records)

    def test_save_continue_and_old_save(self):
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder) / 'profile.json')
            world = self.quiet()
            world.update(.7)
            self.assertTrue(store.save(world.player))
            resumed = World(7, player=store.load())
            with patch.object(resumed, '_update_simulation'):
                resumed.update(.2)
            self.assertAlmostEqual(resumed.player.timing.total_seconds, .9)
            data = json.loads(store.path.read_text())
            data['version'] = 1
            data.pop('timing')
            store.path.write_text(json.dumps(data))
            legacy = store.load()
            self.assertIsNotNone(legacy)
            self.assertFalse(legacy.timing.eligible)
            legacy.timing.advance(1)
            legacy.timing.clear()
            self.assertEqual(legacy.timing.records, {})

    def test_tutorial_and_custom_balance_ineligible(self):
        world = PracticeWorld()
        world.update(.5)
        self.assertEqual(world.player.timing.total_seconds, 0)
        self.assertFalse(World(7, mana_regen=999).player.timing.eligible)

    def test_display_and_unknown_rules(self):
        self.assertEqual(display(61.239), '01:01.23')
        self.assertEqual(display(None), '--:--.--')
        timer = Timing.from_dict(dict(Timing().to_dict(), rules='future'))
        self.assertFalse(timer.eligible)
