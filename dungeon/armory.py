"""Equipment inventory, hover details, and the gold-based enchanter interface."""

from dataclasses import replace

import pygame

from .items import BLANK_COST, ENCHANT_COST, Item, NAMES, RANK_COLORS, RANK_NAMES, SLOTS, SLOT_PURPOSE

PANEL = (19, 29, 40)
LINE = (55, 77, 94)
WHITE = (232, 230, 217)
MUTED = (137, 157, 172)
ICE = (139, 216, 248)
GOLD = (214, 180, 113)
RED = (215, 96, 99)


def item_icon(surface, slot, center, color, scale=1):
    x, y = center
    def p(dx, dy):
        return round(x + dx * scale), round(y + dy * scale)
    def poly(points):
        pygame.draw.polygon(surface, color, [p(dx, dy) for dx, dy in points], max(1, round(scale)))
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
        self.page = 0
        self.close_rect = pygame.Rect(1184, 104, 38, 32)
        self.inventory_tab = pygame.Rect(222, 174, 174, 34)
        self.shop_tab = pygame.Rect(410, 174, 190, 34)
        self.slot_rects = {slot: pygame.Rect(222, 265 + i * 75, 255, 66) for i, slot in enumerate(SLOTS)}
        self.bag_rects = [pygame.Rect(511 + (i % 4) * 87, 265 + (i // 4) * 87, 76, 76) for i in range(16)]
        self.previous_page = pygame.Rect(511, 630, 37, 30)
        self.next_page = pygame.Rect(811, 630, 37, 30)
        self.equip_rect = pygame.Rect(697, 740, 173, 34)
        self.sell_rect = pygame.Rect(511, 740, 93, 34)
        self.destroy_rect = pygame.Rect(612, 740, 77, 34)
        self.cancel_destroy_rect = pygame.Rect(490, 495, 210, 38)
        self.confirm_destroy_rect = pygame.Rect(720, 495, 230, 38)
        self.enchant_tab_rect = pygame.Rect(888, 740, 314, 34)
        self.buy_rects = {slot: pygame.Rect(729, 278 + i * 70, 143, 34) for i, slot in enumerate(SLOTS)}
        self.upgrade_rect = pygame.Rect(917, 575, 288, 45)

    def selected(self, world):
        return world.player.inventory.get(self.selected_uid)

    def bag_page(self, world):
        bag = world.player.inventory.backpack
        self.page = min(self.page, max(0, (len(bag) - 1) // 16))
        return bag[self.page * 16:(self.page + 1) * 16]

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
        if self.close_rect.collidepoint(point):
            return "close"
        if self.inventory_tab.collidepoint(point):
            return "inventory"
        if self.shop_tab.collidepoint(point):
            return "shop"
        item = self.selected(world)
        if self.sell_rect.collidepoint(point):
            if item and world.sell_item(item.uid):
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
        for slot, rect in self.slot_rects.items():
            if rect.collidepoint(point):
                item = inventory.worn(slot)
                self.selected_uid = item.uid if item else None
                return tab
        if tab == "inventory":
            for item, rect in zip(self.bag_page(world), self.bag_rects):
                if rect.collidepoint(point):
                    self.selected_uid = item.uid
                    return tab
            if self.previous_page.collidepoint(point):
                self.page = max(0, self.page - 1)
            elif self.next_page.collidepoint(point):
                self.page = min(max(0, (len(inventory.backpack) - 1) // 16), self.page + 1)
            elif self.enchant_tab_rect.collidepoint(point):
                return "shop"
        elif tab == "shop":
            for slot, rect in self.buy_rects.items():
                if rect.collidepoint(point):
                    item = world.buy_item(slot)
                    if item:
                        self.selected_uid = item.uid
                    return tab
            if self.upgrade_rect.collidepoint(point) and self.selected(world):
                world.enchant_item(self.selected_uid)
        return tab

    def cancel_destroy(self):
        pending = self.pending_destroy_uid is not None
        self.pending_destroy_uid = None
        return pending

    @staticmethod
    def button(r, rect, label, enabled=True, active=False):
        pygame.draw.rect(r.screen, (33, 61, 80) if active else (28, 43, 56), rect, border_radius=4)
        pygame.draw.rect(r.screen, ICE if active else LINE, rect, 1, border_radius=4)
        r.text(label, rect.centerx, rect.y + (rect.height - 16) // 2, 12,
               WHITE if enabled else MUTED, center=True)

    @staticmethod
    def tooltip(r, item, point, owned=False, current=None):
        lines = item.lines
        height = 198 + max(0, len(lines) - 1) * 21 + (35 if current and current.uid != item.uid else 0)
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
        if current and current.uid != item.uid:
            r.text(f"Equipped: Rank {current.rank} {current.name}", x + 14, yy, 10, MUTED)
            yy += 28
        detail = "Maximum enchantment reached" if item.next_cost is None else f"Next enchantment: {item.next_cost:,} gold"
        r.text(detail, x + 14, yy, 11, GOLD)
        r.text(f"Sell value: {item.sell_value:,} gold", x + 14, yy + 22, 11, GOLD)
        if item.slot == "boots":
            note = "Rare drop · first-level clear reward"
        elif item.rank <= 3 and item.rank > 0:
            note = "Rank 3 is the best dropped rank"
        else:
            note = "Ranks 4–5 are enchantment-only"
        r.text(note, x + 14, yy + 45, 10, MUTED)
        r.text("Owned equipment" if owned else "Walk over loot to collect it" if item.source == "drop" else "Unranked shop stock", x + 14, yy + 65, 9, MUTED)

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
            item_icon(r.screen, slot, (rect.x + 31, rect.centery), color if item else MUTED, .7)
            r.text(slot.title(), rect.x + 61, rect.y + 9, 12, MUTED)
            r.text(f"Rank {item.rank} · {RANK_NAMES[item.rank]}" if item else "Empty slot", rect.x + 61, rect.y + 34, 13, color if item else MUTED)
            if mouse and rect.collidepoint(mouse):
                hovered = item if item else slot
        item = self.selected(world)
        if tab == "inventory":
            r.spaced(f"BACKPACK  /  {len(inventory.backpack)} ITEMS", 511, 236, 10, MUTED)
            page_items = self.bag_page(world)
            for i, rect in enumerate(self.bag_rects):
                bag_item = page_items[i] if i < len(page_items) else None
                selected = bag_item and bag_item.uid == self.selected_uid
                pygame.draw.rect(r.screen, (28, 48, 62) if selected else (22, 35, 47), rect, border_radius=5)
                pygame.draw.rect(r.screen, ICE if selected else RANK_COLORS[bag_item.rank] if bag_item else LINE, rect, 1, border_radius=5)
                if bag_item:
                    item_icon(r.screen, bag_item.slot, (rect.centerx, rect.y + 30), RANK_COLORS[bag_item.rank], .8)
                    r.text(f"R{bag_item.rank}", rect.x + 9, rect.y + 55, 11, RANK_COLORS[bag_item.rank])
                    if mouse and rect.collidepoint(mouse):
                        hovered = bag_item
            self.button(r, self.previous_page, "<")
            self.button(r, self.next_page, ">")
            total_pages = max(1, (len(inventory.backpack) + 15) // 16)
            r.text(f"PAGE {self.page + 1} / {total_pages}", 680, 640, 11, MUTED, center=True)
            self.draw_stats(r, world)
        else:
            r.spaced("UNRANKED STOCK  /  RANK 0", 511, 236, 10, MUTED)
            for i, slot in enumerate(SLOTS):
                rect = pygame.Rect(511, 265 + i * 70, 374, 61)
                pygame.draw.rect(r.screen, (22, 35, 47), rect, border_radius=5)
                item_icon(r.screen, slot, (537, rect.centery), MUTED, .6)
                r.text(slot.title(), 565, rect.y + 8, 13, WHITE)
                r.text("Blank · no bonus", 565, rect.y + 33, 10, MUTED)
                self.button(r, self.buy_rects[slot], f"BUY {BLANK_COST[slot]:,} G", enabled=world.player.gold >= BLANK_COST[slot])
                if mouse and rect.collidepoint(mouse):
                    hovered = Item(1, slot, 0, "shop")
            r.text("Drops: Ranks 1–3. Enchant any owned item to Rank 5.", 511, 634, 10, MUTED)
            self.draw_enchanter(r, world, item)
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
            r.text("Select gear to enchant above.", 906, 751, 11, MUTED)
        r.text("New gear fills an empty slot automatically.", 222, 689, 10, MUTED)
        r.text("Chest health must be healed after equipping.", 222, 712, 10, MUTED)
        r.text("I inventory · B shop · Esc close", 222, 755, 10, MUTED)
        if isinstance(hovered, Item):
            owned = inventory.get(hovered.uid) is hovered
            current = inventory.worn(hovered.slot) if not owned or inventory.equipped[hovered.slot] != hovered.uid else None
            self.tooltip(r, hovered, mouse, owned, current)
        elif hovered:
            x, y = min(mouse[0] + 15, 1058), min(mouse[1] + 15, 744)
            pygame.draw.rect(r.screen, (13, 23, 33), (x, y, 368, 95), border_radius=5)
            r.text(hovered.title(), x + 12, y + 10, 17, ICE)
            r.text(SLOT_PURPOSE[hovered], x + 12, y + 44, 11, WHITE)
        if self.pending_destroy_uid is not None:
            self.draw_destroy_confirmation(r, world)

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
        rows = [("Spell damage", f"+{stats.damage:.0%}"), ("Maximum health", str(player.max_hp)),
                ("Armor / hit", str(stats.armor)), ("Cooldown reduction", f"{stats.cooldown:.0%}"),
                ("Movement speed", f"{player.move_speed:.2f}"), ("Critical chance", f"{player.crit_chance:.0%}"),
                ("Critical damage", f"{player.crit_multiplier:.2f}×")]
        for i, (label, value) in enumerate(rows):
            yy = 272 + i * 39
            r.text(label, 916, yy, 12, MUTED)
            r.text(value, 1147, yy, 13, WHITE)
        r.text("Everfrost Treads", 916, 568, 15, GOLD, serif=True)
        r.text("Rarest drop. Guaranteed Rank 1", 916, 600, 11, MUTED)
        r.text("reward for the first level clear.", 916, 622, 11, MUTED)

    def draw_enchanter(self, r, world, item):
        r.spaced("ENCHANT SELECTED ITEM", 917, 236, 10, MUTED)
        if item is None:
            r.text("Choose owned equipment.", 917, 277, 13, MUTED)
            r.text("Or purchase a blank to begin.", 917, 304, 11, MUTED)
            return
        r.text(item.name, 917, 271, 16, RANK_COLORS[item.rank], serif=True)
        r.text(f"RANK {item.rank}  /  {RANK_NAMES[item.rank].upper()}", 917, 304, 11, MUTED)
        for i, line in enumerate(item.lines):
            r.text(line, 917, 338 + i * 21, 10, WHITE)
        if item.rank < 5:
            next_item = replace(item, rank=item.rank + 1)
            r.text(f"NEXT: RANK {next_item.rank}", 917, 427, 12, RANK_COLORS[next_item.rank])
            for i, line in enumerate(next_item.lines):
                r.text(line, 917, 458 + i * 21, 10, WHITE)
            self.button(r, self.upgrade_rect, f"ENCHANT  ·  {item.next_cost:,} GOLD",
                        enabled=world.player.gold >= item.next_cost)
        else:
            r.text("MYTHIC · MAXIMUM RANK", 917, 447, 14, GOLD)
        r.text("R4: 2,500 G    R5: 15,000 G", 917, 643, 11, GOLD)
