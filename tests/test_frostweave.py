"""Persistent set identity, equipped-set procs, and explicit enchanting targets."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from dungeon.armory import Armory
from dungeon.geometry import Vec
from dungeon.items import Inventory, Item, SLOTS
from dungeon.profile import ProfileStore
from dungeon.world import Enemy, Projectile, Spawner, World


class FrostweaveTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.inv = self.world.player.inventory
        self.world.enemies.clear()
        for spawner in self.world.spawners:
            spawner.timer = 999

    def give_set(self, rank=3):
        for slot in SLOTS:
            item = self.inv.create(slot, rank, "shop")
            self.inv.add(item)
            self.inv.equip(item.uid)

    def target(self, kind="husk"):
        enemy = Enemy(Vec(5.5, 13.5), kind, level=30)
        enemy.hp = enemy.max_hp
        self.world.enemies = [enemy]
        return enemy

    def bolt_hit(self, target, spell="q", damage=1):
        self.world.projectiles.append(Projectile(target.pos - Vec(.2, 0), Vec(10, 0), damage=damage, spell=spell))
        self.world._projectiles(.02)

    def test_unlocked_stock_starts_at_rank_three_and_keeps_set_identity(self):
        self.world.player.frostweave_unlocked = True
        self.world.player.gold = 100000
        for slot in SLOTS:
            item = self.world.buy_item(slot)
            self.assertEqual(item.rank, 3)
            self.assertEqual(item.set_id, "frostweave")
            self.assertTrue(item.name.startswith("Frostweave "))
            for rank in (4, 5):
                self.assertTrue(self.world.enchant_item(item.uid))
                updated = self.inv.get(item.uid)
                self.assertEqual((updated.rank, updated.set_id, updated.name), (rank, "frostweave", item.name))

    def test_enchanted_drops_and_rewards_do_not_become_set_pieces(self):
        for source in ("drop", "reward"):
            item = self.inv.create("boots", 1, source)
            self.inv.add(item, auto_equip=False)
            self.inv.upgrade(item.uid)
            updated = self.inv.get(item.uid)
            self.assertIsNone(updated.set_id)
            self.assertEqual(updated.name, "Everfrost Treads")

    def test_all_five_must_be_equipped_and_backpack_duplicates_cannot_complete_set(self):
        self.give_set()
        self.assertEqual(self.inv.stats.frostweave_freeze_chance, .15)
        self.inv.unequip("gloves")
        for _ in range(3):
            self.inv.add(self.inv.create("gloves", 5, "shop"), auto_equip=False)
        self.assertEqual(self.inv.stats.frostweave_pieces, 4)
        self.assertEqual(self.inv.stats.frostweave_freeze_chance, 0)
        ordinary = self.inv.create("gloves", 5)
        self.inv.add(ordinary)
        self.assertEqual(self.inv.stats.frostweave_freeze_chance, 0)

    def test_weakest_equipped_piece_controls_activation_and_rank_scaling(self):
        self.give_set(2)
        self.assertEqual(self.inv.stats.frostweave_freeze_chance, 0)
        for rank, chance in ((3, .15), (4, .25), (5, .40)):
            for index, slot in enumerate(SLOTS):
                self.inv.upgrade(self.inv.worn(slot).uid)
                expected = chance if index == len(SLOTS) - 1 else {3: 0, 4: .15, 5: .25}[rank]
                self.assertEqual(self.inv.stats.frostweave_freeze_chance, expected)
            self.assertEqual(self.inv.stats.frostweave_rank, rank)

    def test_set_identity_and_active_bonus_survive_profile_reload(self):
        self.give_set(3)
        self.inv.upgrade(self.inv.worn("helm").uid)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            self.assertTrue(ProfileStore(path).save(self.world.player))
            loaded = ProfileStore(path).load()
        self.assertEqual(loaded.inventory.to_dict(), self.inv.to_dict())
        self.assertEqual(loaded.inventory.stats.frostweave_freeze_chance, .15)
        self.assertTrue(all(item.name.startswith("Frostweave ") for item in loaded.inventory.items))

    def test_legacy_shop_blanks_migrate_but_unknown_enchanted_origins_are_preserved(self):
        inv = Inventory.from_dict({"items": [
            {"uid": 1, "slot": "helm", "rank": 0, "source": "shop"},
            {"uid": 2, "slot": "chest", "rank": 3, "source": "enchanted"}], "equipped": {}})
        self.assertEqual(inv.get(1).set_id, "frostweave")
        self.assertIsNone(inv.get(2).set_id)
        with self.assertRaises(ValueError):
            Item(3, "helm", 0, set_id="unknown")

    def test_real_frost_bolt_can_freeze_chill_and_interrupt_an_archer(self):
        self.give_set()
        enemy = self.target("archer")
        enemy.windup, enemy.shot_target = .5, self.world.player.pos
        self.world.proc_rng = Mock()
        self.world.proc_rng.random.return_value = 0
        self.assertTrue(self.world.cast("q", enemy.pos))
        self.world._projectiles(.25)
        self.assertEqual(enemy.frozen, 1)
        self.assertEqual(enemy.chilled, 2)
        self.assertEqual(enemy.windup, 0)
        self.assertIsNone(enemy.shot_target)
        self.assertIn("freeze", self.world.events)
        position = enemy.pos
        for _ in range(45):
            self.world.update(1 / 60)
        self.assertEqual(enemy.pos, position)
        self.assertEqual(self.world.player.hp, 100)
        for _ in range(30):
            self.world.update(1 / 60)
        self.assertEqual(enemy.frozen, 0)

    def test_freeze_roll_uses_expected_threshold_at_each_set_rank(self):
        for rank, chance in ((3, .15), (4, .25), (5, .40)):
            for roll, expected in ((chance - .001, 1), (chance, 0)):
                with self.subTest(rank=rank, roll=roll):
                    self.setUp()
                    self.give_set(rank)
                    enemy = self.target()
                    self.world.proc_rng = Mock()
                    self.world.proc_rng.random.return_value = roll
                    self.bolt_hit(enemy)
                    self.assertEqual(enemy.frozen, expected)
                    self.world.proc_rng.random.assert_called_once()

    def test_missing_set_and_non_bolt_attacks_do_not_roll_freeze(self):
        enemy = self.target()
        self.world.proc_rng = Mock()
        self.bolt_hit(enemy)
        self.world.proc_rng.random.assert_not_called()
        self.assertEqual(enemy.frozen, 0)
        self.give_set()
        self.bolt_hit(enemy, spell="other")
        self.world.proc_rng.random.assert_not_called()
        self.assertEqual(enemy.frozen, 0)

    def test_bolt_checks_current_equipment_on_hit_and_cannot_keep_bonus_after_unequip(self):
        self.give_set()
        enemy = self.target()
        self.world.proc_rng = Mock()
        self.world.cast("q", enemy.pos)
        self.inv.unequip("boots")
        self.world._projectiles(.25)
        self.world.proc_rng.random.assert_not_called()
        self.assertEqual(enemy.frozen, 0)

    def test_dead_targets_spawners_misses_and_enemy_arrows_do_not_trigger_set(self):
        self.give_set()
        self.world.proc_rng = Mock()
        enemy = self.target()
        enemy.hp = 1
        self.bolt_hit(enemy)
        self.world.proc_rng.random.assert_not_called()
        spawner = Spawner(Vec(5.5, 13.5), timer=999)
        self.world.spawners = [spawner]
        self.bolt_hit(spawner)
        self.world.proc_rng.random.assert_not_called()
        self.world.projectiles.append(Projectile(Vec(6.5, 14.5), Vec(1, 0), life=.1))
        self.world._projectiles(.2)
        self.world.projectiles.append(Projectile(self.world.player.pos + Vec(.2, 0), Vec(-10, 0), hostile=True))
        self.world._projectiles(.02)
        self.world.proc_rng.random.assert_not_called()
        self.assertNotIn("freeze", self.world.events)

    def test_proc_does_not_shorten_a_longer_existing_freeze(self):
        self.give_set()
        enemy = self.target()
        enemy.frozen = 3
        self.world.proc_rng = Mock()
        self.world.proc_rng.random.return_value = 0
        self.bolt_hit(enemy)
        self.assertEqual(enemy.frozen, 3)


class EnchantingSlotTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.world.player.gold = 10000
        self.inv = self.world.player.inventory
        self.armory = Armory()

    def add(self, slot="helm", rank=0, worn=False):
        item = self.inv.create(slot, rank, "shop")
        self.inv.add(item, auto_equip=worn)
        return item

    def drag(self, source, destination, tab="shop"):
        self.armory.mouse_down(self.world, source, tab)
        self.armory.mouse_motion(destination, tab)
        return self.armory.mouse_up(self.world, destination, tab)

    def test_drag_equipped_item_loads_reference_without_unequipping_or_charging(self):
        item = self.add(worn=True)
        before, gold = self.inv.to_dict(), self.world.player.gold
        self.assertTrue(self.drag(self.armory.slot_rects["helm"].center, self.armory.enchant_slot_rect.center))
        self.assertEqual(self.armory.enchant_uid, item.uid)
        self.assertEqual(self.inv.to_dict(), before)
        self.assertEqual(self.world.player.gold, gold)
        self.armory.click(self.world, self.armory.upgrade_rect.center, "shop")
        self.assertEqual(self.inv.get(item.uid).rank, 1)
        self.assertEqual(self.inv.get(item.uid).set_id, "frostweave")
        self.assertEqual(self.world.player.gold, gold - 50)
        self.assertEqual(self.inv.equipped["helm"], item.uid)

    def test_backpack_drag_targets_exact_item_independently_of_other_selection(self):
        first, second = self.add(), self.add("boots", 1, worn=True)
        self.assertTrue(self.drag(self.armory.shop_bag_rects[0].center, self.armory.enchant_slot_rect.center))
        self.armory.click(self.world, self.armory.slot_rects["boots"].center, "shop")
        self.assertEqual(self.armory.selected_uid, second.uid)
        self.armory.click(self.world, self.armory.upgrade_rect.center, "shop")
        self.assertEqual(self.inv.get(first.uid).rank, 1)
        self.assertEqual(self.inv.get(second.uid).rank, 1)
        self.assertNotIn(first.uid, self.inv.equipped.values())

    def test_empty_slot_cannot_enchant_an_unrelated_selected_item(self):
        item = self.add(worn=True)
        self.armory.selected_uid = item.uid
        self.armory.click(self.world, self.armory.upgrade_rect.center, "shop")
        self.assertEqual(self.inv.get(item.uid).rank, 0)
        self.assertEqual(self.world.player.gold, 10000)
        self.armory.click(self.world, self.armory.load_selected_rect.center, "shop")
        self.assertEqual(self.armory.enchant_uid, item.uid)
        self.armory.click(self.world, self.armory.clear_enchant_rect.center, "shop")
        self.assertIsNone(self.armory.enchant_target(self.world))
        self.assertEqual(len(self.inv.items), 1)

    def test_drop_outside_slot_and_cancelled_drag_keep_items_and_gold(self):
        self.add(worn=True)
        before = self.inv.to_dict()
        self.assertFalse(self.drag(self.armory.slot_rects["helm"].center, (1300, 700)))
        self.assertIsNone(self.armory.enchant_uid)
        self.armory.mouse_down(self.world, self.armory.slot_rects["helm"].center, "shop")
        self.armory.mouse_motion(self.armory.enchant_slot_rect.center, "shop")
        self.assertTrue(self.armory.cancel_drag())
        self.assertFalse(self.armory.mouse_up(self.world, self.armory.enchant_slot_rect.center, "shop"))
        self.assertEqual(self.inv.to_dict(), before)
        self.assertEqual(self.world.player.gold, 10000)

    def test_removed_target_is_cleared_and_never_replaced_by_another_item(self):
        item, other = self.add(), self.add("boots")
        self.armory.load_enchant_item(self.world, item.uid)
        self.world.sell_item(item.uid)
        self.armory.selected_uid = other.uid
        gold = self.world.player.gold
        self.armory.click(self.world, self.armory.upgrade_rect.center, "shop")
        self.assertIsNone(self.armory.enchant_uid)
        self.assertEqual(self.inv.get(other.uid).rank, 0)
        self.assertEqual(self.world.player.gold, gold)

    def test_drag_from_later_shop_backpack_page_uses_correct_uid(self):
        items = [self.add(rank=1) for _ in range(10)]
        self.armory.page = 1
        self.assertTrue(self.drag(self.armory.shop_bag_rects[0].center, self.armory.enchant_slot_rect.center))
        self.assertEqual(self.armory.enchant_uid, items[8].uid)
        self.assertEqual(len(self.inv.items), 10)

    def test_target_enchantment_still_respects_funds_max_rank_stasis_and_death(self):
        item = self.add(rank=5)
        self.armory.load_enchant_item(self.world, item.uid)
        self.armory.click(self.world, self.armory.upgrade_rect.center, "shop")
        self.assertEqual(self.world.player.gold, 10000)
        item = self.add("boots")
        self.armory.load_enchant_item(self.world, item.uid)
        for reason in ("funds", "stasis", "dead"):
            self.world.player.gold = 0 if reason == "funds" else 10000
            self.world.player.stasis = 1 if reason == "stasis" else 0
            self.world.state = "dead" if reason == "dead" else "playing"
            gold = self.world.player.gold
            self.armory.click(self.world, self.armory.upgrade_rect.center, "shop")
            self.assertEqual(self.inv.get(item.uid).rank, 0)
            self.assertEqual(self.world.player.gold, gold)


if __name__ == "__main__":
    unittest.main()
