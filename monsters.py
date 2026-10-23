#!/usr/bin/env python3
__author__ = 'scott.harrison'

from random import randint

from gameobjects import Monster

def main():

    monster_names = ["spider", "goblin", "rat", "gelatinous cube", "skeleton", "whisp"]


class Spider(Monster):

    def __init__(self, spider_name, spider_hit_points, spider_defense, spider_attack):
        #monster_names = ["spider", "goblin", "rat", "gelatinous cube", "skeleton", "whisp"]
        super(Spider, self).__init__(spider_name, spider_hit_points, spider_defense, spider_attack)
        self.stats["Hit Points"] += randint(0, 10)
        self.stats.update({"Name": "spider", "Poison": 5})


if __name__ == "__main__":
    main()
