"""Rank-five Prison qualification and damage regression tests."""
import unittest
from unittest.mock import Mock
from tempfile import TemporaryDirectory
from pathlib import Path
from dungeon.world import World, Enemy, IcePatch
from dungeon.geometry import Vec
from dungeon.items import SLOTS
from dungeon.profile import ProfileStore


class CapstoneTests(unittest.TestCase):
    def setup_world(self, rank=5):
        w = World(7)
        w.enemies.clear()
        w.spawners.clear()
        w.walls.clear()
        w.player.pos = Vec(8, 8)
        for slot in SLOTS:
            item = w.player.inventory.create(slot, rank, "shop")
            w.player.inventory.add(item)
            w.player.inventory.equip(item.uid)
        w.combat_rng = Mock()
        w.combat_rng.random.return_value = .99
        return w

    def arm(self, w, life=6):
        patch = IcePatch(w.player.pos, life=life)
        w.ice_patches.append(patch)
        self.assertTrue(w.cast("r"))
        return patch

    def blast(self, w):
        # Advance actual simulation without enemy movement or phase progression.
        w._spawn = lambda dt: None
        for _ in range(76):
            w._update_simulation(1/30)
        return "frostweave_shatter" in w.events

    def test_setup_duration_and_guaranteed_damage_without_crit_roll(self):
        w = self.setup_world()
        self.arm(w)
        target = Enemy(Vec(9, 8), hp=5000)
        w.enemies = [target]
        target.frozen = 100
        self.assertTrue(self.blast(w))
        self.assertEqual(target.hp, 5000 - round(90 * 1.65 * 1.3 * 2.75 * 3))
        w.combat_rng.random.assert_not_called()

    def test_missing_lower_rank_and_equipment_changes(self):
        for mode in ("rank4", "missing", "swap", "late"):
            with self.subTest(mode=mode):
                w = self.setup_world(4 if mode == "rank4" else 5)
                inv = w.player.inventory
                uid = inv.worn("boots").uid
                if mode in ("missing", "late"):
                    inv.unequip("boots")
                self.arm(w)
                if mode == "swap":
                    inv.unequip("boots")
                if mode == "late":
                    inv.equip(uid)
                self.assertFalse(self.blast(w))
                self.assertIn("shatter", w.events)

    def test_same_patch_identity_expiry_owner_and_displacement(self):
        for mode in ("removed", "replaced", "expired", "exact", "outside", "foreign"):
            with self.subTest(mode=mode):
                w = self.setup_world()
                p = self.arm(w, 2.5 if mode == "exact" else 2 if mode == "expired" else 6)
                if mode in ("removed", "replaced"):
                    w.ice_patches.remove(p)
                if mode == "replaced":
                    w.ice_patches.append(IcePatch(w.player.pos))
                if mode == "outside":
                    w.player.pos += Vec(2.40001, 0)
                if mode == "foreign":
                    p.owner = "enemy"
                self.assertFalse(self.blast(w))

    def test_overlap_longest_then_insertion_order_and_boundary(self):
        w = self.setup_world()
        w.ice_patches = [IcePatch(w.player.pos, life=1)]
        p = self.arm(w)
        w.ice_patches.append(IcePatch(w.player.pos))
        self.assertIs(w._prison_patch, p)
        w.player.pos += Vec(2.4, 0)
        self.assertTrue(self.blast(w))

    def test_range_los_defenses_and_duplicate_hits(self):
        for distance, blocked, expected in ((6.4, False, 1593), (6.40001, False, 0), (4, True, 0)):
            with self.subTest(distance=distance, blocked=blocked):
                w = self.setup_world()
                self.arm(w)
                target = Enemy(w.player.pos + Vec(distance, 0), hp=5000)
                w.enemies = [target, target]
                w._line_clear = lambda a, b: not blocked
                target.frozen = 100
                self.assertTrue(self.blast(w))
                self.assertEqual(5000-target.hp, expected)
        for recovery, support, factor in ((0, True, .65), (1, True, 1.35), (0, False, 1)):
            w = self.setup_world()
            target = Enemy(Vec(9, 8), hp=5000, boss_role="boss", recovery=recovery)
            w.enemies = [target]
            if support:
                w.enemies.append(Enemy(Vec(10, 8), boss_role="support"))
            w._hit(target, 90, 1.3, capstone=True)
            self.assertEqual(5000-target.hp, round(90*1.65*1.3*2.75*3*factor))

    def test_pause_and_profile_reload(self):
        w = self.setup_world()
        p = self.arm(w)
        w.state = "paused"
        w.update(10)
        self.assertEqual((p.life, w.player.stasis), (6, 2.5))
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder)/"profile.json")
            self.assertTrue(store.save(w.player))
            loaded = World(7, player=store.load())
        self.assertEqual(loaded.player.inventory.stats.frostweave_rank, 5)
        self.assertEqual(loaded.player.stasis, 0)
        self.assertIsNone(loaded._prison_patch)
        self.assertEqual(loaded.ice_patches, [])

    def test_ordinary_prison_damage_and_radius(self):
        w = self.setup_world(4)
        self.arm(w)
        target = Enemy(Vec(12, 8), hp=5000, frozen=100)
        w.enemies = [target]
        self.assertFalse(self.blast(w))
        self.assertEqual(target.hp, 5000)
        self.assertEqual(next(e.radius for e in w.effects if e.kind == "shatter"), 3.2)
