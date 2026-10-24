"""Ground-field occupancy, enemy timing, frost damage and non-blocking combat."""
import unittest

from dungeon.abilities import ICE_PATCH_MOVE_FACTOR, ICE_PATCH_ATTACK_FACTOR
from dungeon.geometry import Vec
from dungeon.world import Enemy, IcePatch, Projectile, World


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def empty_world(depth=1):
    world = World(7, level=depth)
    world.enemies.clear()
    world.pickups.clear()
    for spawner in world.spawners:
        spawner.timer = 999
    world.combat_rng.random = lambda: 1
    return world


class IcePatchTests(unittest.TestCase):
    def test_enemy_moves_at_half_speed_inside_then_recovers_outside(self):
        distances = []
        for inside in (False, True):
            world = empty_world()
            enemy = world.make_enemy(Vec(8.5, 14.5), "husk")
            start = enemy.pos
            if inside:
                world.ice_patches.append(IcePatch(start))
            advance(world, .5)
            distances.append((enemy.pos - start).length())
            if inside:
                self.assertTrue(any(name == "Ice Patch" for name, _ in enemy.statuses))
                enemy.pos = Vec(4.5, 14.5)
                world.update(1 / 60)
                self.assertEqual(enemy.attack_rate, 1)
                self.assertAlmostEqual(enemy.move_speed, 1.05)
        self.assertAlmostEqual(distances[1] / distances[0], ICE_PATCH_MOVE_FACTOR)

    def test_attack_cooldown_slows_but_frost_status_durations_do_not(self):
        world = empty_world()
        enemy = world.make_enemy(Vec(8.5, 14.5), "husk", cooldown=2, frozen=1, chilled=2)
        world.ice_patches.append(IcePatch(enemy.pos))
        advance(world, .5)
        self.assertAlmostEqual(enemy.cooldown, 2 - .5 * ICE_PATCH_ATTACK_FACTOR)
        self.assertAlmostEqual(enemy.frozen, .5)
        self.assertAlmostEqual(enemy.chilled, 1.5)

    def test_expiry_removes_enemy_slow_and_mage_buff(self):
        world = empty_world()
        enemy = world.make_enemy(world.player.pos + Vec(1, 0), "husk", frozen=2)
        world.ice_patches.append(IcePatch(world.player.pos, life=.2))
        self.assertEqual(world.frost_multiplier, 1.3)
        advance(world, .3)
        self.assertEqual(world.ice_patches, [])
        self.assertEqual(world.frost_multiplier, 1)
        self.assertEqual(enemy.attack_rate, 1)
        self.assertEqual(enemy.patch_time, 0)

    def test_overlapping_patches_do_not_stack(self):
        world = empty_world()
        enemy = world.make_enemy(world.player.pos + Vec(1, 0), "husk", frozen=2)
        world.ice_patches = [IcePatch(world.player.pos), IcePatch(world.player.pos)]
        world.update(1 / 60)
        self.assertEqual(world.frost_multiplier, 1.3)
        self.assertEqual(enemy.attack_rate, .6)
        self.assertAlmostEqual(enemy.move_speed, 1.05 * .5)

    def test_chill_and_patch_movement_slow_combine(self):
        world = empty_world()
        enemy = world.make_enemy(Vec(8.5, 14.5), "husk", chilled=2)
        start = enemy.pos
        world.ice_patches.append(IcePatch(start))
        advance(world, .5)
        self.assertAlmostEqual((enemy.pos - start).length(), 1.05 * .5 * .6 * .5)

    def test_cast_bolt_keeps_bonus_after_mage_leaves_patch(self):
        world = empty_world()
        enemy = world.make_enemy(Vec(7.5, 13.5), "armor", frozen=5)
        enemy.hp = 500
        world.ice_patches.append(IcePatch(world.player.pos))
        world.cast("q", enemy.pos)
        world.player.pos = Vec(3.5, 9.5)
        advance(world, .5)
        self.assertEqual(enemy.hp, 500 - round(24 * 1.3))
        self.assertEqual(world.frost_multiplier, 1)

    def test_entering_patch_after_cast_does_not_retroactively_boost_bolt(self):
        world = empty_world()
        enemy = world.make_enemy(Vec(7.5, 13.5), "armor", frozen=5)
        enemy.hp = 500
        world.cast("q", enemy.pos)
        world.ice_patches.append(IcePatch(world.player.pos))
        advance(world, .5)
        self.assertEqual(enemy.hp, 476)

    def test_nova_and_prison_get_the_frost_bonus(self):
        for spell, damage in (("w", 14), ("r", 90)):
            world = empty_world()
            enemy = world.make_enemy(world.player.pos + Vec(1, 0), "armor", frozen=5)
            enemy.hp = 500
            world.ice_patches.append(IcePatch(world.player.pos, life=.3))
            world.cast(spell)
            advance(world, 2.6 if spell == "r" else .1)
            self.assertEqual(enemy.hp, 500 - round(damage * 1.3))

    def test_equipment_and_critical_damage_multiply_with_patch_once(self):
        world = empty_world()
        item = world.player.inventory.create("helm", 2)
        world.player.inventory.add(item)
        world.player.inventory.equip(item.uid)
        world.combat_rng.random = lambda: 0
        enemy = world.make_enemy(Vec(7.5, 13.5), "armor", frozen=5)
        enemy.hp = 500
        world.ice_patches.append(IcePatch(world.player.pos))
        world.cast("q", enemy.pos)
        advance(world, .5)
        self.assertEqual(enemy.hp, 500 - round(24 * 1.2 * 1.3 * 2))

    def test_hostile_projectiles_keep_damage_and_cross_the_patch(self):
        world = empty_world()
        world.ice_patches.append(IcePatch(world.player.pos))
        world.projectiles.append(Projectile(world.player.pos + Vec(2, 0), Vec(-5, 0), damage=10, hostile=True))
        advance(world, .5)
        self.assertEqual(world.player.hp, 90)

    def test_ground_boost_does_not_modify_non_spell_damage(self):
        world = empty_world()
        enemy = world.make_enemy(Vec(7.5, 13.5), "armor")
        world.ice_patches.append(IcePatch(world.player.pos))
        world._hit(enemy, 10)
        self.assertEqual(enemy.hp, enemy.max_hp - 10)

    def test_patch_does_not_change_player_cooldown_or_movement_speed(self):
        world = empty_world()
        before = world.player.move_speed
        world.ice_patches.append(IcePatch(world.player.pos))
        world.cast("q", Vec(8.5, 13.5))
        advance(world, .2)
        self.assertEqual(world.player.move_speed, before)
        self.assertAlmostEqual(world.player.cooldowns["q"], .15)

    def test_specimen_windup_and_lunge_both_slow(self):
        world = empty_world(4)
        enemy = world.make_enemy(Vec(8.5, 12.5), "predator")
        world.player.pos = Vec(8.5, 14.5)
        world.ice_patches.append(IcePatch(enemy.pos))
        advance(world, .9)
        self.assertEqual(enemy.action, "warning")
        self.assertEqual(world.player.hp, 100)
        advance(world, .5)
        self.assertEqual(enemy.action, "lunge")
        start = enemy.pos
        advance(world, .1)
        self.assertAlmostEqual((enemy.pos - start).length(), 7 * .5 * .1)

    def test_keeper_and_miniboss_attack_timers_slow(self):
        world = World(7, level=5)
        fight = world.keeper
        world.ice_patches.append(IcePatch(fight.boss.pos))
        fight.next_cast = 10
        self.assertTrue(fight.start("cleaning"))
        warning = fight.mechanics[0].warning
        advance(world, .5)
        self.assertAlmostEqual(fight.next_cast, 10 - .5 * .6)
        self.assertAlmostEqual(fight.mechanics[0].warning, warning - .5 * .6)
        world = empty_world()
        world.spawners.clear()
        world._activate_boss()
        boss = next(e for e in world.enemies if e.boss_role == "boss")
        world.ice_patches.append(IcePatch(boss.pos))
        before = boss.signature_timer
        advance(world, .5)
        self.assertAlmostEqual(boss.signature_timer, before - .5 * .6)

    def test_death_and_floor_transition_clear_patch_state(self):
        world = empty_world()
        world.ice_patches.append(IcePatch(world.player.pos))
        world._hurt_player(1000)
        self.assertEqual(world.ice_patches, [])
        world = empty_world()
        world.ice_patches.append(IcePatch(world.player.pos))
        world.state = "cleared"
        self.assertTrue(world.next_level())
        self.assertEqual(world.ice_patches, [])
        self.assertEqual(world.frost_multiplier, 1)


if __name__ == "__main__":
    unittest.main()
