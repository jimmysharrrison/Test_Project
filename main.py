#!/usr/bin/python
__author__ = 'scott.harrison'

from random import randint

player_name, player_hit_points, player_defense, player_attack = "player1", 100, 10, 5
monster_name, monster_hit_points, monster_defense, monster_attack = "monster", 20, 10, 5
base_roll = 1
d20 = 20
dead = 0
potion_hit_point = 10
starting_potion_count = 3


def main():

    dungeon_rooms = {}
    monsters = {}

    player_one = Player(player_name, player_hit_points, player_defense, player_attack)
    """monster = GameActor(monster_name, monster_hit_points, monster_defense, monster_attack)"""

    number_of_rooms = randint(2, 5)
    print "Number of Rooms: " + str(number_of_rooms)

    for room in range(number_of_rooms):
        dungeon_rooms[room] = DungeonRoom()

    print 'Player One Initialized with %s' % player_one.stats
    print 'You are standing in front of a large wooden door.'

    for room in dungeon_rooms:

        if player_one.stats["Hit Points"] <= dead:
            break

        print "Room %s has %s Doors, %s Monsters, %s Traps, and %s loot" \
              % (room + 1, dungeon_rooms[room].doors, dungeon_rooms[room].monsters, dungeon_rooms[room].traps, dungeon_rooms[room].loot)

        if raw_input("Press 1 to enter the door: ") == "1":
            print 'You step inside the door, there is a large dimly lit room.'

            for monster in range(dungeon_rooms[room].monsters):
                monsters[monster] = Monster(monster_name, monster_hit_points, monster_defense, monster_attack)

                if dungeon_rooms[room].monsters > 0:

                    print 'Suddenly a %s attacks you.' % monsters[monster].stats["Name"]

                    while player_one.stats["Hit Points"] > dead and monsters[monster].stats["Hit Points"] > dead:

                        combat_choice = player_combat_choice()
                        combat(player_one, monsters[monster], combat_choice)

                        if monsters[monster].stats["Hit Points"] <= dead:

                            print 'Congrats you have slain the %s!' % monsters[monster].stats["Name"]
                            dungeon_rooms[room].monsters -= 1
                            break

                        elif player_one.stats["Hit Points"] <= dead:

                            print 'You have been slain!'
                            break
                else:
                    print 'You look around and do not see any immediate danger.'

        else:

            print 'You have decided to end your adventure!'


def player_combat_choice():

    player_choice = raw_input('Press 1 to Attack or 2 to Defend or 3 for a Health Potion: ')

    if player_choice == "1":
        return "attack"

    elif player_choice == "2":
        return "defend"

    elif player_choice == "3":
        return "health potion"

    else:
        return False


def combat(player_one, monster, combat_choice):

    print "----------------------------------------------"

    if combat_choice == "attack":

        if player_one.check_hit(monster.stats, player_one.stats):

            monster.stats["Hit Points"], damage_done = player_one.attack(monster.stats, player_one.stats)
            print 'You attack the %s for %s damage.' % (monster.stats["Name"], damage_done)
            print 'The %s has %s life left!' % (monster.stats["Name"], monster.stats["Hit Points"])
        else:
            print 'You have missed the attack!'

        if monster.check_hit(player_one.stats, monster.stats):

            player_one.stats["Hit Points"], damage_done = monster.attack(player_one.stats, monster.stats)
            print 'The %s Attacks you for %s!' % (monster.stats["Name"], damage_done)
            print 'You have %s health left!' % (player_one.stats["Hit Points"])
        else:
            print 'You dodge the %s\'s attack!' % monster.stats["Name"]

    elif combat_choice == "defend":

        defend_attack, modified_attack, player_one.stats["Hit Points"] = player_one.defend(player_one.stats, monster.stats)
        print 'A %s attacks for %s but you defend (%s) and take %s damage' \
              % (monster.stats["Name"], monster.stats["Attack"], defend_attack, modified_attack)
        print 'You have %s health left!' % (player_one.stats["Hit Points"])

    elif combat_choice == "health potion":

        player_one.stats["Hit Points"] = player_one.health_potion(player_one.stats, player_one.stats["Potion Count"], potion_hit_point)
        print 'You have drank a health potion you now have %s health!' % player_one.stats["Hit Points"]
        player_one.stats["Potion Count"] -= 1
        print 'You have %s potions left!' % player_one.stats["Potion Count"]

    else:

        print 'You have not entered a valid choice!'


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


class Player(GameActor):

    def __init__(self, name, a_player_hit_points, a_player_defense, a_player_attack):
        super(Player, self).__init__(name, a_player_hit_points, a_player_defense, a_player_attack)
        self.stats["Potion Count"] = starting_potion_count


class DungeonRoom(object):
    def __init__(self):
        self.length = randint(5, 12)
        self.width = randint(5, 12)
        self.doors = randint(2, 4)
        self.traps = randint(0, 2)
        self.monsters = randint(0, 3)
        self.loot = randint(1, 3)


class Monster(GameActor):

    def __init__(self, a_name, a_monster_hit_points, a_monster_defense, a_monster_attack):
        monster_names = ["spider", "goblin", "rat", "gelatinous cube", "skeleton", "whisp"]
        super(Monster, self).__init__(a_name, a_monster_hit_points, a_monster_defense, a_monster_attack)
        self.stats["Hit Points"] += randint(0, 10)
        self.stats["Name"] = monster_names[randint(0, len(monster_names))]


if __name__ == "__main__":
    main()
