"""Atomic local persistence for earned equipment, gold, and unlocked depth."""

import json
import os
from pathlib import Path

from .items import Inventory


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
            if not isinstance(data, dict) or data.get("version") != 1:
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
            rewarded = data.get("first_clear_rewarded", False)
            if type(rewarded) is not bool:
                raise ValueError("Invalid reward state")
            player = Player(inventory=inv, first_clear_rewarded=rewarded, current_level=current, **values)
            player.hp = player.max_hp
            self._last = data
            return player
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            self.error = "Profile could not be loaded. Autosave disabled to preserve the original file."
            self.writable = False
            return None

    def save(self, player):
        if not self.writable:
            return False
        data = {"version": 1, "gold": player.gold, "unlocked_level": player.unlocked_level,
                "current_level": player.current_level,
                "potions": player.potions, "kills": player.kills,
                "first_clear_rewarded": player.first_clear_rewarded,
                "inventory": player.inventory.to_dict()}
        if data == self._last:
            return True
        temporary = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
            self._last = data
            self.error = ""
            return True
        except OSError:
            self.error = "Progress could not be saved. Check that your profile folder is writable."
            return False
