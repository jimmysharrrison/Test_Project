import contextlib
import io
import unittest
from unittest.mock import patch

import text_game as main
from gameobjects import Monster, Player
from monsters import Spider


class GameTests(unittest.TestCase):
    def setUp(self):
        self.player = Player("hero", 100, 10, 10)
        self.monster = Monster("monster", 20, 10, 5)

    def test_monster_selection_stays_in_bounds(self):
        with patch("gameobjects.choice", side_effect=lambda names: names[-1]):
            self.assertEqual(Monster("monster", 20, 10, 5).stats["Name"], "whisp")

    def test_spider_initialization(self):
        spider = Spider("monster", 20, 10, 5)
        self.assertEqual(spider.stats["Name"], "spider")
        self.assertEqual(spider.stats["Poison"], 5)

    def test_combat_actions(self):
        initial_monster_health = self.monster.stats["Hit Points"]
        with contextlib.redirect_stdout(io.StringIO()):
            with (
                patch("gameobjects.randint", return_value=5),
                patch("gameobjects.GameActor.check_hit", return_value=True),
            ):
                main.combat(self.player, self.monster, "attack")
                self.assertEqual(self.monster.stats["Hit Points"], initial_monster_health - 5)
                self.assertEqual(self.player.stats["Hit Points"], 95)
                main.combat(self.player, self.monster, "defend")
                self.assertEqual(self.player.stats["Hit Points"], 95)
            main.combat(self.player, self.monster, "health potion")
            self.assertEqual(self.player.stats["Hit Points"], 105)
            self.assertEqual(self.player.stats["Potion Count"], 2)

    def test_empty_potions_preserve_health_and_count(self):
        self.player.stats["Potion Count"] = 0
        with contextlib.redirect_stdout(io.StringIO()):
            main.combat(self.player, self.monster, "health potion")
            health = self.player.health_potion(self.player.stats, 0, 10)
        self.assertEqual(health, 100)
        self.assertEqual(self.player.stats["Hit Points"], 100)
        self.assertEqual(self.player.stats["Potion Count"], 0)

    def test_interactive_room_and_combat(self):
        room = main.DungeonRoom()
        room.monsters = 1
        monster = Monster("monster", 1, 0, 0)
        monster.stats.update({"Hit Points": 1, "Attack": 0})
        output = io.StringIO()
        with (
            patch("text_game.create_dungeon_rooms", return_value={0: room}),
            patch("text_game.Monster", return_value=monster),
            patch("builtins.input", side_effect=["1", "1"]),
            patch("gameobjects.randint", return_value=1),
            contextlib.redirect_stdout(output),
        ):
            main.main()
        self.assertIn("Congrats you have slain", output.getvalue())
        self.assertEqual(room.monsters, 0)


if __name__ == "__main__":
    unittest.main()
