"""Profile discoveries and definition-backed, read-only Codex projections.

Summons share species IDs and count only actual deaths, never recalls/cleanup.
Encounters require a living, on-screen enemy within 7.5 tiles and line of sight,
or direct player combat contact. Practice/debug actors and worlds are excluded.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import inspect
from functools import lru_cache

from .geometry import Vec, project
from .items import (DEFINITIONS, EFFECT_LABELS, Item, SLOTS, NAMES, FROSTWEAVE_NAMES, RANK_NAMES, ENCHANT_COST,
                    FROSTWEAVE_CHANCE, FROSTWEAVE_FREEZE)
from .levels import PHASE_SPEEDS, PLAYABLE_FLOORS
from .combat_values import (LUNGE_CHILL_FACTOR, RANGED, CREATURE, MELEE_REACH, MELEE_INTERVAL,
    SIGNATURE_DAMAGE, SIGNATURE_INTERVAL, SIGNATURE, TENDER_HEAL_HP_PER_SECOND, TENDER_HEAL_RANGE_TILES, DUPLICATE_POOL_BASE_DAMAGE, KEEPER_DAMAGE, scaled_damage,
    HEALTH_PER_FLOOR, DAMAGE_PER_FLOOR, RECOVERY_DAMAGE_MULTIPLIER, SHIELD_DAMAGE_MULTIPLIER)


@dataclass(frozen=True)
class Species:
    id: str
    kind: str
    name: str
    category: str = "ordinary enemy"
    role: str = ""
    floor: int | None = None

    def actor(self, floor=1, phase=1):
        from .world import Enemy
        return Enemy(Vec(), self.kind, level=floor, spawn_phase=phase,
                     boss_role=self.role, boss_name=self.name if self.role else "", species_id=self.id)


def species():
    from .world import ENEMY_STATS
    from .encounters import BOSSES, COMPANIONS, MINIBOSS_IDS
    result = {key: Species(key, key, value[0], "boss" if key == "keeper" else "ordinary enemy",
                          "keeper" if key == "keeper" else "") for key, value in ENEMY_STATS.items()}
    for floor, (name, kind, _) in BOSSES.items():
        key = MINIBOSS_IDS[floor]
        result[key] = Species(key, kind, name, "miniboss", "boss", floor)
        key, kind, role, name = COMPANIONS[floor]
        result[key] = Species(key, kind, name, "ordinary enemy", role, floor)
    result["voidwalker"] = Species("voidwalker", "voidwalker", "The Unbound Voidwalker", "boss", "boss", 6)
    result["oracle"] = Species("oracle", "oracle", "The Many-Eyed Oracle", "boss", "boss", 7)
    result["astronomer"] = Species("astronomer", "astronomer", "The Fallen Astronomer", "boss", "boss", 8)
    result["oracle_channeler"] = Species("oracle_channeler", "thrall", "Oracle Channeler", "ordinary enemy", "channeler", 7)
    result["hourless_breach"] = Species("hourless_breach", "hourless_breach", "The Hourless Breach", "boss", "boss", 9)
    result["devourer"] = Species("devourer", "devourer", "The Threshold Devourer", "boss", "boss", 10)
    result["dimensional_anchor"] = Species("dimensional_anchor", "dimensional_anchor", "Dimensional Anchor", "ordinary enemy", "anchor", 9)
    return result


def species_id(enemy):
    if enemy.species_id:
        return enemy.species_id
    # Legacy/runtime actors may be constructed without an ID. Resolve using the
    # authored variant definition, never create an entry from a display name.
    for entry in species().values():
        if entry.kind == enemy.kind and entry.role == enemy.boss_role and entry.name == enemy.name:
            return entry.id
    return enemy.kind if not enemy.boss_role or enemy.kind == "keeper" else None


def item_id(item):
    return item.catalog_id


def item_templates():
    return {key: Item(1, definition.slot, 3 if definition.set_id else 1, 'drop', definition.set_id,
                      key, None if definition.set_id else 5000) for key, definition in DEFINITIONS.items()}


def observe_items(player, enabled=True):
    if enabled:
        for key in [*(item_id(i) for i in player.inventory.items), *getattr(player.inventory, 'catalog_seen', [])]:
            if key not in player.item_discoveries:
                player.item_discoveries.append(key)


def eligible(world, enemy):
    return not (getattr(world, "practice_mode", False) or world.debug_invulnerable
                or getattr(world, "debug_mode", False) or enemy.debug_only)


def observe_enemy(world, enemy, defeated=False):
    if not eligible(world, enemy):
        return
    key = species_id(enemy)
    if key not in species():
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record = world.player.bestiary.setdefault(key, dict(encountered=True, defeated=False,
        defeats=0, first_encounter=now, first_defeat=None, floors=[], health_range=[enemy.max_hp, enemy.max_hp]))
    if world.level not in record["floors"]:
        record["floors"].append(world.level)
        record["floors"].sort()
    record["health_range"] = [min(record["health_range"][0], enemy.max_hp), max(record["health_range"][1], enemy.max_hp)]
    if defeated and not enemy.codex_counted:
        enemy.codex_counted = True
        record["defeated"] = True
        record["defeats"] += 1
        record["first_defeat"] = record["first_defeat"] or now


def observe_visible(world):
    # This is gameplay visibility, not spawning or opening the Codex.
    from .geometry import WORLD_ORIGIN
    for enemy in world.enemies:
        point = project(enemy.pos, WORLD_ORIGIN)
        if (enemy.hp > 0 and (enemy.pos - world.player.pos).length() <= 7.5
                and 300 <= point.x < 1440 and 166 <= point.y < 776
                and world._line_clear(world.player.pos, enemy.pos)):
            observe_enemy(world, enemy)


def load_discoveries(data):
    from copy import deepcopy
    records = deepcopy(data.get("bestiary", {}))
    items = deepcopy(data.get("item_discoveries", []))
    if not isinstance(records, dict) or not isinstance(items, list):
        raise ValueError("Invalid Codex history")
    for key, record in records.items():
        if not isinstance(key, str) or not isinstance(record, dict):
            raise ValueError("Invalid species history")
        if record.get("encountered") is not True or type(record.get("defeated")) is not bool:
            raise ValueError("Invalid discovery state")
        count = record.get("defeats")
        if type(count) is not int or count < 0 or record["defeated"] != (count > 0):
            raise ValueError("Invalid defeat count")
        for label in ("first_encounter", "first_defeat"):
            value = record.get(label)
            if value is not None:
                if not isinstance(value, str):
                    raise ValueError("Invalid discovery date")
                datetime.fromisoformat(value)
        if not record.get("first_encounter") or (count > 0) != bool(record.get("first_defeat")):
            raise ValueError("Missing discovery date")
        floors = record.get("floors")
        if not isinstance(floors, list) or any(type(f) is not int or not 1 <= f <= PLAYABLE_FLOORS for f in floors):
            raise ValueError("Invalid encountered floor")
        hp = record.get("health_range")
        if not isinstance(hp, list) or len(hp) != 2 or any(type(h) is not int or h <= 0 for h in hp) or hp[0] > hp[1]:
            raise ValueError("Invalid observed health")
    if any(not isinstance(key, str) for key in items):
        raise ValueError("Invalid item history")
    return records, list(dict.fromkeys(items))


FLAVOR = {
    "husk": "Old bones stir between the Tower's worn pillars.",
    "skitter": "A small ember-lit creature darts through the threshold hall.",
    "tree": "Thornveil's old gardens walk beyond their planters.",
    "spider": "A hunter makes its home beneath Thornveil's glass vault.",
    "archer": "The dead draw their bows among the roots.",
    "armor": "An enchantment patrols without its owner.",
    "grimoire": "Loose magic sends a book flapping through the workshop.",
    "fairy": "Spilled potions have unsettled the wizard's little helpers.",
    "crystal": "A crystal-backed specimen has escaped its broken pen.",
    "predator": "A little predator stalks the ruined feeding stations.",
    "arcane": "An escaped specimen bobs above fractured containment runes.",
    "keeper": "The Tower's exhausted caretaker has had a very long shift.",
    "voidling": "A small hunger slipped through the Arcanist's broken bindings.",
    "binder": "The Arcanist's researchers still try to reclaim their escaped captive.",
    "voidwalker": "It was brought here to serve. The broken chains explain its answer.",
    "lasher": "An intruder's path is a line waiting to be struck.",
    "grasper": "Its fingers close around more than flesh: a moment of lost freedom.",
    "anchor": "A living tether reaches from the hall into the dark.",
    "thrall": "The wizard's lips move. The voice behind them is not his own.",
    "oracle_channeler": "A borrowed will shields the Oracle from the consequences of its reach.",
    "oracle": "Every stolen gaze watches the next floor of the Tower.",
    "gravity_adept": "The Arcanist's celestial calculations became a language for falling.",
    "repulsor": "A shattered instrument still insists that everything keep its distance.",
    "star_fragment": "Stone has taken the stars' orbits for its own.",
    "astronomer": "He mistook the weight behind the sky for a revelation.",
    "rift_warden": "An elven guardian keeps arriving at the same unfinished disaster.",
    "chronal_scholar": "The scholar can hold a projectile in a moment, but cannot leave that moment behind.",
    "dimensional_anchor": "A binding fixed between hours. Breaking it makes the next moment possible.",
    "hourless_breach": "Three broken anchors. Three moments in which only ice can hold the wanderer here.",
    "devourer": "The Arcanist opened a way in. The Keeper held it back. Now half a god has found the floor.",
    "oathbound_warden": "The threshold's oathbound guardian stands watch with animated shields.",
    "rootbound_heart": "Thornveil's beating heart awakens among its tenders.",
    "splintered_alchemist": "The workshop's master is surrounded by volatile copies.",
    "animated_shield": "A shield holds the threshold beside its warden.",
    "thorn_tender": "A gardener tends the living heart of Thornveil.",
    "volatile_duplicate": "A volatile copy of the workshop's alchemist.",
}


@lru_cache(maxsize=None)
def source(obj):
    return f"{inspect.getsourcefile(obj).replace(chr(92), '/').split('/dungeon/')[-1]}:{inspect.getsourcelines(obj)[1]}"


@lru_cache(maxsize=None)
def definition_location(module, symbol):
    import ast
    from pathlib import Path
    path = Path(__file__).with_name(module + '.py')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == symbol for target in node.targets):
            return f'dungeon/{module}.py:{node.lineno} ({symbol})'
    return f'dungeon/{module}.py ({symbol})'


def enemy_values(entry, floor=1, phase=1, stage=1, patch=False, chilled=False):
    """Construct disposable actors; never modify a running World or its RNG."""
    from .world import Enemy, ENEMY_STATS, World
    from .keeper import TUNING, KeeperFight
    from .creatures import update_creature
    from .encounters import signature
    from .abilities import ICE_PATCH_ATTACK_FACTOR, ICE_PATCH_MOVE_FACTOR, ABILITIES
    actor = entry.actor(floor, phase)
    base = entry.actor()
    attacks = {}
    from .void_depths import DEPTH_STATS, BOSS_HEALTH, DAMAGE, VoidDepths, ROOT_DURATION, ORACLE_PROTECTION
    from .temporal import (TEMPORAL_STATS, FIXED_HEALTH, TemporalFloor, PORTAL_WARNING, SHOT_WARNING,
                           ECHO_WARNING, FIELD_WARNING, FIELD_LIFE, FIELD_RADIUS, SURVIVAL_SECONDS)
    if entry.kind == "devourer":
        from .maw import (MawFloor, MINION_CAP, ARRIVAL_CAP, SUMMON_WARNING, SUMMON_LIFE,
                          SUMMON_ROSTER, PULL_WARNING, PULL_STRENGTHS, PULL_LIVES, RECOVERY)
        from .void import VOID_FREEZE_CAP, VOID_FROST_RESISTANCE
        attacks = enemy_base_attacks(entry)
        params = dict(reach=14, interval=RECOVERY, stationary=True,
                      pull_warning_seconds=PULL_WARNING, pull_tiles_per_second=PULL_STRENGTHS,
                      pull_life_seconds=PULL_LIVES, core_radius_tiles=1.5,
                      summon_cap=MINION_CAP, pending_arrival_cap=ARRIVAL_CAP,
                      summon_warning_seconds=SUMMON_WARNING, summon_life_seconds=SUMMON_LIFE,
                      summon_roster=SUMMON_ROSTER, freeze_cap=VOID_FREEZE_CAP,
                      frost_resistance=VOID_FROST_RESISTANCE)
        attack_range, interval = params["reach"], params["interval"]
        resistances = f"Freeze cap {VOID_FREEZE_CAP}s; subsequent freeze resisted for {VOID_FROST_RESISTANCE}s."
        implementation = MawFloor.update_enemy
    elif entry.kind in TEMPORAL_STATS:
        attacks = enemy_base_attacks(entry)
        params = {"rift_warden": dict(reach=7, interval=3.2, warning=SHOT_WARNING,
                                       portal_warning_seconds=PORTAL_WARNING, echo_warning_seconds=ECHO_WARNING,
                                       echo_repeats=1, projectile_speed=3.8),
                  "chronal_scholar": dict(reach=7, interval=6.5, warning=FIELD_WARNING,
                                          field_radius_tiles=FIELD_RADIUS, field_life_seconds=FIELD_LIFE),
                  "dimensional_anchor": dict(reach=0, interval=0, damageable_during="exposure"),
                  "hourless_breach": dict(reach=14, interval=0, required_anchor_cycles=3,
                                           survival_window_seconds=SURVIVAL_SECONDS,
                                           prison_seconds=ABILITIES["r"].duration,
                                           reserved_prison_cast=True, checkpoint_retry=True,
                                           health_represents="remaining anchor/survival cycles")}[entry.kind].copy()
        if entry.kind == "rift_warden":
            attacks = {"arcane": scaled_damage(TEMPORAL_STATS[entry.kind][3], floor),
                       "temporal_echo": scaled_damage(TEMPORAL_STATS[entry.kind][3], floor)}
        attack_range, interval = params["reach"], params["interval"]
        resistances = "Direct damage and freeze cannot close the breach; complete its three cycles." if entry.kind == "hourless_breach" else "None implemented"
        implementation = TemporalFloor.update_enemy
    elif entry.kind in DEPTH_STATS:
        from .void import VOID_FREEZE_CAP, VOID_FROST_RESISTANCE
        attacks = enemy_base_attacks(entry)
        params = {"lasher": dict(reach=7, interval=5, warning=1.4, lane_radius_tiles=.4),
                  "grasper": dict(reach=7, interval=5, warning=1.5, grasp_seconds=ROOT_DURATION),
                  "anchor": dict(reach=7, interval=7, warning=1.6, force_tiles_per_second=.9),
                  "thrall": dict(reach=7, interval=3.2, warning=.95, projectile_speed=3.8),
                  "gravity_adept": dict(reach=7, interval=7, warning=1.6, force_tiles_per_second=.85, explosion_radius_tiles=1.3),
                  "repulsor": dict(reach=7, interval=5, warning=1.6, force_tiles_per_second=1.5, force_radius_tiles=5),
                  "star_fragment": dict(reach=.6, interval=.65, orbit_radius_tiles=1.4),
                  "oracle": dict(reach=8, interval=5, warning=1.7, channeler_damage_multiplier=ORACLE_PROTECTION),
                  "astronomer": dict(reach=14, interval=1.3, warning=1.8,
                                      pull_tiles_per_second=1.35, push_tiles_per_second=2.2,
                                      orbit_radius_tiles=3.5, central_danger_radius_tiles=1.5)}[entry.kind].copy()
        if entry.kind == "thrall":
            attacks = {"arcane": scaled_damage(DEPTH_STATS["thrall"][3], floor)}
        resistances = "None implemented; freeze interrupts pending warnings."
        if entry.kind in BOSS_HEALTH:
            params.update(freeze_cap=VOID_FREEZE_CAP, frost_resistance=VOID_FROST_RESISTANCE)
            resistances = f"Freeze cap {VOID_FREEZE_CAP}s; subsequent freeze resisted for {VOID_FROST_RESISTANCE}s."
        attack_range, interval = params["reach"], params["interval"]
        implementation = VoidDepths.update_enemy
    elif entry.kind in ("voidling", "binder", "voidwalker"):
        from .void import (VoidFloor, DARK_DAMAGE, DARK_GRACE, BINDER_WARNING, BINDER_INTERVAL,
                           LUNGE_WARNING, LUNGE_REACH, LUNGE_SPEED, SWEEP_WARNING, SWEEP_RADIUS, ZONE_CAP,
                           VOID_FREEZE_CAP, VOID_FROST_RESISTANCE)
        attacks = enemy_base_attacks(entry)
        if entry.kind == "voidling":
            attacks = {"claw": scaled_damage(8, floor)}
            params = dict(reach=.5, interval=1.1)
        elif entry.kind == "binder":
            params = dict(reach=7, interval=BINDER_INTERVAL, warning=BINDER_WARNING,
                          darkness_life_seconds=4, darkness_radius_tiles=1,
                          darkness_grace_seconds=DARK_GRACE, shared_darkness_cap=ZONE_CAP)
        else:
            params = dict(reach=LUNGE_REACH, interval=2, warning=LUNGE_WARNING,
                          lunge_speed=LUNGE_SPEED, sweep_warning_seconds=SWEEP_WARNING,
                          sweep_radius_tiles=SWEEP_RADIUS, thresholds=(2 / 3, 1 / 3),
                          damage_received_in_recovery_multiplier=RECOVERY_DAMAGE_MULTIPLIER)
        attack_range, interval = params["reach"], params["interval"]
        resistances = "None implemented; freeze interrupts committed attacks."
        if entry.kind == "voidwalker":
            params.update(freeze_cap=VOID_FREEZE_CAP, frost_resistance=VOID_FROST_RESISTANCE)
            resistances = f"Freeze cap {VOID_FREEZE_CAP}s; subsequent freeze resisted for {VOID_FROST_RESISTANCE}s."
        implementation = VoidFloor.update_enemy
    elif entry.kind == "keeper":
        attacks = dict(KEEPER_DAMAGE)
        params = asdict(TUNING)
        params["selected_stage_interval_seconds"] = TUNING.intervals[stage - 1]
        resistances = f"Freeze cap {TUNING.freeze_cap}s; subsequent freeze resisted for {TUNING.frost_resistance}s (not damage resistance)."
        attack_range = "Duty zones; no conventional attack range"
        interval = TUNING.intervals[stage - 1]
        implementation = KeeperFight
    elif entry.kind in CREATURE:
        params = CREATURE[entry.kind].copy()
        attack = "orb" if entry.kind == "arcane" else "charge" if entry.kind == "crystal" else "pounce"
        raw = ENEMY_STATS[entry.kind][3]
        attacks[attack] = scaled_damage(raw, floor) if entry.kind == "arcane" else raw
        resistances = "None implemented"
        attack_range, interval = params["reach"], params["interval"]
        implementation = update_creature
    else:
        params = dict(RANGED[entry.kind]) if entry.kind in RANGED else dict(reach=MELEE_REACH, interval=MELEE_INTERVAL)
        attacks["potion" if entry.kind == "fairy" else "arrow" if entry.kind == "archer" else "melee"] = scaled_damage(ENEMY_STATS[entry.kind][3], floor)
        if entry.role == "boss":
            from .encounters import BOSSES
            attacks[BOSSES[entry.floor][2]] = SIGNATURE_DAMAGE[entry.floor]
            params.update(SIGNATURE[entry.floor])
            params["signature_interval_seconds"] = SIGNATURE_INTERVAL
            params["damage_received_in_recovery_multiplier"] = RECOVERY_DAMAGE_MULTIPLIER
            if entry.floor == 1:
                params["damage_received_with_unfrozen_shield_multiplier"] = SHIELD_DAMAGE_MULTIPLIER
            if entry.floor == 2:
                params.update(tender_healing_hp_per_second=TENDER_HEAL_HP_PER_SECOND, tender_range_tiles=TENDER_HEAL_RANGE_TILES)
            if entry.floor == 3:
                params["pool_damage_to_duplicate_base_hp"] = DUPLICATE_POOL_BASE_DAMAGE
        resistances = "Conditional shield reduction; see parameters" if entry.id == "oathbound_warden" else "None implemented"
        attack_range, interval = params["reach"], params["interval"]
        if entry.id == 'rootbound_heart':
            # The level-two boss update returns before the inherited melee path.
            attacks.pop('melee', None)
            params.pop('reach', None)
            params.pop('interval', None)
            attack_range = 'Shrinking cage zone; see radius and gap parameters'
            interval = SIGNATURE_INTERVAL
        implementation = signature if entry.role == "boss" else World._archer if entry.kind in RANGED else World._update_simulation
    if entry.kind in CREATURE:
        if 'lunge_speed' in params:
            params['effective_lunge_speed_tiles_per_second'] = params['lunge_speed'] * (ICE_PATCH_MOVE_FACTOR if patch else 1) * (LUNGE_CHILL_FACTOR if chilled else 1)
            params['lunge_speed_note'] = 'No phase multiplier; separate from ordinary movement'
    parameter_units = {
        'reach': 'tiles', 'warning': 'seconds', 'interval': 'seconds',
        'projectile_speed': 'tiles_per_second', 'projectile_life': 'seconds',
        'lunge_speed': 'tiles_per_second', 'lunge_duration': 'seconds',
        'recovery': 'seconds', 'blocked_recovery': 'seconds',
        'health': 'hp', 'thresholds': 'health_ratio', 'summon_cap': 'actors',
        'summon_life': 'seconds', 'freeze_cap': 'seconds', 'frost_resistance': 'seconds',
        'vine_life': 'seconds', 'vine_speed': 'movement_multiplier',
        'nova_suppression': 'seconds', 'spill_life': 'seconds',
        'warning_min': 'seconds', 'warning_max': 'seconds', 'reaction_margin': 'seconds',
        'opening_delay': 'seconds', 'intervals': 'seconds_by_stage', 'completion_gold': 'gold',
    }
    params = {key + ('_' + parameter_units[key] if key in parameter_units else ''): value for key, value in params.items()}
    rate = ICE_PATCH_ATTACK_FACTOR if patch else 1
    speed = actor.move_speed * (ICE_PATCH_MOVE_FACTOR if patch else 1) * (1 - ABILITIES['q'].slow if chilled else 1)
    return dict(id=entry.id, name=entry.name, category=entry.category,
        source='; '.join([definition_location('world', 'ENEMY_STATS'),
            *([definition_location('encounters', 'BOSSES' if entry.role == 'boss' else 'COMPANIONS')] if entry.floor and entry.floor <= 3 else []),
            f'dungeon/{source(Enemy)}', f'dungeon/{source(implementation)}', 'dungeon/combat_values.py']),
        preview=f"floor={floor}, phase={phase}, Keeper stage={stage}, Ice Patch={patch}, chilled={chilled}",
        base_health_hp=base.max_hp, effective_health_hp=actor.max_hp,
        base_damage_hp_per_hit=enemy_base_attacks(entry), effective_damage_hp_per_hit=attacks,
        configured_movement_speed_tiles_per_second=base.move_speed,
        base_speed_tiles_per_second=0 if entry.id == 'rootbound_heart' else base.move_speed, effective_speed_tiles_per_second=0 if entry.id == 'rootbound_heart' else round(speed, 5),
        base_attack_interval_seconds=TUNING.intervals[0] if entry.kind == "keeper" else interval,
        attack_interval_seconds=interval, effective_attack_interval_seconds=round(interval / rate, 5),
        attack_range_tiles=attack_range, detection_range_tiles="Not implemented; pursuit uses pathfinding (Codex visibility is separate)",
        resistances=resistances, immunities="None permanent implemented", parameters=params,
        modifiers=dict(health_per_floor=0 if entry.kind in ("keeper", "voidwalker", "devourer", *BOSS_HEALTH, *FIXED_HEALTH) else HEALTH_PER_FLOOR,
                       standard_attack_damage_per_floor=0 if entry.kind in ("keeper", "crystal", "predator", "binder", "voidwalker", "devourer", *(k for k in DEPTH_STATS if k != "thrall")) or entry.id == "rootbound_heart" else DAMAGE_PER_FLOOR,
                       signature_and_lunge_damage="Fixed; no floor multiplier", phase_speed=PHASE_SPEEDS[phase - 1],
                       attack_clock_rate=rate, chill_movement_multiplier=1-ABILITIES['q'].slow if chilled else 1,
                       note="Intervals exclude warning/recovery and scheduling delays; damage precedes player armor/invulnerability."))


def enemy_base_attacks(entry):
    from .world import ENEMY_STATS
    from .void import DARK_DAMAGE, LUNGE_DAMAGE, SWEEP_DAMAGE
    from .void_depths import DAMAGE, DEPTH_STATS
    if entry.kind == "devourer":
        return {"Inward Convergence": DAMAGE["convergence"], "Grasping Chorus": DAMAGE["chorus"], "Lashing Strike": DAMAGE["lash"]}
    if entry.kind in ("rift_warden", "chronal_scholar", "dimensional_anchor", "hourless_breach"):
        return {"arcane": 9, "temporal_echo": 9} if entry.kind == "rift_warden" else {}
    if entry.kind in DEPTH_STATS:
        return {"lasher": {"Lashing Strike": DAMAGE["lash"]},
                "grasper": {"Grasping Strike": DAMAGE["grasp"]},
                "anchor": {"darkness": DARK_DAMAGE}, "thrall": {"arcane": DEPTH_STATS["thrall"][3]},
                "oracle": {"Searching Gaze": DAMAGE["gaze"], "Grasping Chorus": DAMAGE["chorus"]},
                "gravity_adept": {"Collapsing Star": DAMAGE["well"]}, "repulsor": {},
                "star_fragment": {"Orbiting Fragment": DAMAGE["fragment"]},
                "astronomer": {"Inward Convergence": DAMAGE["convergence"], "Orbiting Ruin": DAMAGE["orbit"],
                               "Collapsing Star": DAMAGE["well"]}}[entry.kind]
    if entry.kind == "binder":
        return {"darkness": DARK_DAMAGE}
    if entry.kind == "voidwalker":
        return {"Rift Lunge": LUNGE_DAMAGE, "Rending Sweep": SWEEP_DAMAGE, "darkness": DARK_DAMAGE}
    if entry.kind == "voidling":
        return {"claw": 8}
    if entry.kind == 'keeper':
        return dict(KEEPER_DAMAGE)
    name = 'orb' if entry.kind == 'arcane' else 'charge' if entry.kind == 'crystal' else 'pounce' if entry.kind == 'predator' else 'potion' if entry.kind == 'fairy' else 'arrow' if entry.kind == 'archer' else 'melee'
    values = {name: ENEMY_STATS[entry.kind][3]}
    if entry.role == 'boss':
        from .encounters import BOSSES
        values[BOSSES[entry.floor][2]] = SIGNATURE_DAMAGE[entry.floor]
    if entry.id == 'rootbound_heart':
        values.pop('melee', None)
    return values


def tactics(entry):
    text = {
        'devourer': 'A stationary giant half embedded in a dimensional floor rupture. Damage it directly; it has no shield. Watch the locked tentacle circles and lanes, move outward before gravity draws you into its damaging core, and clear marked portal arrivals. It summons regular creatures from Floors 6–9, at most six at once. Pulls and grabs exclude one another. Glacial Prison resists gravity but is optional and uses its normal mana/cooldown. Brief freezes cancel pending attacks and arrivals; active fields finish their visible lifetime.',
        'rift_warden': 'Portal exits are marked before arrival and checked again for occupancy. Its slow arcane shot locks aim; a pale temporal echo repeats that exact shot once. Freeze cancels an unfinished portal or shot. Stasis fields hold projectiles briefly without aging them.',
        'chronal_scholar': 'Places a marked stasis circle that pauses friendly and hostile projectiles. The release countdown warns when their original movement will resume. Freeze interrupts a pending field; released fields expire independently.',
        'dimensional_anchor': 'Damage the exposed anchor during each Hourless Breach cycle. Breaking it begins Stopped Hour; prepare to use R. Anchors do not award repeat-attempt loot.',
        'hourless_breach': 'An environmental encounter. Learn ice anchoring in a safe repeatable lesson. Break each of three anchors, then press R immediately when Stopped Hour begins. A reserved Prison cast bypasses mana, cooldown and cast recovery during the cue; an already-active Prison is extended safely. Unanchored failure returns to the nearby checkpoint with restored resources. Shop transactions persist and encounter adds grant no farmable loot.',
        'lasher': 'A stationary tentacle locks a lane, then lashes it. Sidestep the gold lane; freeze interrupts the warning.',
        'grasper': 'Marks your location, then roots you if the strike connects. Move out of the ring. If caught, attack or freeze the grasping tentacle; spells and potions remain available. Restraint expires after 2.2 seconds.',
        'anchor': 'Channels a warned pull toward its own darkness pool. Destroy or freeze the anchor to break the pull. Keep moving away; Prison anchors you. Released darkness expires independently.',
        'thrall': 'An enthralled wizard fires slow arcane bolts after a locked aim warning. Sidestep or use cover; freeze interrupts casting.',
        'oracle_channeler': 'A stationary enthralled wizard protects the Oracle while alive and unfrozen within eight tiles. Defeat or freeze it to expose the boss. Channelers expire after 24 seconds.',
        'oracle': 'Break or freeze its channelers to remove 80% damage protection. Avoid the sweeping gaze and staggered tentacle circles. Destroy summoned anchor tentacles. Gaze is cancelled during a grasp. Brief freezes interrupt warnings, followed by resistance.',
        'gravity_adept': 'Marks a star at your location. Leave the attraction circle before its final central explosion. Freeze interrupts the warning; released stars keep their lifetime.',
        'repulsor': 'Warns before an outward force pulse. Move toward its center or leave its radius before release. Walls stop displacement; Prison prevents it.',
        'star_fragment': 'Travels around a fixed circular orbit and damages on contact. Watch its path; frost and Ice Patch slow it. Freeze stops it.',
        'astronomer': 'Stationary inside a broken celestial instrument. Move outward for Convergence, inward for Rejection; pulses have a neutral recovery interval. Avoid orbiting fragments and leave collapsing stars. Later health stages combine one gravity field with orbiting ruin. Prison resists forces; brief freezes interrupt warnings.',
        'voidling': 'Pursues and claws in melee. Keep distance with Bolt and Ice Patch.',
        'binder': 'Marks your location before releasing darkness. Move out of the gold ring; freeze the caster before release to cancel it. Active fields expire and have a brief entry grace period.',
        'voidwalker': 'Targets the nearest mage or binder. Sidestep the locked lunge lane; leave the sweep fan. Brief freezes interrupt attacks, followed by temporary freeze resistance. Punish recovery for bonus damage. At two-thirds and one-third health it breaks a pillar and calls voidlings. Later lunges leave expiring darkness. Summons are recalled on victory.',
        'keeper': 'Stationary; marked repair lines and cleaning zones deal damage. Follow safe markers. Nova suppresses vines. Brief freezes have a resistance window; Ice Patch slows duty clocks. Later stages overlap duties and summon specimens; Prison protects during damage windows.',
        'crystal': 'Pursues, warns, then charges in a locked direction. Sidestep the lane; terrain stops the charge. Nova interrupts it; Ice Patch slows the lunge and attack clock.',
        'predator': 'Closes distance, crouches, then pounces along a locked direction. Sidestep after the warning. Nova interrupts; Ice Patch slows the pounce.',
        'arcane': 'Approaches to cast a slow straight orb, retreats when too close. Dodge sideways; freeze interrupts the warning. Ice Patch slows movement and casting.',
        'archer': 'Pursues until in firing range and retreats nearby. Aim locks during the warning. Move sideways; freeze cancels the shot; cover breaks the aim line.',
        'fairy': 'Pursues and throws aimed potions, retreating nearby. Sidestep the locked aim line or use cover. Freeze interrupts the warning.',
        'oathbound_warden': 'Pursues and uses Winterbreaker charge. Sidestep the marked lane. Unfrozen shields reduce incoming damage; freeze or defeat them. Attack during recovery for increased damage.',
        'rootbound_heart': 'Stationary heart casts a shrinking Briar Cage. Exit through its gap. Nearby unfrozen tenders heal it; freeze or defeat them. Attack during recovery.',
        'splintered_alchemist': 'Pursues and casts sequential Chain Reaction pools. Leave the marked pools; lure duplicates into them. Freeze cancels owned hazards. Attack during recovery.',
        'animated_shield': 'Pursues and strikes in melee. Freeze it to disable the Warden\'s protection; keep space with Bolt and Ice Patch.',
        'thorn_tender': 'Pursues and strikes in melee; heals its nearby heart while unfrozen. Freeze it or defeat it before focusing the heart.',
        'volatile_duplicate': 'Throws aimed potions; vulnerable to its master\'s potion pools. Lure it into marked pools and move out yourself.',
    }.get(entry.id, 'Pursues along walkable paths and strikes in melee. Kite with Frost Bolt; freeze with Nova to stop attacks. Ice Patch slows movement and attack clocks.')
    return text + ' Stand in your Ice Patch for stronger frost damage. Glacial Prison prevents damage while active, then shatters nearby enemies.'


def item_values(key, rank):
    from dataclasses import replace
    definition = DEFINITIONS[key]
    minimum = 3 if definition.set_id else 1
    available = minimum <= rank <= definition.max_rank
    item = replace(item_templates()[key], rank=rank) if available else item_templates()[key]
    return dict(id=key, name=definition.name, slot=definition.slot,
        source=f"dungeon/{source(Item)}; {definition_location('items', 'DEFINITIONS')}; {definition_location('items', 'NEW_DEFINITIONS')}",
        preview=f'rank={rank} ({RANK_NAMES[rank]})',
        availability='Available' if available else f'Unavailable: supported ranks {minimum}–{definition.max_rank}',
        kind='Catalog template; not a rolled or owned instance. Ordinary values below use midpoint quality.',
        base_stats=item.lines if definition.set_id else ['One enchantment slot; no legacy fixed bonuses'],
        effective_stats=item.lines if available else ['Unavailable at this rank'],
        roll_ranges={f'rank {r}': f'{low / 10:.1f}–{high / 10:.1f}% {EFFECT_LABELS[definition.effect]}' for r, (low, high) in enumerate(definition.ranges, 1)} if not definition.set_id else 'None: fixed Frostweave bonuses',
        enchantment_slots=0 if definition.set_id else 1,
        enchantment_progression={f'rank {r}': f'{ENCHANT_COST[r]} gold (next step)' for r in range(minimum + 1, definition.max_rank + 1)},
        roll_upgrade_rule='Preserve the original percentile; never reroll during enchanting',
        set_membership=definition.set_id or 'None',
        acquisition='First Keeper victory gives a Rank 3 crown and unlocks Rank 3 stock/drops' if definition.set_id else 'Ordinary drop pool; stock includes the five original templates',
        icon_description=definition.icon,
        set_bonuses=(dict(required='All five equipped; set rank is the minimum equipped rank', bolt_freeze_chance=FROSTWEAVE_CHANCE,
            freeze_seconds=FROSTWEAVE_FREEZE, rank5='Prison cast inside its still-active Ice Patch: triple critical shatter and double radius') if definition.set_id else 'None'))


def flatten(values, prefix=''):
    lines = []
    for key, value in values.items():
        label = (prefix + str(key)).replace('_', ' ')
        if isinstance(value, dict):
            lines.extend(flatten(value, label + ' / '))
        else:
            lines.append(f'{label}: {"Absent" if value is None else value}')
    return lines


class Codex:
    """UI state only. Developer visibility and preview contexts never touch saves."""
    def __init__(self, development=False):
        self.development = development
        self.show_undiscovered = False
        self.tab = 'Bestiary'
        self.selected = None
        self.query = ''
        self.category = None
        self.floor_filter = None
        self.slot = None
        self.rank_filter = None
        self.sort = 'name'
        self.floor, self.phase, self.stage, self.rank = 1, 1, 1, 1
        self.patch = self.chilled = False
        self.scroll = self.detail_scroll = 0
        self.search_active = False
        self.return_mode = 'playing'
        self.notice = ''
        self.buttons = []

    @property
    def developer_view(self):
        return self.development and self.show_undiscovered

    def open(self, mode):
        if mode != 'codex':
            self.return_mode = mode
        return 'codex'

    def close(self):
        return self.return_mode

    def rows(self, player):
        rows = []
        definitions = species() if self.tab == 'Bestiary' else item_templates()
        for key, definition in definitions.items():
            record = player.bestiary.get(key, {}) if self.tab == 'Bestiary' else {}
            known = bool(record.get('encountered')) if self.tab == 'Bestiary' else key in player.item_discoveries
            visible = known or self.developer_view
            if not visible:
                # Unknown rows never participate in semantic search/filter/sort.
                if not (self.query or self.category or self.floor_filter or self.slot or self.rank_filter is not None):
                    rows.append(dict(id=key, name='Unknown entry', locked=True, metric=None))
                continue
            name = definition.name
            if self.query.casefold() not in (name + (' ' + key if self.developer_view else '')).casefold():
                continue
            if self.tab == 'Bestiary':
                if self.category and definition.category != self.category:
                    continue
                if self.floor_filter and self.floor_filter not in record.get('floors', []):
                    continue
                details = enemy_values(definition, self.floor, self.phase, self.stage, self.patch, self.chilled) if self.developer_view or record.get('defeated') else {}
                metric = {'health': details.get('effective_health_hp'), 'speed': details.get('effective_speed_tiles_per_second'),
                    'damage': max(details.get('effective_damage_hp_per_hit', {}).values(), default=0) if details else None}.get(self.sort)
            else:
                if self.rank_filter is not None and not (3 if definition.set_id else 1) <= self.rank_filter <= definition.max_rank:
                    continue
                if self.slot and definition.slot != self.slot:
                    continue
                if self.rank_filter is not None and not self.developer_view and not any(item_id(i) == key and i.rank == self.rank_filter for i in player.inventory.items):
                    continue
                metric = None
            rows.append(dict(id=key, name=name, locked=False, metric=metric, slot=getattr(definition, 'slot', ''),
                rank=max((i.rank for i in player.inventory.items if item_id(i) == key), default=-1)))
        return sorted(rows, key=lambda row: (row['locked'], row.get('slot', '') if self.sort == 'slot' else '',
            -row.get('rank', -1) if self.sort == 'rank' and not self.developer_view else 0,
            row['metric'] is None, -(row['metric'] or 0), row['name'].casefold()))

    def details(self, player, key):
        if self.tab == 'Item Catalog':
            if not self.developer_view and key not in player.item_discoveries:
                return ['Locked entry. Collect this equipment to learn more.']
            return flatten(item_values(key, self.rank))
        record = player.bestiary.get(key, {})
        if not self.developer_view and not record.get('encountered'):
            return ['Locked entry. Encounter this creature to learn more.']
        entry = species()[key]
        lines = [entry.name, 'Category: ' + entry.category, 'Lore: ' + FLAVOR.get(key, FLAVOR.get(entry.kind, 'A creature inhabiting the Tower.')),
            'Encountered floors: ' + (', '.join(map(str, record.get('floors', []))) or 'None'),
            f"Lifetime defeats: {record.get('defeats', 0)}", 'First encounter (UTC): ' + str(record.get('first_encounter') or 'Never'),
            'First defeat (UTC): ' + str(record.get('first_defeat') or 'Never')]
        if self.developer_view or record.get('defeated'):
            lines += ['Mechanics / advice: ' + tactics(entry)]
            if record.get('health_range'):
                lines += [f"Observed maximum health range (HP): {record['health_range'][0]}–{record['health_range'][1]}"]
            values = enemy_values(entry, self.floor, self.phase)
            # Player-facing projections include only this defeated species and
            # omit unrelated developer context, internal IDs and source paths.
            values = {key: value for key, value in values.items() if key not in ('id', 'name', 'category', 'source', 'preview', 'modifiers')}
            lines += [f'Preview: floor {self.floor}, spawn phase {self.phase}; base values use floor 1 / phase 1.']
            lines += flatten(values)
        else:
            lines += ['Combat details unlock after the first defeat.']
        if self.developer_view:
            # Inspectors reach IDs and numeric values immediately; lore and
            # progression remain distinct further down the same scroll panel.
            lines = flatten(enemy_values(entry, self.floor, self.phase, self.stage, self.patch, self.chilled)) + lines[:7] + ['Mechanics / advice: ' + tactics(entry)]
        return lines

    def copy_details(self, player):
        if not self.selected:
            return ''
        rows = {row['id']: row for row in self.rows(player)}
        if self.selected not in rows or rows[self.selected]['locked']:
            return 'Locked entry.'
        return '\n'.join((['Developer View (read-only)'] if self.developer_view else []) + self.details(player, self.selected))

    def draw(self, r, world, mouse):
        import pygame
        from .armory import Armory, item_icon
        from .geometry import unproject
        from .render import ORIGIN
        screen = r.screen
        screen.fill((9, 15, 23))
        ice, white, muted = (139, 216, 248), (232, 230, 217), (145, 164, 174)
        self.buttons = []
        def button(action, label, rect):
            rect = pygame.Rect(rect)
            self.buttons.append((action, rect))
            Armory.button(r, rect, label)
        r.text('CODEX' + (' / Developer View' if self.developer_view else ''), 45, 24, 29, ice)
        r.character_portrait((1178, 44), 48, world.player)
        button('tab:Bestiary', '1  Bestiary', (45, 72, 200, 34))
        button('tab:Item Catalog', '2  Item Catalog', (255, 72, 220, 34))
        button('close', 'Close / Esc', (1225, 28, 170, 36))
        if self.development:
            button('developer', ('[x]' if self.show_undiscovered else '[ ]') + ' Show undiscovered content', (780, 74, 410, 34))
        rows = self.rows(world.player)
        total = len(species()) if self.tab == 'Bestiary' else len(item_templates())
        known = sum(key in world.player.bestiary for key in species()) if self.tab == 'Bestiary' else sum(key in world.player.item_discoveries for key in item_templates())
        r.text(f'{self.tab}  |  Discovered {known} / {total}  |  {len(rows)} shown', 45, 120, 15, white)
        button('search', ('Search: ' + self.query + ('_' if self.search_active else ''))[:65], (45, 152, 590, 34))
        if self.tab == 'Bestiary':
            button('category', 'Category: ' + (self.category or 'All'), (45, 200, 300, 32))
            button('filter_floor', 'Encountered floor: ' + str(self.floor_filter or 'All'), (355, 200, 280, 32))
            button('sort', 'Sort: ' + self.sort + ' (descending values)', (45, 242, 590, 32))
        else:
            button('sort', 'Sort: ' + self.sort, (45, 242, 590, 32))
            button('slot', 'Slot: ' + (self.slot or 'All'), (45, 200, 280, 32))
            button('rank_filter', 'Rank: ' + str(self.rank_filter if self.rank_filter is not None else 'All'), (335, 200, 300, 32))
        if self.tab == 'Bestiary':
            if self.developer_view or world.player.bestiary.get(self.selected, {}).get('defeated'):
                button('floor', f'Preview floor {self.floor}', (680, 152, 225, 32))
                button('phase', f'Phase {self.phase}', (915, 152, 150, 32))
            if self.developer_view:
                button('stage', f'Keeper stage {self.stage}', (1075, 152, 260, 32))
                button('patch', f'Ice Patch: {self.patch}', (680, 194, 245, 32))
                button('chilled', f'Chilled: {self.chilled}', (935, 194, 245, 32))
        else:
            button('rank', f'Preview rank {self.rank} / {RANK_NAMES[self.rank]}', (680, 152, 510, 32))
        button('copy', 'Copy details', (1200, 242, 195, 32))
        r.text('Read-only preview. Scroll either panel; click filters to cycle.', 680, 242, 12, muted)
        left = pygame.Rect(45, 290, 590, 480)
        right = pygame.Rect(665, 290, 730, 480)
        pygame.draw.rect(screen, (19, 29, 40), left, border_radius=7)
        pygame.draw.rect(screen, (19, 29, 40), right, border_radius=7)
        if self.selected not in {row['id'] for row in rows}:
            self.selected = rows[0]['id'] if rows else None
            self.detail_scroll = 0
        self.scroll = min(max(0, self.scroll), max(0, len(rows) - 10))
        for index, row in enumerate(rows[self.scroll:self.scroll + 10]):
            y = 302 + index * 46
            rect = pygame.Rect(55, y, 570, 40)
            self.buttons.append(('select:' + row['id'], rect))
            if row['id'] == self.selected:
                pygame.draw.rect(screen, (37, 67, 86), rect, border_radius=4)
            label = '[?]  Unknown entry' if row['locked'] else row['name']
            if row['metric'] is not None:
                label += f"  /  {row['metric']:g}"
            r.text(label, 69, y + 11, 15, muted if row['locked'] else white)
        if not rows:
            r.text('No discovered entries match these filters.', 65, 325, 15, muted)
        lines = self.details(world.player, self.selected) if self.selected else ['Select an entry.']
        visible = next((row for row in rows if row['id'] == self.selected), None)
        if visible and not visible['locked']:
            if self.tab == 'Bestiary':
                actor = species()[self.selected].actor(self.floor, self.phase)
                actor.pos = unproject(Vec(1335, 410), ORIGIN)
                screen.set_clip(right)
                r.enemy(actor, 0)
                screen.set_clip(None)
            else:
                item = item_templates()[self.selected]
                item_icon(screen, item.slot, (1340, 337), ice, item=item)
        # Reserve portrait space on every wrapped line to keep long mechanics legible.
        wrapped = []
        for line in lines:
            words, current = line.split(), ''
            for word in words:
                candidate = (current + ' ' + word).strip()
                if r.font(14).size(candidate)[0] > 590 and current:
                    wrapped.append(current)
                    current = word
                else:
                    current = candidate
            wrapped.append(current)
            wrapped.append('')
        self.detail_scroll = min(max(0, self.detail_scroll), max(0, len(wrapped) - 19))
        screen.set_clip(right)
        for i, line in enumerate(wrapped[self.detail_scroll:self.detail_scroll + 19]):
            r.text(line, 685, 302 + i * 24, 14, white if line else muted)
        screen.set_clip(None)
        r.text(f'List {min(len(rows), self.scroll + 1)}–{min(len(rows), self.scroll + 10)} / {len(rows)}', 45, 789, 12, muted)
        r.text(f'Details {self.detail_scroll + 1} / {len(wrapped)} lines · Wheel to scroll', 680, 789, 12, muted)
        r.text(self.notice or ('Developer visibility changes no discoveries, items, counts, or achievements.' if self.developer_view else 'Encounter to identify. Defeat to study combat mechanics.'), 45, 830, 14, ice)

    def click(self, player, point):
        action = next((action for action, rect in self.buttons if rect.collidepoint(point)), None)
        self.search_active = action == 'search'
        self.notice = ''
        def cycle(value, options):
            return options[(options.index(value) + 1) % len(options)] if value in options else options[0]
        if action == 'close':
            return self.close()
        if action == 'developer' and self.development:
            self.show_undiscovered = not self.show_undiscovered
            if not self.show_undiscovered:
                self.patch = self.chilled = False
                self.stage = 1
            self.selected = None
        elif action and action.startswith('tab:'):
            self.tab = action[4:]
            self.query = ''
            self.category = self.floor_filter = self.slot = self.rank_filter = None
            self.sort = 'name'
            self.selected = None
        elif action and action.startswith('select:'):
            self.selected = action[7:]
            if self.tab == 'Item Catalog' and self.selected in DEFINITIONS:
                definition = DEFINITIONS[self.selected]
                self.rank = min(definition.max_rank, max(3 if definition.set_id else 1, self.rank))
        elif action == 'category':
            self.category = cycle(self.category, [None, 'ordinary enemy', 'miniboss', 'boss'])
        elif action == 'filter_floor':
            self.floor_filter = cycle(self.floor_filter, [None, *range(1, PLAYABLE_FLOORS + 1)])
        elif action == 'slot':
            self.slot = cycle(self.slot, [None, *SLOTS])
        elif action == 'rank_filter':
            self.rank_filter = cycle(self.rank_filter, [None, 0, 1, 2, 3, 4, 5])
            if self.rank_filter is not None:
                self.rank = self.rank_filter
        elif action == 'sort':
            self.sort = cycle(self.sort, ['name', 'health', 'damage', 'speed'] if self.tab == 'Bestiary' else ['name', 'slot', 'rank'])
        elif action == 'rank':
            definition = DEFINITIONS.get(self.selected)
            options = list(range(3, 6)) if definition and definition.set_id else [1, 2, 3]
            self.rank = cycle(self.rank, options)
        elif action in ('floor', 'phase', 'stage'):
            setattr(self, action, cycle(getattr(self, action), list(range(1, PLAYABLE_FLOORS + 1 if action == 'floor' else 4))))
        elif action in ('patch', 'chilled'):
            setattr(self, action, not getattr(self, action))
        elif action == 'copy':
            import pygame
            try:
                if not pygame.scrap.get_init():
                    pygame.scrap.init()
                pygame.scrap.put_text(self.copy_details(player))
                self.notice = 'Details copied as plain text.'
            except (pygame.error, AttributeError):
                self.notice = 'Clipboard unavailable in this display session.'
        if action and action not in ('search', 'copy'):
            self.scroll = self.detail_scroll = 0
        return 'codex'

    def event(self, event, player, mouse):
        import pygame
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self.click(player, mouse)
            if event.button in (4, 5):
                attr = 'scroll' if mouse[0] < 650 else 'detail_scroll'
                setattr(self, attr, max(0, getattr(self, attr) + (-3 if event.button == 4 else 3)))
        elif event.type == pygame.MOUSEWHEEL:
            attr = 'scroll' if mouse[0] < 650 else 'detail_scroll'
            setattr(self, attr, max(0, getattr(self, attr) - event.y * 3))
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.search_active = False
                return self.close()
            if self.search_active:
                if event.key == pygame.K_BACKSPACE:
                    self.query = self.query[:-1]
                elif event.key == pygame.K_RETURN:
                    self.search_active = False
                elif getattr(event, 'unicode', '').isprintable():
                    self.query = (self.query + event.unicode)[:80]
                self.scroll = self.detail_scroll = 0
            elif event.key in (pygame.K_1, pygame.K_2):
                self.tab = 'Bestiary' if event.key == pygame.K_1 else 'Item Catalog'
                self.selected = self.category = self.floor_filter = self.slot = self.rank_filter = None
                self.sort, self.query = 'name', ''
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                rows = self.rows(player)
                keys = [row['id'] for row in rows]
                if keys:
                    index = keys.index(self.selected) if self.selected in keys else 0
                    index = min(len(keys) - 1, max(0, index + (-1 if event.key == pygame.K_UP else 1)))
                    self.selected = keys[index]
                    self.scroll = min(index, max(index - 9, self.scroll))
                    self.detail_scroll = 0
        return 'codex'
