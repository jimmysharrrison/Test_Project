"""Title screen, instructions, pause navigation, and reached-level selection."""

from dataclasses import dataclass

import pygame

from .levels import FOCUS_FLOORS, MOTTO, PHASE_SPEEDS, PLAYABLE_FLOORS, TOWER_FLOORS, floor_name

FRONTEND_MODES = {"title", "levels", "howto", "confirm_new", "tutorial_offer", "story", "journal", "achievements",
                  "save_slots", "load_slots", "confirm_overwrite", "confirm_load"}


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
        self.save_enabled = False
        self.save_slots = []
        self.active_slot = None
        self.pending_slot = None
        self.can_resume = False

    @staticmethod
    def level_count(world):
        return PLAYABLE_FLOORS

    def buttons(self, world, mode):
        if mode == "title":
            return [Button(action, label, pygame.Rect(800, 278 + i * 62, 340, 48), enabled)
                    for i, (action, label, enabled) in enumerate((
                        ("start", "New Game", True),
                        ("load_game", "Load Game", any(row["occupied"] for row in self.save_slots)),
                        ("levels", "Level Select", True),
                        ("howto", "How to Play", True),
                        ("story", "The Story", True),
                        ("quit", "Quit", True),
                    ))] + [Button("save_game", "Save Game", pygame.Rect(800, 660, 340, 38), self.save_enabled and self.has_character),
                           Button("resume", "Resume Current Game", pygame.Rect(310, 660, 340, 44), self.can_resume),
                           Button("codex", "Codex", pygame.Rect(800, 735, 160, 38)), Button("achievements", "Achievements", pygame.Rect(974, 735, 166, 38)), Button("tutorial", "Tutorial / Drearamore Practice", pygame.Rect(310, 725, 340, 48))]
        if mode in ("save_slots", "load_slots"):
            rows = self.save_slots or [{"slot": i, "occupied": False, "valid": False, "label": "Empty", "detail": ""} for i in range(1, 5)]
            action = "save_slot" if mode == "save_slots" else "load_slot"
            return [Button(f"{action}:{row['slot']}", f"Slot {row['slot']} / {row['label']}" + (" / Current" if row['slot'] == self.active_slot else ""),
                           pygame.Rect(336, 265 + i * 91, 768, 74),
                           self.save_enabled if mode == "save_slots" else row["valid"])
                    for i, row in enumerate(rows)] + [Button("slots_back", "Back", pygame.Rect(552, 728, 336, 46))]
        if mode in ("confirm_overwrite", "confirm_load"):
            return [Button("cancel_slot", "Cancel", pygame.Rect(370, 530, 310, 48)),
                    Button("overwrite_slot" if mode == "confirm_overwrite" else "confirm_load_slot",
                           "Overwrite Save" if mode == "confirm_overwrite" else "Load Game", pygame.Rect(760, 530, 310, 48))]
        if mode == "tutorial_offer":
            return [Button("learn_first", "Play Tutorial", pygame.Rect(370, 530, 310, 48)),
                    Button("skip_tutorial", "Skip / Start Game", pygame.Rect(760, 530, 310, 48))]
        if mode == "confirm_new":
            return [Button("cancel_new", "Keep Current Game", pygame.Rect(370, 530, 310, 48)),
                    Button("confirm_new", "Start Over at Level 1", pygame.Rect(760, 530, 310, 48))]
        if mode in ("howto", "story", "journal", "achievements"):
            return [Button("back", "Back", pygame.Rect(552, 728, 336, 46))]
        if mode == "paused":
            return [Button("codex", "Codex", pygame.Rect(669, 414, 366, 38)), Button("resume", "Resume", pygame.Rect(669, 529, 366, 51)),
                    Button("howto", "How to Play", pygame.Rect(669, 465, 366, 44)),
                    Button("main_menu", "Main Menu", pygame.Rect(669, 592, 366, 44)),
                    Button("save_game", "Save Game", pygame.Rect(493, 465, 164, 44), self.save_enabled),
                    Button("load_game", "Load Game", pygame.Rect(1047, 465, 164, 44), any(row["occupied"] for row in self.save_slots))]
        if mode == "levels":
            total = self.level_count(world)
            self.page = min(self.page, (total - 1) // 6)
            rows = []
            for i, level in enumerate(range(self.page * 6 + 1, min(total, self.page * 6 + 6) + 1)):
                name = floor_name(level)
                available = level <= min(world.player.unlocked_level, PLAYABLE_FLOORS)
                status = "PLAY" if available else "COMING LATER" if level > PLAYABLE_FLOORS else "LOCKED"
                rows.append(Button(f"level:{level}", f"{level:02d}    {name}    /    {status}",
                                   pygame.Rect(336, 256 + i * 68, 768, 54),
                                   available))
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
            if mode in ("save_slots", "load_slots") and ":" in button.action:
                row = self.save_slots[int(button.action.split(":")[1]) - 1] if self.save_slots else None
                if row and row["detail"]:
                    renderer.text(row["detail"], button.rect.centerx, button.rect.y + 46, 12, (145, 164, 174), center=True)

    def background(self, renderer):
        renderer.screen.fill((9, 15, 22))
        # A distant tower frames the title rather than an outdoor forest border.
        for x in (70, 1250):
            pygame.draw.polygon(renderer.screen, (19, 28, 39),
                                [(x, 810), (x + 25, 240), (x + 60, 155), (x + 95, 240), (x + 120, 810)])
            for y in range(280, 750, 70):
                pygame.draw.rect(renderer.screen, (45, 67, 85), (x + 49, y, 22, 33), 1, border_radius=8)
        renderer.glow(720, 420, (69, 132, 172), 330, 30)
        renderer.text("FROST MAGE", 720, 48, 48, (218, 233, 242), serif=True, center=True)
        renderer.text("THE TOWER", 720, 112, 13, (139, 216, 248), center=True)
        renderer.character_portrait((488, 79), 60)
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
            renderer.character_portrait((852, 281), 44, world.player)
            renderer.text("The Tower can wait.", 852, 315, 34, white, serif=True, center=True)
            renderer.text("Your adventure is paused.", 852, 381, 15, muted, center=True)
            if self.notice:
                renderer.text(self.notice, 852, 648, 12, ice, center=True)
        else:
            self.background(renderer)
        if mode == "title":
            pygame.draw.line(renderer.screen, (44, 64, 79), (728, 208), (728, 730))
            renderer.text("WINTER HAS A CHAMPION", 480, 223, 13, ice, center=True)
            renderer.glow(480, 410, ice, 130, 43)
            pygame.draw.circle(renderer.screen, (47, 75, 95), (480, 414), 118, 1)
            renderer.character_portrait((480, 414), 236, world.player)
            renderer.text("A Nameless Wanderer", 480, 551, 29, white, serif=True, center=True)
            renderer.text("Trained at Drearamore. Drawn to The Tower.", 480, 604, 13, muted, center=True)
            renderer.text(MOTTO, 480, 641, 17, ice, serif=True, center=True)
            renderer.text("YOUR ASCENT", 970, 223, 13, ice, center=True)
            label = f"Active: Slot {self.active_slot}" if self.active_slot else "New game / choose a slot to save"
            renderer.text(label if self.has_character else "Four save slots / start a new adventure", 970, 708, 12, muted, center=True)
        elif mode in ("save_slots", "load_slots"):
            renderer.text("Save Game" if mode == "save_slots" else "Load Game", 720, 190, 30, white, serif=True, center=True)
            renderer.text("Choose one of four slots. Existing saves require overwrite confirmation." if mode == "save_slots" else
                          "Choose a saved adventure. Empty or unreadable slots cannot be loaded.", 720, 235, 14, muted, center=True)
            renderer.text("Use Save Game to update a slot. New games leave your saved adventures intact." if mode == "save_slots" else
                          "Loading restores the saved encounter, health, equipment, and progress.", 720, 667, 13, ice, center=True)
        elif mode in ("confirm_overwrite", "confirm_load"):
            renderer.text(f"Overwrite Slot {self.pending_slot}?" if mode == "confirm_overwrite" else f"Load Slot {self.pending_slot}?",
                          720, 270, 35, white, serif=True, center=True)
            row = next((r for r in self.save_slots if r["slot"] == self.pending_slot), None)
            if row:
                renderer.text(f"Slot {self.pending_slot}: {row['label']}", 720, 353, 18, ice, center=True)
            renderer.text("This replaces the saved adventure in this slot." if mode == "confirm_overwrite" else
                          "This leaves the current adventure. Progress without a save slot will be lost.",
                          720, 401, 15, muted, center=True)
            renderer.text("Cancel returns without changing your game or any save file.", 720, 434, 14, muted, center=True)
        elif mode == "achievements":
            from .achievements import DEFINITIONS
            renderer.text("Achievements / Cosmetic Badges", 720, 195, 29, white, center=True)
            for i, (key, definition) in enumerate(DEFINITIONS.items()):
                y = 290 + i * 120
                date = world.player.achievements.get(key)
                pygame.draw.circle(renderer.screen, ice if date else muted, (310, y + 20), 25, 3)
                renderer.text("*" if date else "?", 310, y + 7, 22, ice, center=True)
                renderer.text(definition["title"], 360, y, 22, white)
                renderer.text(definition["description"], 360, y + 34, 12, muted)
                renderer.text(f"Unlocked: {date[:10]} (UTC)" if date else "Locked", 360, y + 60, 14, ice)
        elif mode == "levels":
            renderer.text(f"The Tower / {PLAYABLE_FLOORS} Playable Floors", 720, 188, 29, white, serif=True, center=True)
            renderer.text("Twenty stories rise above you. Reach a floor to unlock it; replays keep your gear.",
                          720, 229, 13, muted, center=True)
            renderer.text(f"Page {self.page + 1} / {(self.level_count(world) + 5) // 6}", 720, 696, 12, muted, center=True)
        elif mode == "tutorial_offer":
            renderer.text("Remember your training?", 720, 270, 35, white, serif=True, center=True)
            renderer.text("Practice movement, every spell, healing, and equipping gear at Drearamore.",
                          720, 353, 16, ice, center=True)
            renderer.text("A safe, separate practice character. Skip now or replay Tutorial from the main menu.",
                          720, 401, 14, muted, center=True)
        elif mode == "confirm_new":
            renderer.text("Begin a new ascent?", 720, 270, 35, white, serif=True, center=True)
            renderer.text("Start on the ground floor with a fresh Frost Mage.", 720, 353, 18, ice, center=True)
            renderer.text("Saved slots are kept. Progress without a save slot will be lost.",
                          720, 401, 15, muted, center=True)
            renderer.text("Choose Keep Current Game to return without changing anything.",
                          720, 434, 14, muted, center=True)
        elif mode == "howto":
            self.instructions(renderer)
        elif mode == "story":
            self.story(renderer)
        elif mode == "journal":
            self.journal(renderer, world)
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
        spells = (("Q", "Frost Bolt", "Hold Q to fire. Damages and slows enemies."),
                  ("W", "Frost Nova", "Freeze nearby enemies and stop their attacks."),
                  ("E", "Ice Patch", "Slow enemy movement and attacks; stand inside for +30% frost."),
                  ("R", "Glacial Prison", "Become immune, then shatter for area damage."))
        for i, (key, name, detail) in enumerate(spells):
            y = 389 + i * 65
            renderer.key(key, 282, y, 29)
            renderer.text(name, 325, y - 1, 16, ice)
            renderer.text(detail, 282, y + 28, 11, muted)
        pygame.draw.line(renderer.screen, (44, 64, 79), (720, 253), (720, 687))
        renderer.text("SURVIVE & PROGRESS", 764, 251, 13, ice)
        for i, line in enumerate(("1: healing potion. I: inventory. B: shop.",
                                  "Escape pauses. J opens the floor journal. M: sound.",
                                  "Click spell buttons if you prefer using the mouse.",
                                  "For Q / E, click the spell, then click a target.",
                                  "Right click or Escape cancels a targeted spell.")):
            renderer.text(line, 764, 286 + i * 25, 11, white)
        renderer.text("THREE PHASES PER FLOOR", 764, 446, 13, ice)
        for i, line in enumerate(("Floors 1-3: two waves, then a mini-boss. Menagerie: 2/3/4 devices.",
                                  "Three-second intermissions. Floor 5 is the Keeper boss encounter.",
                                  "New mobs move 15% / 30% faster in phases 2 / 3.",
                                  "Defeat bosses and companions; ordinary survivors are optional.",
                                  "Reach the portal, then press Enter to climb.",
                                  "Each floor unlocks on arrival. Health and mana refill.")):
            renderer.text(line, 764, 483 + i * 25, 11, white)
        renderer.text("Dodge archer aim lines. Freeze interrupts their shots.", 764, 646, 11, muted)
        renderer.text("Low health turns the screen edges red. Heal to recover.", 764, 671, 11, muted)

    @staticmethod
    def paragraph(renderer, text, y, width=860, size=14, color=(185, 201, 210)):
        line = ""
        for word in text.split():
            candidate = (line + " " + word).strip()
            if renderer.font(size).size(candidate)[0] > width:
                renderer.text(line, 282, y, size, color)
                y += size + 11
                line = word
            else:
                line = candidate
        renderer.text(line, 282, y, size, color)
        return y + size + 11

    def story(self, renderer):
        renderer.text("At the Foot of The Tower", 720, 190, 30, (232, 230, 217), serif=True, center=True)
        y = 265
        for text in (
            "She is a Frost Mage, a wanderer with no name yet spoken. Her road began at Drearamore, "
            "a college devoted to the elemental arts. Its motto remains with her: elementis fidelis est.",
            "Now she stands before The Tower. Twenty stories rise beyond its doors. Worn stone and "
            "four great pillars guard the ground floor; above them, the gardens of Thornveil grow beneath glass.",
            "Higher still, a wizard's helper fairies have spilled the alchemist's potions. The helpers have "
            "lost their senses, and the enchanted objects around them are waking up. Something is wrong here.",
            "Each opening floor has two spawner phases and a final mini-boss encounter. The fifth floor belongs to the lower tower's furious caretaker, the Keeper. Each new phase sends "
            "swifter creatures into her path. Only when the final seals fall will The Tower allow her to climb.",
        ):
            y = self.paragraph(renderer, text, y) + 23
        renderer.text(MOTTO, 720, 660, 20, (139, 216, 248), serif=True, center=True)

    def journal(self, renderer, world):
        renderer.text(world.level_data.name, 720, 190, 29, (232, 230, 217), serif=True, center=True)
        renderer.text(f"THE TOWER / FLOOR {world.level} OF {TOWER_FLOORS}", 720, 234, 12,
                      (139, 216, 248), center=True)
        self.paragraph(renderer, world.level_data.story, 280)
        for i, text in enumerate(world.level_data.phase_lines):
            y = 412 + i * 85
            tag = "CURRENT" if world.phase == i + 1 else ""
            encounter = "HEALTH STAGE" if world.keeper else "BOSS ENCOUNTER" if i == 2 and not world.level_data.menagerie else f"{world.level_data.phase_counts[i]} SPAWNERS"
            label = (f"STAGE {i + 1} / {('100-67', '67-33', '33-0')[i]}% HEALTH / AT MOST TWO DUTIES  {tag}"
                     if world.keeper else f"PHASE {i + 1} / {encounter} / {PHASE_SPEEDS[i]:.0%} MOB SPEED  {tag}")
            renderer.text(label,
                          282, y, 12, (139, 216, 248))
            self.paragraph(renderer, text, y + 29, size=12)
        footer = ("The Devourer stays fixed. Run outward before gravity activates; control the summons. R resists the pull." if world.level == 10 else
                  "Safe practice teaches R. Each Stopped Hour restores a reserved cast. Failure returns to the boss checkpoint." if world.level == 9 else
                  "Break the seals, defeat the Oracle, and climb to the observatory. R is optional." if world.level == 7 else
                  "Break the foci and defeat the Astronomer. React to the arrows; R resists gravity." if world.level == 8 else
                  "Defeat the Keeper to reach Broken Containment on floor 6." if world.keeper else
                  "Break five binding circles, then defeat the Voidwalker. Darkness expires; R is optional." if world.void else
                  "Break nine containment devices. Take time to collect your loot." if world.level_data.menagerie else
                  "Break five spawners and defeat the boss and its companions. Collect loot before entering the portal.")
        renderer.text(footer,
                      720, 685, 12, (145, 164, 174), center=True)
