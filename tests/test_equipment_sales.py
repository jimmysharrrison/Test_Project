"""Upgrade comparisons and transactional, confirmed equipment sales."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dungeon.armory import Armory
from dungeon.items import SLOTS
from dungeon.profile import ProfileStore
from dungeon.world import World


class EquipmentSalesTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.inv = self.world.player.inventory

    def add(self, slot="helm", rank=1, worn=False):
        item = self.inv.create(slot, rank)
        self.inv.add(item, auto_equip=False)
        if worn:
            self.inv.equip(item.uid)
        return item

    def test_upgrades_compare_the_matching_slot_and_react_to_equipment_changes(self):
        for slot in SLOTS:
            worn = self.add(slot, 2, worn=True)
            lower, equal, higher = (self.add(slot, rank) for rank in (1, 2, 3))
            self.assertFalse(self.inv.is_upgrade(worn))
            self.assertFalse(self.inv.is_upgrade(lower))
            self.assertFalse(self.inv.is_upgrade(equal))
            self.assertTrue(self.inv.is_upgrade(higher))
            self.inv.equip(higher.uid)
            self.assertFalse(self.inv.is_upgrade(higher))
            self.assertFalse(self.inv.is_upgrade(equal))
            self.inv.unequip(slot)
            self.assertTrue(self.inv.is_upgrade(lower))
            self.assertFalse(self.inv.is_upgrade(self.add(slot, 0)))

    def test_highest_upgrades_sort_first_without_changing_saved_item_order(self):
        self.add("helm", 3, worn=True)
        lower = self.add("helm", 2)
        first_upgrade = self.add("chest", 1)
        for _ in range(20):
            self.add("helm", 3)
        best = self.add("boots", 5)
        same_rank = self.add("chest", 1)
        original = self.inv.to_dict()
        bag = self.inv.prioritized_backpack
        self.assertEqual(bag[:3], [best, first_upgrade, same_rank])
        self.assertEqual(bag[3], lower)
        self.assertEqual(self.inv.to_dict(), original)
        self.assertEqual(set(bag), set(self.inv.backpack))

    def test_bulk_sale_covers_all_pages_but_only_exact_rank_and_never_worn_items(self):
        worn = self.add("chest", 2, worn=True)
        for rank in (0, 1, 3, 4, 5):
            self.add("helm", rank)
        sold = [self.add(SLOTS[i % 5], 2) for i in range(35)]
        quote = self.world.quote_sale(2)
        self.assertEqual(set(quote), set(sold))
        expected = sum(item.sell_value for item in sold)
        self.assertTrue(self.world.sell_items(quote))
        self.assertEqual(self.world.player.gold, expected)
        self.assertIs(self.inv.worn("chest"), worn)
        self.assertEqual({i.rank for i in self.inv.backpack}, {0, 1, 3, 4, 5})
        self.assertFalse(self.world.sell_items(quote))
        self.assertEqual(self.world.player.gold, expected)

    def test_bulk_sale_rejects_changed_or_equipped_quote_without_partial_sale(self):
        for change in ("equip", "enchant", "remove"):
            with self.subTest(change=change):
                self.setUp()
                first, second = self.add(rank=3), self.add("boots", 3)
                quote = self.world.quote_sale(3)
                if change == "equip":
                    self.inv.equip(second.uid)
                elif change == "enchant":
                    self.inv.upgrade(second.uid)
                else:
                    self.inv.remove(second.uid)
                before = self.inv.to_dict()
                self.assertFalse(self.world.sell_items(quote))
                self.assertEqual(self.inv.to_dict(), before)
                self.assertIsNotNone(self.inv.get(first.uid))
                self.assertEqual(self.world.player.gold, 0)

    def test_new_items_after_quote_are_not_sold_without_being_quoted(self):
        old = self.add(rank=2)
        quote = self.world.quote_sale(2)
        new = self.add(rank=2)
        self.assertTrue(self.world.sell_items(quote))
        self.assertIsNone(self.inv.get(old.uid))
        self.assertIsNotNone(self.inv.get(new.uid))
        self.assertEqual(self.world.player.gold, old.sell_value)

    def test_empty_invalid_and_duplicate_quotes_do_not_pay_gold(self):
        item = self.add(rank=3)
        for rank in (-1, 6, True, "3"):
            self.assertEqual(self.world.quote_sale(rank), ())
        self.assertFalse(self.world.sell_items(()))
        self.assertFalse(self.world.sell_items((item, item)))
        self.assertIsNotNone(self.inv.get(item.uid))
        self.assertEqual(self.world.player.gold, 0)

    def test_bulk_sale_respects_stasis_and_death_and_persists_on_success(self):
        for _ in range(4):
            self.add(rank=4)
        quote = self.world.quote_sale(4)
        self.world.player.stasis = 1
        self.assertFalse(self.world.sell_items(quote))
        self.world.player.stasis = 0
        self.world.state = "dead"
        self.assertFalse(self.world.sell_items(quote))
        self.world.state = "playing"
        self.assertTrue(self.world.sell_items(quote))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            ProfileStore(path).save(self.world.player)
            loaded = ProfileStore(path).load()
        self.assertEqual(loaded.inventory.items, [])
        self.assertEqual(loaded.gold, sum(item.sell_value for item in quote))


class SaleConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.inv = self.world.player.inventory
        self.armory = Armory()

    def add(self, rank, slot="helm"):
        item = self.inv.create(slot, rank)
        self.inv.add(item, auto_equip=False)
        return item

    def tap(self, rect, tab="inventory"):
        return self.armory.click(self.world, rect.center, tab)

    def test_individual_rank_three_four_and_five_require_confirmation_in_both_tabs(self):
        for tab in ("inventory", "shop"):
            for rank in (3, 4, 5):
                with self.subTest(tab=tab, rank=rank):
                    self.setUp()
                    item = self.add(rank)
                    self.armory.selected_uid = item.uid
                    self.tap(self.armory.sell_rect, tab)
                    self.assertEqual(self.armory.pending_sale_items, (item,))
                    self.assertIsNotNone(self.inv.get(item.uid))
                    self.assertEqual(self.world.player.gold, 0)
                    self.tap(self.armory.cancel_destroy_rect, tab)
                    self.assertEqual(self.armory.pending_sale_items, ())
                    self.assertIsNotNone(self.inv.get(item.uid))
                    self.tap(self.armory.sell_rect, tab)
                    self.tap(self.armory.confirm_destroy_rect, tab)
                    self.assertIsNone(self.inv.get(item.uid))
                    self.assertEqual(self.world.player.gold, item.sell_value)
                    self.assertEqual(self.armory.pending_sale_items, ())

    def test_low_rank_single_sales_remain_immediate(self):
        for rank in (0, 1, 2):
            item = self.add(rank)
            before = self.world.player.gold
            self.armory.selected_uid = item.uid
            self.tap(self.armory.sell_rect)
            self.assertIsNone(self.inv.get(item.uid))
            self.assertEqual(self.world.player.gold, before + item.sell_value)
            self.assertEqual(self.armory.pending_sale_items, ())

    def test_sell_all_always_confirms_every_rank_even_for_one_item(self):
        for rank in range(6):
            with self.subTest(rank=rank):
                self.setUp()
                item = self.add(rank)
                self.tap(self.armory.sale_rank_rects[rank])
                self.tap(self.armory.sell_all_rect)
                self.assertEqual(self.armory.pending_sale_items, (item,))
                self.assertEqual(self.armory.pending_sale_rank, rank)
                self.assertIsNotNone(self.inv.get(item.uid))
                self.assertEqual(self.world.player.gold, 0)
                self.tap(self.armory.confirm_destroy_rect)
                self.assertIsNone(self.inv.get(item.uid))
                self.assertEqual(self.world.player.gold, item.sell_value)

    def test_modal_blocks_underlying_controls_and_cancelling_keeps_everything(self):
        item = self.add(3)
        self.armory.selected_uid = item.uid
        self.tap(self.armory.sell_rect)
        before = self.inv.to_dict()
        for rect in (self.armory.sell_all_rect, self.armory.equip_rect, self.armory.destroy_rect,
                     self.armory.close_rect, self.armory.shop_tab, self.armory.sale_rank_rects[1]):
            self.assertEqual(self.tap(rect), "inventory")
            self.assertEqual(self.inv.to_dict(), before)
        self.assertEqual(self.armory.sale_rank, 0)
        self.assertTrue(self.armory.cancel_confirmation())
        self.assertFalse(self.armory.cancel_confirmation())
        self.assertEqual(self.inv.to_dict(), before)
        self.assertEqual(self.world.player.gold, 0)

    def test_sale_confirmation_does_not_sell_equipped_or_changed_items(self):
        first, second = self.add(3), self.add(3, "boots")
        self.tap(self.armory.sale_rank_rects[3])
        self.tap(self.armory.sell_all_rect)
        self.inv.equip(second.uid)
        self.tap(self.armory.confirm_destroy_rect)
        self.assertIsNotNone(self.inv.get(first.uid))
        self.assertIsNotNone(self.inv.get(second.uid))
        self.assertEqual(self.world.player.gold, 0)
        self.assertEqual(self.armory.pending_sale_items, ())

    def test_empty_bulk_sale_and_equipped_single_sale_cannot_open_confirmation(self):
        item = self.add(5)
        self.inv.equip(item.uid)
        self.armory.selected_uid = item.uid
        self.tap(self.armory.sale_rank_rects[5])
        self.tap(self.armory.sell_all_rect)
        self.tap(self.armory.sell_rect)
        self.assertEqual(self.armory.pending_sale_items, ())
        self.assertEqual(self.world.player.gold, 0)


if __name__ == "__main__":
    unittest.main()

