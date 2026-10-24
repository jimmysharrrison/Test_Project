"""Forest progression, encounter composition, and dodgeable ranged combat."""

from math import floor
import unittest

from dungeon.geometry import Vec
from dungeon.navigation import flood
from dungeon.world import Enemy, Projectile, World


def finish_floor(world):
    for phase in range(1, 4):
        for spawner in world.spawners[:]:
            world._hit(spawner, 10000)
        if world.phase == 3:
            for guardian in world.enemies[:]:
                if guardian.boss_role:
                    world._hit(guardian, 10000)
        if phase < 3:
            for _ in range(183):
                world.update(1 / 60)


class ForestLevelTests(unittest.TestCase):
    def test_both_levels_have_reachable_encounters_and_exit(self):
        for depth in (1, 2, 3):
            with self.subTest(depth=depth):
                world = World(7, level=depth)
                self.assertEqual(len(world.layout), 17)
                self.assertTrue(all(len(row) == 17 for row in world.layout))
                reached = flood((floor(world.player.pos.x), floor(world.player.pos.y)), world.blocked)
                points = [world.player.pos, world.exit]
                points += [actor.pos for actor in world.enemies + world.spawners + world.pickups]
                for point in points:
                    self.assertTrue(world.walkable(point), point)
                    self.assertIn((floor(point.x), floor(point.y)), reached)

    def test_forest_has_distinct_layout_roster_and_spawners(self):
        first, forest = World(7), World(7, level=2)
        self.assertEqual({e.kind for e in first.enemies}, {"husk", "skitter"})
        self.assertEqual({e.kind for e in forest.enemies}, {"tree", "spider", "archer"})
        self.assertNotEqual(first.walls, forest.walls)
        self.assertEqual({s.name for s in first.spawners}, {"Molten Rift"})
        self.assertEqual({s.name for s in forest.spawners}, {"Blighted Heart"})
        self.assertTrue(all(e.hp == e.max_hp for e in forest.enemies))

    def test_generators_only_spawn_their_level_roster(self):
        for depth, expected in ((1, {"husk", "skitter"}), (2, {"tree", "spider", "archer"})):
            world = World(7, level=depth)
            kinds = set()
            for _ in range(80):
                world.enemies.clear()
                for spawner in world.spawners:
                    spawner.timer = 0
                world._spawn(1 / 60)
                kinds.update(e.kind for e in world.enemies)
                self.assertTrue(all(world.walkable(e.pos) and e.hp == e.max_hp for e in world.enemies))
            self.assertEqual(kinds, expected)

    def test_portal_enters_forest_with_gear_and_resets_transient_combat(self):
        world = World(7)
        inv = world.player.inventory
        inv.add(inv.create("chest", 2))
        world.player.gold = 300
        world.enemies.clear()
        finish_floor(world)
        player = world.player
        world.player.pos = world.exit
        world.update(1 / 60)
        gear, gold = inv.to_dict(), world.player.gold
        world.projectiles.append(Projectile(Vec(7, 7), Vec(1, 0), hostile=True))
        world.player.hp, world.player.mana = 12, 8
        world.player.cooldowns["r"] = 20
        self.assertTrue(world.next_level())
        self.assertEqual(world.level, 2)
        self.assertEqual(player.current_level, 2)
        self.assertEqual(player.unlocked_level, 2)
        self.assertEqual(world.level_data.name, "Thornveil Atrium")
        self.assertIs(world.player, player)
        self.assertEqual(inv.to_dict(), gear)
        self.assertEqual(player.gold, gold)
        self.assertEqual(player.hp, player.max_hp)
        self.assertEqual(player.mana, 100)
        self.assertTrue(all(cd == 0 for cd in player.cooldowns.values()))
        self.assertEqual(world.projectiles, [])
        self.assertFalse(world.exit_open)
        self.assertTrue(player.first_clear_rewarded)

    def test_forest_clear_opens_portal_with_survivors_and_no_duplicate_boots(self):
        world = World(7, level=2)
        world.enemies = [Enemy(Vec(14.5, 14.5), "tree")]
        finish_floor(world)
        self.assertTrue(world.exit_open)
        self.assertTrue(world.enemies)
        self.assertEqual(world.player.unlocked_level, 2)
        self.assertFalse(any(item.source == "reward" for item in world.player.inventory.items))
        self.assertTrue(any(p.kind in ("gold", "item") for p in world.pickups))
        world.player.pos = world.exit
        world.update(1 / 60)
        self.assertEqual(world.state, "cleared")
        self.assertTrue(world.next_level())
        self.assertEqual(world.level, 3)
        self.assertEqual(world.player.unlocked_level, 3)
        self.assertEqual({e.kind for e in world.enemies}, {"armor", "grimoire", "fairy"})


class ArcherTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7, level=2)
        self.world.pickups.clear()
        for spawner in self.world.spawners:
            spawner.timer = 999
        self.world.player.pos = Vec(3.5, 14.5)
        self.archer = Enemy(Vec(7.5, 14.5), "archer", level=2)
        self.archer.hp = self.archer.max_hp
        self.world.enemies = [self.archer]

    def advance(self, seconds):
        for _ in range(round(seconds * 60)):
            self.world.update(1 / 60)

    def arrow(self, pos=None, velocity=None, damage=9):
        shot = Projectile(pos or Vec(7.5, 14.5), velocity or Vec(-5.5, 0),
                          life=1.7, damage=damage, hostile=True)
        self.world.projectiles.append(shot)
        return shot

    def test_archer_aims_before_firing_and_hits_at_range(self):
        start = self.archer.pos
        self.advance(.5)
        self.assertGreater(self.archer.windup, 0)
        self.assertEqual(self.world.projectiles, [])
        self.assertEqual(self.world.player.hp, 100)
        self.advance(.3)
        self.assertEqual(len(self.world.projectiles), 1)
        self.assertTrue(self.world.projectiles[0].hostile)
        self.advance(.8)
        self.assertEqual(self.world.player.hp, 91)
        self.assertEqual(self.archer.pos, start)

    def test_archer_fires_periodically_rather_than_every_frame(self):
        shots = []
        for _ in range(8 * 60):
            self.world.events.clear()
            self.world.update(1 / 60)
            if "arrow" in self.world.events:
                shots.append(self.world.time)
        self.assertEqual(len(shots), 3)
        for a, b in zip(shots, shots[1:]):
            self.assertAlmostEqual(b - a, 3.45, delta=.06)

    def test_player_can_dodge_locked_aim_during_bow_draw(self):
        self.advance(.1)
        aim = self.archer.shot_target
        self.world.request_move(Vec(3.5, 12.5))
        self.advance(.65)
        self.assertEqual(aim, Vec(3.5, 14.5))
        shot = self.world.projectiles[0]
        self.assertAlmostEqual(shot.velocity.y, 0)
        self.advance(1)
        self.assertEqual(self.world.player.hp, 100)
        self.assertLess(self.world.player.pos.y, 13)

    def test_freezing_interrupts_bow_draw_and_stops_shooting(self):
        self.archer.pos = Vec(5.5, 14.5)
        self.advance(.1)
        self.assertGreater(self.archer.windup, 0)
        self.world.cast("w")
        self.advance(2)
        self.assertEqual(self.archer.windup, 0)
        self.assertIsNone(self.archer.shot_target)
        self.assertEqual(self.world.projectiles, [])
        self.assertEqual(self.world.player.hp, 100)
        self.advance(1.5)
        self.assertIn("arrow", self.world.events)

    def test_archer_routes_around_obstructions_before_shooting(self):
        self.world.player.pos = Vec(5.5, 7.5)
        self.archer.pos = Vec(8.5, 7.5)
        self.advance(.5)
        self.assertNotIn("arrow", self.world.events)
        for _ in range(8 * 60):
            self.world.update(1 / 60)
            self.assertTrue(self.world.walkable(self.archer.pos))
        self.assertIn("arrow", self.world.events)

    def test_archer_retreats_when_player_gets_close(self):
        self.archer.pos = Vec(5, 14.5)
        self.archer.cooldown = 2
        self.advance(.3)
        self.assertGreater(self.archer.pos.x, 5)

    def test_arrows_are_blocked_by_terrain(self):
        self.world.enemies.clear()
        self.world.walls.add((5, 14))
        self.arrow()
        self.advance(1.5)
        self.assertEqual(self.world.player.hp, 100)
        self.assertEqual(self.world.projectiles, [])

    def test_ice_patch_does_not_block_arrows_in_flight(self):
        self.world.enemies.clear()
        self.arrow()
        self.assertTrue(self.world.cast("e", Vec(5.5, 14.5)))
        self.advance(1.5)
        self.assertEqual(self.world.player.hp, 91)
        self.assertEqual(self.world.projectiles, [])

    def test_ice_patch_slows_bow_draw_without_cancelling_it(self):
        self.advance(.1)
        before = self.archer.windup
        self.assertTrue(self.world.cast("e", Vec(5.5, 14.5)))
        self.advance(.3)
        self.assertNotIn("arrow", self.world.events)
        self.assertAlmostEqual(before - self.archer.windup, .3 * .6)
        self.assertGreater(self.archer.windup, 0)
        self.assertEqual(self.world.player.hp, 100)

    def test_arrows_respect_armor_and_shared_hit_invulnerability(self):
        self.world.enemies.clear()
        inv = self.world.player.inventory
        inv.add(inv.create("legs", 3))
        self.arrow()
        self.arrow()
        self.advance(1)
        self.assertEqual(self.world.player.hp, 94)
        self.assertEqual(self.world.events.count("hurt"), 1)
        self.assertEqual(self.world.projectiles, [])

    def test_glacial_prison_absorbs_arrows(self):
        self.world.enemies.clear()
        self.arrow()
        self.world.cast("r")
        self.advance(1)
        self.assertEqual(self.world.player.hp, 100)
        self.assertEqual(self.world.projectiles, [])

    def test_enemy_arrows_do_not_hit_other_enemies_or_chill_player(self):
        blocker = Enemy(Vec(5.5, 14.5), "tree", level=2, frozen=3)
        self.world.enemies = [blocker]
        self.arrow()
        self.advance(1)
        self.assertEqual(blocker.hp, 44)
        self.assertEqual(self.world.player.hp, 91)

    def test_lethal_arrow_ends_run_before_food_can_revive_player(self):
        from dungeon.world import Pickup
        self.world.enemies.clear()
        self.world.player.hp = 1
        self.arrow(pos=self.world.player.pos + Vec(.35, 0))
        self.world.pickups = [Pickup(self.world.player.pos, "food", 25)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 0)
        self.assertEqual(self.world.state, "dead")
        self.assertIn("dead", self.world.events)

    def test_arrow_lifetime_does_not_advance_on_zero_time_or_travel_past_expiry(self):
        self.world.enemies.clear()
        shot = self.arrow(pos=Vec(7.5, 14.5), velocity=Vec(1, 0))
        self.world.update(0)
        self.assertIn(shot, self.world.projectiles)
        self.assertEqual(shot.pos, Vec(7.5, 14.5))
        shot.life = .01
        self.world.update(1 / 30)
        self.assertAlmostEqual(shot.pos.x, 7.51)
        self.assertNotIn(shot, self.world.projectiles)


if __name__ == "__main__":
    unittest.main()
