"""Boss mechanics, telegraphs, encounter gates, and persistent floor rewards."""
import unittest
from math import cos, sin

from dungeon.encounters import signature, update_hazards
from dungeon.geometry import Vec
from dungeon.world import World


def encounter(depth=1):
    world = World(7, level=depth)
    world.enemies.clear()
    world.spawners.clear()
    world.pickups.clear()
    world._activate_boss()
    return world, next(e for e in world.enemies if e.boss_role == "boss")


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


class EncounterTests(unittest.TestCase):
    def test_miniboss_gold_scales_by_floor_and_drops_only_once(self):
        for depth, reward in ((1, 500), (2, 575), (3, 650)):
            world, boss = encounter(depth)
            world.pickups.clear()
            world._hit(boss, 10000)
            world._hit(boss, 10000)
            gold = [pickup.value for pickup in world.pickups if pickup.kind == "gold"]
            self.assertEqual(gold, [reward])
            self.assertEqual(world.player.gold, 0)
            world._collect_remaining_rewards()
            self.assertEqual(world.player.gold, reward)

    def test_victory_cues_are_once_per_boss_and_keeper_is_distinct(self):
        for depth in (1, 2, 3, 5):
            world = World(7, level=5) if depth == 5 else encounter(depth)[0]
            boss = next(e for e in world.enemies if e.boss_role in ("boss", "keeper"))
            world.events.clear()
            world._hit(boss, 10000)
            world._hit(boss, 10000)
            expected = "keeper_victory" if depth == 5 else "miniboss_victory"
            self.assertEqual(world.events.count(expected), 1)
            self.assertNotIn("miniboss_victory" if depth == 5 else "keeper_victory", world.events)

    def test_full_clear_reminder_waits_for_survivors_and_only_fires_once(self):
        for depth in (1, 2, 3, 4, 5):
            world = World(7, level=depth)
            world.phase = 3
            world.spawners.clear()
            world._complete_level()
            survivor = world.make_enemy(Vec(12.5, 12.5), "armor")
            world.update(1 / 60)
            self.assertFalse(world.floor_clear_notice)
            for enemy in world.enemies[:]:
                world._hit(enemy, 10000)
            world.update(1 / 60)
            advance(world, 1.5)
            self.assertTrue(world.floor_clear_notice)
            world.floor_clear_notice = False
            advance(world, .1)
            self.assertFalse(world.floor_clear_notice)

    def test_minibosses_warn_after_one_second_without_shortening_telegraphs(self):
        for depth, delays in ((1, [1.2]), (2, [1.6]), (3, [1.2, 1.75, 2.3])):
            with self.subTest(depth=depth):
                world, boss = encounter(depth)
                world.player.invincible = 10
                advance(world, .9)
                self.assertFalse(world.hazards)
                advance(world, .1)
                self.assertEqual(len(world.hazards), len(delays))
                for hazard, delay in zip(world.hazards, delays):
                    self.assertIs(hazard.owner, boss)
                    self.assertAlmostEqual(hazard.delay, delay)

    def test_freeze_still_delays_miniboss_opener(self):
        world, boss = encounter(2)
        boss.frozen = 2
        advance(world, 1.5)
        self.assertFalse(world.hazards)
        self.assertEqual(boss.signature_timer, 1)

    def test_each_encounter_requires_boss_and_companions_and_keeps_loot(self):
        for depth in (1, 2, 3):
            world, boss = encounter(depth)
            world._hit(boss, 10000)
            self.assertFalse(world.exit_open)
            for companion in world.enemies[:]:
                world._hit(companion, 10000)
            self.assertTrue(world.exit_open)
            rewards = list(world.pickups)
            self.assertTrue(any(p.kind == "gold" for p in rewards))
            self.assertTrue(any(p.kind == "item" for p in rewards))
            gold = world.player.gold
            advance(world, 20)
            self.assertEqual(world.pickups, rewards)
            self.assertEqual(world.player.gold, gold)
            expected = gold + sum(p.value for p in rewards if p.kind == "gold")
            world.player.pos = world.exit
            world.update(1 / 60)
            self.assertEqual(world.player.gold, expected)
            self.assertFalse(any(p.kind in ("gold", "item") for p in world.pickups))

    def test_rewards_stay_on_ground_during_spawner_intermission(self):
        world = World(7)
        world.enemies.clear()
        for spawner in world.spawners[:]:
            world._hit(spawner, 10000)
        rewards = list(world.pickups)
        advance(world, 3.1)
        self.assertEqual(world.phase, 2)
        self.assertEqual(world.pickups, rewards)

    def test_victory_loot_can_be_collected_by_walking_over_it(self):
        world, boss = encounter()
        for guardian in world.enemies[:]:
            world._hit(guardian, 10000)
        gold = next(p for p in world.pickups if p.kind == "gold")
        value = sum(p.value for p in world.pickups if p.kind == "gold" and (p.pos - gold.pos).length() < .65)
        world.player.pos = gold.pos
        world.update(1 / 60)
        self.assertNotIn(gold, world.pickups)
        self.assertEqual(world.player.gold, value)
        self.assertEqual(world.state, "playing")

    def test_warden_locks_charge_lane_then_hits_wall_and_recovers(self):
        world, boss = encounter()
        boss.pos, world.player.pos = Vec(8.5, 8.5), Vec(8.5, 12.5)
        signature(world, boss)
        target = world.hazards[0].direction
        world.player.pos = Vec(4.5, 13.5)
        start = boss.pos
        update_hazards(world, 1)
        self.assertEqual(boss.pos, start)
        for _ in range(180):
            update_hazards(world, 1 / 60)
        self.assertFalse(world.hazards)
        self.assertGreater(boss.recovery, 0)
        self.assertEqual(boss.pos.x, start.x)
        self.assertGreater(boss.pos.y, start.y)
        self.assertEqual(target, Vec(0, 1))
        self.assertEqual(world.player.hp, 100)
        self.assertTrue(world.walkable(boss.pos, .3))

    def test_cage_cannot_leave_a_safe_spot_at_its_center(self):
        world, boss = encounter(2)
        boss.pos = world.player.pos + Vec(3, 0)
        signature(world, boss)
        for _ in range(170):
            update_hazards(world, 1 / 60)
        self.assertLess(world.player.hp, 100)

    def test_warden_charge_damages_player_in_lane(self):
        world, boss = encounter()
        boss.pos, world.player.pos = Vec(8.5, 8.5), Vec(8.5, 10.5)
        signature(world, boss)
        for _ in range(110):
            update_hazards(world, 1 / 60)
        self.assertEqual(world.player.hp, 76)

    def test_shields_reduce_damage_and_recovery_rewards_attacking(self):
        world, boss = encounter()
        world.combat_rng.random = lambda: 1
        world._hit(boss, 100)
        self.assertEqual(boss.max_hp - boss.hp, 65)
        boss.recovery = 2
        world._hit(boss, 100)
        self.assertEqual(boss.max_hp - boss.hp, 200)

    def test_heart_is_stationary_and_tenders_heal_until_frozen(self):
        world, boss = encounter(2)
        start = boss.pos
        boss.hp -= 100
        for tender in world.enemies[1:]:
            tender.pos = start + Vec(1, 0)
        advance(world, .2)
        self.assertEqual(boss.pos, start)
        self.assertGreater(boss.hp, boss.max_hp - 100)
        for tender in world.enemies[1:]:
            tender.frozen = 10
        hp = boss.hp
        advance(world, .2)
        self.assertEqual(boss.hp, hp)

    def test_cage_has_safe_gap_and_closes_over_center(self):
        world, boss = encounter(2)
        signature(world, boss)
        cage = world.hazards[0]
        opening = cage.pos + Vec(cos(cage.gap), sin(cage.gap)) * cage.radius
        opposite = cage.pos - Vec(cos(cage.gap), sin(cage.gap)) * cage.radius
        self.assertFalse(cage.contains(opening))
        self.assertTrue(cage.contains(opposite))
        update_hazards(world, 1)
        self.assertEqual(world.player.hp, 100)
        for _ in range(110):
            update_hazards(world, 1 / 60)
        self.assertLess(world.player.hp, 100)
        self.assertFalse(world.hazards)
        self.assertGreater(boss.recovery, 0)

    def test_pools_ignite_in_sequence_and_damage_duplicates(self):
        world, boss = encounter(3)
        boss.pos = Vec(8.5, 8.5)
        world.player.pos = Vec(8.5, 13.5)
        duplicate = world.enemies[1]
        duplicate.pos = world.player.pos
        before = duplicate.hp
        signature(world, boss)
        self.assertEqual(len(world.hazards), 3)
        world.player.pos = Vec(3.5, 13.5)
        update_hazards(world, 1.21)
        self.assertEqual(len(world.hazards), 2)
        self.assertLess(duplicate.hp, before)
        self.assertEqual(world.player.hp, 100)
        update_hazards(world, .55)
        self.assertEqual(len(world.hazards), 1)
        update_hazards(world, .55)
        self.assertFalse(world.hazards)

    def test_freezing_or_killing_caster_cancels_pending_hazards(self):
        for depth in (1, 2, 3):
            world, boss = encounter(depth)
            signature(world, boss)
            boss.frozen = 1
            update_hazards(world, .1)
            self.assertFalse(world.hazards)
            boss.frozen = 0
            signature(world, boss)
            world._hit(boss, 10000)
            update_hazards(world, .1)
            self.assertFalse(world.hazards)

    def test_boss_placement_defers_when_there_is_no_safe_space(self):
        world = World(7)
        world.walls |= {(x, y) for x in range(1, 16) for y in range(1, 16) if (x, y) != (3, 13)}
        self.assertFalse(world._activate_boss())
        self.assertEqual(world.phase, 1)
        self.assertFalse(world.boss_started)


if __name__ == "__main__":
    unittest.main()
