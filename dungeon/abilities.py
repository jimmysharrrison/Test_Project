"""Frost Mage spell definitions shared by the simulation and interface."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Ability:
    key: str
    name: str
    cooldown: float
    mana: float
    targeted: bool
    description: str
    range: float = 0
    damage: int = 0
    duration: float = 0
    freeze: float = 0
    slow: float = 0


ABILITIES = {
    "q": Ability("q", "Frost Bolt", 0.35, 0, True,
                 "24 damage. Chills for 2s. Hold Q to repeat.", 10, damage=24, duration=2, slow=0.4),
    "w": Ability("w", "Frost Nova", 8, 25, False,
                 "14 damage nearby. Freezes enemies for 2.25s.", 2.8, damage=14, freeze=2.25),
    "e": Ability("e", "Ice Wall", 14, 30, True,
                 "A barrier lasting 6s. Blocks movement and projectiles.", 5, duration=6),
    "r": Ability("r", "Glacial Prison", 45, 45, False,
                 "Invulnerable for 2.5s, then shatters for 90 damage.", 3.2, damage=90, duration=2.5, freeze=2),
}
