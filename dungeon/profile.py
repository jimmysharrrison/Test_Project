"""Atomic local persistence for earned equipment, gold, and unlocked depth."""

import json
import os
from pathlib import Path

from .items import Inventory
from .levels import PLAYABLE_FLOORS


def default_path():
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "Embervault" / "profile.json"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "embervault" / "profile.json"


class ProfileStore:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else default_path()
        self.error = ""
        self.writable = True
        self._last = None

    def load(self):
        from .world import Player
        try:
            if not self.path.exists():
                return None
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") not in (1, 2):
                raise ValueError("Unsupported profile")
            inv = Inventory.from_dict(data["inventory"])
            values = {key: data.get(key, default) for key, default in
                      (("gold", 0), ("unlocked_level", 1), ("potions", 3), ("kills", 0))}
            for key, value in values.items():
                if type(value) is not int or not (1 if key == "unlocked_level" else 0) <= value <= 1_000_000_000:
                    raise ValueError("Invalid saved player values")
            # Older saves only tracked the highest depth; retain that progress.
            current = data.get("current_level", values["unlocked_level"])
            if type(current) is not int or not 1 <= current <= values["unlocked_level"]:
                raise ValueError("Invalid current level")
            # Old builds repeated the forest indefinitely; keep gear and map those depths to the authored tower.
            current = min(current, PLAYABLE_FLOORS)
            values["unlocked_level"] = min(values["unlocked_level"], PLAYABLE_FLOORS)
            rewarded = data.get("first_clear_rewarded", False)
            if type(rewarded) is not bool:
                raise ValueError("Invalid reward state")
            cleared = data.get("cleared_floor", 0)
            completed = data.get("lower_tower_completed", False)
            if type(cleared) is not int or cleared not in (0, 5) or type(completed) is not bool:
                raise ValueError("Invalid tower completion state")
            if cleared and (current != 5 or not completed):
                raise ValueError("Invalid cleared floor")
            player = Player(cleared_floor=cleared, lower_tower_completed=completed, inventory=inv, first_clear_rewarded=rewarded, current_level=current, **values)
            unlocked = data.get('frostweave_unlocked', completed)
            if type(unlocked) is not bool:
                raise ValueError('Invalid Frostweave unlock')
            player.frostweave_unlocked = unlocked
            from .timing import Timing
            player.timing = Timing.from_dict(data.get("timing"))
            if player.timing.floor != current:
                player.timing.eligible = False
                player.timing.begin_floor(current)
            from .achievements import AchievementRun, load_unlocks
            player.achievement_run = AchievementRun.from_dict(data.get("achievement_run"), current)
            player.achievements = load_unlocks(data.get("achievements", {}))
            pending = data.get("achievement_notifications", [])
            if not isinstance(pending, list) or any(key not in player.achievements for key in pending):
                raise ValueError("Invalid achievement notifications")
            player.achievement_notifications = pending.copy()
            from .codex import load_discoveries, observe_items
            player.bestiary, player.item_discoveries = load_discoveries(data)
            observe_items(player)  # Owned equipment is evidence; aggregate kills are not.
            player.hp = player.max_hp
            self._last = data
            return player
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            self.error = "Profile could not be loaded. Autosave disabled to preserve the original file."
            self.writable = False
            return None

    def save(self, player, *, snapshot=None):
        if not self.writable:
            return False
        if player.achievement_run.floor != player.current_level:
            player.achievement_run.enter(player.current_level)
        from .codex import observe_items
        observe_items(player)
        data = {"frostweave_unlocked": player.frostweave_unlocked, "bestiary": player.bestiary, "item_discoveries": player.item_discoveries.copy(), "achievement_notifications": player.achievement_notifications.copy(), "achievement_run": player.achievement_run.to_dict(), "achievements": player.achievements.copy(), "version": 2, "timing": player.timing.to_dict(), "gold": player.gold, "unlocked_level": player.unlocked_level,
                "current_level": player.current_level,
                "cleared_floor": player.cleared_floor, "lower_tower_completed": player.lower_tower_completed,
                "potions": player.potions, "kills": player.kills,
                "first_clear_rewarded": player.first_clear_rewarded,
                "inventory": player.inventory.to_dict()}
        if snapshot is not None:
            data["game_state"] = snapshot
        if data == self._last:
            return True
        temporary = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
            self._last = json.loads(json.dumps(data))
            self.error = ""
            return True
        except OSError:
            self.error = "Progress could not be saved. Check that your profile folder is writable."
            return False
