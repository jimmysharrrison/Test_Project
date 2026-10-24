import unittest

from dungeon.geometry import Vec, project, unproject
from dungeon.world import Enemy, LAYOUT, Pickup, Spawner, World


class GeometryTests(unittest.TestCase):
    def test_projection_round_trip_with_offset(self):
        origin = Vec(857, 226)
        for point in (Vec(0, 0), Vec(3.5, 13.5), Vec(-2.2, 7.1)):
            result = unproject(project(point, origin), origin)
            self.assertAlmostEqual(result.x, point.x)
            self.assertAlmostEqual(result.y, point.y)


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.world = World(seed=10)

    def advance(self, seconds):
        for _ in range(round(seconds * 60)):
            self.world.update(1 / 60)

    def peaceful(self):
        self.world.enemies.clear()
        for rift in self.world.spawners:
            rift.timer = 999

    def test_layout_and_initial_entities_are_valid(self):
        self.assertEqual(len(LAYOUT), 17)
        self.assertTrue(all(len(row) == 17 for row in LAYOUT))
        points = [self.world.player.pos, self.world.exit]
        points += [e.pos for e in self.world.enemies + self.world.spawners + self.world.pickups]
        self.assertTrue(all(self.world.walkable(point) for point in points))

    def test_fast_movement_cannot_tunnel_through_walls(self):
        end = self.world.move(Vec(3.5, 5.5), Vec(8, 0))
        self.assertLess(end.x, 5)
        self.assertTrue(self.world.walkable(end))
        self.assertEqual(self.world.move(Vec(1.3, 8.5), Vec(-10, 0)).x, 1.3)

    def test_movement_is_consistent_at_different_frame_rates(self):
        for fps in (30, 60, 120):
            world = World(5)
            world.enemies.clear()
            world.player.pos = Vec(2.5, 14.5)
            world.request_move(Vec(10.5, 14.5))
            for _ in range(fps):
                world.update(1 / fps)
            self.assertAlmostEqual(world.player.pos.x, 5.6)

    def test_click_order_paths_around_obstacles_and_stops(self):
        self.peaceful()
        self.world.player.pos = Vec(2.5, 5.5)
        goal = Vec(8.5, 5.5)
        self.world.request_move(goal)
        self.assertGreater(len(self.world.path), 1)
        for _ in range(360):
            self.world.update(1 / 60)
            self.assertTrue(self.world.walkable(self.world.player.pos))
        self.assertLess((self.world.player.pos - goal).length(), 0.03)
        self.assertIsNone(self.world.destination)

    def test_wall_click_resolves_to_reachable_floor(self):
        self.peaceful()
        target = Vec(5.5, 5.5)
        self.world.request_move(target)
        destination = self.world.destination
        self.assertTrue(self.world.walkable(destination))
        self.assertNotEqual(destination, target)
        self.advance(10)
        self.assertLess((self.world.player.pos - destination).length(), 0.03)

    def test_unreachable_click_does_not_cross_sealed_region(self):
        self.peaceful()
        self.world.walls.update((8, y) for y in range(1, 16))
        self.world.request_move(Vec(12.5, 14.5))
        self.assertLess(self.world.destination.x, 8)
        self.advance(5)
        self.assertLess(self.world.player.pos.x, 8)
        self.assertIsNone(self.world.destination)

    def test_new_move_order_replaces_old_destination(self):
        self.peaceful()
        self.world.request_move(Vec(10.5, 14.5))
        self.world.request_move(Vec(2.5, 14.5))
        self.advance(2)
        self.assertLess((self.world.player.pos - Vec(2.5, 14.5)).length(), 0.03)
        self.world.request_move(Vec(10.5, 14.5))
        self.world.stop()
        position = self.world.player.pos
        self.advance(1)
        self.assertEqual(self.world.player.pos, position)

    def test_crowd_cannot_damage_player_multiple_times_in_one_frame(self):
        self.world.enemies = [Enemy(self.world.player.pos) for _ in range(8)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 90)
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 90)

    def test_potions_are_limited_and_healing_is_capped(self):
        self.world.use_potion()
        self.assertEqual(self.world.player.potions, 3)
        self.world.player.hp = 80
        self.world.use_potion()
        self.assertEqual((self.world.player.hp, self.world.player.potions), (100, 2))
        self.world.player.hp = 20
        self.world.player.potions = 0
        self.world.use_potion()
        self.assertEqual(self.world.player.hp, 20)

    def test_projectiles_are_blocked_by_walls(self):
        self.world.player.pos = Vec(3.5, 5.5)
        target = Spawner(Vec(7.5, 5.5), timer=999)
        self.world.spawners = [target]
        self.world.enemies.clear()
        self.world.cast("q", target.pos)
        self.advance(1)
        self.assertEqual(target.hp, 176)
        self.assertEqual(len(self.world.projectiles), 0)

    def test_rift_can_be_destroyed_and_stops_spawning(self):
        self.world.player.pos = Vec(5.5, 14.5)
        target = Spawner(Vec(8.5, 14.5), timer=999)
        self.world.spawners = [target]
        self.world.enemies.clear()
        for _ in range(8):
            self.world.cast("q", target.pos)
            self.advance(0.4)
        self.assertEqual(self.world.spawners, [])
        self.assertFalse(self.world.exit_open)
        self.assertGreaterEqual(self.world.player.gold, 75)
        self.advance(1)
        self.assertEqual(self.world.enemies, [])
        self.advance(3)
        self.assertEqual(self.world.phase, 2)
        self.assertEqual(len(self.world.spawners), 3)
        self.assertNotIn(target, self.world.spawners)

    def test_enemies_navigate_around_obstacles(self):
        self.peaceful()
        self.world.player.pos = Vec(8.5, 5.5)
        enemy = Enemy(Vec(2.5, 5.5))
        self.world.enemies = [enemy]
        self.advance(8)
        self.assertLess((enemy.pos - self.world.player.pos).length(), 1)
        self.assertTrue(self.world.walkable(enemy.pos))

    def test_spawners_respect_enemy_limit(self):
        self.world.enemies = [Enemy(Vec(12.5, 14.5)) for _ in range(40)]
        for spawner in self.world.spawners:
            spawner.timer = 0
        self.world.update(1 / 60)
        self.assertEqual(len(self.world.enemies), 40)

    def test_gold_and_food_pickups(self):
        self.world.player.hp = 90
        self.world.pickups = [Pickup(self.world.player.pos, "gold", 25), Pickup(self.world.player.pos, "food", 25)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.gold, 25)
        self.assertEqual(self.world.player.hp, 100)
        self.assertEqual(self.world.pickups, [])

    def test_gate_requires_rifts_to_be_cleared(self):
        self.world.player.pos = self.world.exit
        self.world.update(1 / 60)
        self.assertEqual(self.world.state, "playing")
        self.world.enemies.clear()
        for phase in range(1, 4):
            for spawner in self.world.spawners[:]:
                self.world._hit(spawner, 10000)
            self.assertEqual(self.world.exit_open, phase == 3)
            if phase < 3:
                self.advance(3.05)
                self.assertEqual(self.world.state, "playing")
        self.world.update(1 / 60)
        self.assertEqual(self.world.state, "cleared")
        time = self.world.time
        self.world.update(1)
        self.assertEqual(self.world.time, time)

    def test_death_ends_run(self):
        self.world.player.hp = 1
        self.world.enemies = [Enemy(self.world.player.pos)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 0)
        self.assertEqual(self.world.state, "dead")
        self.world.use_potion()
        self.assertEqual(self.world.player.hp, 0)


if __name__ == "__main__":
    unittest.main()
