"""Menagerie combat, Keeper fairness, persistent mechanics and save compatibility."""
import json
from math import floor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from dungeon.abilities import ABILITIES
from dungeon.creatures import update_creature
from dungeon.geometry import Vec
from dungeon.keeper import Mechanic, TUNING
from dungeon.levels import MENAGERIE, PLAYABLE_FLOORS
from dungeon.navigation import flood
from dungeon.profile import ProfileStore
from dungeon.world import Enemy, IcePatch, Player, Projectile, World


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def specimen(kind):
    world = World(7, level=4)
    world.enemies.clear()
    world.pickups.clear()
    for device in world.spawners:
        device.timer = 999
    enemy = world.make_enemy(Vec(8.5, 9.5), kind)
    world.player.pos = Vec(8.5, 13.5)
    return world, enemy


def keeper():
    world = World(7, level=5)
    world.keeper.next_cast = 999
    return world, world.keeper, world.keeper.boss


class MenagerieTests(unittest.TestCase):
    def test_two_three_four_devices_intermissions_and_survivors(self):
        world = World(17, level=4)
        world.enemies.clear()
        survivor = world.make_enemy(Vec(14.5, 14.5), "arcane", frozen=100)
        total = 0
        for phase, count in enumerate((2, 3, 4), 1):
            self.assertEqual((world.phase, len(world.spawners)), (phase, count))
            for device in world.spawners[:]:
                self.assertEqual(device.name, "Containment Device")
                self.assertEqual(device.spawn_phase, phase)
                world._hit(device, 10000)
                total += 1
            if phase < 3:
                self.assertFalse(world.exit_open)
                self.assertEqual(world.intermission, 3)
                advance(world, 3.05)
        self.assertEqual(total, 9)
        self.assertTrue(world.exit_open)
        self.assertIn(survivor, world.enemies)
        self.assertTrue(any(p.kind == "gold" for p in world.pickups))
        for _ in range(92):
            world.update(1 / 60)
        world.player.pos = world.exit
        world.update(1 / 60)
        self.assertTrue(world.next_level())
        self.assertEqual(world.level, 5)
        self.assertIs(world.keeper.world, world)
        world._hit(world.keeper.boss, 10000)
        self.assertTrue(world.exit_open)

    def test_roster_and_managed_population_cap(self):
        world = World(7, level=4)
        kinds = set()
        for _ in range(40):
            for device in world.spawners:
                device.timer = 0
            world._spawn(1 / 60)
            kinds.update(e.kind for e in world.enemies)
        self.assertEqual(kinds, {"crystal", "predator", "arcane"})
        self.assertEqual(len(world.enemies), 14)

    def test_charge_direction_is_locked_after_warning(self):
        world, enemy = specimen("crystal")
        advance(world, .1)
        self.assertEqual(enemy.action, "warning")
        locked = enemy.attack_direction
        world.player.pos = Vec(4.5, 13.5)
        advance(world, 1.7)
        self.assertEqual(enemy.attack_direction, locked)
        self.assertEqual(enemy.pos.x, 8.5)
        self.assertGreater(enemy.pos.y, 9.5)
        self.assertEqual(world.player.hp, 100)

    def test_terrain_stops_charge_and_staggers_beast(self):
        world, enemy = specimen("crystal")
        world.walls.update(((7, 11), (8, 11), (9, 11)))
        world._navigation_changed()
        # Begin the charge before the wall is raised.
        enemy.action, enemy.action_time = "lunge", .8
        enemy.attack_direction = Vec(0, 1)
        advance(world, .6)
        self.assertLess(enemy.pos.y, 10.71)
        self.assertGreater(enemy.recovery, .5)
        self.assertEqual(enemy.action, "")
        self.assertEqual(world.player.hp, 100)

    def test_frost_interrupts_specimen_windups(self):
        for kind in ("crystal", "predator", "arcane"):
            world, enemy = specimen(kind)
            world.player.pos = enemy.pos + Vec(0, 2)
            advance(world, .1)
            self.assertEqual(enemy.action, "warning")
            world._freeze(enemy, 2.25)
            advance(world, .1)
            self.assertEqual(enemy.action, "")
            self.assertFalse(world.projectiles)

    def test_predator_warns_then_pounces_and_recovers(self):
        world, enemy = specimen("predator")
        world.player.pos = enemy.pos + Vec(0, 2)
        advance(world, .65)
        self.assertEqual(world.player.hp, 100)
        self.assertEqual(enemy.action, "warning")
        advance(world, .55)
        self.assertEqual(world.player.hp, 89)
        self.assertGreater(enemy.recovery, 0)
        hp = world.player.hp
        advance(world, .5)
        self.assertEqual(world.player.hp, hp)

    def test_at_most_two_lunges_are_telegraphed_together(self):
        world, enemy = specimen("predator")
        world.player.pos = Vec(8.5, 12.5)
        for x in (7.5, 8.5, 9.5):
            world.make_enemy(Vec(x, 10.5), "predator")
        advance(world, .1)
        self.assertEqual(sum(e.action == "warning" for e in world.enemies), 2)

    def test_arcane_bolt_is_slow_and_blocked_by_terrain(self):
        world, enemy = specimen("arcane")
        advance(world, .8)
        self.assertEqual(world.projectiles, [])
        advance(world, .3)
        self.assertTrue(world.projectiles)
        self.assertAlmostEqual(world.projectiles[0].velocity.length(), 3.2)
        world.walls.update(((7, 11), (8, 11), (9, 11)))
        world._navigation_changed()
        advance(world, 2)
        self.assertEqual(world.player.hp, 100)
        self.assertEqual(world.projectiles, [])


class KeeperTests(unittest.TestCase):
    def test_no_spawners_or_automatic_empty_room_completion(self):
        world, fight, boss = keeper()
        advance(world, 1)
        self.assertFalse(world.spawners)
        self.assertFalse(world.exit_open)
        self.assertEqual(world.state, "playing")
        self.assertEqual(boss.hp, TUNING.health)

    def test_health_thresholds_change_stage_without_healing_or_invulnerability(self):
        world, fight, boss = keeper()
        world.combat_rng.random = lambda: 1
        for hp, stage in ((TUNING.health * .8, 1), (TUNING.health * 2 / 3, 2), (TUNING.health / 3, 3)):
            boss.hp = hp
            world.update(1 / 60)
            self.assertEqual((fight.stage, world.phase), (stage, stage))
            self.assertEqual(boss.hp, hp)
            world._hit(boss, 10)
            self.assertEqual(boss.hp, hp - 10)

    def test_stage_one_isolates_and_stage_two_pairs_compatible_attacks(self):
        world, fight, boss = keeper()
        self.assertTrue(fight.start("vines"))
        self.assertFalse(fight.start("repairs"))
        boss.hp = TUNING.health * .6
        world.update(1 / 60)
        self.assertTrue(fight.start("repairs"))
        self.assertEqual(fight.active_kinds, {"vines", "repairs"})
        self.assertFalse(fight.start("cleaning"))
        self.assertFalse(fight.start("specimens"))

    def test_persistent_spills_vines_and_living_summons_count_toward_limit(self):
        world, fight, boss = keeper()
        boss.hp = TUNING.health * .2
        world.update(1 / 60)
        fight.mechanics = [Mechanic("vines", (Vec(10.5, 10.5),), .8, 0, 7),
                           Mechanic("cleaning", (Vec(12.5, 12.5),), 1, 0, 3)]
        self.assertFalse(fight.start("repairs"))
        self.assertFalse(fight.start("specimens"))
        fight.mechanics.pop()
        world.make_enemy(Vec(12.5, 8.5), "arcane", summoned=True, summon_life=20)
        self.assertEqual(fight.active_kinds, {"vines", "specimens"})
        self.assertFalse(fight.start("cleaning"))

    def test_strict_summon_cap_and_finite_recall(self):
        world, fight, boss = keeper()
        boss.hp = TUNING.health * .2
        world.update(1 / 60)
        self.assertTrue(fight.start("specimens"))
        advance(world, 2.2)
        self.assertEqual(len(fight.live_summons), 4)
        for _ in range(10):
            self.assertFalse(fight.start("specimens"))
        for enemy in fight.live_summons:
            enemy.frozen = 30
        advance(world, TUNING.summon_life + .1)
        self.assertEqual(fight.live_summons, [])

    def test_summons_do_not_shield_the_keeper(self):
        world, fight, boss = keeper()
        for x in (4.5, 6.5, 10.5, 12.5):
            world.make_enemy(Vec(x, 7.5), "arcane", summoned=True, summon_life=20)
        before = boss.hp
        world._hit(boss, 24)
        self.assertLess(boss.hp, before)

    def test_spills_warn_and_expire_without_hitting_a_player_who_escapes(self):
        world, fight, boss = keeper()
        self.assertTrue(fight.start("cleaning"))
        mechanic = fight.mechanics[0]
        self.assertGreaterEqual(mechanic.warning, 2)
        world.path = list(mechanic.route[1:])
        advance(world, mechanic.warning + mechanic.life + .2)
        self.assertEqual(world.player.hp, 100)
        self.assertFalse(fight.mechanics)

    def test_ignoring_a_potion_warning_takes_damage_after_impact(self):
        world, fight, boss = keeper()
        fight.start("cleaning")
        advance(world, 1.9)
        self.assertEqual(world.player.hp, 100)
        advance(world, .6)
        self.assertLess(world.player.hp, 100)

    def test_nova_temporarily_suppresses_vines_and_vines_expire(self):
        world, fight, boss = keeper()
        mechanic = Mechanic("vines", (world.player.pos,), .85, 0, 7)
        fight.mechanics.append(mechanic)
        self.assertEqual(fight.slow_at(world.player.pos), TUNING.vine_speed)
        self.assertTrue(world.cast("w"))
        self.assertEqual(fight.slow_at(world.player.pos), 1)
        advance(world, 4.1)
        self.assertEqual(fight.slow_at(world.player.pos), TUNING.vine_speed)
        advance(world, 3)
        self.assertEqual(fight.slow_at(world.player.pos), 1)
        self.assertFalse(fight.mechanics)

    def test_frost_resistance_prevents_lock_and_normal_enemies_keep_full_freeze(self):
        world, fight, boss = keeper()
        self.assertTrue(world._freeze(boss, 2.25))
        self.assertEqual(boss.frozen, TUNING.freeze_cap)
        for _ in range(40):
            world._freeze(boss, 2.25)
            world.update(1 / 60)
        self.assertEqual(boss.frozen, 0)
        self.assertGreater(boss.frost_resistance, 0)
        advance(world, 2.5)
        self.assertTrue(world._freeze(boss, 2.25))
        ordinary = world.make_enemy(Vec(10.5, 10.5), "crystal")
        self.assertTrue(world._freeze(ordinary, 2.25))
        self.assertEqual(ordinary.frozen, 2.25)

    def test_routes_account_for_movement_speed_terrain_vines_and_enemies(self):
        world, fight, boss = keeper()
        world.player.pos = Vec(8.5, 13.5)
        world.walls.update(((7, 12), (8, 12), (9, 12)))
        world._navigation_changed()
        world.make_enemy(Vec(7.5, 13.5), "crystal", frozen=50)
        fight.mechanics.append(Mechanic("vines", (Vec(9.5, 13.5),), .85, 0, 7))
        fight.stage = 3
        self.assertTrue(fight.start("cleaning"))
        mechanic = fight.mechanics[-1]
        self.assertFalse(mechanic.contains(mechanic.safe, .5))
        self.assertGreaterEqual(mechanic.warning, mechanic.route_seconds + TUNING.reaction_margin)
        for a, b in zip(mechanic.route, mechanic.route[1:]):
            self.assertTrue(fight._segment_clear(a, b, mechanic))
        world.path = list(mechanic.route[1:])
        advance(world, mechanic.warning + .1)
        self.assertEqual(world.player.hp, 100)

    def test_no_safe_route_delays_attack_instead_of_trapping_player(self):
        world, fight, boss = keeper()
        x, y = floor(world.player.pos.x), floor(world.player.pos.y)
        world.walls.update(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
        world._navigation_changed()
        self.assertFalse(fight.start("cleaning"))
        self.assertFalse(fight.mechanics)

    def test_changed_wall_geometry_rechecks_a_warning(self):
        world, fight, boss = keeper()
        self.assertTrue(fight.start("cleaning"))
        mechanic = fight.mechanics[0]
        old_safe = mechanic.safe
        world.walls.update(((floor(old_safe.x), floor(old_safe.y)),))
        world._navigation_changed()
        advance(world, .3)
        self.assertTrue(not fight.mechanics or mechanic.safe != old_safe)
        self.assertEqual(world.player.hp, 100)

    def test_safe_areas_across_arena_corners_and_wall_configurations(self):
        for seed in (3, 7, 19, 41):
            for position in (Vec(1.5, 1.5), Vec(15.5, 15.5), Vec(1.5, 15.5), Vec(15.5, 1.5), Vec(8.5, 13.5)):
                world = World(seed, level=5)
                fight = world.keeper
                world.player.pos = position
                # Player-created barriers must be included in the route proof.
                world.walls.update(((7, 10), (8, 10), (9, 10)))
                world._navigation_changed()
                self.assertTrue(fight.start("cleaning"))
                mechanic = fight.mechanics[0]
                self.assertFalse(mechanic.contains(mechanic.safe, .5))
                self.assertGreaterEqual(mechanic.warning, mechanic.route_seconds + TUNING.reaction_margin)
                self.assertTrue(world.walkable(mechanic.safe, .28))

    def test_ongoing_scheduler_never_exceeds_limits(self):
        world, fight, boss = keeper()
        boss.hp = TUNING.health * .2
        world.player.invincible = 90
        fight.next_cast = 0
        seen = set()
        for _ in range(60 * 50):
            world.update(1 / 60)
            seen |= fight.active_kinds
            self.assertLessEqual(len(fight.active_kinds), 2)
            self.assertLessEqual(len(fight.live_summons), TUNING.summon_cap)
        self.assertEqual(seen, {"repairs", "vines", "cleaning", "specimens"})

    def test_scheduler_introduces_all_duties_early_without_repeats(self):
        for stage in (1, 2, 3):
            with self.subTest(stage=stage):
                world = World(7, level=5)
                fight = world.keeper
                fight.boss.hp = TUNING.health * {1: 1, 2: .5, 3: .2}[stage]
                world.player.invincible = 90
                for _ in range(60 * 24):
                    world.update(1 / 60)
                    self.assertLessEqual(len(fight.active_kinds), 1 if stage == 1 else 2)
                    if not fight.pending_duties:
                        break
                self.assertFalse(fight.pending_duties)
                self.assertEqual(len(fight.history), 4)
                self.assertEqual({row[2] for row in fight.history}, {"repairs", "vines", "cleaning", "specimens"})
                self.assertAlmostEqual(fight.history[0][0], TUNING.opening_delay, delta=1 / 60)
                self.assertTrue(all(TUNING.warning_min <= row[3] <= TUNING.warning_max for row in fight.history))

    def test_cancelled_warning_stays_due_and_safety_still_blocks_casts(self):
        from unittest.mock import patch

        world, fight, boss = keeper()
        self.assertTrue(fight.start("cleaning"))
        with patch.object(fight, "_warning_still_safe", return_value=False), patch.object(fight, "_certify", return_value=False):
            advance(world, .3)
            self.assertFalse(fight.mechanics)
            self.assertIn("cleaning", fight.pending_duties)
            fight.next_cast = 0
            advance(world, 1)
            self.assertEqual(len(fight.history), 1)
        fight.next_cast = 0
        advance(world, .1)
        self.assertTrue(fight.mechanics)

    def test_death_cleans_hazards_summons_and_hostile_projectiles(self):
        world, fight, boss = keeper()
        fight.start("cleaning")
        world.make_enemy(Vec(12.5, 8.5), "arcane", summoned=True, summon_life=20)
        world.projectiles.append(Projectile(Vec(7, 7), Vec(), hostile=True))
        world._hurt_player(1000)
        self.assertEqual(world.state, "dead")
        self.assertFalse(fight.mechanics)
        self.assertFalse(fight.live_summons)
        self.assertFalse(world.projectiles)
        self.assertEqual(world.player.gold, 0)
        self.assertFalse(world.player.lower_tower_completed)

    def test_kill_cleans_fight_awards_once_and_portal_leads_to_floor_six(self):
        world, fight, boss = keeper()
        fight.start("cleaning")
        world.make_enemy(Vec(12.5, 8.5), "arcane", summoned=True, summon_life=20)
        world._hit(boss, 10000)
        gold, gear = world.player.gold, world.player.inventory.to_dict()
        self.assertEqual(gold, TUNING.completion_gold)
        self.assertTrue(world.exit_open)
        self.assertFalse(fight.mechanics)
        self.assertFalse(fight.live_summons)
        self.assertTrue(world.player.lower_tower_completed)
        self.assertEqual(world.player.cleared_floor, 5)
        world._hit(boss, 10000)
        advance(world, 2)
        self.assertEqual((world.player.gold, world.player.inventory.to_dict()), (gold, gear))
        for _ in range(92):
            world.update(1 / 60)
        world.player.pos = world.exit
        world.update(1 / 60)
        self.assertEqual(world.state, "cleared")
        self.assertTrue(world.next_level())
        self.assertEqual(world.level, 6)
        self.assertIs(world.void.world, world)
        self.assertTrue(world.player.frostweave_unlocked)

    def test_boss_death_during_projectile_iteration_cannot_process_removed_shots(self):
        world, fight, boss = keeper()
        world.projectiles = [Projectile(boss.pos, Vec(), damage=10000),
                             Projectile(world.player.pos, Vec(), hostile=True)]
        world._projectiles(.01)
        self.assertTrue(world.level_completed)
        self.assertEqual(world.player.hp, 100)

    def test_area_spell_keeper_kill_skips_summons_removed_by_victory(self):
        for spell in ("r", "w"):
            for boosted in (False, True):
                with self.subTest(spell=spell, ice_patch=boosted):
                    world, fight, boss = keeper()
                    world.player.pos, boss.pos, boss.hp = Vec(8.5, 9.5), Vec(8.5, 8.5), 1
                    summons = [world.make_enemy(position, "crystal", summoned=True, summon_life=20, frozen=10)
                               for position in (Vec(7.5, 9.5), Vec(9.5, 9.5), Vec(8.5, 10.5), Vec(9.5, 8.5))]
                    for enemy in summons:
                        enemy.hp = 1
                    world.selected = summons[-1]
                    if boosted:
                        world.ice_patches.append(IcePatch(world.player.pos))
                    self.assertTrue(world.cast(spell))
                    advance(world, 2.7 if spell == "r" else .1)
                    self.assertTrue(world.exit_open)
                    self.assertEqual(world.state, "playing")
                    self.assertEqual(world.enemies, [])
                    self.assertEqual(world.player.kills, 1)
                    self.assertTrue(all(enemy.hp == 1 for enemy in summons))
                    self.assertIsNone(world.selected)
                    self.assertEqual(world.player.gold, TUNING.completion_gold)
                    gear = world.player.inventory.to_dict()
                    advance(world, 1)
                    self.assertEqual(world.player.inventory.to_dict(), gear)
                    self.assertEqual(world.player.gold, TUNING.completion_gold)

    def test_recalled_summon_cannot_take_a_stale_hit_or_drop_loot(self):
        world, fight, boss = keeper()
        summon = world.make_enemy(Vec(9.5, 8.5), "crystal", summoned=True, summon_life=20)
        health = summon.hp
        world._hit(boss, 10000)
        pickups = list(world.pickups)
        world._hit(summon, 10000)
        self.assertEqual(summon.hp, health)
        self.assertEqual(world.player.kills, 1)
        self.assertEqual(world.pickups, pickups)
        self.assertEqual(world.player.gold, TUNING.completion_gold)


class KeeperSaves(unittest.TestCase):
    def test_old_version_one_save_preserves_gear_gold_and_level(self):
        player = Player(current_level=3, unlocked_level=3, gold=3456, first_clear_rewarded=True)
        player.inventory.add(player.inventory.create("helm", 3))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            ProfileStore(path).save(player)
            data = json.loads(path.read_text())
            del data["cleared_floor"], data["lower_tower_completed"]
            path.write_text(json.dumps(data))
            loaded = ProfileStore(path).load()
        self.assertEqual((loaded.current_level, loaded.unlocked_level, loaded.gold), (3, 3, 3456))
        self.assertEqual(loaded.inventory.to_dict(), player.inventory.to_dict())
        self.assertFalse(loaded.lower_tower_completed)

    def test_reload_defeated_room_does_not_award_again_but_explicit_replay_can(self):
        world, fight, boss = keeper()
        world._hit(boss, 10000)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            self.assertTrue(ProfileStore(path).save(world.player))
            loaded = ProfileStore(path).load()
        before = loaded.gold
        restored = World(7, player=loaded, level=5)
        advance(restored, 1)
        self.assertTrue(restored.exit_open)
        self.assertIsNone(restored.keeper.boss)
        self.assertEqual(restored.player.gold, before)
        loaded.cleared_floor = 0  # Explicit replay, as in begin_level.
        replay = World(7, player=loaded, level=5)
        self.assertFalse(replay.exit_open)
        replay._hit(replay.keeper.boss, 10000)
        self.assertEqual(replay.player.gold, before + TUNING.completion_gold)

    def test_restart_after_death_has_fresh_boss_state(self):
        world, fight, boss = keeper()
        boss.hp = 100
        fight.start("vines")
        world._hurt_player(1000)
        world.player.hp = world.player.max_hp
        restarted = World(8, player=world.player, level=5)
        self.assertEqual(restarted.keeper.boss.hp, TUNING.health)
        self.assertEqual(restarted.keeper.stage, 1)
        self.assertFalse(restarted.keeper.mechanics)
        self.assertFalse(restarted.keeper.live_summons)


if __name__ == "__main__":
    unittest.main()
