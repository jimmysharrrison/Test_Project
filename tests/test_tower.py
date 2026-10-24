"""Three-phase tower floors, safe transitions, story scope, and alchemical enemies."""

from math import floor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from dungeon.geometry import Vec
from dungeon.levels import COLUMNS, FLOORS, MOTTO, PHASE_COUNTS, PHASE_DELAY, PHASE_SPEEDS, level_for_depth
from dungeon.menus import Menus
from dungeon.navigation import flood
from dungeon.profile import ProfileStore
from dungeon.world import Enemy, IceWall, Player, World


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def break_spawners(world):
    for spawner in world.spawners[:]:
        world._hit(spawner, 10000)


class TowerTests(unittest.TestCase):
    def test_ground_floor_has_four_equally_spaced_solid_columns(self):
        world = World(7)
        self.assertEqual(len(COLUMNS), 4)
        distances = {(Vec(x + .5, y + .5) - Vec(8.5, 8.5)).length() for x, y in COLUMNS}
        self.assertEqual(len(distances), 1)
        self.assertEqual({(x, y) for x, y in world.walls if 0 < x < 16 and 0 < y < 16}, set(COLUMNS))
        self.assertTrue(all(not world.walkable(Vec(x + .5, y + .5)) for x, y in COLUMNS))
        self.assertEqual(MOTTO, "elementis fidelis est")
        self.assertIn("Drearamore", FLOORS[0].story)

    def test_all_phase_positions_are_reachable_and_each_floor_uses_two_three_four(self):
        for depth, data in enumerate(FLOORS, 1):
            world = World(7, level=depth)
            reached = flood((3, 13), world.blocked)
            self.assertEqual(tuple(len(phase) for phase in data.phase_spawners), PHASE_COUNTS)
            self.assertEqual(len(world.spawners), 2)
            for phase in data.phase_spawners:
                for x, y in phase:
                    self.assertTrue(world.walkable(Vec(x, y)))
                    self.assertIn((floor(x), floor(y)), reached)

    def test_phase_delays_counts_gate_and_boot_reward_only_after_final_clear(self):
        for depth in (1, 2, 3):
            with self.subTest(floor=depth):
                world = World(7, level=depth)
                world.enemies.clear()
                total = 0
                for phase, count in enumerate(PHASE_COUNTS, 1):
                    self.assertEqual((world.phase, len(world.spawners)), (phase, count))
                    break_spawners(world)
                    total += count
                    self.assertEqual(world.spawners_defeated, total)
                    if phase < 3:
                        self.assertFalse(world.exit_open)
                        self.assertFalse(world.level_completed)
                        self.assertFalse(world.player.first_clear_rewarded)
                        self.assertEqual(world.intermission, PHASE_DELAY)
                        advance(world, PHASE_DELAY - .1)
                        self.assertEqual(world.phase, phase)
                        self.assertEqual(world.spawners, [])
                        self.assertAlmostEqual(world.intermission, .1)
                        advance(world, .1)
                    else:
                        self.assertTrue(world.exit_open)
                        self.assertTrue(world.level_completed)
                        self.assertEqual(world.player.first_clear_rewarded, depth == 1)
                self.assertEqual(world.spawners_defeated, 9)
                self.assertEqual(world.player.unlocked_level, depth)
                self.assertFalse(any(p.kind in ("gold", "item") for p in world.pickups))
                count = len(world.player.inventory.items)
                advance(world, .5)
                self.assertEqual(len(world.player.inventory.items), count)

    def test_intermission_does_not_pause_survivors_or_player_movement(self):
        world = World(7)
        world.enemies = [Enemy(Vec(14.5, 14.5))]
        break_spawners(world)
        player_start, enemy_start = world.player.pos, world.enemies[0].pos
        world.request_move(Vec(4.5, 14.5))
        advance(world, 1)
        self.assertNotEqual(world.player.pos, player_start)
        self.assertNotEqual(world.enemies[0].pos, enemy_start)
        self.assertAlmostEqual(world.intermission, 2)
        self.assertFalse(world.exit_open)

    def test_phase_changes_do_not_reset_health_mana_or_cooldowns(self):
        world = World(7)
        world.enemies.clear()
        world.pickups.clear()
        world.player.hp, world.player.mana = 40, 10
        world.player.cooldowns["r"] = 40
        break_spawners(world)
        advance(world, 3.05)
        self.assertEqual(world.phase, 2)
        self.assertEqual(world.player.hp, 40)
        self.assertLess(world.player.mana, 40)
        self.assertGreater(world.player.cooldowns["r"], 36)

    def test_new_phase_spawns_faster_mobs_but_existing_cohorts_keep_their_speed(self):
        world = World(7)
        world.enemies.clear()
        spawned = []
        for phase, multiplier in enumerate(PHASE_SPEEDS, 1):
            for spawner in world.spawners:
                spawner.timer = 999
            world.spawners[0].timer = 0
            world._spawn(1 / 60)
            enemy = world.enemies[-1]
            spawned.append(enemy)
            enemy.frozen = 30
            self.assertEqual(enemy.spawn_phase, phase)
            base = Enemy(enemy.pos, enemy.kind).move_speed
            self.assertAlmostEqual(enemy.move_speed / base, multiplier)
            if phase < 3:
                break_spawners(world)
                advance(world, 3.05)
        self.assertEqual([enemy.spawn_phase for enemy in spawned], [1, 2, 3])
        self.assertEqual(spawned[0].move_speed, Enemy(spawned[0].pos, spawned[0].kind).move_speed)

    def test_phase_speed_affects_actual_movement_and_chill_still_reduces_it(self):
        distances = []
        for phase, chilled in ((1, 0), (3, 0), (3, 2)):
            world = World(7)
            for spawner in world.spawners:
                spawner.timer = 999
            world.player.pos = Vec(3.5, 14.5)
            start = Vec(7.5, 14.5)
            enemy = Enemy(start, spawn_phase=phase, chilled=chilled)
            world.enemies = [enemy]
            advance(world, .5)
            distances.append((enemy.pos - start).length())
        self.assertAlmostEqual(distances[1] / distances[0], 1.30)
        self.assertAlmostEqual(distances[2] / distances[1], .60)

    def test_new_spawners_avoid_player_survivors_and_temporary_ice(self):
        world = World(7)
        world.enemies.clear()
        break_spawners(world)
        world.player.pos = Vec(4.5, 8.5)
        world.enemies = [Enemy(Vec(8.5, 12.5), frozen=20)]
        world.ice_walls.append(IceWall(((12, 7), (12, 8), (12, 9))))
        world._navigation_changed()
        advance(world, 3.05)
        self.assertEqual((world.phase, len(world.spawners)), (2, 3))
        for spawner in world.spawners:
            self.assertTrue(world.walkable(spawner.pos, .55))
            self.assertGreaterEqual((spawner.pos - world.player.pos).length(), 1)
            self.assertGreaterEqual((spawner.pos - world.enemies[0].pos).length(), .8)
        self.assertEqual(len({spawner.pos for spawner in world.spawners}), 3)

    def test_only_three_authored_floors_are_playable_and_terminal_portal_ends_build(self):
        for invalid in (0, 4, 20):
            with self.assertRaises(ValueError):
                World(7, level=invalid)
        world = World(7, level=3)
        world.enemies.clear()
        for phase in (1, 2, 3):
            break_spawners(world)
            if phase < 3:
                advance(world, 3.05)
        world.player.pos = world.exit
        world.update(1 / 60)
        self.assertEqual(world.state, "won")
        self.assertFalse(world.next_level())
        self.assertEqual(world.player.unlocked_level, 3)
        menu = Menus()
        choices = [b for b in menu.buttons(world, "levels") if b.action.startswith("level:")]
        self.assertEqual(len(choices), 5)
        self.assertEqual([b.enabled for b in choices], [True, True, True, False, False])
        self.assertIn("COMING LATER", choices[3].label)
        self.assertIn("story", [b.action for b in menu.buttons(world, "title")])

    def test_legacy_endless_depth_maps_to_third_floor_without_losing_gear_or_gold(self):
        player = Player(unlocked_level=18, current_level=17, gold=12345, first_clear_rewarded=True)
        item = player.inventory.create("helm", 5, "shop")
        player.inventory.add(item)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            ProfileStore(path).save(player)
            loaded = ProfileStore(path).load()
        self.assertEqual((loaded.current_level, loaded.unlocked_level, loaded.gold), (3, 3, 12345))
        self.assertEqual(loaded.inventory.to_dict(), player.inventory.to_dict())
        self.assertTrue(loaded.first_clear_rewarded)


class AlchemistTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7, level=3)
        self.world.pickups.clear()
        for spawner in self.world.spawners:
            spawner.timer = 999
        self.world.player.pos = Vec(3.5, 14.5)
        self.fairy = Enemy(Vec(7.5, 14.5), "fairy", level=3)
        self.fairy.hp = self.fairy.max_hp
        self.world.enemies = [self.fairy]

    def test_workshop_has_unique_roster_and_alchemical_generators(self):
        world = World(7, level=3)
        self.assertEqual(world.level_data.theme, "alchemy")
        self.assertEqual({enemy.kind for enemy in world.enemies}, {"armor", "grimoire", "fairy"})
        self.assertEqual({s.name for s in world.spawners}, {"Unstable Alembic"})
        kinds = set()
        for _ in range(80):
            world.enemies.clear()
            for spawner in world.spawners:
                spawner.timer = 0
            world._spawn(1 / 60)
            kinds.update(enemy.kind for enemy in world.enemies)
        self.assertEqual(kinds, {"armor", "grimoire", "fairy"})

    def test_fairy_telegraphs_then_fires_a_potion_bolt_at_player(self):
        advance(self.world, .5)
        self.assertGreater(self.fairy.windup, 0)
        self.assertEqual(self.world.projectiles, [])
        advance(self.world, .45)
        self.assertEqual(len(self.world.projectiles), 1)
        self.assertEqual(self.world.projectiles[0].spell, "potion")
        self.assertTrue(self.world.projectiles[0].hostile)
        self.assertIn("potion_cast", self.world.events)
        advance(self.world, 1)
        self.assertEqual(self.world.player.hp, 91)

    def test_fairy_potion_can_be_dodged_and_blocked_by_ice_wall(self):
        advance(self.world, .1)
        self.world.request_move(Vec(3.5, 12.5))
        advance(self.world, 1.7)
        self.assertEqual(self.world.player.hp, 100)
        self.setUp()
        advance(self.world, .95)
        self.assertTrue(self.world.cast("e", Vec(5.5, 14.5)), self.world.message)
        advance(self.world, 1.5)
        self.assertEqual(self.world.player.hp, 100)
        self.assertEqual(self.world.projectiles, [])

    def test_frostweave_can_freeze_all_three_alchemical_enemy_types(self):
        from dungeon.items import SLOTS
        for slot in SLOTS:
            inv = self.world.player.inventory
            inv.add(inv.create(slot, 3, "shop"))
        self.world.proc_rng = Mock()
        self.world.proc_rng.random.return_value = 0
        from dungeon.world import Projectile
        for kind in ("armor", "grimoire", "fairy"):
            enemy = Enemy(Vec(7.5, 14.5), kind, level=3)
            enemy.hp = enemy.max_hp
            self.world.enemies = [enemy]
            self.world.projectiles = [Projectile(enemy.pos - Vec(.2, 0), Vec(10, 0), damage=1)]
            self.world._projectiles(.02)
            self.assertEqual(enemy.frozen, 1)
            self.assertEqual(enemy.chilled, 2)


if __name__ == "__main__":
    unittest.main()
