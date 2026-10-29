"""Equipment inventory, hover details, and the gold-based enchanter interface."""

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pygame

from .items import stock_price, DEFINITIONS, BLANK_COST, FROSTWEAVE_FREEZE, Item, RANK_COLORS, RANK_NAMES, SLOTS, SLOT_PURPOSE

PANEL = (19, 29, 40)
LINE = (55, 77, 94)
WHITE = (232, 230, 217)
MUTED = (137, 157, 172)
ICE = (139, 216, 248)
GOLD = (214, 180, 113)
RED = (215, 96, 99)
UPGRADE = (116, 226, 153)

FROSTWEAVE_ART = {
    "helm": "frostweave-crown.png",
    "chest": "frostweave-vestment.png",
    "legs": "frostweave-leggings.png",
    "gloves": "frostweave-grips.png",
    "boots": "frostweave-treads.png",
}
IMAGE_ROOT = Path(__file__).resolve().parents[1] / "Images" / "Icons" / "Equipment"


@lru_cache(maxsize=128)
def equipment_art(filename):
    try:
        image = pygame.image.load(str(IMAGE_ROOT / filename))
        bounds = image.get_bounding_rect(min_alpha=32)
        return image.subsurface(bounds).copy() if bounds.width and bounds.height else None
    except (OSError, pygame.error):
        return None


@lru_cache(maxsize=512)
def equipment_icon(filename, size):
    image = equipment_art(filename)
    if image is None:
        return None
    factor = (size - 4) / max(image.get_size())
    dimensions = tuple(max(1, round(value * factor)) for value in image.get_size())
    return pygame.transform.smoothscale(image, dimensions)


@lru_cache(maxsize=5)
def frostweave_art(slot):
    filename = FROSTWEAVE_ART.get(slot)
    return equipment_art(filename) if filename else None


@lru_cache(maxsize=32)
def frostweave_icon(slot, size):
    filename = FROSTWEAVE_ART.get(slot)
    return equipment_icon(filename, size) if filename else None


def item_icon(surface, slot, center, color, scale=1, item=None, set_id=None):
    if (item.set_id if item is not None else set_id) == "frostweave":
        image = frostweave_icon(slot, max(8, round(60 * scale)))
        if image is not None:
            surface.blit(image, image.get_rect(center=center))
            return
    elif item is not None:
        filename = item.name.lower().replace("’", "").replace("'", "").replace(" ", "-") + ".png"
        image = equipment_icon(filename, max(8, round(60 * scale)))
        if image is not None:
            surface.blit(image, image.get_rect(center=center))
            return
    x, y = center
    def p(dx, dy):
        return round(x + dx * scale), round(y + dy * scale)
    def poly(points):
        pygame.draw.polygon(surface, color, [p(dx, dy) for dx, dy in points], max(1, round(scale)))
    if item is not None and item.template_id and not item.set_id:
        definition = DEFINITIONS[item.template_id]
        variant = list(DEFINITIONS).index(item.template_id) % 3
        rune = (160, 225, 245) if variant == 0 else (130, 220, 170) if variant == 1 else (200, 165, 240)
        pygame.draw.circle(surface, rune, p(0, 0), max(2, round(4 * scale)), 1)
    if slot == "helm":
        poly([(-14, 8), (-15, -10), (-7, -5), (0, -17), (7, -5), (15, -10), (14, 8)])
        pygame.draw.line(surface, color, p(-13, 3), p(13, 3), max(1, round(scale)))
    elif slot == "chest":
        poly([(-7, -15), (-16, -11), (-21, 0), (-13, 5), (-9, -1), (-10, 17), (10, 17),
              (9, -1), (13, 5), (21, 0), (16, -11), (7, -15), (4, -10), (-4, -10)])
        pygame.draw.line(surface, color, p(0, -8), p(0, 13), max(1, round(scale)))
    elif slot == "legs":
        poly([(-12, -16), (12, -16), (11, 16), (3, 16), (0, -1), (-3, 16), (-11, 16)])
        pygame.draw.line(surface, color, p(-11, -10), p(11, -10), max(1, round(scale)))
    elif slot == "gloves":
        poly([(-12, 15), (-16, 5), (-16, -9), (-12, -14), (-8, -9), (-7, -2), (-3, -8),
              (1, -6), (-4, 7), (-4, 15)])
        poly([(6, 15), (3, 3), (7, -12), (11, -14), (15, -9), (15, 4), (12, 15)])
    else:
        poly([(-14, -14), (-4, -14), (-4, 6), (2, 10), (1, 16), (-17, 16), (-18, 10), (-14, 5)])
        poly([(5, -14), (15, -14), (15, 6), (21, 10), (20, 16), (3, 16), (2, 10), (5, 5)])


class Armory:
    def __init__(self):
        self.selected_uid = None
        self.pending_destroy_uid = None
        self.pending_sale_items = ()
        self.pending_sale_rank = None
        self.sale_rank = 0
        self.page = 0
        self.enchant_uid = None
        self.drag_uid = None
        self.drag_start = None
        self.dragging = False
        self.close_rect = pygame.Rect(1184, 104, 38, 32)
        self.inventory_tab = pygame.Rect(222, 174, 174, 34)
        self.shop_tab = pygame.Rect(410, 174, 190, 34)
        self.slot_rects = {slot: pygame.Rect(222, 265 + i * 75, 255, 66) for i, slot in enumerate(SLOTS)}
        self.bag_rects = [pygame.Rect(511 + (i % 4) * 87, 265 + (i // 4) * 87, 76, 76) for i in range(16)]
        self.shop_bag_rects = [pygame.Rect(511 + (i % 4) * 87, 486 + (i // 4) * 74, 76, 64) for i in range(8)]
        self.previous_page = pygame.Rect(511, 630, 37, 30)
        self.next_page = pygame.Rect(811, 630, 37, 30)
        self.equip_rect = pygame.Rect(697, 740, 173, 34)
        self.sell_rect = pygame.Rect(511, 740, 93, 34)
        self.destroy_rect = pygame.Rect(612, 740, 77, 34)
        self.cancel_destroy_rect = pygame.Rect(490, 495, 210, 38)
        self.confirm_destroy_rect = pygame.Rect(720, 495, 230, 38)
        self.sale_rank_rects = {rank: pygame.Rect(222 + rank * 42, 669, 36, 28) for rank in range(6)}
        self.sell_all_rect = pygame.Rect(222, 730, 255, 34)
        self.enchant_tab_rect = pygame.Rect(888, 740, 314, 34)
        self.buy_rects = {slot: pygame.Rect(729, 269 + i * 38, 143, 28) for i, slot in enumerate(SLOTS)}
        self.upgrade_rect = pygame.Rect(917, 575, 288, 45)
        self.enchant_slot_rect = pygame.Rect(917, 265, 288, 86)
        self.load_selected_rect = pygame.Rect(917, 368, 288, 30)
        self.clear_enchant_rect = pygame.Rect(917, 637, 100, 26)

    def selected(self, world):
        return world.player.inventory.get(self.selected_uid)

    def bag_page(self, world, tab="inventory"):
        bag = world.player.inventory.prioritized_backpack
        size = 8 if tab == "shop" else 16
        self.page = min(self.page, max(0, (len(bag) - 1) // size))
        return bag[self.page * size:(self.page + 1) * size]

    def enchant_target(self, world):
        item = world.player.inventory.get(self.enchant_uid)
        if item is None:
            self.enchant_uid = None
        return item

    def load_enchant_item(self, world, uid):
        item = world.player.inventory.get(uid)
        if item is None:
            return False
        self.enchant_uid = item.uid
        world.announce(f"{item.name} placed in the enchanting slot. Choose Enchant to apply the next rank.")
        return True

    def owned_at(self, world, point, tab):
        for slot, rect in self.slot_rects.items():
            if rect.collidepoint(point):
                return world.player.inventory.worn(slot)
        rects = self.shop_bag_rects if tab == "shop" else self.bag_rects
        return next((item for item, rect in zip(self.bag_page(world, tab), rects) if rect.collidepoint(point)), None)

    def mouse_down(self, world, point, tab):
        self.cancel_drag()
        blocked = self.pending_destroy_uid is not None or bool(self.pending_sale_items)
        action = self.click(world, point, tab)
        if not blocked and action == tab and not self.pending_sale_items and self.pending_destroy_uid is None:
            item = self.owned_at(world, point, tab)
            if item is not None:
                self.drag_uid, self.drag_start = item.uid, point
                self.dragging = False
        return action

    def mouse_motion(self, point, tab):
        if self.drag_uid is not None and self.drag_start is not None:
            dx, dy = point[0] - self.drag_start[0], point[1] - self.drag_start[1]
            self.dragging = self.dragging or dx * dx + dy * dy >= 36
            if self.dragging and self.shop_tab.collidepoint(point):
                return "shop"
        return tab

    def mouse_up(self, world, point, tab):
        uid, dragging = self.drag_uid, self.dragging
        # A release can be delivered without a final motion event.
        if uid is not None and self.drag_start is not None:
            self.mouse_motion(point, tab)
            dragging = self.dragging
        self.cancel_drag()
        if uid is not None and dragging and tab == "shop" and self.enchant_slot_rect.collidepoint(point):
            return self.load_enchant_item(world, uid)
        return False

    def cancel_drag(self):
        pending = self.dragging
        self.drag_uid, self.drag_start, self.dragging = None, None, False
        return pending

    def click(self, world, point, tab):
        inventory = world.player.inventory
        if self.pending_destroy_uid is not None:
            if self.cancel_destroy_rect.collidepoint(point):
                self.cancel_destroy()
            elif self.confirm_destroy_rect.collidepoint(point):
                uid = self.pending_destroy_uid
                self.cancel_destroy()
                if world.destroy_item(uid):
                    self.selected_uid = None
            return tab
        if self.pending_sale_items:
            if self.cancel_destroy_rect.collidepoint(point):
                self.cancel_confirmation()
            elif self.confirm_destroy_rect.collidepoint(point):
                items = self.pending_sale_items
                self.cancel_confirmation()
                if world.sell_items(items) and self.selected_uid in {item.uid for item in items}:
                    self.selected_uid = None
            return tab
        if self.close_rect.collidepoint(point):
            return "close"
        if self.inventory_tab.collidepoint(point):
            return "inventory"
        if self.shop_tab.collidepoint(point):
            return "shop"
        item = self.selected(world)
        for rank, rect in self.sale_rank_rects.items():
            if rect.collidepoint(point):
                self.sale_rank = rank
                return tab
        if self.sell_all_rect.collidepoint(point):
            if world._can_manage_gear():
                items = world.quote_sale(self.sale_rank)
                if items:
                    self.pending_sale_items = items
                    self.pending_sale_rank = self.sale_rank
                else:
                    world.announce(f"No unequipped Rank {self.sale_rank} equipment to sell.")
            return tab
        if self.sell_rect.collidepoint(point):
            if item and world._discardable_item(item.uid) is not None:
                if item.rank >= 3:
                    self.pending_sale_items = (item,)
                    self.pending_sale_rank = None
                elif world.sell_item(item.uid):
                    self.selected_uid = None
            return tab
        if self.destroy_rect.collidepoint(point):
            if item and world._discardable_item(item.uid) is not None:
                self.pending_destroy_uid = item.uid
            return tab
        if self.equip_rect.collidepoint(point):
            if item:
                if inventory.equipped[item.slot] == item.uid:
                    world.unequip_item(item.slot)
                else:
                    world.equip_item(item.uid)
            return tab
        if tab == "shop":
            if self.load_selected_rect.collidepoint(point):
                self.load_enchant_item(world, self.selected_uid)
                return tab
            if self.clear_enchant_rect.collidepoint(point):
                self.enchant_uid = None
                return tab
        for slot, rect in self.slot_rects.items():
            if rect.collidepoint(point):
                item = inventory.worn(slot)
                self.selected_uid = item.uid if item else None
                return tab
        if tab in ("inventory", "shop"):
            rects = self.shop_bag_rects if tab == "shop" else self.bag_rects
            for item, rect in zip(self.bag_page(world, tab), rects):
                if rect.collidepoint(point):
                    self.selected_uid = item.uid
                    return tab
            if self.previous_page.collidepoint(point):
                self.page = max(0, self.page - 1)
            elif self.next_page.collidepoint(point):
                size = 8 if tab == "shop" else 16
                self.page = min(max(0, (len(inventory.backpack) - 1) // size), self.page + 1)
            elif tab == "inventory" and self.enchant_tab_rect.collidepoint(point):
                return "shop"
        if tab == "shop":
            for slot, rect in self.buy_rects.items():
                if rect.collidepoint(point):
                    item = world.buy_item(slot)
                    if item:
                        self.selected_uid = item.uid
                        self.enchant_uid = item.uid
                    return tab
            if self.upgrade_rect.collidepoint(point) and self.enchant_target(world):
                world.enchant_item(self.enchant_uid)
        return tab

    def cancel_destroy(self):
        pending = self.pending_destroy_uid is not None
        self.pending_destroy_uid = None
        return pending

    def cancel_confirmation(self):
        pending = bool(self.pending_sale_items)
        self.pending_sale_items = ()
        self.pending_sale_rank = None
        return self.cancel_destroy() or pending

    @staticmethod
    def button(r, rect, label, enabled=True, active=False):
        pygame.draw.rect(r.screen, (33, 61, 80) if active else (28, 43, 56), rect, border_radius=4)
        pygame.draw.rect(r.screen, ICE if active else LINE, rect, 1, border_radius=4)
        r.text(label, rect.centerx, rect.y + (rect.height - 16) // 2, 12,
               WHITE if enabled else MUTED, center=True)

    @staticmethod
    def tooltip(r, item, point, owned=False, current=None, upgrade=False):
        lines = item.lines
        if not owned and item.source == 'shop' and item.template_id and not item.set_id:
            import textwrap
            from .items import EFFECT_LABELS
            definition = DEFINITIONS[item.template_id]
            low, high = definition.ranges[item.rank - 1]
            lines = ['One enchantment / rolled on purchase'] + textwrap.wrap(f'{low / 10:.1f}–{high / 10:.1f}% {EFFECT_LABELS[definition.effect]}', width=43)
        height = (198 + max(0, len(lines) - 1) * 21
                  + (35 if current and current.uid != item.uid else 0) + (24 if upgrade else 0)
                  + (64 if item.set_id == "frostweave" else 0))
        x, y = min(point[0] + 18, 1068), min(point[1] + 18, 888 - height)
        x, y = max(8, x), max(8, y)
        color = RANK_COLORS[item.rank]
        box = pygame.Rect(x, y, 360, height)
        pygame.draw.rect(r.screen, (13, 23, 33), box, border_radius=6)
        pygame.draw.rect(r.screen, color, box, 1, border_radius=6)
        r.text(item.name, x + 14, y + 13, 18, color, serif=True)
        r.text(f"{item.slot.upper()}  ·  RANK {item.rank} / {RANK_NAMES[item.rank].upper()}", x + 14, y + 45, 11, MUTED)
        for i, line in enumerate(lines):
            r.text(line, x + 14, y + 74 + i * 21, 11, WHITE)
        yy = y + 86 + len(lines) * 21
        if item.set_id == "frostweave":
            r.text("FROSTWEAVE / FIVE-PIECE SET", x + 14, yy, 11, ICE)
            r.text("Equip all five pieces at Rank 3 or higher.", x + 14, yy + 19, 10, WHITE)
            r.text("R3: 15% / R4: 25% / R5: 40% bolt freeze (1s).", x + 14, yy + 38, 10, ICE)
            yy += 64
        if upgrade:
            r.text("UPGRADE FOR YOUR EQUIPPED SLOT", x + 14, yy, 11, UPGRADE)
            yy += 24
        if current and current.uid != item.uid:
            r.text(f"Equipped: Rank {current.rank} {current.name}", x + 14, yy, 10, MUTED)
            yy += 28
        detail = "Maximum enchantment reached" if item.next_cost is None else f"Next enchantment: {item.next_cost:,} gold"
        r.text(detail, x + 14, yy, 11, GOLD)
        r.text(f"Sell value: {item.sell_value:,} gold", x + 14, yy + 22, 11, GOLD)
        if item.set_id == "frostweave":
            note = "Set rank = lowest equipped piece · Enchanter stock"
        elif item.slot == "boots":
            note = "Rare drop · first-level clear reward"
        elif item.rank <= 3 and item.rank > 0:
            note = "Rank 3 is the best dropped rank"
        else:
            note = "Ranks 4–5 are enchantment-only"
        note = ("Frostweave / unlocked by the Keeper" if item.set_id else "One rolled enchantment / maximum Rank 3") if item.template_id else note
        r.text(note, x + 14, yy + 45, 10, MUTED)
        r.text("Owned equipment" if owned else "Walk over loot to collect it" if item.source == "drop" else "Shop template / randomized on purchase" if not item.set_id and item.template_id else "Frostweave shop stock", x + 14, yy + 65, 9, MUTED)

    def draw(self, r, world, mouse, tab):
        inventory = world.player.inventory
        if self.selected(world) is None and inventory.items:
            self.selected_uid = inventory.items[0].uid
        veil = pygame.Surface(r.screen.get_size(), pygame.SRCALPHA)
        veil.fill((4, 9, 16, 210))
        r.screen.blit(veil, (0, 0))
        pygame.draw.rect(r.screen, PANEL, (190, 80, 1060, 740), border_radius=12)
        pygame.draw.rect(r.screen, LINE, (190, 80, 1060, 740), 1, border_radius=12)
        r.spaced("FROSTBOUND ARMORY", 222, 105, 22, ICE, 1)
        r.text("Equipment & enchantments", 222, 145, 12, MUTED)
        r.character_portrait((894, 130), 56, world.player)
        r.text(f"{world.player.gold:,} GOLD", 955, 113, 21, GOLD, serif=True)
        self.button(r, self.close_rect, "X")
        self.button(r, self.inventory_tab, "I  /  INVENTORY", active=tab == "inventory")
        self.button(r, self.shop_tab, "B  /  ENCHANTER", active=tab == "shop")
        r.text("Game paused", 1107, 184, 11, MUTED)
        pygame.draw.line(r.screen, LINE, (222, 223), (1217, 223))
        r.spaced("EQUIPPED", 222, 236, 10, MUTED)
        hovered = None
        for slot, rect in self.slot_rects.items():
            item = inventory.worn(slot)
            color = RANK_COLORS[item.rank] if item else LINE
            selected = item is not None and item.uid == self.selected_uid
            pygame.draw.rect(r.screen, (25, 43, 56) if selected else (22, 35, 47), rect, border_radius=5)
            pygame.draw.rect(r.screen, ICE if selected else color, rect, 1, border_radius=5)
            item_icon(r.screen, slot, (rect.x + 31, rect.centery), color if item else MUTED, .7, item=item)
            label = slot.title() + (" / Frostweave" if item and item.set_id == "frostweave" else "")
            r.text(label, rect.x + 61, rect.y + 9, 12, MUTED)
            r.text(f"Rank {item.rank} · {RANK_NAMES[item.rank]}" if item else "Empty slot", rect.x + 61, rect.y + 34, 13, color if item else MUTED)
            if mouse and rect.collidepoint(mouse):
                hovered = item if item else slot
        item = self.selected(world)
        if tab == "inventory":
            hovered = self.draw_backpack(r, world, mouse, tab) or hovered
            self.draw_stats(r, world)
        else:
            unlocked = world.player.frostweave_unlocked
            r.spaced("FROSTWEAVE STOCK / RANK 3" if unlocked else "ORDINARY STOCK / RANK 1", 511, 236, 10, ICE)
            for i, slot in enumerate(SLOTS):
                key = ('frostweave:' if unlocked else 'standard:') + slot
                stock = Item(1, slot, 3 if unlocked else 1, 'shop', 'frostweave' if unlocked else None, key, None if unlocked else 5000)
                cost = stock_price(slot, unlocked)
                rect = pygame.Rect(511, 265 + i * 38, 374, 32)
                pygame.draw.rect(r.screen, (22, 35, 47), rect, border_radius=5)
                item_icon(r.screen, slot, (533, rect.centery), ICE, .43, item=stock)
                r.text(stock.name, 555, rect.y + 8, 11, WHITE)
                self.button(r, self.buy_rects[slot], f"BUY {cost:,} G", enabled=world.player.gold >= cost)
                if mouse and rect.collidepoint(mouse):
                    hovered = stock
            hovered = self.draw_backpack(r, world, mouse, tab) or hovered
            self.draw_enchanter(r, world, mouse)
            if mouse and self.enchant_slot_rect.collidepoint(mouse) and self.enchant_target(world):
                hovered = self.enchant_target(world)
        pygame.draw.line(r.screen, LINE, (511, 677), (1217, 677))
        r.text(item.name if item else "Select a piece of equipment", 511, 692, 18,
               RANK_COLORS[item.rank] if item else WHITE, serif=True)
        r.text(world.message if world.message_time > 0 else "Hover any item for its details.", 511, 722, 10, MUTED)
        equipped = item is not None and inventory.equipped[item.slot] == item.uid
        disposable = item is not None and not equipped and world.state != "dead" and world.player.stasis <= 0
        self.button(r, self.sell_rect, f"SELL {item.sell_value:,}G" if item else "SELL", enabled=disposable)
        self.button(r, self.destroy_rect, "DESTROY", enabled=disposable)
        self.button(r, self.equip_rect, "UNEQUIP" if equipped else "EQUIP ITEM", enabled=item is not None)
        if tab == "inventory":
            self.button(r, self.enchant_tab_rect, "OPEN ENCHANTMENTS  >")
        else:
            r.text("Drag equipment into the slot above.", 906, 751, 11, MUTED)
        self.draw_bulk_sale(r, world)
        if isinstance(hovered, Item) and not self.dragging:
            owned = inventory.get(hovered.uid) is hovered
            current = inventory.worn(hovered.slot) if not owned or inventory.equipped[hovered.slot] != hovered.uid else None
            self.tooltip(r, hovered, mouse, owned, current, upgrade=owned and inventory.is_upgrade(hovered))
        elif hovered and not self.dragging:
            x, y = min(mouse[0] + 15, 1058), min(mouse[1] + 15, 744)
            pygame.draw.rect(r.screen, (13, 23, 33), (x, y, 368, 95), border_radius=5)
            r.text(hovered.title(), x + 12, y + 10, 17, ICE)
            r.text(SLOT_PURPOSE[hovered], x + 12, y + 44, 11, WHITE)
        if self.pending_destroy_uid is not None:
            self.draw_destroy_confirmation(r, world)
        elif self.pending_sale_items:
            self.draw_sale_confirmation(r, world)
        elif self.dragging and mouse:
            dragged = inventory.get(self.drag_uid)
            if dragged is not None:
                x, y = mouse
                pygame.draw.rect(r.screen, (20, 39, 54), (x - 28, y - 29, 56, 59), border_radius=5)
                pygame.draw.rect(r.screen, ICE, (x - 28, y - 29, 56, 59), 1, border_radius=5)
                item_icon(r.screen, dragged.slot, (x, y - 4), RANK_COLORS[dragged.rank], .65, item=dragged)
                r.text(f"R{dragged.rank}", x, y + 15, 10, ICE, center=True)

    def draw_backpack(self, r, world, mouse, tab):
        inventory = world.player.inventory
        shop = tab == "shop"
        r.spaced(f"BACKPACK  /  {len(inventory.backpack)} ITEMS", 511, 461 if shop else 236, 10, MUTED)
        page_items = self.bag_page(world, tab)
        rects = self.shop_bag_rects if shop else self.bag_rects
        hovered = None
        for i, rect in enumerate(rects):
            bag_item = page_items[i] if i < len(page_items) else None
            selected = bag_item and bag_item.uid == self.selected_uid
            upgrade = bag_item is not None and inventory.is_upgrade(bag_item)
            fill = (28, 48, 62) if selected else (23, 47, 39) if upgrade else (22, 35, 47)
            pygame.draw.rect(r.screen, fill, rect, border_radius=5)
            pygame.draw.rect(r.screen, ICE if selected else RANK_COLORS[bag_item.rank] if bag_item else LINE, rect, 1, border_radius=5)
            if upgrade:
                pygame.draw.rect(r.screen, UPGRADE, rect.inflate(4, 4), 2, border_radius=6)
                pygame.draw.circle(r.screen, (19, 45, 32), (rect.right - 12, rect.y + 12), 10)
                pygame.draw.lines(r.screen, UPGRADE, False,
                                  [(rect.right - 18, rect.y + 12), (rect.right - 13, rect.y + 17),
                                   (rect.right - 6, rect.y + 7)], 2)
            if bag_item:
                item_icon(r.screen, bag_item.slot, (rect.centerx, rect.y + (25 if shop else 30)),
                          RANK_COLORS[bag_item.rank], .65 if shop else .8, item=bag_item)
                r.text(f"R{bag_item.rank}", rect.x + 9, rect.bottom - 21, 11, RANK_COLORS[bag_item.rank])
                if bag_item.set_id == "frostweave":
                    r.text("FW", rect.right - 23, rect.bottom - 20, 9, ICE)
                if mouse and rect.collidepoint(mouse):
                    hovered = bag_item
        self.button(r, self.previous_page, "<")
        self.button(r, self.next_page, ">")
        total_pages = max(1, (len(inventory.backpack) + len(rects) - 1) // len(rects))
        r.text(f"PAGE {self.page + 1} / {total_pages}", 680, 640, 11, MUTED, center=True)
        r.text("DRAG GEAR TO THE ENCHANTING SLOT" if shop else "GREEN CHECK = UPGRADE  /  UPGRADES FIRST",
               511, 664, 10, ICE if shop else UPGRADE)
        return hovered

    def draw_bulk_sale(self, r, world):
        items = world.quote_sale(self.sale_rank)
        total = sum(item.sell_value for item in items)
        r.spaced("SELL BACKPACK BY RANK", 222, 646, 10, MUTED, 1)
        for rank, rect in self.sale_rank_rects.items():
            self.button(r, rect, f"R{rank}", active=rank == self.sale_rank)
        r.text(f"{len(items)} items  ·  {total:,} GOLD", 222, 706, 11, GOLD)
        enabled = bool(items) and world.state != "dead" and world.player.stasis <= 0
        self.button(r, self.sell_all_rect, f"SELL ALL RANK {self.sale_rank}", enabled=enabled)
        r.text("Equipped items are never sold.", 222, 775, 10, MUTED)
        r.text("I inventory · B shop · Esc close", 222, 796, 9, MUTED)

    def draw_sale_confirmation(self, r, world):
        items = self.pending_sale_items
        total = sum(item.sell_value for item in items)
        upgrades = sum(world.player.inventory.is_upgrade(item) for item in items)
        shade = pygame.Surface(r.screen.get_size(), pygame.SRCALPHA)
        shade.fill((4, 9, 16, 190))
        r.screen.blit(shade, (0, 0))
        box = pygame.Rect(448, 300, 544, 270)
        pygame.draw.rect(r.screen, PANEL, box, border_radius=8)
        pygame.draw.rect(r.screen, GOLD, box, 1, border_radius=8)
        r.text("ARE YOU SURE?", 720, 321, 25, WHITE, serif=True, center=True)
        if self.pending_sale_rank is not None:
            detail = f"Sell all {len(items)} backpack items of Rank {self.pending_sale_rank}?"
        else:
            item = items[0]
            detail = f"Sell Rank {item.rank} {item.name}?"
        r.text(detail, 720, 368, 15, WHITE, center=True)
        r.text(f"You will receive {total:,} gold.", 720, 402, 16, GOLD, center=True)
        r.text("Equipped items are kept. This sale cannot be undone.", 720, 435, 12, MUTED, center=True)
        if upgrades:
            r.text(f"Includes {upgrades} upgrade{'s' if upgrades != 1 else ''} for your current equipment!",
                   720, 462, 11, UPGRADE, center=True)
        elif any(item.rank >= 3 for item in items):
            r.text("This sale includes Rank 3 or higher equipment.", 720, 462, 11, GOLD, center=True)
        self.button(r, self.cancel_destroy_rect, "CANCEL / ESC")
        self.button(r, self.confirm_destroy_rect, "CONFIRM SALE")
        pygame.draw.rect(r.screen, GOLD, self.confirm_destroy_rect, 1, border_radius=4)

    def draw_destroy_confirmation(self, r, world):
        item = world.player.inventory.get(self.pending_destroy_uid)
        if item is None:
            self.cancel_destroy()
            return
        shade = pygame.Surface(r.screen.get_size(), pygame.SRCALPHA)
        shade.fill((4, 9, 16, 180))
        r.screen.blit(shade, (0, 0))
        box = pygame.Rect(448, 300, 544, 270)
        pygame.draw.rect(r.screen, PANEL, box, border_radius=8)
        pygame.draw.rect(r.screen, RED, box, 1, border_radius=8)
        r.text("Destroy this item?", 720, 324, 25, WHITE, serif=True, center=True)
        r.text(item.name, 720, 370, 18, RANK_COLORS[item.rank], center=True)
        r.text(f"Rank {item.rank} · {item.slot.title()}", 720, 401, 12, MUTED, center=True)
        r.text("This permanently removes the item. No gold is received.", 720, 439, 12, WHITE, center=True)
        self.button(r, self.cancel_destroy_rect, "CANCEL / ESC")
        self.button(r, self.confirm_destroy_rect, "DESTROY ITEM")
        pygame.draw.rect(r.screen, RED, self.confirm_destroy_rect, 1, border_radius=4)

    def draw_stats(self, r, world):
        player = world.player
        stats = player.inventory.stats
        r.spaced("CHARACTER STATS", 916, 236, 10, MUTED)
        rows = [("Spell damage", f"+{stats.damage:.1%}"), ("Maximum health", str(player.max_hp)),
                ("Armor / hit", str(stats.armor)), ("Cooldown reduction", f"{stats.cooldown:.1%}"),
                ("Movement speed", f"{player.move_speed:.2f}"), ("Critical chance", f"{player.crit_chance:.1%}"),
                ("Critical damage", f"{player.crit_multiplier:.2f}×")]
        for i, (label, value) in enumerate(rows):
            yy = 272 + i * 39
            r.text(label, 916, yy, 12, MUTED)
            r.text(value, 1147, yy, 13, WHITE)
        r.text("Frostweave / Five-piece set", 916, 556, 15, ICE, serif=True)
        progress = f"Equipped: {stats.frostweave_pieces} / 5"
        if stats.frostweave_pieces == 5:
            progress += f" · Lowest rank {stats.frostweave_rank}"
        r.text(progress, 916, 585, 11, MUTED)
        if stats.frostweave_freeze_chance:
            r.text(f"Frost Bolt: {stats.frostweave_freeze_chance:.0%} freeze / {FROSTWEAVE_FREEZE:g}s",
                   916, 609, 11, UPGRADE)
        else:
            r.text("Equip all five pieces at Rank 3+.", 916, 609, 11, MUTED)
        r.text("R3: 15%  /  R4: 25%  /  R5: 40%", 916, 636, 10, ICE)
        r.text("R5: Ice Patch + Prison Cataclysm (see R)", 916, 658, 10, ICE)

    def draw_enchanter(self, r, world, mouse):
        item = self.enchant_target(world)
        hover = self.dragging and mouse and self.enchant_slot_rect.collidepoint(mouse)
        r.spaced("ENCHANTING SLOT", 917, 236, 10, ICE)
        pygame.draw.rect(r.screen, (27, 53, 70) if hover else (22, 35, 47), self.enchant_slot_rect, border_radius=6)
        pygame.draw.rect(r.screen, ICE if hover or item else LINE, self.enchant_slot_rect, 2, border_radius=6)
        if item is None:
            r.text("DROP EQUIPMENT HERE", 1061, 284, 14, ICE, center=True)
            r.text("Worn gear or backpack items", 1061, 313, 11, MUTED, center=True)
        else:
            item_icon(r.screen, item.slot, (947, 306), RANK_COLORS[item.rank], .65, item=item)
            r.text(item.name, 980, 282, 13, RANK_COLORS[item.rank], serif=True)
            r.text(f"Rank {item.rank} / {RANK_NAMES[item.rank]}", 980, 311, 11, MUTED)
        self.button(r, self.load_selected_rect, "PLACE SELECTED ITEM", enabled=self.selected(world) is not None)
        self.button(r, self.clear_enchant_rect, "CLEAR SLOT", enabled=item is not None)
        r.text("Frostweave only: R4 / R5", 1030, 646, 9, GOLD)
        if item is None:
            r.text("Drag gear here, then choose Enchant.", 917, 425, 11, MUTED)
            r.text("Placing an item does not spend gold.", 917, 450, 11, MUTED)
            self.button(r, self.upgrade_rect, "ENCHANT / NO ITEM", enabled=False)
            return
        for i, line in enumerate(item.lines):
            r.text(line, 917, 412 + i * 19, 10, WHITE)
        if item.next_cost is not None:
            if not item.set_id and world.player.unlocked_level < {1: 1, 2: 3, 3: 5}[item.rank + 1]:
                r.text("Reach floor 3 for R2 / floor 5 for R3", 917, 552, 10, GOLD)
            next_item = replace(item, rank=item.rank + 1)
            r.text(f"NEXT: RANK {next_item.rank}", 917, 478, 12, RANK_COLORS[next_item.rank])
            for i, line in enumerate(next_item.lines):
                r.text(line, 917, 503 + i * 19, 10, WHITE)
            self.button(r, self.upgrade_rect, f"ENCHANT  ·  {item.next_cost:,} GOLD",
                        enabled=world.player.gold >= item.next_cost and (item.set_id is not None or world.player.unlocked_level >= {1: 1, 2: 3, 3: 5}[item.rank + 1]) and world.state != "dead" and world.player.stasis <= 0)
        else:
            r.text(f"RANK {item.max_rank} · MAXIMUM", 917, 493, 14, GOLD)
            self.button(r, self.upgrade_rect, "MAXIMUM RANK", enabled=False)
