"""Menagerie specimens share the ordinary Enemy damage, loot and frost systems."""
from .combat_values import CREATURE, LUNGE_CHILL_FACTOR

KINDS = ("crystal", "predator", "arcane")
CHARGE_WARNING = CREATURE["crystal"]["warning"]
POUNCE_WARNING = CREATURE["predator"]["warning"]
LUNGE_CAP = 2


def interrupt(enemy):
    if enemy.action:
        enemy.action = ""
        enemy.action_time = 0
        enemy.recovery = .8
        enemy.cooldown = max(enemy.cooldown, 2)


def update_creature(world, enemy, dt):
    from .world import ENEMY_STATS
    params = CREATURE[enemy.kind]
    world.refresh_patch_status(enemy)
    enemy.recovery = max(0, enemy.recovery - dt * enemy.attack_rate)
    if enemy.recovery > 0:
        return
    if enemy.action == "warning":
        enemy.action_time -= dt * enemy.attack_rate
        if enemy.action_time <= 0:
            if enemy.kind == "arcane":
                world.enemy_bolt(enemy, enemy.attack_direction, speed=params["projectile_speed"], spell="arcane", life=params["projectile_life"])
                enemy.action = ""
                enemy.cooldown, enemy.recovery = params["interval"], params["recovery"]
            else:
                enemy.action = "lunge"
                world._record("enemy_attack", source=enemy.kind, attack=enemy.kind + "_lunge", stage="release")
                enemy.action_time = params["lunge_duration"]
        return
    if enemy.action == "lunge":
        # Swept steps prevent tunnelling or sliding along terrain.
        speed = params["lunge_speed"] * (LUNGE_CHILL_FACTOR if enemy.chilled > 0 else 1)
        move_factor = world.enemy_move_factor(enemy)
        remaining = speed * dt * move_factor
        blocked = False
        while remaining > 1e-8:
            step = min(.1, remaining)
            candidate = enemy.pos + enemy.attack_direction * step
            if not world.walkable(candidate, .3):
                blocked = True
                break
            enemy.pos = candidate
            if (enemy.pos - world.player.pos).length() < .62:
                world._hurt_player(ENEMY_STATS[enemy.kind][3], source=enemy.kind, attack="charge" if enemy.kind == "crystal" else "pounce", attacker=enemy)
            remaining -= step
        enemy.action_time -= dt * move_factor
        if blocked or enemy.action_time <= 0:
            enemy.action = ""
            enemy.recovery = params["blocked_recovery"] if blocked else params["recovery"]
            enemy.cooldown = params["interval"]
        return
    distance = (world.player.pos - enemy.pos).length()
    reach = params["reach"]
    lunges = sum(e.action in ("warning", "lunge") and e.kind != "arcane" for e in world.enemies)
    if (enemy.cooldown <= 0 and distance <= reach and distance > .1
            and world._line_clear(enemy.pos, world.player.pos)
            and (enemy.kind == "arcane" or lunges < LUNGE_CAP)):
        enemy.action = "warning"
        enemy.action_time = params["warning"]
        world._record("enemy_attack", source=enemy.kind, attack="orb" if enemy.kind == "arcane" else "charge" if enemy.kind == "crystal" else "pounce",
                      stage="warning", warning_seconds=enemy.action_time / enemy.attack_rate)
        enemy.attack_origin = enemy.pos
        enemy.attack_direction = (world.player.pos - enemy.pos).unit()
    elif distance > (4 if enemy.kind == "arcane" else 1):
        world._move_enemy(enemy, dt)
    elif enemy.kind == "arcane" and distance < 2.5:
        world._move_enemy(enemy, dt, (enemy.pos - world.player.pos).unit())
