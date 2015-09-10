#!/usr/bin/python
__author__ = 'scott.harrison'

from random import randint

player_name, player_hit_points, player_defense, player_attack = "player1", 100, 10, 10
monster_name, monster_hit_points, monster_defense, monster_attack = "monster", 20, 10, 5
base_roll = 1
d20 = 20
dead = 0
potion_hit_point = 10
starting_potion_count = 3
number_of_rooms = randint(2, 6)

