"""Rolled item identity, actual combat effects, progression gates and persistence."""
from dataclasses import replace
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from dungeon.items import DEFINITIONS, Inventory, Item, roll_value
from dungeon.world import World, Enemy, IcePatch, RimeTrail
from dungeon.geometry import Vec
from dungeon.profile import ProfileStore
from dungeon.codex import Codex, item_templates, item_values


class RolledItemTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.world.enemies.clear()
        self.world.spawners.clear()
        self.world.level_completed = False
        self.inv = self.world.player.inventory

    def wear(self, key, rank=1, quality=10000):
        definition = DEFINITIONS[key]
        item = Item(self.inv.next_uid, definition.slot, rank, 'drop', definition.set_id, key, None if definition.set_id else quality)
        self.inv.add(item, auto_equip=False)
        self.inv.equip(item.uid)
        return item

    def test_25_templates_all_ordinary_items_have_one_rolled_slot_and_three_ranks(self):
        self.assertEqual(len(DEFINITIONS), 25)
        self.assertEqual(len(item_templates()), 25)
        for key, definition in DEFINITIONS.items():
            for rank in range(1, 6):
                with self.subTest(key=key, rank=rank):
                    valid = 3 <= rank <= 5 if definition.set_id else rank <= 3
                    if not valid:
                        with self.assertRaises(ValueError):
                            self.inv.create_template(key, rank, Random(1))
                        self.assertIn('Unavailable', item_values(key, rank)['availability'])
                    else:
                        item = self.inv.create_template(key, rank, Random(1))
                        self.assertEqual(item.enchantment_slots, 0 if definition.set_id else 1)
                        self.assertEqual(item.name, definition.name)
                        if not definition.set_id:
                            lo, hi = definition.ranges[rank - 1]
                            self.assertGreaterEqual(item.enchantment_value, lo / 1000)
                            self.assertLessEqual(item.enchantment_value, hi / 1000)

    def test_roll_endpoints_variation_and_monotonic_upgrade_quality(self):
        values = set()
        rng = Random(20)
        for _ in range(50):
            values.add(self.inv.create_template('snowstep_boots', 1, rng).quality)
        self.assertGreater(len(values), 40)
        for definition in DEFINITIONS.values():
            if definition.set_id:
                continue
            for rank, (lo, hi) in enumerate(definition.ranges, 1):
                self.assertEqual(roll_value(definition, rank, 0), lo / 1000)
                self.assertEqual(roll_value(definition, rank, 10000), hi / 1000)
            item = self.wear(definition.id, quality=4273)
            previous = item.enchantment_value
            for rank in (2, 3):
                self.assertTrue(self.inv.upgrade(item.uid))
                updated = self.inv.get(item.uid)
                self.assertEqual(updated.quality, 4273)
                self.assertGreater(updated.enchantment_value, previous)
                previous = updated.enchantment_value
            snapshot = self.inv.to_dict()
            self.assertFalse(self.inv.upgrade(item.uid))
            self.assertEqual(snapshot, self.inv.to_dict())

    def test_new_items_do_not_inherit_legacy_fixed_bonuses_and_sidegrades_arent_upgrades(self):
        first = self.wear('snowstep_boots')
        self.assertAlmostEqual(self.inv.stats.speed, .059)
        self.assertEqual(self.inv.stats.crit_chance, 0)
        other = self.inv.create_template('shardhunter_boots', 3, Random(1))
        self.inv.add(other, auto_equip=False)
        self.assertFalse(self.inv.is_upgrade(other))
        self.inv.equip(other.uid)
        self.assertEqual(self.inv.stats.speed, 0)
        self.assertGreater(self.inv.stats.crit_chance, 0)
        self.assertIn(first, self.inv.backpack)
        legacy = self.inv.create('boots', 3)
        self.inv.add(legacy, auto_equip=False)
        self.inv.equip(legacy.uid)
        new_standard = self.inv.create_template('standard:boots', 3, Random(1))
        self.inv.add(new_standard, auto_equip=False)
        self.assertFalse(self.inv.is_upgrade(new_standard))

    def test_real_spell_damage_health_mana_crit_speed_and_cooldown(self):
        self.wear('apprentice_rimeband')
        target = self.world.make_enemy(Vec(6.5, 13.5), 'husk')
        with patch.object(self.world.combat_rng, 'random', return_value=1):
            self.world._hit(target, 100)
        # Use a larger fresh target to inspect non-overkill rounding.
        target = self.world.make_enemy(Vec(6.5, 13.5), 'armor', boss_role='support')
        target.hp = 1000
        with patch.object(self.world.combat_rng, 'random', return_value=1):
            self.world._hit(target, 100)
        self.assertEqual(target.hp, 894)
        self.wear('deepwell_circlet')
        self.assertEqual(self.world.player.max_mana, 105.9)
        self.wear('snowbound_robe')
        self.assertEqual(self.world.player.max_hp, 105.9)
        self.wear('shardhunter_boots')
        self.assertAlmostEqual(self.world.player.crit_chance, .059)
        self.wear('snowstep_boots')
        self.assertAlmostEqual(self.world.player.move_speed, 3.1 * 1.059)
        self.wear('quickrime_gloves')
        self.assertAlmostEqual(self.world.player.cooldown_for('w'), 8 * .981)
        self.world.cast('w')
        self.assertAlmostEqual(self.world.player.cooldowns['w'], 8 * .981)

    def test_mana_cost_regeneration_stationarity_and_area_reach_gameplay(self):
        self.wear('frugalweave_wraps')
        self.world.player.mana = 25 * .971
        self.assertTrue(self.world.cast('w'))
        self.assertAlmostEqual(self.world.player.mana, 0)
        self.wear('stillwater_vestment')
        self.world.player.cast_time = 0
        self.world.update(.02)
        self.assertAlmostEqual(self.world.player.mana, 6 * 1.059 * .02)
        previous = self.world.player.mana
        self.world.request_move(self.world.player.pos + Vec(1, 0))
        self.world.update(.02)
        self.assertAlmostEqual(self.world.player.mana - previous, 6 * .02)
        self.wear('snowseer_hood')
        self.world.stop()
        self.world.player.mana = 100
        self.world.player.cast_time = 0
        self.world.player.cooldowns['w'] = 0
        target = self.world.make_enemy(self.world.player.pos + Vec(2.85, 0), 'husk')
        target.hp = 100
        self.world.cast('w')
        self.assertLess(target.hp, 100)
        self.world.player.cast_time = 0
        self.world.cast('e', self.world.player.pos)
        self.assertAlmostEqual(self.world.ice_patches[-1].radius, 2.4 * 1.029)

    def test_food_potion_and_percentage_damage_reduction(self):
        self.wear('runestitched_leggings')
        player = self.world.player
        player.hp = 10
        self.world.use_potion()
        self.assertAlmostEqual(player.hp, 52.36)
        from dungeon.world import Pickup
        self.world.pickups = [Pickup(player.pos, 'food', 25)]
        self.world.update(.02)
        self.assertAlmostEqual(player.hp, 52.36 + 26.475)
        self.wear('stonefrost_leggings')
        player.hp, player.invincible = 100, 0
        self.world._hurt_player(10)
        self.assertAlmostEqual(player.hp, 90.19)

    def test_winterthorn_tracks_exact_attacker_respects_cooldown_and_no_freeze(self):
        self.wear('winterthorn_coat')
        first = self.world.make_enemy(self.world.player.pos, 'husk')
        second = self.world.make_enemy(self.world.player.pos, 'husk')
        self.assertTrue(self.world._hurt_player(10, attacker=first))
        self.assertAlmostEqual(first.gear_slow, .059)
        self.assertEqual(second.gear_slow, 0)
        self.assertEqual(first.frozen, 0)
        self.assertEqual(self.world.player.thorn_cooldown, 3)
        self.world.player.invincible = 0
        self.world._hurt_player(10, attacker=second)
        self.assertEqual(second.gear_slow, 0)
        self.world.player.thorn_cooldown = 0
        self.world.player.invincible = 1
        self.world._hurt_player(10, attacker=second)
        self.assertEqual(second.gear_slow, 0)
        self.assertEqual(self.world.player.thorn_cooldown, 0)

    def test_projectile_retaliation_targets_shooter_not_nearby_species(self):
        from dungeon.world import Projectile
        self.wear('winterthorn_coat')
        shooter = self.world.make_enemy(Vec(8, 8), 'archer')
        self.world.projectiles = [Projectile(self.world.player.pos - Vec(.1, 0), Vec(1, 0), damage=10, hostile=True, attacker=shooter)]
        self.world._projectiles(.02)
        self.assertAlmostEqual(shooter.gear_slow, .059)

    def test_trail_only_while_moving_expires_no_spell_bonus_or_attack_slow(self):
        self.wear('rimetrail_boots')
        self.world.update(.02)
        self.assertEqual(self.world.rime_trails, [])
        self.world.request_move(self.world.player.pos + Vec(2, 0))
        for _ in range(20):
            self.world.update(.02)
        self.assertGreater(len(self.world.rime_trails), 0)
        self.world.stop()
        trail = self.world.rime_trails[-1]
        enemy = self.world.make_enemy(trail.pos, 'husk')
        self.world.player.pos = trail.pos
        self.world.update(.02)
        self.assertAlmostEqual(enemy.gear_slow, .059)
        self.assertEqual(self.world.frost_multiplier, 1)
        self.assertEqual(enemy.patch_time, 0)
        self.assertEqual(enemy.attack_rate, 1)
        self.assertEqual(self.world.ice_patches, [])
        for _ in range(60):
            self.world.update(.02)
        self.assertEqual(self.world.rime_trails, [])
        self.assertEqual(enemy.gear_slow, 0)

    def test_strongest_slow_has_its_own_lifetime_and_lingering_excludes_freeze(self):
        self.wear('lingering_frost_grips')
        target = self.world.make_enemy(self.world.player.pos + Vec(.2, 0), 'armor')
        self.world.apply_gear_slow(target, .4, .02)
        self.world.apply_gear_slow(target, .059, 1)
        self.world.update(.03)
        self.assertAlmostEqual(target.gear_slow, .059)
        from dungeon.world import Projectile
        self.world.projectiles = [Projectile(target.pos - Vec(.1, 0), Vec(10, 0), damage=1)]
        self.world._projectiles(.02)
        self.assertAlmostEqual(target.chilled, 2.118)
        self.world._freeze(target, 2)
        self.assertEqual(target.frozen, 2)
        target.chilled = 0
        target.pos = Vec(8, 8)
        self.world._enemy_direction = lambda e: Vec(1, 0)
        before = target.pos
        self.world._move_enemy(target, .02)
        self.assertAlmostEqual((target.pos - before).length(), .9 * .941 * .02)

    def test_driftwalker_reduces_actual_slow_duration(self):
        self.wear('driftwalker_trousers', 3)
        self.world.player.apply_slow(.55, 2)
        self.assertAlmostEqual(self.world.player.slow_time, 1.702)
        self.world.player.slow_pulse = 0
        before = self.world.player.pos
        self.world.request_move(before + Vec(1, 0))
        self.world.update(.02)
        self.assertAlmostEqual((self.world.player.pos - before).length(), 3.1 * .55 * .02)

    def test_floor_progression_gates_enchanting_and_drop_ranks(self):
        item = self.wear('snowstep_boots')
        self.world.player.gold = 10000
        before = self.inv.to_dict()
        self.assertFalse(self.world.enchant_item(item.uid))
        self.assertEqual(before, self.inv.to_dict())
        self.assertEqual(self.world.player.gold, 10000)
        self.world.player.unlocked_level = 3
        self.assertTrue(self.world.enchant_item(item.uid))
        self.assertFalse(self.world.enchant_item(item.uid))
        self.world.player.unlocked_level = 5
        self.assertTrue(self.world.enchant_item(item.uid))
        self.assertFalse(self.world.enchant_item(item.uid))
        for floor, expected in ((1, {1}), (2, {1}), (3, {1, 2}), (4, {1, 2}), (5, {1, 2, 3})):
            world = World(7, level=floor)
            for _ in range(1000):
                world._drop_equipment(Vec(8, 8), guaranteed=True)
            drops = [p.item for p in world.pickups if p.kind == 'item']
            self.assertEqual({item.rank for item in drops}, expected)
            self.assertFalse(any(item.set_id for item in drops))
            self.assertEqual({item.template_id for item in drops}, {d.id for d in DEFINITIONS.values() if not d.set_id})

    def test_first_keeper_unlock_reward_repeat_protection_and_post_unlock_drops(self):
        world = World(7, level=5)
        world.player.gold = 10000
        self.assertIsNone(world.buy_item('helm').set_id)
        world.keeper.defeated()
        self.assertTrue(world.player.frostweave_unlocked)
        reward = [item for item in world.player.inventory.items if item.source == 'reward']
        self.assertEqual([(item.template_id, item.rank) for item in reward], [('frostweave:helm', 3)])
        self.assertEqual(world.buy_item('boots').rank, 3)
        self.assertEqual(world.player.inventory.items[-1].set_id, 'frostweave')
        world.keeper.defeated()
        self.assertEqual(len([i for i in world.player.inventory.items if i.source == 'reward']), 1)
        world.player.cleared_floor = 0
        retry = World(7, player=world.player, level=5)
        retry.keeper.defeated()
        self.assertEqual(len([i for i in world.player.inventory.items if i.source == 'reward']), 1)
        for _ in range(300):
            retry._drop_equipment(Vec(8, 8), guaranteed=True)
        frost = [p.item for p in retry.pickups if p.kind == 'item' and p.item.set_id]
        self.assertGreater(len(frost), 0)
        self.assertEqual({i.rank for i in frost}, {3})

    def test_roundtrip_identity_quality_discovery_unlock_and_legacy_stats(self):
        item = self.wear('rimetrail_boots', 2, 7317)
        self.world.player.frostweave_unlocked = True
        legacy = Item(self.inv.next_uid, 'helm', 5)
        self.inv.add(legacy)
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder) / 'profile.json')
            self.assertTrue(store.save(self.world.player))
            loaded = ProfileStore(store.path).load()
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.inventory.to_dict(), self.inv.to_dict())
            self.assertEqual(loaded.inventory.get(item.uid).quality, 7317)
            self.assertIn('rimetrail_boots', loaded.item_discoveries)
            self.assertTrue(loaded.frostweave_unlocked)
            self.assertEqual(loaded.inventory.stats.damage, .65)
        for quality in (-1, 10001, True, .5, '1'):
            with self.assertRaises(ValueError):
                replace(item, quality=quality)

    def test_developer_catalog_ranges_rank_limits_and_no_randomness_or_progress(self):
        from copy import deepcopy
        codex = Codex(True)
        codex.show_undiscovered, codex.tab = True, 'Item Catalog'
        before = deepcopy(self.world.player)
        rng = self.world.loot_rng.getstate()
        self.assertEqual(len(codex.rows(self.world.player)), 25)
        codex.selected, codex.rank = 'rimetrail_boots', 3
        text = codex.copy_details(self.world.player)
        self.assertIn('rank=3', text)
        self.assertIn('2.0–9.9%', text)
        self.assertIn('One enchantment slot', text)
        codex.rank_filter = 5
        self.assertEqual(len(codex.rows(self.world.player)), 5)
        self.assertEqual(self.world.loot_rng.getstate(), rng)
        self.assertEqual(self.world.player.inventory.to_dict(), before.inventory.to_dict())
        self.assertEqual(self.world.player.item_discoveries, before.item_discoveries)
