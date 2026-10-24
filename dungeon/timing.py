"""Active-play timing and versioned, separate campaign/practice records."""
from dataclasses import asdict, dataclass, field
from math import isfinite

RULES = "active-v1-balance-2"


def display(seconds):
    if seconds is None:
        return "--:--.--"
    hundredths = int(seconds * 100)
    minutes, rest = divmod(hundredths, 6000)
    return f"{minutes:02d}:{rest // 100:02d}.{rest % 100:02d}"


@dataclass
class Timing:
    rules: str = RULES
    floor: int = 1
    floor_seconds: float = 0.0
    total_seconds: float = 0.0
    eligible: bool = True
    category: str = "campaign"
    stopped: bool = False
    cleared: list = field(default_factory=list)
    records: dict = field(default_factory=dict)
    new_best: bool = False
    previous_best: float | None = None
    new_run_best: bool = False

    def advance(self, seconds):
        if not isfinite(seconds) or seconds <= 0:
            return
        if not self.stopped:
            self.floor_seconds += seconds
        if not self.stopped or (self.floor < 5 and self.floor in self.cleared):
            self.total_seconds += seconds

    def begin_floor(self, floor):
        self.floor = floor
        self.floor_seconds = 0.0
        self.stopped = self.new_best = False
        self.previous_best = None
        self.new_run_best = False

    def restart(self, floor=1, campaign=False):
        self.floor_seconds = self.total_seconds = 0.0
        self.cleared = []
        self.eligible = True
        self.rules = RULES
        self.category = "campaign" if campaign else "practice"
        self.begin_floor(floor)

    def key(self):
        return f"{self.rules}/{self.category}/floor-{self.floor}"

    def best(self):
        return self.records.get(self.key())

    def clear(self):
        if self.stopped:
            return
        self.stopped = True
        if not self.eligible or self.rules != RULES:
            return
        key = self.key()
        self.previous_best = self.records.get(key)
        self.new_best = self.floor_seconds < self.records.get(key, float("inf"))
        if self.new_best:
            self.records[key] = self.floor_seconds
        self.cleared.append(self.floor)
        if self.category == "campaign" and self.cleared == [1, 2, 3, 4, 5]:
            key = f"{RULES}/campaign/first-five"
            self.new_run_best = self.total_seconds < self.records.get(key, float("inf"))
            if self.new_run_best:
                self.records[key] = self.total_seconds

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if data is None:
            return cls(eligible=False)
        if not isinstance(data, dict) or not isinstance(data.get("records", {}), dict):
            raise ValueError("Invalid timing data")
        timer = cls(**data)
        if not isinstance(timer.rules, str) or any(not isinstance(key, str) for key in timer.records):
            raise ValueError("Invalid timing rules/records")
        for value in [timer.floor_seconds, timer.total_seconds, *timer.records.values()]:
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError("Invalid timing value")
        if timer.previous_best is not None and (type(timer.previous_best) not in (int, float) or not isfinite(timer.previous_best) or timer.previous_best < 0):
            raise ValueError("Invalid previous best")
        if timer.category not in ("campaign", "practice") or type(timer.floor) is not int or not 1 <= timer.floor <= 5:
            raise ValueError("Invalid timing category/floor")
        if any(type(x) is not bool for x in (timer.eligible, timer.stopped, timer.new_best, timer.new_run_best)):
            raise ValueError("Invalid timing flags")
        if not isinstance(timer.cleared, list) or any(type(x) is not int or not 1 <= x <= 5 for x in timer.cleared):
            raise ValueError("Invalid timing clears")
        if timer.rules != RULES:
            timer.eligible = False
        return timer
