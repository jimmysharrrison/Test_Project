import unittest

from dungeon.controls import Controls
from dungeon.geometry import Vec
from dungeon.world import Enemy, Spawner, World


class SpellTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.world.enemies.clear()
        for rift in self.world.spawners:
            rift.timer = 999

    def advance(self, seconds):
        for _ in range(round(seconds * 60)):
            self.world.update(1 / 60)

    def test_bolt_is_a_skillshot_and_applies_chill(self):
        enemy = Enemy(Vec(5.5, 13.5))
        self.world.enemies = [enemy]
        self.assertTrue(self.world.cast("q", enemy.pos))
        self.assertFalse(self.world.cast("q", enemy.pos))
        self.advance(0.25)
        self.assertEqual(enemy.hp, 20)
        self.assertGreater(enemy.chilled, 0)
        self.assertEqual(self.world.player.mana, 100)

    def test_frost_nova_freezes_movement_and_attacks_then_expires(self):
        enemy = Enemy(self.world.player.pos + Vec(0.4, 0))
        self.world.enemies = [enemy]
        self.world.cast("w")
        position = enemy.pos
        self.advance(2)
        self.assertEqual(enemy.pos, position)
        self.assertEqual(enemy.hp, 30)
        self.assertEqual(self.world.player.hp, 100)
        self.assertGreater(enemy.frozen, 0)
        self.advance(0.5)
        self.assertEqual(enemy.frozen, 0)
        self.assertLess(self.world.player.hp, 100)

    def test_nova_does_not_hit_through_stone(self):
        self.world.player.pos = Vec(4.5, 5.5)
        enemy = Enemy(Vec(6.5, 5.5))
        self.world.enemies = [enemy]
        self.world.cast("w")
        self.assertEqual(enemy.hp, 44)
        self.assertEqual(enemy.frozen, 0)

    def test_insufficient_mana_does_not_spend_cooldown(self):
        self.world.player.mana = 10
        self.assertFalse(self.world.cast("w"))
        self.assertEqual(self.world.player.mana, 10)
        self.assertEqual(self.world.player.cooldowns["w"], 0)
        self.advance(1)
        self.assertAlmostEqual(self.world.player.mana, 18)

    def test_prison_prevents_damage_casting_and_movement_then_shatters(self):
        self.world.player.hp = 50
        self.world.enemies = [Enemy(self.world.player.pos + Vec(0.4, 0)),
                              Enemy(self.world.player.pos + Vec(2, 0))]
        self.world.request_move(Vec(9.5, 14.5))
        start = self.world.player.pos
        self.assertTrue(self.world.cast("r"))
        self.assertFalse(self.world.cast("q", Vec(8.5, 14.5)))
        self.world.use_potion()
        self.assertEqual(self.world.player.potions, 3)
        self.advance(2)
        self.assertEqual(self.world.player.pos, start)
        self.assertEqual(self.world.player.hp, 50)
        self.advance(0.6)
        self.assertEqual(self.world.player.stasis, 0)
        self.assertEqual(self.world.enemies, [])
        self.assertEqual(self.world.player.kills, 2)
        self.assertGreater(self.world.player.cooldowns["r"], 40)
        self.assertNotEqual(self.world.player.pos, start)

    def test_patch_is_walkable_bolts_cross_it_and_it_expires(self):
        target = Vec(6.5, 13.5)
        self.assertTrue(self.world.cast("e", target))
        self.assertTrue(self.world.walkable(target))
        self.assertEqual(self.world.player.mana, 70)
        self.advance(.25)
        rift = Spawner(Vec(9.5, 13.5), timer=999)
        self.world.spawners = [rift]
        self.world.cast("q", rift.pos)
        self.advance(1)
        self.assertEqual(rift.hp, 152)
        self.advance(5)
        self.assertEqual(self.world.ice_patches, [])

    def test_patch_preserves_existing_move_order_and_mage_speed(self):
        goal = Vec(9.5, 13.5)
        self.world.request_move(goal)
        self.assertTrue(self.world.cast("e", Vec(6.5, 13.5)))
        self.advance(2.3)
        self.assertLess((self.world.player.pos - goal).length(), .03)

    def test_patch_invalid_placement_does_not_spend_resources(self):
        for target in (Vec(15.5, 2.5), Vec(5.5, 11.5), Vec(6.5, 10.5)):
            self.assertFalse(self.world.cast("e", target))
        self.assertEqual(self.world.player.mana, 100)
        self.assertEqual(self.world.player.cooldowns["e"], 0)

    def test_patch_can_cover_the_mage_or_an_enemy(self):
        self.world.enemies = [Enemy(self.world.player.pos + Vec(1, 0))]
        self.assertTrue(self.world.cast("e", self.world.player.pos))
        self.assertEqual(self.world.frost_multiplier, 1.3)
        self.assertEqual(self.world.enemies[0].attack_rate, .6)

    def test_patch_in_a_doorway_does_not_seal_the_corridor(self):
        from dungeon.navigation import flood
        self.world.player.pos = Vec(3.5, 8.5)
        self.world.walls.update((7, y) for y in range(1, 16) if y not in (7, 8, 9))
        before = flood((3, 8), self.world.blocked)
        self.assertTrue(self.world.cast("e", Vec(7.5, 8.5)))
        self.assertEqual(flood((3, 8), self.world.blocked), before)
        self.assertTrue(self.world.walkable(Vec(7.5, 8.5)))

    def test_target_clears_after_death(self):
        target = Enemy(Vec(5.5, 13.5))
        self.world.enemies = [target]
        self.world.selected = target
        self.world._hit(target, 99)
        self.assertIsNone(self.world.selected)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.world = World(7)
        self.controls = Controls(self.world)

    def test_left_click_selects_without_attacking_or_moving(self):
        target = self.world.enemies[0]
        self.controls.left_world(target.pos, target)
        self.assertIs(self.world.selected, target)
        self.assertEqual(self.world.projectiles, [])
        self.assertEqual(self.world.path, [])
        self.controls.left_world(Vec(3.5, 14.5))
        self.assertIsNone(self.world.selected)

    def test_right_click_orders_persist_and_held_input_updates_goal(self):
        self.controls.right_down(Vec(8.5, 14.5))
        first = self.world.destination
        for _ in range(12):
            self.controls.update(1 / 60, Vec(2.5, 14.5))
        self.assertNotEqual(self.world.destination, first)
        self.assertEqual(self.world.destination, Vec(2.5, 14.5))
        self.controls.right_up()
        self.controls.update(1 / 60)
        self.assertEqual(self.world.destination, Vec(2.5, 14.5))

    def test_clickable_bolt_arms_then_fires_at_confirmed_point(self):
        self.controls.ability_button("q")
        self.assertEqual(self.controls.armed, "q")
        self.assertEqual(self.world.projectiles, [])
        self.controls.left_world(Vec(5.5, 13.5))
        self.assertIsNone(self.controls.armed)
        self.assertEqual(len(self.world.projectiles), 1)

    def test_self_cast_button_casts_without_aim_confirmation(self):
        self.controls.ability_button("w")
        self.assertIsNone(self.controls.armed)
        self.assertEqual(self.world.player.mana, 75)
        self.assertGreater(self.world.player.cooldowns["w"], 0)

    def test_right_click_cancels_aim_without_issuing_a_move(self):
        self.controls.ability_button("e")
        self.controls.right_down(Vec(8.5, 14.5))
        for _ in range(30):
            self.controls.update(1 / 60, Vec(8.5, 14.5))
        self.assertIsNone(self.controls.armed)
        self.assertIsNone(self.world.destination)
        self.controls.right_up()
        self.controls.update(0.2, Vec(8.5, 14.5))
        self.assertIsNotNone(self.world.destination)

    def test_held_q_repeats_with_cooldown(self):
        self.controls.point(Vec(10.5, 13.5))
        count = 0
        for _ in range(60):
            self.controls.update(1 / 60, repeat_q=True)
            count += self.world.events.count("bolt")
            self.world.events.clear()
            self.world.update(1 / 60)
        self.assertEqual(count, 3)

    def test_spell_aim_can_account_for_projectile_visual_height(self):
        self.controls.point(Vec(6, 12), Vec(6.5, 12.5))
        self.controls.hotkey("q")
        expected = (Vec(6.5, 12.5) - self.world.player.pos).unit()
        self.assertEqual(self.world.projectiles[0].velocity, expected * 10)


if __name__ == "__main__":
    unittest.main()
