#!/usr/bin/python
__author__ = 'scott.harrison'

from settings import *

class GameActor(object):

    def __init__(self, name, hit_points, defense, attack):

        self.stats = {
            "Name": name,
            "Hit Points": hit_points,
            "Defense": defense,
            "Attack": attack
        }

    def attack(self, defender_stats, attacker_stats):

        attack_damage = randint(1, attacker_stats["Attack"])
        defender_stats["Hit Points"] -= attack_damage
        return defender_stats["Hit Points"], attack_damage

    def check_hit(self, defender_stats, attacker_stats):

        chance_to_hit = randint(base_roll, d20) + attacker_stats["Attack"]
        if chance_to_hit > defender_stats["Defense"]:
            return True
        else:
            return False

    def health_potion(self, drinker_stats, potion_count, life_to_restore):

        if potion_count > 0:
            drinker_stats["Hit Points"] += life_to_restore
            print "You have restored %s life!" % life_to_restore
            return drinker_stats["Hit Points"]

        else:
            print "You do not have anymore Health Potions!"

    def defend(self, defender_stats, attacker_stats):

        defend_attack = randint(0, defender_stats["Defense"])
        modified_attack = attacker_stats["Attack"] - defend_attack

        if modified_attack <= 0:
            modified_attack = 0

        defender_stats["Hit Points"] -= modified_attack
        return defend_attack, modified_attack, defender_stats["Hit Points"]


class Monster(GameActor):

    def __init__(self, a_name, a_monster_hit_points, a_monster_defense, a_monster_attack):
        monster_names = ["spider", "goblin", "rat", "gelatinous cube", "skeleton", "whisp"]
        super(Monster, self).__init__(a_name, a_monster_hit_points, a_monster_defense, a_monster_attack)
        self.stats["Hit Points"] += randint(0, 10)
        self.stats["Name"] = monster_names[randint(0, len(monster_names))]
        #self.stats.update({'Poison': 5})


class Player(GameActor):

    def __init__(self, name, a_player_hit_points, a_player_defense, a_player_attack):
        super(Player, self).__init__(name, a_player_hit_points, a_player_defense, a_player_attack)
        self.stats["Potion Count"] = starting_potion_count