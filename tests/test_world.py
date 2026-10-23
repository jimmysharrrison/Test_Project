import unittest

from dungeon.geometry import Vec, project, screen_direction, unproject
from dungeon.world import Enemy, LAYOUT, Pickup, Spawner, World


class GeometryTests(unittest.TestCase):
    def test_projection_round_trip_with_offset(self):
        origin = Vec(857, 226)
        for point in (Vec(0, 0), Vec(3.5, 13.5), Vec(-2.2, 7.1)):
            result = unproject(project(point, origin), origin)
            self.assertAlmostEqual(result.x, point.x)
            self.assertAlmostEqual(result.y, point.y)

    def test_screen_controls_follow_screen_axes(self):
        right = project(screen_direction(1, 0))
        up = project(screen_direction(0, -1))
        self.assertGreater(right.x, 0)
        self.assertAlmostEqual(right.y, 0)
        self.assertLess(up.y, 0)
        self.assertAlmostEqual(up.x, 0)
        self.assertAlmostEqual(screen_direction(1, 1).length(), 1)
        self.assertEqual(screen_direction(0, 0), Vec())


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.world = World(seed=10)

    def advance(self, seconds, **kwargs):
        for _ in range(round(seconds * 60)):
            self.world.update(1 / 60, **kwargs)

    def test_layout_and_initial_entities_are_valid(self):
        self.assertEqual(len(LAYOUT), 17)
        self.assertTrue(all(len(row) == 17 for row in LAYOUT))
        points = [self.world.player.pos, self.world.exit]
        points += [e.pos for e in self.world.enemies + self.world.spawners + self.world.pickups]
        self.assertTrue(all(self.world.walkable(point) for point in points))

    def test_dash_cannot_tunnel_through_walls(self):
        start = Vec(3.5, 3.5)
        end = self.world.move(start, Vec(8, 0))
        self.assertLess(end.x, 4)
        self.assertTrue(self.world.walkable(end))
        self.assertEqual(self.world.move(Vec(1.3, 8.5), Vec(-10, 0)).x, 1.3)

    def test_movement_is_consistent_at_different_frame_rates(self):
        results = []
        for fps in (30, 60, 120):
            world = World(5)
            world.enemies.clear()
            world.player.pos = Vec(2.5, 14.5)
            for _ in range(fps):
                world.update(1 / fps, Vec(1, 0))
            results.append(world.player.pos.x)
        for x in results:
            self.assertAlmostEqual(x, 5.6)

    def test_crowd_cannot_damage_player_multiple_times_in_one_frame(self):
        self.world.enemies = [Enemy(self.world.player.pos) for _ in range(8)]
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 90)
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 90)

    def test_dash_grants_invulnerability_and_has_cooldown(self):
        self.world.enemies = [Enemy(self.world.player.pos)]
        self.world.dash(Vec(1, 0))
        self.world.update(1 / 60)
        self.assertEqual(self.world.player.hp, 100)
        cooldown = self.world.player.dash_cooldown
        self.world.dash(Vec(-1, 0))
        self.assertEqual(self.world.player.dash_direction, Vec(1, 0))
        self.assertEqual(self.world.player.dash_cooldown, cooldown)

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
        self.world.player.pos = Vec(3.5, 3.5)
        target = Spawner(Vec(6.5, 3.5), timer=999)
        self.world.spawners = [target]
        self.world.enemies.clear()
        self.world.attack(target.pos)
        self.advance(1)
        self.assertEqual(target.hp, 176)
        self.assertEqual(len(self.world.projectiles), 0)

    def test_rift_can_be_destroyed_and_stops_spawning(self):
        self.world.player.pos = Vec(5.5, 14.5)
        target = Spawner(Vec(8.5, 14.5), timer=999)
        self.world.spawners = [target]
        self.world.enemies.clear()
        for _ in range(8):
            self.world.attack(target.pos)
            self.advance(0.4)
        self.assertEqual(self.world.spawners, [])
        self.assertTrue(self.world.exit_open)
        self.assertTrue(any(p.value == 75 for p in self.world.pickups))
        self.advance(10)
        self.assertEqual(self.world.enemies, [])

    def test_enemies_navigate_around_obstacles(self):
        self.world.player.pos = Vec(7.5, 7.5)
        enemy = Enemy(Vec(2.5, 7.5))
        self.world.enemies = [enemy]
        self.world.spawners.clear()
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

    def test_gate_requires_rifts_and_enemies_to_be_cleared(self):
        self.world.player.pos = self.world.exit
        self.world.update(1 / 60)
        self.assertEqual(self.world.state, "playing")
        self.world.spawners.clear()
        self.world.enemies.clear()
        self.world.update(1 / 60)
        self.assertEqual(self.world.state, "won")
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
