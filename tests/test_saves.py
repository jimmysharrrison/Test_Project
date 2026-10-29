"""Save checkpoints preserve live encounters and require explicit replacement."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from dungeon.geometry import Vec
from dungeon.profile import ProfileStore
from dungeon.saves import SaveSlots, encode_world, decode_world
from dungeon.world import World, Player, Projectile, IcePatch


class SaveSlotTests(unittest.TestCase):
    def test_four_independent_slots_survive_restart(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            slots = SaveSlots(path)
            for slot in range(1, 5):
                world = World(slot, level=slot)
                world.player.gold = slot * 100
                world.player.hp = 37
                world.player.mana = 24
                world.player.pos = Vec(4.5, 12.5)
                world.player.cooldowns['w'] = 3.25
                self.assertTrue(slots.save(slot, world))
            reopened = SaveSlots(path)
            self.assertEqual(len(list(Path(folder).glob('*.json'))), 4)
            self.assertEqual(len(reopened.summaries()), 4)
            for slot in range(1, 5):
                world = reopened.load(slot)
                self.assertEqual((world.level, world.player.gold, world.player.hp, world.player.mana), (slot, slot * 100, 37, 24))
                self.assertEqual(world.player.pos, Vec(4.5, 12.5))
                self.assertEqual(world.player.cooldowns['w'], 3.25)
            for invalid in (0, 5, -1, '1', True):
                with self.assertRaises(ValueError):
                    slots.store(invalid)

    def test_occupied_slot_requires_confirmation_and_other_slots_are_unchanged(self):
        with TemporaryDirectory() as folder:
            slots = SaveSlots(Path(folder) / 'profile.json')
            world = World(7)
            for slot in range(1, 5):
                self.assertTrue(slots.save(slot, world))
            before = [store.path.read_bytes() for store in slots.stores]
            world.player.gold = 987
            self.assertFalse(slots.save(2, world))
            self.assertEqual([s.path.read_bytes() for s in slots.stores], before)
            self.assertTrue(slots.save(2, world, overwrite=True))
            self.assertEqual(slots.load(2).player.gold, 987)
            for slot in (1, 3, 4):
                self.assertEqual(slots.store(slot).path.read_bytes(), before[slot - 1])

    def test_legacy_profile_is_slot_one_and_reading_never_rewrites_it(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            ProfileStore(path).save(Player(current_level=2, unlocked_level=3, gold=246))
            before = path.read_bytes()
            slots = SaveSlots(path)
            self.assertIn('Legacy', slots.summaries()[0]['detail'])
            world = slots.load(1, seed=7)
            self.assertEqual((world.level, world.player.gold), (2, 246))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(len(list(Path(folder).glob('*.json'))), 1)

    def test_corrupt_slot_is_preserved_and_can_only_be_explicitly_replaced(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'profile.json'
            path.write_text('broken save')
            slots = SaveSlots(path)
            before = path.read_bytes()
            rows = slots.summaries()
            self.assertTrue(rows[0]['occupied'])
            self.assertFalse(rows[0]['valid'])
            self.assertIsNone(slots.load(1))
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(slots.save(1, World(7)))
            self.assertTrue(slots.save(2, World(7)))
            self.assertEqual(path.read_bytes(), before)
            self.assertTrue(slots.save(1, World(7), overwrite=True))
            self.assertIsNotNone(slots.load(1))

    def test_atomic_write_failure_keeps_old_slot(self):
        with TemporaryDirectory() as folder:
            slots = SaveSlots(Path(folder) / 'profile.json')
            world = World(7)
            self.assertTrue(slots.save(1, world))
            before = slots.store(1).path.read_bytes()
            world.player.gold = 77
            with patch.object(Path, 'replace', side_effect=OSError('write failed')):
                self.assertFalse(slots.save(1, world, overwrite=True))
            self.assertEqual(slots.store(1).path.read_bytes(), before)

    def test_live_fight_roundtrip_keeps_random_state_and_shared_references(self):
        for floor in range(1, 6):
            with self.subTest(floor=floor):
                world = World(7, level=floor)
                for _ in range(40):
                    world.update(1 / 60)
                actor = world.enemies[0]
                actor.hp -= 7
                world.selected = actor
                world.projectiles.append(Projectile(actor.pos, Vec(1, 0), attacker=actor))
                patch = IcePatch(world.player.pos)
                world.ice_patches.append(patch)
                world._prison_patch = patch
                encoded = json.loads(json.dumps(encode_world(world)))
                loaded = decode_world(encoded)
                self.assertIs(loaded.selected, loaded.enemies[0])
                self.assertIs(loaded.projectiles[-1].attacker, loaded.enemies[0])
                self.assertIs(loaded._prison_patch, loaded.ice_patches[-1])
                self.assertEqual(loaded.enemies[0].hp, actor.hp)
                self.assertEqual(loaded.time, world.time)
                if loaded.keeper:
                    self.assertIs(loaded.keeper.world, loaded)
                    self.assertIs(loaded.keeper.boss, loaded.enemies[0])
                for name in ('rng', 'combat_rng', 'proc_rng', 'loot_rng'):
                    self.assertEqual(getattr(loaded, name).getstate(), getattr(world, name).getstate())
                # Continue both simulations from the same live checkpoint.
                world._prison_patch = loaded._prison_patch = None
                for _ in range(30):
                    world.update(1 / 60)
                    loaded.update(1 / 60)
                self.assertEqual(loaded.player.hp, world.player.hp)
                self.assertEqual([(e.kind, e.pos, e.hp) for e in loaded.enemies], [(e.kind, e.pos, e.hp) for e in world.enemies])

    def test_completed_floor_and_pending_presentation_restore(self):
        world = World(7)
        world._completion_remaining = .7
        world._completion_requested = True
        loaded = decode_world(encode_world(world))
        self.assertEqual(loaded._completion_remaining, .7)
        self.assertTrue(loaded._completion_requested)
        keeper = World(7, level=5)
        keeper.keeper.defeated()
        loaded = decode_world(encode_world(keeper))
        self.assertTrue(loaded.level_completed)
        self.assertTrue(loaded.keeper.finished)
        self.assertEqual(loaded.player.gold, keeper.player.gold)

    def test_malformed_snapshot_and_unknown_types_are_rejected(self):
        for data in ({}, {'version': 99}, {'version': 1, 'world': {'id': 0, 'type': 'Executable', 'data': {}}}):
            with self.subTest(data=data), self.assertRaises((ValueError, KeyError)):
                decode_world(data)
        with TemporaryDirectory() as folder:
            slots = SaveSlots(Path(folder) / 'profile.json')
            slots.save(1, World(7))
            data = json.loads(slots.store(1).path.read_text())
            data['game_state']['world']['data']['phase'] = 500
            slots.store(1).path.write_text(json.dumps(data))
            before = slots.store(1).path.read_bytes()
            self.assertIsNone(slots.load(1))
            self.assertFalse(slots.summaries()[0]['valid'])
            self.assertEqual(slots.store(1).path.read_bytes(), before)
