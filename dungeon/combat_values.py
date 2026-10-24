"""Shared combat parameters used by simulation and read-only Codex previews.
Distances are world tiles, durations seconds, speeds tiles/second, damage HP/hit.
"""
HEALTH_PER_FLOOR = .15
DAMAGE_PER_FLOOR = .12
MINIBOSS_HEALTH = 380
COMPANION_HEALTH = 85
LUNGE_CHILL_FACTOR = .6
MELEE_REACH = .5
MELEE_INTERVAL = .9
RANGED = {
    "archer": dict(reach=7.5, warning=.65, interval=2.8, projectile_speed=5.5),
    "fairy": dict(reach=6.5, warning=.8, interval=2.3, projectile_speed=4.4),
}
CREATURE = {
    "crystal": dict(reach=6, warning=1.05, interval=4.6, lunge_speed=6.5, lunge_duration=.8, recovery=1.1, blocked_recovery=1.6),
    "predator": dict(reach=3.3, warning=.8, interval=3.4, lunge_speed=7, lunge_duration=.33, recovery=1.1, blocked_recovery=1.6),
    "arcane": dict(reach=7, warning=.95, interval=3.2, projectile_speed=3.2, projectile_life=4, recovery=.9),
}
SIGNATURE_DAMAGE = {1: 24, 2: 22, 3: 18}
SIGNATURE_INTERVAL = 7
KEEPER_DAMAGE = {"Deep Cleaning": 12, "Structural Repairs": 22}
RECOVERY_DAMAGE_MULTIPLIER = 1.35
SHIELD_DAMAGE_MULTIPLIER = .65

def scaled_damage(base, floor):
    return round(base * (1 + DAMAGE_PER_FLOOR * (floor - 1)))

SIGNATURE = {
    1: dict(warning_seconds=1.2, charge_speed_tiles_per_second=9, hit_range_tiles=.8, charge_duration_seconds=1.4, recovery_seconds=2.2),
    2: dict(warning_seconds=1.6, cage_radius_tiles=2.1, cage_contraction_tiles_per_second=1.8, cage_gap_half_angle_radians=.48, active_seconds=1.1, recovery_seconds=1.8),
    3: dict(warning_seconds=1.2, pool_spacing_tiles=1.7, pool_stagger_seconds=.55, radius_tiles=.85, recovery_seconds=1.8),
}
TENDER_HEAL_HP_PER_SECOND = 5
TENDER_HEAL_RANGE_TILES = 5
DUPLICATE_POOL_BASE_DAMAGE = 45
