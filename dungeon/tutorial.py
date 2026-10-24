"""Replayable Drearamore lessons using the real World and armory.

Only this disposable World suppresses encounters, enemy movement and damage.
The desktop keeps the suspended ascent separate and never saves this player.
"""

from dataclasses import replace

from .abilities import ABILITIES
from .geometry import Vec
from .items import Inventory
from .levels import FROSTFALL, room
from .world import Enemy, Pickup, World


LESSONS = (
    ("move", "A remembered lesson", (
        "Drearamore welcomes you back. Right click the gold ring to move there.",
        "Hold right click to follow the cursor; S stops. Useful for dodging aim lines.",
        "Practice assistance: harmless enemies; each lesson and Retry refill resources. Your ascent is safe.")),
    ("select", "Inspect your opponent", (
        "Left click the marked training dummy. This selects; it is not a basic attack.",
        "Its health and active effects appear in SELECTED TARGET on the left.",
        "Your red health and blue mana meters are above it. Inspect before choosing a spell.")),
    ("bolt", "Q / Frost Bolt", (
        "Aim the cursor at the dummy and press Q; hold Q to repeat. Land one projectile.",
        "24 base damage; 2s chill slows movement by 40%. Slow does not stop attacks or freeze.",
        "Free to cast; 0.35s cooldown shown on Q. Useful for attacking from a distance.")),
    ("nova", "W / Frost Nova", (
        "Press W near BOTH marked dummies. Catch both inside the gold radius.",
        "14 base damage within 2.8 tiles; freezes survivors for 2.25s, stopping attacks.",
        "Costs 25 mana; 8s cooldown. Use when surrounded or to create space. Retry if missed.")),
    ("patch", "E / Ice Patch", (
        "Aim at the gold ring near the dummy and press E; walk inside the field too.",
        "6s field, radius 2.4: enemies move 50% slower and attack 40% slower.",
        "Standing inside gives +30% frost damage. Useful for holding ground; it blocks nothing.",
        "30 mana; 14s cooldown; place within 5 tiles on clear, visible floor. No Ice Wall in this build.")),
    ("prison", "R / Glacial Prison", (
        "Wait for the archer's aim line, then press R near the dummies. Absorb a shot; shatter hits both.",
        "Stationary and invulnerable for 2.5s; cannot cast or heal. Movement resumes afterward.",
        "Release: 90 base damage within 3.2 tiles; survivors freeze 2s. 45 mana; 45s cooldown.",
        "A timed defense, not a repeat attack. Harmless arrows here; Retry resets the long cooldown.")),
    ("heal", "1 / Healing potion", (
        "Practice-only damage removed 30 health. Press 1, or click Healing potion, to recover.",
        "Restores up to 40 health; consumes one of your limited potions. No mana cost or cooldown.",
        "Full health wastes no potion; Glacial Prison prevents healing. Food also restores health.")),
    ("pickup", "Collect practice equipment", (
        "Right click the labeled practice crown to walk over it and collect it automatically.",
        "Empty slots auto-equip loot. You already wear a Rank 1 crown, so this goes into the backpack.",
        "The backpack has pages, not a fixed capacity. This practice item never enters your save.")),
    ("inspect", "I / Inspect and compare", (
        "Open I GEAR (or press I), then click the practice crown in the backpack.",
        "Hover it to inspect: Rimeweaver Crown, helm, Rank 2 / Runed, +20% spell damage.",
        "Compare the tooltip's equipped Rank 1 crown: +10%. Backpack ownership grants no bonus.",
        "Closed the panel? Press I again. The five slots are helm, chest, legs, gloves and boots.")),
    ("equip", "Equip the crown", (
        "With the Rank 2 crown selected, click EQUIP ITEM at the bottom of the inventory.",
        "Watch the highlighted helm slot and spell damage stat: +10% becomes +20%.",
        "Your old Rank 1 crown returns to the backpack. Equip changes the worn item immediately.",
        "If the item was sold or destroyed, Retry restores the practice setup for this lesson.")),
    ("set", "Ranks and Frostweave", (
        "The five slots grant damage, health, armor, cooldown reduction, and speed/critical bonuses.",
        "B opens the enchanter. Ordinary gear: one rolled enchantment, R2 at floor 3, R3 at floor 5; maximum Rank 3.",
        "The Keeper's first defeat unlocks Rank 3 Frostweave; only Frostweave can reach Ranks 4 and 5.",
        "Frostweave requires all FIVE pieces WORN. Set rank is the lowest equipped piece's rank.",
        "At set rank 3/4/5, Bolt has 15/25/40% chance to freeze for 1s. Backpack pieces do not count.",
        "No purchase needed here. Read this, then choose Next lesson.")),
    ("final", "Put it together", (
        "Defeat the three marked practice enemies. They cannot hurt you. Choose your spells and positioning.",
        "Right click: move / hold to follow; left click: inspect; cursor aims Q and E; S: stop.",
        "Q Bolt / W Nova / E Patch / R Prison / 1 heal / I gear / B enchanter / Esc pause / J journal.",
        "M toggles sound. Spell buttons also work: click Q or E, then left click to aim; right click cancels.",
        "Need another try? Restart Practice begins this encounter again with full resources.")),
    ("complete", "Lesson complete", (
        "Your remembered lesson is complete. You can replay Tutorial from the main menu at any time.",
        "Start Game begins a fresh ascent if you came from New Game; otherwise it resumes your ascent.",
        "All practice loot, damage, cooldown resets and gold are discarded. Your saved character is untouched.")),
)


class PracticeWorld(World):
    practice_mode = True
    """Scope assistance to this room; all spell resolution and equipment remain inherited."""

    def __init__(self, seed=7):
        self.lesson_events = []
        self.practice_combat = False
        self.archer_enabled = False
        super().__init__(seed)
        self.layout = room(set())
        self.walls = {(x, y) for y, row in enumerate(self.layout)
                      for x, tile in enumerate(row) if tile == "#"}
        self.level_data = replace(FROSTFALL, name="Drearamore / A Remembered Lesson",
                                  chapter="TUTORIAL    /    ISOLATED PRACTICE",
                                  subtitle="Harmless foes. Retry refills resources. Your ascent is suspended.",
                                  layout=self.layout, columns=())
        self.spawners.clear()
        self.enemies.clear()
        self.pickups.clear()
        self.effects.clear()
        self.events.clear()
        self.message_time = 0
        self.exit = Vec(1.5, 1.5)

    def _record(self, event, **data):
        self.lesson_events.append((event, data))

    def _phase_cleared(self):
        pass

    def _move_enemy(self, enemy, dt, direction=None):
        if self.practice_combat:
            super()._move_enemy(enemy, dt, direction)

    def _archer(self, enemy, dt):
        if self.archer_enabled or self.practice_combat:
            super()._archer(enemy, dt)

    def _hurt_player(self, amount, source="unknown", attack="contact", attacker=None):
        # Let the real protected-state check decide whether the practice arrow is absorbed.
        if self.player.stasis > 0:
            result = super()._hurt_player(amount, source, attack, attacker=attacker)
            self._record("practice_protected", blocked=not result)
        return False

    def _drop_equipment(self, pos, guaranteed=False):
        pass


class Tutorial:
    def __init__(self, normal_world, from_new_game=False):
        self.normal_world = normal_world
        self.from_new_game = from_new_game
        self.world = PracticeWorld()
        self.index = 0
        self.completed = set()
        self.skipped = set()
        self.ready = False
        self.retry()

    @property
    def step(self):
        return LESSONS[self.index][0]

    def retry(self):
        w = self.world
        p = w.player
        p.pos = Vec(8.5, 10.5)
        p.hp, p.mana, p.potions = p.max_hp, 100, 3
        p.cooldowns = dict.fromkeys(ABILITIES, 0.0)
        p.stasis = p.cast_time = p.invincible = p.flash = 0
        p.stasis_frost_multiplier = 1
        w.stop()
        w.state = "playing"
        w.projectiles.clear()
        w.effects.clear()
        w.ice_patches.clear()
        w.rime_trails.clear()
        p.slow_time = p.slow_pulse = p.thorn_cooldown = 0
        w.enemies.clear()
        w.pickups.clear()
        w.selected = None
        w.events.clear()
        w.message_time = 0
        w.archer_enabled = self.step == "prison"
        w.practice_combat = self.step == "final"
        self.mark = Vec(10.5, 10.5)
        self.ready = False
        self.saw_stasis = self.protected = self.shattered = False
        self.patch_enemy = self.patch_mage = False
        if self.step in ("select", "bolt", "patch"):
            self.targets = [Enemy(Vec(11.5 if self.step == "patch" else 10.5, 9.5), boss_name="Training dummy")]
            self.mark = self.targets[0].pos
        elif self.step in ("nova", "prison"):
            self.targets = [Enemy(Vec(9.8, 10), boss_name="Training dummy"),
                            Enemy(Vec(7.3, 10), boss_name="Training archer" if self.step == "prison" else "Training dummy",
                                  kind="archer" if self.step == "prison" else "husk")]
        elif self.step == "final":
            self.targets = [Enemy(Vec(10, 9), kind="husk"), Enemy(Vec(7, 9), kind="husk"),
                            Enemy(Vec(10, 7), kind="archer", cooldown=2)]
        else:
            self.targets = []
        for target in self.targets:
            target.hp = target.max_hp
        w.enemies = list(self.targets)
        if self.step in ("pickup", "inspect", "equip"):
            # Reconstruct only disposable gear, including on Retry after a sale or destruction.
            p.inventory = Inventory()
            old = p.inventory.create("helm", 1)
            p.inventory.add(old)
            self.old_uid = old.uid
            self.item = p.inventory.create("helm", 2)
            if self.step == "pickup":
                w.pickups.append(Pickup(self.mark, "item", 0, self.item))
            else:
                p.inventory.add(self.item, auto_equip=False)
            p.hp = p.max_hp
        if self.step == "heal":
            p.hp = p.max_hp - 30
        w.lesson_events.clear()

    def next(self, skip=False):
        if self.step == "complete" or not (skip or self.ready or self.step == "set"):
            return False
        (self.skipped if skip else self.completed).add(self.step)
        self.index += 1
        self.retry()
        return True

    def observe(self, mode="playing", armory=None, mouse=None):
        w, p = self.world, self.world.player
        if w.state == "dead":
            self.retry()
            w.announce("Practice restored. No progress or loot was lost.")
            return
        events = w.lesson_events[:]
        w.lesson_events.clear()
        if self.step == "move":
            done = (p.pos - self.mark).length() < .55
        elif self.step == "select":
            done = w.selected in self.targets
        elif self.step == "bolt":
            done = any(e == "spell_resolved" and d.get("spell") == "q" and d.get("targets_hit", 0) > 0
                       for e, d in events)
        elif self.step == "nova":
            done = any(e == "spell_resolved" and d.get("spell") == "w" and d.get("targets_hit") == 2
                       for e, d in events)
        elif self.step == "patch":
            self.patch_enemy |= any(w.patch_time_at(t.pos) > 0 for t in self.targets)
            self.patch_mage |= w.frost_multiplier > 1
            done = self.patch_enemy and self.patch_mage
        elif self.step == "prison":
            self.saw_stasis |= p.stasis > 0
            self.protected |= any(e == "practice_protected" and d["blocked"] for e, d in events)
            self.shattered |= any(e == "spell_resolved" and d.get("spell") == "r" and d.get("targets_hit") == 2
                                  for e, d in events)
            done = self.saw_stasis and self.protected and self.shattered and p.stasis == 0
        elif self.step == "heal":
            done = any(e == "healing" and d.get("source") == "potion" and d.get("hp_restored", 0) > 0
                       for e, d in events)
        elif self.step == "pickup":
            done = p.inventory.get(self.item.uid) is not None
        elif self.step == "inspect":
            # Require actual selection and a hover over the real item/compare tooltip.
            done = (mode == "inventory" and armory is not None and armory.selected_uid == self.item.uid
                    and mouse is not None and armory.owned_at(w, mouse, mode) == self.item)
        elif self.step == "equip":
            done = p.inventory.equipped["helm"] == self.item.uid and p.inventory.stats.damage == .20
        elif self.step == "final":
            done = not w.enemies
        else:
            done = self.step in ("set", "complete")
        if self.step == "equip":
            self.ready = bool(done)
        else:
            self.ready |= bool(done)

    def buttons(self):
        import pygame
        # Footer is outside all combat and armory click targets, in logical canvas coordinates.
        if self.step == "complete":
            actions = [("start_game", "Start Game"), ("exit", "Return to Menu"), ("restart", "Restart Tutorial")]
        else:
            actions = [("next", "Next lesson" if self.ready else "Complete the action"),
                       ("retry", "Restart Practice" if self.step == "final" else "Retry Step"),
                       ("skip", "Skip Step"), ("exit", "Exit Tutorial")]
        return [(action, label, pygame.Rect(320 + i * 270, 867, 258, 29))
                for i, (action, label) in enumerate(actions)]

    def click(self, point):
        return next((action for action, label, rect in self.buttons() if rect.collidepoint(point)), None)

    def draw(self, r, mode):
        import pygame
        from .render import iso
        ice, gold = (139, 216, 248), (214, 180, 113)
        # Guidance occupies the title region in inventory, and the unused top of the room in play.
        inventory = mode in ("inventory", "shop")
        box = pygame.Rect(318, 4 if inventory else 201, 1080, 94 if inventory else 156)
        pygame.draw.rect(r.screen, (14, 28, 40), box, border_radius=6)
        pygame.draw.rect(r.screen, ice, box, 1, border_radius=6)
        _, title, lines = LESSONS[self.index]
        r.text(f"{self.index + 1}/{len(LESSONS)}  {title.upper()}" + ("  /  COMPLETE" if self.ready else "  /  YOUR TURN"),
               box.x + 12, box.y + 8, 15, gold)
        visible = lines if not inventory else lines[:3]
        for i, line in enumerate(visible):
            r.text(line, box.x + 12, box.y + 33 + i * (17 if inventory else 22), 12, ice)
        if not inventory:
            pygame.draw.rect(r.screen, (19, 26, 33), (324, 168, 1072, 31), border_radius=5)
            r.text("DREARAMORE / PRACTICE", 338, 176, 11, ice)
            r.text("One objective at a time. Enter or Next lesson continues after success.", 580, 176, 11, gold)
            if self.step in ("move", "pickup", "patch"):
                r.radius(self.mark, .55, gold, 3)
                x, y = iso(self.mark)
                r.text("PRACTICE CROWN / WALK HERE" if self.step == "pickup" else "HERE", x, y + 22, 12, gold, center=True)
            if self.step in ("nova", "prison"):
                r.radius(self.world.player.pos, ABILITIES["w" if self.step == "nova" else "r"].range, gold, 2)
            for target in self.targets:
                if target in self.world.enemies:
                    r.radius(target.pos, .45, gold, 2)
            key = {"bolt": "q", "nova": "w", "patch": "e", "prison": "r"}.get(self.step)
            highlights = [r.ability_rects[key]] if key else []
            if self.step in ("select", "bolt", "heal"):
                highlights += [pygame.Rect(43, 340, 220, 86)]
            if self.step == "select":
                highlights += [pygame.Rect(43, 498, 220, 144)]
            if self.step == "heal":
                highlights += [r.potion_rect]
            if self.step in ("inspect", "equip"):
                highlights += [r.gear_button]
                r.text("Press I to reopen inventory and continue.", 330, 720, 14, gold)
        else:
            highlights = []
            if self.step in ("inspect", "equip"):
                highlights = [r.armory.bag_rects[0], r.armory.slot_rects["helm"]]
                if self.step == "equip":
                    highlights += [r.armory.equip_rect, pygame.Rect(906, 237, 304, 296)]
        for rect in highlights:
            pygame.draw.rect(r.screen, gold, rect.inflate(6, 6), 3, border_radius=5)
        # Replace unrelated tower objectives with the lesson's persistence/assistance status.
        if not inventory:
            pygame.draw.rect(r.screen, (19, 26, 33), (43, 661, 220, 118))
            r.text("DREARAMORE PRACTICE", 48, 668, 12, gold)
            r.text(f"{len(self.completed)} done / {len(self.skipped)} skipped", 48, 696, 12, ice)
            r.text("No damage from enemies", 48, 722, 11, ice)
            r.text("No practice progress saved", 48, 746, 11, ice)
        for action, label, rect in self.buttons():
            enabled = action != "next" or self.ready
            r.armory.button(r, rect, label, enabled=enabled)
