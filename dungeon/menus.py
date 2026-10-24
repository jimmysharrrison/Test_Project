"""Title screen, instructions, pause navigation, and reached-level selection."""

from dataclasses import dataclass

import pygame

from .levels import level_for_depth

FRONTEND_MODES = {"title", "levels", "howto", "confirm_new"}


@dataclass(frozen=True, slots=True)
class Button:
    action: str
    label: str
    rect: pygame.Rect
    enabled: bool = True


class Menus:
    def __init__(self):
        self.has_character = False
        self.page = 0
        self.focus = {}
        self.notice = ""

    @staticmethod
    def level_count(world):
        # Show the next locked destination as well as every reached depth.
        return max(2, world.player.unlocked_level + 1)

    def buttons(self, world, mode):
        if mode == "title":
            return [Button(action, label, pygame.Rect(800, 278 + i * 62, 340, 48), enabled)
                    for i, (action, label, enabled) in enumerate((
                        ("start", "Start Game", True),
                        ("continue", "Continue", self.has_character),
                        ("levels", "Level Select", True),
                        ("howto", "How to Play", True),
                        ("quit", "Quit", True),
                    ))]
        if mode == "confirm_new":
            return [Button("cancel_new", "Keep Current Game", pygame.Rect(370, 530, 310, 48)),
                    Button("confirm_new", "Start Over at Level 1", pygame.Rect(760, 530, 310, 48))]
        if mode == "howto":
            return [Button("back", "Back", pygame.Rect(552, 728, 336, 46))]
        if mode == "paused":
            return [Button("resume", "Resume", pygame.Rect(669, 529, 366, 51)),
                    Button("howto", "How to Play", pygame.Rect(669, 465, 366, 44)),
                    Button("main_menu", "Main Menu", pygame.Rect(669, 592, 366, 44))]
        if mode == "levels":
            total = self.level_count(world)
            self.page = min(self.page, (total - 1) // 6)
            rows = []
            for i, level in enumerate(range(self.page * 6 + 1, min(total, self.page * 6 + 6) + 1)):
                name = level_for_depth(level).name
                status = "PLAY" if level <= world.player.unlocked_level else "LOCKED"
                rows.append(Button(f"level:{level}", f"{level:02d}    {name}    /    {status}",
                                   pygame.Rect(336, 256 + i * 68, 768, 54),
                                   level <= world.player.unlocked_level))
            return rows + [
                Button("previous", "Previous", pygame.Rect(336, 728, 190, 44), self.page > 0),
                Button("back", "Main Menu", pygame.Rect(570, 728, 300, 44)),
                Button("next", "Next", pygame.Rect(914, 728, 190, 44), (self.page + 1) * 6 < total),
            ]
        return []

    def click(self, world, mode, point):
        return next((b.action for b in self.buttons(world, mode)
                     if b.enabled and b.rect.collidepoint(point)), None)

    def activate(self, world, mode):
        enabled = [b for b in self.buttons(world, mode) if b.enabled]
        if not enabled:
            return None
        return next((b.action for b in enabled if b.action == self.focus.get(mode)), enabled[0].action)

    def move_focus(self, world, mode, delta):
        actions = [b.action for b in self.buttons(world, mode) if b.enabled]
        if actions:
            current = self.focus.get(mode)
            index = actions.index(current) if current in actions else 0
            self.focus[mode] = actions[(index + delta) % len(actions)]

    def draw_buttons(self, renderer, world, mode, mouse):
        active = self.activate(world, mode)
        for button in self.buttons(world, mode):
            hover = mouse is not None and button.rect.collidepoint(mouse)
            focused = active == button.action
            fill = (39, 66, 82) if button.enabled and (hover or focused) else (24, 36, 46)
            edge = (139, 216, 248) if button.enabled and (hover or focused) else (57, 77, 91)
            color = (230, 234, 225) if button.enabled else (94, 107, 116)
            pygame.draw.rect(renderer.screen, fill, button.rect, border_radius=5)
            pygame.draw.rect(renderer.screen, edge, button.rect, 1, border_radius=5)
            renderer.text(button.label, button.rect.centerx, button.rect.y + 13,
                          15, color, center=True)

    def background(self, renderer):
        renderer.screen.fill((9, 15, 22))
        for x, y, size in ((90, 740, 310), (218, 580, 210), (1235, 590, 260), (1370, 780, 350)):
            renderer.pine(x, y, size)
        renderer.glow(720, 420, (69, 132, 172), 330, 30)
        renderer.text("EMBERVAULT", 720, 48, 48, (218, 233, 242), serif=True, center=True)
        renderer.text("THE FROZEN DESCENT", 720, 112, 13, (139, 216, 248), center=True)
        pygame.draw.rect(renderer.screen, (17, 26, 35), (236, 164, 968, 642), border_radius=14)
        pygame.draw.rect(renderer.screen, (57, 77, 91), (236, 164, 968, 642), 1, border_radius=14)

    def draw(self, renderer, world, mouse, mode):
        white, muted, ice = (232, 230, 217), (145, 164, 174), (139, 216, 248)
        if mode == "paused":
            veil = pygame.Surface(renderer.screen.get_size(), pygame.SRCALPHA)
            veil.fill((5, 10, 16, 182))
            renderer.screen.blit(veil, (0, 0))
            pygame.draw.rect(renderer.screen, (20, 29, 36), (477, 254, 750, 416), border_radius=12)
            pygame.draw.rect(renderer.screen, (57, 77, 91), (477, 254, 750, 416), 1, border_radius=12)
            renderer.text("The descent can wait.", 852, 315, 34, white, serif=True, center=True)
            renderer.text("Your adventure is paused.", 852, 381, 15, muted, center=True)
        else:
            self.background(renderer)
        if mode == "title":
            pygame.draw.line(renderer.screen, (44, 64, 79), (728, 208), (728, 730))
            renderer.text("WINTER HAS A CHAMPION", 480, 223, 13, ice, center=True)
            renderer.glow(480, 410, ice, 130, 43)
            pygame.draw.circle(renderer.screen, (47, 75, 95), (480, 414), 118, 1)
            renderer.player(world.player, 0, (480, 504), 3.8)
            renderer.text("The Ice Mage", 480, 551, 31, white, serif=True, center=True)
            renderer.text("A frozen oath. A forest worth saving.", 480, 604, 14, muted, center=True)
            renderer.text("Move with the mouse. Master the cold.", 480, 634, 13, muted, center=True)
            renderer.text("YOUR DESCENT", 970, 223, 13, ice, center=True)
            if self.has_character:
                renderer.text(f"Continue: Level {world.player.current_level} · {world.level_data.name}",
                              970, 607, 12, muted, center=True)
            else:
                renderer.text("Start Game begins at level 1.", 970, 607, 13, muted, center=True)
            renderer.text("Start Game creates a fresh character.", 970, 637, 12, muted, center=True)
            renderer.text("Level Select keeps your equipment and gold.", 970, 660, 12, muted, center=True)
        elif mode == "levels":
            renderer.text("Choose your destination", 720, 188, 29, white, serif=True, center=True)
            renderer.text("Reach a level through its portal to unlock it. Replays keep your gear and gold.",
                          720, 229, 13, muted, center=True)
            renderer.text(f"Page {self.page + 1} / {(self.level_count(world) + 5) // 6}", 720, 696, 12, muted, center=True)
        elif mode == "confirm_new":
            renderer.text("Begin a new descent?", 720, 270, 35, white, serif=True, center=True)
            renderer.text("Start over at level 1 with a fresh Ice Mage.", 720, 353, 18, ice, center=True)
            renderer.text("This replaces your saved character, equipment, gold, and level unlocks.",
                          720, 401, 15, muted, center=True)
            renderer.text("Choose Keep Current Game to return without changing anything.",
                          720, 434, 14, muted, center=True)
        elif mode == "howto":
            self.instructions(renderer)
        self.draw_buttons(renderer, world, mode, mouse)
        if mode != "paused":
            renderer.text("Click a button or use ↑ / ↓ and Enter. Escape goes back. M toggles sound.",
                          720, 839, 12, muted, center=True)
            notice = self.notice or renderer.profile_notice
            if notice:
                renderer.text(notice, 720, 781, 11, (214, 180, 113), center=True)

    @staticmethod
    def instructions(renderer):
        white, muted, ice = (232, 230, 217), (145, 164, 174), (139, 216, 248)
        renderer.text("How to Play", 720, 190, 30, white, serif=True, center=True)
        renderer.text("MOVE & TARGET", 282, 251, 13, ice)
        for i, line in enumerate(("Right click ground to move; hold to follow the cursor.",
                                  "Left click an enemy to inspect health and effects.",
                                  "Aim skill shots with the mouse. S stops movement.")):
            renderer.text(line, 282, 286 + i * 25, 12, white)
        spells = (("Q", "Ice Bolt", "Hold Q to fire. Damages and slows enemies."),
                  ("W", "Frost Nova", "Freeze nearby enemies and stop their attacks."),
                  ("E", "Ice Wall", "Block enemies and arrows with a temporary wall."),
                  ("R", "Glacial Prison", "Become immune, then shatter for area damage."))
        for i, (key, name, detail) in enumerate(spells):
            y = 389 + i * 65
            renderer.key(key, 282, y, 29)
            renderer.text(name, 325, y - 1, 16, ice)
            renderer.text(detail, 282, y + 28, 11, muted)
        pygame.draw.line(renderer.screen, (44, 64, 79), (720, 253), (720, 687))
        renderer.text("SURVIVE & PROGRESS", 764, 251, 13, ice)
        for i, line in enumerate(("1: healing potion. I: inventory. B: shop.",
                                  "Escape pauses. M toggles sound.",
                                  "Click spell buttons if you prefer using the mouse.",
                                  "For Q / E, click the spell, then click a target.",
                                  "Right click or Escape cancels a targeted spell.")):
            renderer.text(line, 764, 286 + i * 25, 11, white)
        renderer.text("OPEN THE PORTAL", 764, 446, 13, ice)
        for i, line in enumerate(("Destroy all three spawners to open the portal.",
                                  "Surviving monsters are optional and still dangerous.",
                                  "Reach the portal and press Enter for the next level.",
                                  "Gear and gold carry over; health and mana refill.",
                                  "Each level unlocks when you enter it for the first time.")):
            renderer.text(line, 764, 483 + i * 27, 11, white)
        renderer.text("Dodge archer aim lines. Freeze interrupts their shots.", 764, 646, 11, muted)
        renderer.text("Low health turns the screen edges red. Heal to recover.", 764, 671, 11, muted)
