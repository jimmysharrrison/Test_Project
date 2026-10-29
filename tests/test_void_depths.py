"""Oracle restraint/protection, Astronomer gravity, progression and persistence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dungeon.codex import enemy_values, species
from dungeon.geometry import Vec
from dungeon.menus import Menus
from dungeon.saves import SaveSlots, decode_world, encode_world
from dungeon.void_depths import (VoidDepths, VoidMechanic, BOSS_HEALTH, MECHANIC_CAP,
                                 ROOT_DURATION, force_player, orbit_points)
from dungeon.world import IcePatch, Projectile, World


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def quiet(level=7):
    world = World(7, level=level, completion_delay_ms=0)
    world.enemies.clear()
    world.pickups.clear()
    world.player.pos = Vec(8.5, 10.5)
    for spawner in world.spawners:
        spawner.timer = 999
    return world


def boss_room(level=7):
    world = quiet(level)
    world.spawners.clear()
    world.void.activate_boss()
    world.void.boss.cooldown = 999
    return world, world.void.boss


class VoidDepthTests(unittest.TestCase):
    def test_distinct_rosters_names_and_future_floor_boundary(self):
        seven, eight = World(7, level=7), World(7, level=8)
        self.assertIsInstance(seven.void, VoidDepths)
        self.assertEqual({s.name for s in seven.spawners}, {"Enthrallment Seal"})
        self.assertEqual({s.name for s in eight.spawners}, {"Celestial Focus"})
        self.assertEqual({e.kind for e in seven.enemies}, {"lasher", "grasper", "thrall"})
        self.assertEqual({e.kind for e in eight.enemies}, {"gravity_adept", "repulsor", "star_fragment"})
        with self.assertRaises(ValueError):
            World(7, level=11)

    def test_two_three_waves_then_correct_boss_and_no_resource_reset(self):
        for level in (7, 8):
            world = quiet(level)
            world.player.hp = 71
            world.player.cooldowns["r"] = 40
            for phase, count in ((1, 2), (2, 3)):
                self.assertEqual(len(world.spawners), count)
                for spawner in world.spawners[:]:
                    world._hit(spawner, 10000)
                self.assertFalse(world.exit_open)
                advance(world, 3.05)
            self.assertEqual(world.phase, 3)
            self.assertEqual(world.void.boss.kind, "oracle" if level == 7 else "astronomer")
            self.assertEqual(world.void.boss.hp, BOSS_HEALTH[world.void.boss.kind])
            self.assertEqual(world.player.hp, 71)
            self.assertGreater(world.player.cooldowns["r"], 33)

    def test_grab_requires_a_hit_and_allows_spells_and_potions(self):
        world = quiet()
        grasper = world.make_enemy(Vec(8.5, 8.5), "grasper", cooldown=999)
        world.void.warn("grasp", grasper, world.player.pos, 1.1)
        advance(world, 1)
        self.assertFalse(world.void.rooted)
        advance(world, .2)
        self.assertTrue(world.void.rooted)
        pos = world.player.pos
        world.request_move(pos + Vec(3, 0))
        advance(world, .1)
        self.assertEqual(world.player.pos, pos)
        self.assertEqual(world.can_cast("q"), "")
        before = world.player.potions
        world.use_potion()
        self.assertEqual(world.player.potions, before - 1)
        self.assertTrue(world.cast("w"))
        self.assertFalse(world.void.rooted)
        advance(world, .3)
        self.assertNotEqual(world.player.pos, pos)

    def test_grab_dodge_prison_kill_and_natural_expiry(self):
        for counter in ("dodge", "prison", "kill", "expire"):
            world = quiet()
            grasper = world.make_enemy(Vec(8.5, 8.5), "grasper", cooldown=999)
            world.void.warn("grasp", grasper, world.player.pos, 1.1)
            if counter == "dodge":
                world.request_move(world.player.pos + Vec(3, 0))
            elif counter == "prison":
                world.cast("r")
            advance(world, 1.2)
            if counter in ("dodge", "prison"):
                self.assertFalse(world.void.rooted)
                self.assertEqual(world.player.hp, 100)
            else:
                self.assertTrue(world.void.rooted)
                if counter == "kill":
                    world._hit(grasper, 10000)
                else:
                    advance(world, ROOT_DURATION + .1)
                self.assertFalse(world.void.rooted)

    def test_freeze_interrupts_new_enemy_warnings(self):
        world = quiet()
        enemy = world.make_enemy(Vec(8.5, 8.5), "lasher", cooldown=999)
        world.void.warn("lash", enemy, enemy.pos, 1.1, end=world.player.pos)
        world._freeze(enemy, 2)
        self.assertFalse(world.void.mechanics)
        advance(world, 1.3)
        self.assertEqual(world.player.hp, 100)

    def test_anchor_is_a_counterable_pull_and_released_darkness_expires(self):
        world = quiet()
        anchor = world.make_enemy(Vec(8.5, 7.5), "anchor", cooldown=999)
        world.void.warn("tether", anchor, anchor.pos, 1.1, 4, 7, strength=.9)
        world.void.add_darkness(anchor.pos, anchor, warning=1.1, life=4)
        start = world.player.pos
        advance(world, 1.4)
        self.assertLess(world.player.pos.y, start.y)
        world._hit(anchor, 10000)
        stopped = world.player.pos
        advance(world, .3)
        self.assertEqual(world.player.pos, stopped)
        self.assertFalse(world.void.mechanics)
        self.assertTrue(world.void.zones)
        advance(world, 4)
        self.assertFalse(world.void.zones)

    def test_one_force_and_grasp_mutual_exclusion_and_total_cap(self):
        world = quiet()
        e = world.make_enemy(Vec(8.5, 7.5), "anchor", cooldown=999)
        self.assertTrue(world.void.warn("tether", e, e.pos, life=4, radius=7, strength=.9))
        self.assertFalse(world.void.warn("rejection", e, e.pos, life=1, radius=7, strength=1))
        self.assertFalse(world.void.warn("grasp", e, world.player.pos))
        for _ in range(8):
            world.void.warn("chorus", e, Vec(4.5, 6.5))
        self.assertEqual(len(world.void.mechanics), MECHANIC_CAP)

    def test_oracle_channelers_reduce_damage_until_both_interrupted(self):
        world, boss = boss_room()
        guards = [e for e in world.enemies if e.boss_role == "channeler"]
        self.assertEqual(len(guards), 2)
        self.assertTrue(world.void.protected)
        world.combat_rng.seed(0)
        before = boss.hp
        world._hit(boss, 100)
        self.assertEqual(before - boss.hp, 20)
        for e in guards:
            world._freeze(e, 2)
        self.assertFalse(world.void.protected)
        world.combat_rng.seed(0)
        before = boss.hp
        world._hit(boss, 100)
        self.assertEqual(before - boss.hp, 100)

    def test_gaze_cancelled_during_grab(self):
        world, boss = boss_room()
        grasper = world.make_enemy(Vec(8.5, 8.5), "grasper", cooldown=999)
        self.assertTrue(world.void.warn("gaze", boss, boss.pos, end=world.player.pos))
        world.void.root_owner, world.void.root_left = grasper, 2
        advance(world, .1)
        self.assertFalse(any(m.kind == "gaze" for m in world.void.mechanics))

    def test_oracle_replenishes_channelers_and_warns_anchor_arrival(self):
        world, boss = boss_room()
        for e in world.enemies[:]:
            if e.boss_role == "channeler":
                world._hit(e, 10000)
        boss.hp = round(boss.max_hp * .6)
        boss.cooldown = 0
        advance(world, .1)
        self.assertTrue(any(m.kind == "communion" for m in world.void.mechanics))
        advance(world, 2)
        self.assertTrue(world.void.protected)
        self.assertLessEqual(sum(e.boss_role == "channeler" for e in world.enemies), 2)

    def test_pull_push_and_prison_use_wall_safe_movement(self):
        world = quiet(8)
        start = world.player.pos
        force_player(world, Vec(8.5, 7.5), 2, .2)
        self.assertLess(world.player.pos.y, start.y)
        force_player(world, Vec(8.5, 7.5), 2, .2, outward=True)
        self.assertAlmostEqual(world.player.pos.y, start.y)
        world.player.stasis = 1
        force_player(world, Vec(8.5, 7.5), 2, .2)
        self.assertEqual(world.player.pos, start)
        world.player.stasis = 0
        world.player.pos = Vec(15.5, 15.5)
        force_player(world, Vec(8.5, 7.5), 100, 1, outward=True)
        self.assertTrue(world.walkable(world.player.pos))
        self.assertGreater(world.player.hp, 0)

    def test_regular_gravity_field_warns_and_star_detonates(self):
        world = quiet(8)
        e = world.make_enemy(Vec(8.5, 7.5), "gravity_adept", cooldown=999)
        world.void.warn("well", e, world.player.pos, 1.2, 1, 2.2, strength=.85)
        advance(world, 1.1)
        self.assertEqual(world.player.hp, 100)
        advance(world, 1.2)
        self.assertEqual(world.player.hp, 78)
        self.assertFalse(world.void.mechanics)

    def test_walk_can_overcome_pull_without_prison(self):
        world, boss = boss_room(8)
        world.void.warn("convergence", boss, boss.pos, 1.1, 3, 14, strength=1.35)
        advance(world, 1.2)
        distance = (world.player.pos - boss.pos).length()
        world.request_move(Vec(8.5, 14.5))
        advance(world, 1)
        self.assertGreater((world.player.pos - boss.pos).length(), distance)

    def test_late_astronomer_combines_one_force_with_orbit_and_preserves_neutral_gap(self):
        world, boss = boss_room(8)
        boss.hp = boss.max_hp // 4
        boss.cooldown = 0
        advance(world, .1)
        self.assertEqual({m.kind for m in world.void.mechanics}, {"convergence", "orbit"})
        self.assertEqual(sum(m.kind in ("convergence", "rejection", "well") for m in world.void.mechanics), 1)
        world.debug_invulnerable = True
        advance(world, 5.1)
        self.assertFalse(world.void.mechanics)
        self.assertGreater(boss.cooldown, .1)

    def test_orbiting_enemy_freezes_and_patch_slows_angular_motion(self):
        world = quiet(8)
        fragment = world.make_enemy(Vec(6.5, 7.5), "star_fragment")
        advance(world, .2)
        world._freeze(fragment, 1)
        point = fragment.pos
        advance(world, .5)
        self.assertEqual(fragment.pos, point)
        advance(world, .6)
        phase = fragment.action_time
        world.ice_patches.append(IcePatch(fragment.pos))
        advance(world, .1)
        self.assertLess(fragment.action_time - phase, .06)

    def test_warnings_slow_inside_ice_patch(self):
        world, boss = boss_room(8)
        world.ice_patches.append(IcePatch(boss.pos))
        world.void.warn("rejection", boss, boss.pos, 1.8, 1, 14, strength=2.2)
        advance(world, 2)
        self.assertGreater(world.void.mechanics[0].warning, .4)

    def test_cleanup_and_progression_into_the_temporal_floor(self):
        for level in (7, 8):
            world, boss = boss_room(level)
            world.void.warn("orbit" if level == 8 else "chorus", boss, boss.pos)
            world.void.root_owner, world.void.root_left = boss, 1
            world._hit(boss, 100000)
            self.assertTrue(world.exit_open)
            self.assertFalse(world.void.mechanics)
            self.assertFalse(world.void.rooted)
            self.assertFalse(any(e.summoned for e in world.enemies))
            world.update(1 / 60)
            world.player.pos = world.exit
            world.update(1 / 60)
            self.assertEqual(world.state, "cleared")
            self.assertTrue(world.next_level())
            self.assertEqual(world.level, level + 1)
            self.assertIs(world.void.world, world)

    def test_same_tick_death_wins_over_boss_clear(self):
        for level in (7, 8):
            world, boss = boss_room(level)
            world.player.hp = 1
            world.projectiles = [Projectile(boss.pos, Vec(), damage=100000),
                                 Projectile(world.player.pos, Vec(), hostile=True, damage=100000)]
            world.update(1 / 60)
            self.assertEqual(world.state, "dead")
            self.assertFalse(world.level_completed)
            self.assertFalse(world.void.mechanics)

    @patch("dungeon.codex.datetime", wraps=datetime)
    def test_live_encounter_roundtrip_and_slot_load_keep_shared_references(self, clock):
        clock.now.return_value = datetime(2026, 10, 24, tzinfo=timezone.utc)
        for level in (7, 8):
            world, boss = boss_room(level)
            world.void.warn("gaze" if level == 7 else "convergence", boss, boss.pos,
                            end=world.player.pos if level == 7 else None, life=3, radius=14, strength=1)
            loaded = decode_world(json.loads(json.dumps(encode_world(world))))
            self.assertIs(loaded.void.boss, loaded.void.mechanics[0].owner)
            self.assertIs(loaded.void.world, loaded)
            advance(world, 2)
            advance(loaded, 2)
            self.assertEqual(encode_world(loaded), encode_world(world))
            with TemporaryDirectory() as folder:
                slots = SaveSlots(Path(folder) / "profile.json")
                self.assertTrue(slots.save(1, world), slots.error)
                restored = slots.load(1)
                self.assertIsNotNone(restored, slots.error)
                self.assertEqual(restored.level, level)

    def test_old_floor_six_terminal_checkpoint_can_continue_and_level_select_has_second_page(self):
        world = World(7, level=6)
        world.level_completed = True
        world.state = "won"
        restored = decode_world(encode_world(world))
        self.assertEqual(restored.state, "cleared")
        self.assertTrue(restored.next_level())
        self.assertEqual(restored.level, 7)
        menu = Menus()
        menu.page = 1
        choices = [b for b in menu.buttons(restored, "levels") if b.action.startswith("level:")]
        self.assertEqual([b.action for b in choices], ["level:7", "level:8", "level:9", "level:10"])
        self.assertEqual([b.enabled for b in choices], [True, False, False, False])

    def test_codex_new_values_are_available_and_match_health(self):
        for key in ("lasher", "grasper", "anchor", "thrall", "oracle_channeler", "oracle",
                    "gravity_adept", "repulsor", "star_fragment", "astronomer"):
            entry = species()[key]
            values = enemy_values(entry, 8)
            self.assertEqual(values["effective_health_hp"], entry.actor(8).max_hp)


if __name__ == "__main__":
    unittest.main()
