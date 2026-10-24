"""Authored mini-boss signatures; every fifth floor is reserved for a full boss."""
from dataclasses import dataclass
from math import atan2, pi

from .geometry import Vec
from .combat_values import SIGNATURE_DAMAGE, SIGNATURE_INTERVAL, SIGNATURE, DUPLICATE_POOL_BASE_DAMAGE

MINIBOSS_OPENING_DELAY = 1.0
MINIBOSS_GOLD = 500

BOSSES = {1: ("Oathbound Warden", "armor", "Winterbreaker"),
          2: ("Rootbound Heart", "tree", "Briar Cage"),
          3: ("Splintered Alchemist", "grimoire", "Chain Reaction")}


# Stable variant IDs are independent of their editable display names.
COMPANIONS = {1: ("animated_shield", "armor", "support", "Animated Shield"),
              2: ("thorn_tender", "tree", "support", "Thorn Tender"),
              3: ("volatile_duplicate", "fairy", "duplicate", "Volatile Duplicate")}
MINIBOSS_IDS = {1: "oathbound_warden", 2: "rootbound_heart", 3: "splintered_alchemist"}

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
            return abs(offset.length() - self.radius) < .5 and abs(difference) > SIGNATURE[2]["cage_gap_half_angle_radians"]
        return offset.length() < self.radius + .23


def signature(world, boss):
    """Lock warning positions at cast time so movement can avoid the attack."""
    player = world.player.pos
    params = SIGNATURE[world.level]
    if world.level == 1:
        direction = (player - boss.pos).unit()
        world.hazards.append(Hazard(boss, boss.pos, params["warning_seconds"], kind="charge", direction=direction))
    elif world.level == 2:
        delta = boss.pos - player
        world.hazards.append(Hazard(boss, player, params["warning_seconds"], params["cage_radius_tiles"], "cage", gap=atan2(delta.y, delta.x)))
    else:
        for i, offset in enumerate((Vec(), Vec(params["pool_spacing_tiles"], 0), Vec(-params["pool_spacing_tiles"], 0))):
            pos = player + offset
            if world.walkable(pos):
                world.hazards.append(Hazard(boss, pos, params["warning_seconds"] + i * params["pool_stagger_seconds"], params["radius_tiles"]))
    world._record("boss_attack", source=boss.kind, attack=BOSSES[world.level][2])
    boss.signature_timer = SIGNATURE_INTERVAL
    world.announce(f"{BOSSES[world.level][2]}! " +
                   {1: "Dodge the marked charge lane.", 2: "Escape through the gap in the roots.",
                    3: "Move away from the marked potion pools."}[world.level])


def update_hazards(world, dt):
    for hazard in world.hazards[:]:
        if hazard.owner not in world.enemies or hazard.owner.frozen > 0:
            world.hazards.remove(hazard)
            continue
        world.refresh_patch_status(hazard.owner)
        rate = hazard.owner.attack_rate if hazard.delay > 0 else world.enemy_move_factor(hazard.owner) if hazard.kind == "charge" else 1
        hazard.delay -= dt * rate
        if hazard.delay > 0:
            continue
        boss = hazard.owner
        if hazard.kind == "charge":
            destination = boss.pos + hazard.direction * (SIGNATURE[1]["charge_speed_tiles_per_second"] * dt * world.enemy_move_factor(boss))
            blocked = not world.walkable(destination, .3)
            if not blocked:
                boss.pos = destination
            if (boss.pos - world.player.pos).length() < SIGNATURE[1]["hit_range_tiles"]:
                world._hurt_player(SIGNATURE_DAMAGE[1], source=boss.kind, attack="Winterbreaker", attacker=boss)
            if blocked or hazard.delay < -SIGNATURE[1]["charge_duration_seconds"]:
                boss.recovery = SIGNATURE[1]["recovery_seconds"]
                world.hazards.remove(hazard)
        else:
            if hazard.kind == "cage":
                hazard.radius = max(.25, SIGNATURE[2]["cage_radius_tiles"] + hazard.delay * SIGNATURE[2]["cage_contraction_tiles_per_second"])
            if hazard.contains(world.player.pos):
                world._hurt_player(SIGNATURE_DAMAGE[2] if hazard.kind == "cage" else SIGNATURE_DAMAGE[3], source=boss.kind, attack="Briar Cage" if hazard.kind == "cage" else "Chain Reaction", attacker=boss)
            if hazard.kind == "pool":
                for enemy in world.enemies[:]:
                    if enemy.boss_role == "duplicate" and hazard.contains(enemy.pos):
                        world._hit(enemy, DUPLICATE_POOL_BASE_DAMAGE, spell="environment")
            if hazard.kind != "cage" or hazard.delay < -SIGNATURE[2]["active_seconds"]:
                boss.recovery = SIGNATURE[world.level]["recovery_seconds"]
                world.hazards.remove(hazard)
