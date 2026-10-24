"""Cosmetic definitions and persistent run evidence, independent of presentation/rewards."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from math import isfinite
from uuid import uuid4

DEFINITIONS = {
    "untouched_lower_tower": {
        "title": "Untouched: Lower Tower",
        "description": "Clear floors 1 through 5 in order in one fresh campaign without damage or retries.",
    },
}

@dataclass
class AchievementRun:
    run_id: str = field(default_factory=lambda: str(uuid4()))
    starting_floor: int = 1
    floor: int = 1
    cleared: list = field(default_factory=list)
    damage: float = 0
    deaths: int = 0
    retries: int = 0
    eligible: bool = True

    def invalidate(self):
        self.eligible = False

    def enter(self, floor):
        if floor != self.floor:
            if floor != self.floor + 1 or self.cleared != list(range(1, floor)):
                self.invalidate()
            self.floor = floor

    def hurt(self, actual):
        if actual > 0:
            self.damage += actual
            self.invalidate()

    def retry(self):
        self.retries += 1
        self.invalidate()

    def clear(self, floor, unlocked, *, keeper=False, alive=True, practice=False):
        if practice or not alive:
            self.invalidate()
            return None
        if floor in self.cleared:
            return None
        if floor != self.floor or self.cleared != list(range(1, floor)):
            self.invalidate()
        self.cleared.append(floor)
        key = "untouched_lower_tower"
        if (floor == 5 and keeper and self.eligible and self.starting_floor == 1
                and self.cleared == [1, 2, 3, 4, 5] and self.damage == 0
                and self.deaths == self.retries == 0 and key not in unlocked):
            unlocked[key] = datetime.now(timezone.utc).isoformat()
            return key
        return None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data, floor):
        # Partial history is never upgraded into a flawless campaign.
        if not isinstance(data, dict) or set(data) != set(cls.__dataclass_fields__):
            return cls(floor=floor, eligible=False)
        run = cls(**data)
        if (not isinstance(run.run_id, str) or not run.run_id
                or type(run.eligible) is not bool
                or any(type(x) is not int or x < 0 for x in (run.deaths, run.retries))
                or type(run.damage) not in (int, float) or not isfinite(run.damage) or run.damage < 0
                or type(run.floor) is not int or type(run.starting_floor) is not int
                or not isinstance(run.cleared, list)
                or any(type(x) is not int for x in run.cleared)):
            raise ValueError("Invalid achievement run")
        expected = list(range(1, floor))
        if (run.floor != floor or run.starting_floor != 1 or floor not in range(1, 6)
                or run.cleared not in (expected, expected + [floor])
                or run.damage or run.deaths or run.retries):
            run.invalidate()
        return run


def load_unlocks(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid achievements")
    for key, date in data.items():
        if not isinstance(key, str) or not isinstance(date, str):
            raise ValueError("Invalid achievement date")
        datetime.fromisoformat(date)
    return data.copy()
