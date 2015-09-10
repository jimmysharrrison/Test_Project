#!/usr/bin/python
__author__ = 'scott.harrison'

from gameobjects import *

def main():

    monster_names = ["spider", "goblin", "rat", "gelatinous cube", "skeleton", "whisp"]


class Spider(Monster):

    def __init__(self, spider_name, spider_hit_points, spider_defense, spider_attack):
        #monster_names = ["spider", "goblin", "rat", "gelatinous cube", "skeleton", "whisp"]
        super(Spider, self).__init__(spider_name, spider_hit_points, spider_defense, spider_attack)
        self.stats["Hit Points"] += randint(0, 10)
        self.stats["Name"] = "spider"
        self.stats.update({'Poison': 5})


if __name__ == "__main__":
    main()