"""Authored mini-boss signatures; every fifth floor is reserved for a full boss."""
from dataclasses import dataclass
from math import atan2, pi

from .geometry import Vec

BOSSES = {1: ("Oathbound Warden", "armor", "Winterbreaker"),
          2: ("Rootbound Heart", "tree", "Briar Cage"),
          3: ("Splintered Alchemist", "grimoire", "Chain Reaction")}


@dataclass(slots=True)
class Hazard:
    owner: object
    pos: Vec
    delay: float
    radius: float = .85
    kind: str = "pool"
    direction: Vec = Vec()
    gap: float = 0

    def contains(self, point):
        offset = point - self.pos
        if self.kind == "cage":
            if offset.length() < .1 and self.radius < .5:
                return True
            angle = atan2(offset.y, offset.x)
            difference = (angle - self.gap + pi) % (2 * pi) - pi
            return abs(offset.length() - self.radius) < .5 and abs(difference) > .48
        return offset.length() < self.radius + .23


def signature(world, boss):
    """Lock warning positions at cast time so movement can avoid the attack."""
    player = world.player.pos
    if world.level == 1:
        direction = (player - boss.pos).unit()
        world.hazards.append(Hazard(boss, boss.pos, 1.2, kind="charge", direction=direction))
    elif world.level == 2:
        delta = boss.pos - player
        world.hazards.append(Hazard(boss, player, 1.6, 2.1, "cage", gap=atan2(delta.y, delta.x)))
    else:
        for i, offset in enumerate((Vec(), Vec(1.7, 0), Vec(-1.7, 0))):
            pos = player + offset
            if world.walkable(pos):
                world.hazards.append(Hazard(boss, pos, 1.2 + i * .55))
    boss.signature_timer = 7
    world.announce(f"{BOSSES[world.level][2]}! " +
                   {1: "Dodge the marked charge lane.", 2: "Escape through the gap in the roots.",
                    3: "Move away from the marked potion pools."}[world.level])


def update_hazards(world, dt):
    for hazard in world.hazards[:]:
        if hazard.owner not in world.enemies or hazard.owner.frozen > 0:
            world.hazards.remove(hazard)
            continue
        hazard.delay -= dt
        if hazard.delay > 0:
            continue
        boss = hazard.owner
        if hazard.kind == "charge":
            destination = boss.pos + hazard.direction * (9 * dt)
            blocked = not world.walkable(destination, .3)
            if not blocked:
                boss.pos = destination
            if (boss.pos - world.player.pos).length() < .8:
                world._hurt_player(24)
            if blocked or hazard.delay < -1.4:
                boss.recovery = 2.2
                world.hazards.remove(hazard)
        else:
            if hazard.kind == "cage":
                hazard.radius = max(.25, 2.1 + hazard.delay * 1.8)
            if hazard.contains(world.player.pos):
                world._hurt_player(22 if hazard.kind == "cage" else 18)
            if hazard.kind == "pool":
                for enemy in world.enemies[:]:
                    if enemy.boss_role == "duplicate" and hazard.contains(enemy.pos):
                        world._hit(enemy, 45)
            if hazard.kind != "cage" or hazard.delay < -1.1:
                boss.recovery = 1.8
                world.hazards.remove(hazard)
