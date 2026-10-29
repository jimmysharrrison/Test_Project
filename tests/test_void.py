"""Floor-six counterplay, progression, bounded hazards and live checkpoints."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dungeon.codex import enemy_values, species
from dungeon.geometry import Vec
from dungeon.levels import PLAYABLE_FLOORS
from dungeon.saves import SaveSlots, decode_world, encode_world
from dungeon.void import (GroundZone, DARK_DAMAGE, LUNGE_DAMAGE, PILLARS,
                          POPULATION_CAP, ZONE_CAP, VOID_HEALTH, VOID_FREEZE_CAP, in_sweep)
from dungeon.world import IcePatch, Projectile, World


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def quiet():
    world = World(7, level=6, completion_delay_ms=0)
    world.enemies.clear()
    world.pickups.clear()
    for spawner in world.spawners:
        spawner.timer = 999
    return world


def boss_room():
    world = quiet()
    world.spawners.clear()
    world.void.activate_boss()
    boss = world.void.boss
    world.enemies[:] = [boss]
    boss.pos = Vec(8.5, 7.5)
    world.player.pos = Vec(8.5, 11.5)
    boss.cooldown = 999
    return world, boss


class VoidTests(unittest.TestCase):
    def test_scope_lore_roster_and_spawner_names(self):
        world = World(7, level=6)
        self.assertEqual(PLAYABLE_FLOORS, 10)
        with self.assertRaises(ValueError):
            World(7, level=11)
        self.assertEqual({e.kind for e in world.enemies}, {"binder", "voidling"})
        self.assertEqual({s.name for s in world.spawners}, {"Fractured Binding Circle"})
        self.assertIn("eleven through fifteen", world.level_data.story)
        self.assertIn("without oversight", world.level_data.story)

    def test_two_waves_then_boss_without_resource_reset(self):
        world = quiet()
        world.player.hp, world.player.mana = 63, 20
        world.player.cooldowns["r"] = 40
        for phase in (1, 2):
            self.assertEqual(len(world.spawners), 2 if phase == 1 else 3)
            for s in world.spawners[:]:
                world._hit(s, 10000)
            self.assertFalse(world.exit_open)
            advance(world, 3.05)
        self.assertEqual(world.phase, 3)
        self.assertEqual(world.void.boss.hp, VOID_HEALTH)
        self.assertEqual(world.spawners_defeated, 5)
        self.assertEqual(world.player.hp, 63)
        self.assertGreater(world.player.cooldowns["r"], 33)

    def test_spawn_population_and_binder_caps(self):
        world = World(7, level=6)
        for _ in range(100):
            for s in world.spawners:
                s.timer = 0
            world._spawn(.02)
        self.assertLessEqual(len(world.enemies), POPULATION_CAP)
        self.assertLessEqual(sum(e.kind == "binder" for e in world.enemies), 3)
        self.assertTrue({e.kind for e in world.enemies} <= {"binder", "voidling"})

    def test_binder_locks_position_and_freeze_cancels_warning(self):
        world = quiet()
        binder = world.make_enemy(Vec(6.5, 12.5), "binder")
        advance(world, .1)
        self.assertEqual(len(world.void.zones), 1)
        locked = world.void.zones[0].pos
        world.player.pos = Vec(6.5, 14.5)
        self.assertEqual(world.void.zones[0].pos, locked)
        world._freeze(binder, 2)
        self.assertFalse(world.void.zones)
        advance(world, 1)
        self.assertEqual(world.player.hp, 100)

    def test_darkness_entry_grace_prison_and_expiration(self):
        world = quiet()
        binder = world.make_enemy(Vec(10.5, 12.5), "binder", cooldown=999)
        zone = GroundZone(world.player.pos, binder, warning=0, life=2)
        world.void.zones.append(zone)
        advance(world, .3)
        self.assertEqual(world.player.hp, 100)
        advance(world, .1)
        self.assertEqual(world.player.hp, 100 - DARK_DAMAGE)
        world.player.invincible = 0
        world.player.stasis = 2.5
        advance(world, 1)
        self.assertEqual(world.player.hp, 100 - DARK_DAMAGE)
        advance(world, .7)
        self.assertFalse(world.void.zones)

    def test_active_darkness_survives_caster_death_but_warning_does_not(self):
        world = quiet()
        binder = world.make_enemy(Vec(10.5, 12.5), "binder", cooldown=999)
        active = GroundZone(Vec(8.5, 9.5), binder, warning=0, life=2)
        warning = GroundZone(Vec(6.5, 9.5), binder)
        world.void.zones.extend((active, warning))
        world._hit(binder, 10000)
        advance(world, .1)
        self.assertEqual(world.void.zones, [active])
        advance(world, 2)
        self.assertFalse(world.void.zones)

    def test_darkness_is_capped_separated_and_avoids_terrain(self):
        world = quiet()
        binder = world.make_enemy(Vec(8.5, 8.5), "binder", cooldown=999)
        for point in (Vec(4.5, 7.5), Vec(8.5, 7.5), Vec(12.5, 7.5), Vec(8.5, 11.5)):
            self.assertTrue(world.void.add_darkness(point, binder))
        self.assertEqual(len(world.void.zones), ZONE_CAP)
        self.assertFalse(world.void.add_darkness(Vec(4.5, 11.5), binder))
        world.void.zones.clear()
        self.assertFalse(world.void.add_darkness(Vec(1.1, 1.1), binder))
        self.assertTrue(world.void.add_darkness(Vec(8.5, 8.5), binder))
        self.assertFalse(world.void.add_darkness(Vec(9.5, 8.5), binder))

    def test_warning_accounts_for_committed_prison(self):
        world = quiet()
        binder = world.make_enemy(Vec(10.5, 12.5), "binder", cooldown=999)
        world.player.stasis = 2.5
        self.assertTrue(world.void.add_darkness(world.player.pos, binder))
        self.assertGreaterEqual(world.void.zones[0].warning, 3.3)

    def test_containment_discharge_warns_then_hits_enemies_once_and_can_be_dodged(self):
        world = quiet()
        world.void.discharge_in = 0
        advance(world, .1)
        lane = next(z for z in world.void.zones if z.kind == "discharge")
        point = (lane.pos + lane.end) * .5
        enemy = world.make_enemy(point, "voidling", frozen=10)
        hp = enemy.hp
        world.player.pos = point
        advance(world, .4)
        self.assertEqual(world.player.hp, 100)
        world.player.pos = Vec(3.5, 13.5)
        advance(world, 1.5)
        self.assertEqual(world.player.hp, 100)
        self.assertEqual(hp - enemy.hp, 30)

    def test_wave_cap_reserves_boss_arrival_room(self):
        world = quiet()
        for _ in range(100):
            for spawner in world.spawners:
                spawner.timer = 0
            world._spawn(.02)
        world.spawners.clear()
        self.assertTrue(world.void.activate_boss())
        self.assertLessEqual(len(world.enemies), POPULATION_CAP)

    def test_lunge_is_locked_dodgeable_and_has_recovery(self):
        world, boss = boss_room()
        world.void.begin_attack(boss, "lunge_warning", world.player.pos)
        direction = boss.attack_direction
        world.request_move(Vec(11.5, 11.5))
        advance(world, 2.1)
        self.assertEqual(world.player.hp, 100)
        self.assertEqual(boss.attack_direction, direction)
        self.assertGreater(boss.recovery, 0)
        hp = boss.hp
        world.combat_rng.seed(0)
        world._hit(boss, 100)
        self.assertEqual(hp - boss.hp, 135)

    def test_lunge_hits_and_terrain_stops_swept_motion(self):
        world, boss = boss_room()
        world.void.begin_attack(boss, "lunge_warning", world.player.pos)
        advance(world, 2)
        self.assertEqual(world.player.hp, 100 - LUNGE_DAMAGE)
        world, boss = boss_room()
        world.walls.add((8, 9))
        world.void.begin_attack(boss, "lunge_warning", world.player.pos)
        advance(world, 2)
        self.assertLess(boss.pos.y, 8.7)
        self.assertEqual(world.player.hp, 100)
        self.assertGreater(boss.recovery, 0)

    def test_sweep_uses_front_fan_and_freeze_interrupts(self):
        self.assertTrue(in_sweep(Vec(8, 8), Vec(0, 1), Vec(8, 10)))
        self.assertFalse(in_sweep(Vec(8, 8), Vec(0, 1), Vec(8, 6)))
        world, boss = boss_room()
        world.player.pos = boss.pos + Vec(0, 1.5)
        world.void.begin_attack(boss, "sweep", world.player.pos)
        world._freeze(boss, 1)
        self.assertEqual(boss.action, "")
        advance(world, 1.4)
        self.assertEqual(world.player.hp, 100)

    def test_rage_damages_binders_without_using_player_bonuses_or_crits(self):
        world, boss = boss_room()
        binder = world.make_enemy(boss.pos + Vec(0, 2), "binder", cooldown=999)
        hp = binder.hp
        world.void.begin_attack(boss, "lunge_warning", binder.pos)
        advance(world, 2)
        self.assertLess(binder.hp, hp)
        self.assertEqual((hp - binder.hp) % LUNGE_DAMAGE, 0)

    def test_ice_patch_slows_attack_warning(self):
        world, boss = boss_room()
        world.ice_patches.append(IcePatch(boss.pos))
        world.void.begin_attack(boss, "lunge_warning", world.player.pos)
        advance(world, 1.3)
        self.assertEqual(boss.action, "lunge_warning")

    def test_brief_boss_freeze_interrupts_then_resists_repeated_freezes(self):
        world, boss = boss_room()
        world.void.begin_attack(boss, "lunge_warning", world.player.pos)
        self.assertTrue(world._freeze(boss, 2.25))
        self.assertEqual(boss.frozen, VOID_FREEZE_CAP)
        self.assertEqual(boss.action, "")
        advance(world, .7)
        self.assertFalse(world._freeze(boss, 2.25))
        advance(world, 3)
        self.assertTrue(world._freeze(boss, 2.25))

    def test_skipping_threshold_still_breaks_both_pillars_with_bounded_summons(self):
        world, boss = boss_room()
        boss.hp = boss.max_hp // 4
        world.debug_invulnerable = True
        advance(world, 10)
        self.assertEqual(world.void.broken_pillars, 2)
        self.assertEqual(world.void.stage, 3)
        self.assertLessEqual(sum(e.summoned for e in world.enemies), 4)

    def test_player_can_occupy_summon_warning_without_spawn_overlap(self):
        world, boss = boss_room()
        world.void.begin_attack(boss, "shatter", world.player.pos)
        point = world.void.zones[0].pos
        world.player.pos = point
        advance(world, 1.7)
        self.assertTrue(all((e.pos - point).length() >= .8 for e in world.enemies if e.summoned))

    def test_boss_death_cleans_fight_and_opens_floor_seven_once(self):
        world, boss = boss_room()
        world.void.zones.append(GroundZone(world.player.pos, boss, warning=0))
        world.make_enemy(Vec(12.5, 12.5), "voidling", summoned=True, summon_life=18)
        world.make_enemy(Vec(2.5, 5.5), "binder", cooldown=999)
        world.projectiles.append(Projectile(boss.pos, Vec(), damage=10000))
        world.update(1 / 60)
        self.assertTrue(world.exit_open)
        self.assertTrue(world.void.finished)
        self.assertFalse(world.void.zones)
        self.assertFalse(any(e.summoned for e in world.enemies))
        kills = world.player.kills
        drops = len(world.pickups)
        world._hit(boss, 10000)
        self.assertEqual(world.player.kills, kills)
        self.assertEqual(len(world.pickups), drops)
        world.player.pos = world.exit
        world.update(1 / 60)
        self.assertEqual(world.state, "cleared")
        self.assertTrue(world.next_level())
        self.assertEqual(world.level, 7)

    def test_same_tick_death_takes_precedence_over_clear(self):
        world, boss = boss_room()
        world.player.hp = 1
        world.projectiles.extend((Projectile(boss.pos, Vec(), damage=10000),
                                  Projectile(world.player.pos, Vec(), hostile=True, damage=10000)))
        world.update(1 / 60)
        self.assertEqual(world.state, "dead")
        self.assertFalse(world.level_completed)
        self.assertFalse(world.void.zones)

    @patch("dungeon.codex.datetime", wraps=datetime)
    def test_midfight_roundtrip_preserves_references_and_continuation(self, clock):
        clock.now.return_value = datetime(2026, 10, 24, tzinfo=timezone.utc)
        world, boss = boss_room()
        boss.hp = 700
        world.void.begin_attack(boss, "lunge_warning", world.player.pos)
        world.void.add_darkness(Vec(5.5, 7.5), boss)
        world.selected = boss
        loaded = decode_world(json.loads(json.dumps(encode_world(world))))
        self.assertIs(loaded.void.world, loaded)
        self.assertIs(loaded.void.boss, loaded.selected)
        self.assertIs(loaded.void.zones[0].owner, loaded.selected)
        for current in (world, loaded):
            advance(current, 2.5)
        self.assertEqual(loaded.player.hp, world.player.hp)
        self.assertEqual(loaded.void.boss.pos, boss.pos)
        self.assertEqual(encode_world(loaded), encode_world(world))

    def test_floor_six_slot_persists_codex_timer_and_completed_encounter(self):
        world, boss = boss_room()
        world._hit(boss, 10000)
        with TemporaryDirectory() as folder:
            slots = SaveSlots(Path(folder) / "profile.json")
            self.assertTrue(slots.save(1, world), slots.error)
            loaded = slots.load(1)
            self.assertIsNotNone(loaded, slots.error)
            self.assertTrue(loaded.exit_open)
            self.assertTrue(loaded.player.bestiary["voidwalker"]["defeated"])
            self.assertEqual(loaded.player.timing.floor, 6)
            self.assertEqual(loaded.player.kills, world.player.kills)

    def test_old_terminal_snapshot_can_continue_into_floor_six(self):
        world = World(7, level=5)
        world._hit(world.keeper.boss, 10000)
        world.state = "won"
        snapshot = encode_world(world)
        del snapshot["world"]["data"]["void"]
        loaded = decode_world(snapshot)
        self.assertEqual(loaded.state, "cleared")
        self.assertTrue(loaded.next_level())
        self.assertEqual(loaded.level, 6)
        self.assertIs(loaded.void.world, loaded)

    def test_codex_values_match_floor_six_damage_and_health(self):
        for key in ("voidling", "binder", "voidwalker"):
            values = enemy_values(species()[key], 6, 3)
            self.assertEqual(values["effective_health_hp"], species()[key].actor(6, 3).max_hp)
        self.assertEqual(enemy_values(species()["binder"], 6)["effective_damage_hp_per_hit"], {"darkness": DARK_DAMAGE})


if __name__ == "__main__":
    unittest.main()
