import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from dungeon.geometry import Vec
from dungeon.items import ENCHANT_COST, Inventory, Item, SLOTS, VALUES
from dungeon.profile import ProfileStore
from dungeon.world import Enemy, Player, Spawner, World


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.world.enemies.clear()
        for rift in self.world.spawners:
            rift.timer = 999

    def wear(self, slot, rank):
        item = self.world.player.inventory.create(slot, rank)
        self.world.player.inventory.add(item)
        self.world.equip_item(item.uid)
        return item

    def advance(self, seconds):
        for _ in range(round(seconds * 60)):
            self.world.update(1 / 60)

    def finish_floor(self):
        for phase in range(1, 4):
            for spawner in self.world.spawners[:]:
                self.world._hit(spawner, 10000)
            if phase < 3:
                self.advance(3.05)

    def test_each_slot_has_three_helpful_dropped_ranks_and_two_higher_enchantments(self):
        for slot, stat in (("helm", "damage"), ("chest", "health"), ("legs", "armor"),
                           ("gloves", "cooldown"), ("boots", "speed")):
            for rank in range(1, 6):
                inv = Inventory()
                inv.add(inv.create(slot, rank))
                self.assertGreater(getattr(inv.stats, stat), VALUES[stat][rank - 1])
        self.assertGreater(ENCHANT_COST[5], ENCHANT_COST[4] * 5)

    def test_swapping_replaces_bonus_and_preserves_previous_item(self):
        first = self.wear("helm", 1)
        second = self.wear("helm", 3)
        inv = self.world.player.inventory
        self.assertEqual(inv.stats.damage, .3)
        self.assertEqual(inv.worn("helm").uid, second.uid)
        self.assertIn(first, inv.backpack)
        self.world.unequip_item("helm")
        self.assertEqual(inv.stats.damage, 0)
        self.assertEqual(len(inv.backpack), 2)
        self.world.equip_item(first.uid)
        self.assertEqual(inv.stats.damage, .1)

    def test_chest_increases_maximum_health_without_swap_healing(self):
        chest = self.wear("chest", 3)
        player = self.world.player
        self.assertEqual((player.hp, player.max_hp), (100, 160))
        self.world.use_potion()
        self.assertEqual(player.hp, 140)
        self.world.unequip_item("chest")
        self.assertEqual((player.hp, player.max_hp), (100, 100))
        self.world.equip_item(chest.uid)
        self.assertEqual((player.hp, player.max_hp), (100, 160))
        self.world.use_potion()
        self.world.use_potion()
        self.assertEqual(player.hp, 160)

    def test_helm_modifies_bolt_nova_and_ultimate_damage(self):
        self.wear("helm", 3)
        target = Spawner(Vec(5.5, 13.5), timer=999)
        self.world.spawners = [target]
        with patch.object(self.world.combat_rng, "random", return_value=.99):
            self.world.cast("q", target.pos)
            self.advance(.25)
            self.assertEqual(target.hp, 145)
            self.world.cast("w")
            self.assertEqual(target.hp, 127)
            self.advance(.25)
            self.world.cast("r")
            self.advance(2.6)
            self.assertEqual(target.hp, 10)

    def test_leg_armor_reduces_incoming_hits_with_a_one_damage_floor(self):
        self.wear("legs", 3)
        self.world.enemies = [Enemy(self.world.player.pos)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 93)
        self.wear("legs", 5)
        self.world.player.invincible = 0
        self.world.enemies = [Enemy(self.world.player.pos, "skitter", 26)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 92)

    def test_gloves_reduce_new_cast_cooldowns_without_reducing_an_existing_timer(self):
        self.world.player.cooldowns["w"] = 8
        self.wear("gloves", 3)
        self.assertEqual(self.world.player.cooldowns["w"], 8)
        self.world.cast("r")
        self.assertAlmostEqual(self.world.player.cooldowns["r"], 38.25)

    def test_boots_affect_real_movement_and_critical_hit_damage(self):
        self.wear("boots", 3)
        player = self.world.player
        self.assertAlmostEqual(player.crit_chance, .11)
        self.assertAlmostEqual(player.crit_multiplier, 2.35)
        player.pos = Vec(2.5, 14.5)
        self.world.request_move(Vec(10.5, 14.5))
        self.advance(1)
        self.assertAlmostEqual(player.pos.x, 6.065)
        target = Spawner(Vec(12.5, 14.5), timer=999)
        self.world.spawners = [target]
        with patch.object(self.world.combat_rng, "random", return_value=.10):
            self.world._hit(target, 24)
        self.assertEqual(target.hp, 120)
        self.assertTrue(any(effect.kind == "critical" for effect in self.world.effects))

    def test_purchase_and_insufficient_funds_are_atomic(self):
        self.world.player.gold = 50
        item = self.world.buy_item("helm")
        self.assertEqual(self.world.player.gold, 10)
        self.assertEqual(item.rank, 0)
        self.assertEqual(self.world.player.inventory.stats.damage, 0)
        self.assertFalse(self.world.enchant_item(item.uid))
        self.assertEqual(self.world.player.gold, 10)
        self.assertEqual(self.world.player.inventory.get(item.uid).rank, 0)
        self.assertFalse(self.world.buy_item("boots"))
        self.assertEqual(len(self.world.player.inventory.items), 1)
        self.world.player.gold = 50
        self.assertTrue(self.world.enchant_item(item.uid))
        self.assertEqual(self.world.player.gold, 0)
        self.assertEqual(self.world.player.inventory.stats.damage, .1)

    def test_all_enchantments_charge_each_rank_and_stop_at_five(self):
        self.world.player.gold = sum(ENCHANT_COST.values()) + 40
        item = self.world.buy_item("helm")
        for rank in range(1, 6):
            self.assertTrue(self.world.enchant_item(item.uid))
            self.assertEqual(self.world.player.inventory.get(item.uid).rank, rank)
        self.assertEqual(self.world.player.gold, 0)
        self.assertFalse(self.world.enchant_item(item.uid))
        self.assertEqual(self.world.player.inventory.get(item.uid).rank, 5)
        self.assertFalse(self.world.enchant_item(999))
        self.assertFalse(self.world.equip_item(999))

    def test_stasis_prevents_gear_and_shop_exploits(self):
        item = self.wear("helm", 1)
        self.world.player.gold = 10000
        self.world.cast("r")
        self.assertFalse(self.world.unequip_item("helm"))
        self.assertFalse(self.world.enchant_item(item.uid))
        self.assertFalse(self.world.buy_item("chest"))
        self.assertEqual(self.world.player.gold, 10000)

    def test_drop_table_never_rolls_rank_four_or_five_and_boots_are_rarest(self):
        for _ in range(1000):
            self.world._drop_equipment(Vec(5.5, 5.5), guaranteed=True)
        items = [p.item for p in self.world.pickups if p.kind == "item"]
        self.assertEqual(len(items), 1000)
        self.assertEqual({item.rank for item in items}, {1, 2, 3})
        counts = {slot: sum(i.slot == slot for i in items) for slot in SLOTS}
        self.assertGreater(counts["boots"], 0)
        self.assertLess(counts["boots"], min(counts[slot] for slot in SLOTS[:-1]))

    def test_first_clear_opens_gate_with_survivors_and_awards_boots_once(self):
        self.world.enemies = [Enemy(Vec(14.5, 14.5))]
        self.finish_floor()
        self.assertTrue(self.world.exit_open)
        self.assertEqual(len(self.world.enemies), 1)
        reward = [i for i in self.world.player.inventory.items if i.source == "reward"]
        self.assertEqual([(i.slot, i.rank) for i in reward], [("boots", 1)])
        for _ in range(20):
            self.world.update(1 / 60)
        self.assertEqual(len([i for i in self.world.player.inventory.items if i.source == "reward"]), 1)
        self.assertTrue(self.world.player.first_clear_rewarded)
        self.assertEqual(self.world.player.unlocked_level, 1)
        self.assertFalse(any(p.kind in ("item", "gold") for p in self.world.pickups))

    def test_next_level_carries_gear_gold_and_scales_enemies(self):
        self.wear("helm", 3)
        self.world.player.gold = 777
        self.finish_floor()
        self.world.player.pos = self.world.exit
        self.world.update(1 / 60)
        self.assertEqual(self.world.state, "cleared")
        inv = self.world.player.inventory.to_dict()
        gold = self.world.player.gold
        player = self.world.player
        player.hp = 20
        self.assertTrue(self.world.next_level())
        self.assertIs(self.world.player, player)
        self.assertEqual(self.world.level, 2)
        self.assertEqual(self.world.player.inventory.to_dict(), inv)
        self.assertEqual(self.world.player.gold, gold)
        self.assertEqual(self.world.player.hp, self.world.player.max_hp)
        self.assertGreater(self.world.enemies[0].max_hp, 44)
        self.assertGreater(self.world.gold_value(75), 75)
        self.assertFalse(self.world.next_level())

    def test_replaying_first_level_does_not_duplicate_clear_reward(self):
        self.world.player.first_clear_rewarded = True
        self.finish_floor()
        self.assertFalse(any(item.source == "reward" for item in self.world.player.inventory.items))


    def test_selling_spare_gear_credits_quoted_value_only_once(self):
        worn = self.wear("helm", 3)
        inv = self.world.player.inventory
        spare = inv.create("helm", 2)
        inv.add(spare, auto_equip=False)
        self.world.player.gold = 100
        quoted = spare.sell_value
        self.assertTrue(self.world.sell_item(spare.uid))
        self.assertEqual(self.world.player.gold, 100 + quoted)
        self.assertIsNone(inv.get(spare.uid))
        self.assertIs(inv.worn("helm"), worn)
        self.assertEqual(inv.stats.damage, .3)
        self.assertFalse(self.world.sell_item(spare.uid))
        self.assertEqual(self.world.player.gold, 100 + quoted)

    def test_equipped_gear_must_be_unequipped_before_disposal(self):
        item = self.wear("chest", 3)
        player = self.world.player
        self.assertFalse(self.world.sell_item(item.uid))
        self.assertFalse(self.world.destroy_item(item.uid))
        self.assertIsNotNone(player.inventory.get(item.uid))
        self.assertEqual(player.max_hp, 160)
        self.assertEqual(player.gold, 0)
        self.world.unequip_item("chest")
        self.assertTrue(self.world.destroy_item(item.uid))
        self.assertEqual(player.max_hp, 100)

    def test_destroying_removes_only_selected_spare_and_grants_no_gold(self):
        inv = self.world.player.inventory
        first = inv.create("boots", 3)
        second = inv.create("boots", 1)
        inv.add(first, auto_equip=False)
        inv.add(second, auto_equip=False)
        self.world.player.gold = 300
        self.world.player.first_clear_rewarded = True
        self.assertTrue(self.world.destroy_item(first.uid))
        self.assertIsNone(inv.get(first.uid))
        self.assertIs(inv.get(second.uid), second)
        self.assertEqual(self.world.player.gold, 300)
        self.assertTrue(self.world.player.first_clear_rewarded)
        self.assertFalse(self.world.destroy_item(first.uid))
        self.assertGreater(inv.create("helm", 0).uid, second.uid)

    def test_sale_values_scale_with_rank_without_buy_or_enchant_arbitrage(self):
        from dungeon.items import BLANK_COST
        for slot in SLOTS:
            previous = 0
            for rank in range(6):
                item = Item(1, slot, rank)
                self.assertGreater(item.sell_value, previous)
                self.assertLess(item.sell_value, BLANK_COST[slot] + sum(ENCHANT_COST[r] for r in range(1, rank + 1)))
                if rank:
                    self.assertLess(item.sell_value - previous, ENCHANT_COST[rank])
                previous = item.sell_value

    def test_stasis_and_death_block_selling_and_destruction(self):
        inv = self.world.player.inventory
        item = inv.create("gloves", 2)
        inv.add(item, auto_equip=False)
        self.world.cast("r")
        self.assertFalse(self.world.sell_item(item.uid))
        self.assertFalse(self.world.destroy_item(item.uid))
        self.world.player.stasis = 0
        self.world.state = "dead"
        self.assertFalse(self.world.sell_item(item.uid))
        self.assertFalse(self.world.destroy_item(item.uid))
        self.assertIs(inv.get(item.uid), item)
        self.assertEqual(self.world.player.gold, 0)


class ProfileTests(unittest.TestCase):
    def test_legacy_save_retains_unlocks_and_uses_last_known_depth(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            store = ProfileStore(path)
            store.save(Player(unlocked_level=2, gold=77))
            data = json.loads(path.read_text())
            del data["current_level"]
            path.write_text(json.dumps(data))
            loaded = ProfileStore(path).load()
            self.assertEqual((loaded.current_level, loaded.unlocked_level, loaded.gold), (2, 2, 77))

    def test_invalid_current_level_preserves_save(self):
        for invalid in (0, 3, True, "2"):
            with self.subTest(value=invalid), TemporaryDirectory() as folder:
                path = Path(folder) / "profile.json"
                ProfileStore(path).save(Player(unlocked_level=2))
                data = json.loads(path.read_text())
                data["current_level"] = invalid
                contents = json.dumps(data)
                path.write_text(contents)
                store = ProfileStore(path)
                self.assertIsNone(store.load())
                self.assertFalse(store.save(Player()))
                self.assertEqual(path.read_text(), contents)

    def test_profile_round_trip_preserves_ownership_enchants_gold_and_depth(self):
        player = Player(gold=12345, unlocked_level=3, first_clear_rewarded=True)
        for rank, slot in enumerate(SLOTS, 1):
            player.inventory.add(player.inventory.create(slot, rank, "enchanted"))
        player.inventory.add(player.inventory.create("helm", 2), auto_equip=False)
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder) / "profile.json")
            self.assertIsNone(store.load())
            self.assertTrue(store.save(player))
            loaded = ProfileStore(store.path).load()
            self.assertEqual(loaded.inventory.to_dict(), player.inventory.to_dict())
            self.assertEqual(loaded.gold, 12345)
            self.assertEqual(loaded.unlocked_level, 3)
            self.assertEqual(loaded.current_level, 1)
            self.assertTrue(loaded.first_clear_rewarded)
            self.assertEqual(loaded.hp, loaded.max_hp)

    def test_sold_and_destroyed_items_stay_removed_after_reload(self):
        world = World(7)
        inv = world.player.inventory
        sold = inv.create("helm", 2)
        destroyed = inv.create("gloves", 3)
        kept = inv.create("boots", 1)
        for item in (sold, destroyed, kept):
            inv.add(item, auto_equip=False)
        world.player.first_clear_rewarded = True
        self.assertTrue(world.sell_item(sold.uid))
        self.assertTrue(world.destroy_item(destroyed.uid))
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder) / "profile.json")
            self.assertTrue(store.save(world.player))
            player = ProfileStore(store.path).load()
            self.assertEqual(player.gold, sold.sell_value)
            self.assertEqual([item.uid for item in player.inventory.items], [kept.uid])
            self.assertTrue(player.first_clear_rewarded)
            self.assertGreater(player.inventory.create("helm", 0).uid, kept.uid)

    def test_corrupt_or_future_profile_is_preserved_and_not_overwritten(self):
        for contents in ("broken json", '{"version": 99}'):
            with TemporaryDirectory() as folder:
                path = Path(folder) / "profile.json"
                path.write_text(contents)
                store = ProfileStore(path)
                self.assertIsNone(store.load())
                self.assertFalse(store.save(Player()))
                self.assertEqual(path.read_text(), contents)
                self.assertTrue(store.error)

    def test_failed_atomic_replace_preserves_previous_save(self):
        with TemporaryDirectory() as folder:
            store = ProfileStore(Path(folder) / "profile.json")
            player = Player(gold=50)
            self.assertTrue(store.save(player))
            player.gold = 100
            with patch.object(Path, "replace", side_effect=OSError("Disk unavailable")):
                self.assertFalse(store.save(player))
            self.assertEqual(json.loads(store.path.read_text())["gold"], 50)
            self.assertTrue(store.error)

    def test_inventory_rejects_duplicate_items_invalid_rank_and_wrong_equipment_slot(self):
        inv = Inventory()
        item = inv.create("helm", 1)
        inv.add(item)
        with self.assertRaises(ValueError):
            inv.add(item)
        for slot, rank in (("weapon", 1), ("helm", 6), ("helm", -1)):
            with self.assertRaises(ValueError):
                Item(1, slot, rank)
        data = inv.to_dict()
        data["equipped"]["boots"] = item.uid
        with self.assertRaises(ValueError):
            Inventory.from_dict(data)


if __name__ == "__main__":
    unittest.main()
