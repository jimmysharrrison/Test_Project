"""Room layouts, encounter rosters, and presentation for each chapter."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Level:
    name: str
    chapter: str
    subtitle: str
    theme: str
    layout: tuple[str, ...]
    enemies: tuple[tuple[float, float, str], ...]
    spawners: tuple[tuple[float, float], ...]
    spawn_kinds: tuple[str, ...]
    spawn_weights: tuple[int, ...]
    pickups: tuple[tuple[float, float, str, int], ...]

    @property
    def forest(self):
        return self.theme == "forest"


FROSTFALL = Level(
    name="Frostfall Glade",
    chapter="CHAPTER I    /    WINTER AGAINST THE EMBER",
    subtitle="The mountain calls its dead. Let winter answer.",
    theme="ruins",
    layout=(
        "#################",
        "#...............#",
        "#...##..........#",
        "#...##....##....#",
        "#.........##....#",
        "#...............#",
        "#..##...........#",
        "#..##.....##....#",
        "#.........##....#",
        "#...............#",
        "#.....##........#",
        "#.....##....##..#",
        "#...........##..#",
        "#...............#",
        "#...............#",
        "#...............#",
        "#################",
    ),
    enemies=((7.5, 5.5, "husk"), (12.5, 5.5, "husk"), (10.5, 12.5, "skitter")),
    spawners=((4.5, 4.5), (13.5, 4.5), (12.5, 13.5)),
    spawn_kinds=("husk", "skitter"),
    spawn_weights=(65, 35),
    pickups=((7.5, 13.5, "food", 25), (12.5, 8.5, "food", 25),
             (8.5, 6.5, "gold", 25), (5.5, 9.5, "gold", 25)),
)

THORNVEIL = Level(
    name="Thornveil Forest",
    chapter="CHAPTER II    /    ROOTS OF THE CURSED",
    subtitle="Dark roots stir. The dead draw their bows.",
    theme="forest",
    layout=(
        "#################",
        "#...............#",
        "#.......##......#",
        "#..##...##..#...#",
        "#..##.......#...#",
        "#...............#",
        "#...............#",
        "#.....##........#",
        "#.....##...##...#",
        "#..........##...#",
        "#..##...........#",
        "#..#............#",
        "#........#......#",
        "#........##.....#",
        "#...............#",
        "#...............#",
        "#################",
    ),
    enemies=((6.5, 5.5, "tree"), (10.5, 7.5, "tree"),
             (6.5, 12.5, "spider"), (13.5, 10.5, "spider"),
             (8.5, 11.5, "archer"), (12.5, 6.5, "archer")),
    spawners=((4.5, 5.5), (13.5, 4.5), (12.5, 13.5)),
    spawn_kinds=("tree", "spider", "archer"),
    spawn_weights=(45, 35, 20),
    pickups=((7.5, 13.5, "food", 25), (13.5, 8.5, "food", 25),
             (8.5, 6.5, "gold", 25), (5.5, 9.5, "gold", 25)),
)


def level_for_depth(depth):
    # Further depths retain the forest encounter until new chapters are authored.
    return FROSTFALL if depth == 1 else THORNVEIL
