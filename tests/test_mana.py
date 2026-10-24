import tempfile
import unittest
from pathlib import Path
from dungeon.world import World
from dungeon.geometry import Vec
from dungeon.profile import ProfileStore
from dungeon.items import SLOTS


class ManaTests(unittest.TestCase):
    def world(self, rate=6):
        w = World(7, mana_regen=rate)
        w.enemies.clear()
        for s in w.spawners:
            s.timer = 9999
        return w

    def test_frame_rates_and_clamp(self):
        for fps in (30, 60, 144):
            w = self.world()
            w.player.mana = 0
            for _ in range(fps * 4):
                w.update(1 / fps)
            self.assertAlmostEqual(w.player.mana, 24)
            w.player.mana = 150
            w.update(1 / fps)
            self.assertEqual(w.player.mana, w.player.max_mana)
        # Existing simulation caps a long frame at 1/30, including cooldowns.
        w = self.world()
        w.player.mana = 0
        w.update(1 / 15)
        self.assertAlmostEqual(w.player.mana, .2)

    def test_paused_and_stasis(self):
        w = self.world()
        w.player.mana = 0
        w.state = 'paused'
        w.update(1)
        self.assertEqual(w.player.mana, 0)
        w.state = 'playing'
        w.player.stasis = 2
        w.update(1 / 30)
        self.assertAlmostEqual(w.player.mana, .2)

    def test_free_fallback_at_empty(self):
        w = self.world()
        w.player.mana = 0
        self.assertFalse(w.cast('w'))
        self.assertTrue(w.cast('q', w.player.pos + Vec(1, 0)))
        self.assertEqual(w.player.mana, 0)

    def test_equipment_and_reload(self):
        w = self.world()
        w.player.mana = 12
        for slot in SLOTS:
            item = w.player.inventory.create(slot, 5, 'shop')
            w.player.inventory.add(item)
            w.player.inventory.equip(item.uid)
        self.assertEqual(w.player.max_mana, 100)
        self.assertEqual(w.player.mana, 12)
        self.assertAlmostEqual(w.player.cooldown_for('w'), 5.6)
        w.player.inventory.unequip('gloves')
        self.assertEqual(w.player.mana, 12)
        with tempfile.TemporaryDirectory() as d:
            store = ProfileStore(Path(d) / 'profile.json')
            self.assertTrue(store.save(w.player))
            player = store.load()
            self.assertEqual(player.mana, 100)  # Existing fresh-room resume contract.
            fresh = World(7, player=player, mana_regen=6)
            fresh.player.mana = 0
            fresh.update(1 / 30)
            self.assertAlmostEqual(fresh.player.mana, .2)

    def test_configuration(self):
        for rate in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                World(mana_regen=rate)
        w = self.world(8)
        w.player.mana = 0
        w.update(1 / 30)
        self.assertAlmostEqual(w.player.mana, 8 / 30)

    def test_recovery_thresholds(self):
        for rate in (8, 6):
            for rank in (0, 5):
                w = self.world(rate)
                if rank:
                    item = w.player.inventory.create('gloves', rank, 'shop')
                    w.player.inventory.add(item)
                w.player.mana = 0
                for frame in range(1, 2401):
                    w.update(1 / 120)
                    self.assertAlmostEqual(w.player.mana, min(100, frame * rate / 120), places=7)
                self.assertEqual(w.player.mana, 100)

    def test_floor_transition_retains_rate(self):
        w = self.world(5.5)
        w.state = 'cleared'
        w.player.mana = 0
        self.assertTrue(w.next_level())
        self.assertEqual(w.mana_regen, 5.5)
        self.assertEqual(w.player.mana, 100)
