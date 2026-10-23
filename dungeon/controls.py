"""Mouse orders and spell-button targeting, independent of Pygame events."""

from .abilities import ABILITIES


class Controls:
    def __init__(self, world):
        self.world = world
        self.armed = None
        self.aim = world.player.pos + world.player.facing * 4
        self.bolt_aim = self.aim
        self.follow_timer = 0
        self.suppress_right = False

    def point(self, target, bolt_target=None):
        self.aim = target
        self.bolt_aim = target if bolt_target is None else bolt_target

    def hotkey(self, key):
        self.armed = None
        return self.world.cast(key, self.bolt_aim if key == "q" else self.aim)

    def ability_button(self, key):
        reason = self.world.can_cast(key)
        if reason:
            self.world.announce(reason)
            return
        if ABILITIES[key].targeted:
            self.armed = None if self.armed == key else key
            if self.armed:
                self.world.announce(f"{ABILITIES[key].name}: left click a target. Right click cancels.")
        else:
            self.armed = None
            self.world.cast(key, self.aim)

    def left_world(self, target, selected=None, bolt_target=None):
        self.point(target, bolt_target)
        if self.armed is not None:
            if self.world.cast(self.armed, self.bolt_aim if self.armed == "q" else target):
                self.armed = None
        else:
            self.world.selected = selected

    def right_down(self, target=None):
        if self.armed is not None:
            self.armed = None
            self.suppress_right = True
            self.world.announce("Targeting cancelled.")
        elif target is not None:
            self.world.request_move(target)
            self.follow_timer = 0.1

    def right_up(self):
        self.suppress_right = False

    def cancel(self):
        was_armed = self.armed is not None
        self.armed = None
        return was_armed

    def update(self, dt, right_target=None, repeat_q=False):
        self.follow_timer = max(0, self.follow_timer - dt)
        if right_target is not None and not self.suppress_right and self.follow_timer <= 0:
            self.world.request_move(right_target, marker=False)
            self.follow_timer = 0.1
        if repeat_q and self.armed is None:
            self.world.cast("q", self.bolt_aim, feedback=False)
