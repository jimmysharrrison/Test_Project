#!/usr/bin/python
__author__ = 'scott.harrison'

from gameobjects import *
from settings import *


def main():

    dungeon_rooms = {}
    monsters = {}

    player_one = Player(player_name, player_hit_points, player_defense, player_attack)

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


class DungeonRoom(object):

    clear = False

    def __init__(self):
        self.length = randint(5, 12)
        self.width = randint(5, 12)
        self.doors = randint(2, 4)
        self.traps = randint(0, 2)
        self.monsters = randint(0, 3)
        self.loot = randint(1, 3)

    def is_clear(self):
        self.clear = True

if __name__ == "__main__":
    main()
