"""The Tower's authored floors, story, and three escalating encounter phases."""

from dataclasses import dataclass

TOWER_FLOORS = 20
FOCUS_FLOORS = 5
PHASE_COUNTS = (2, 3, 0)
PHASE_SPEEDS = (1.0, 1.15, 1.30)
PHASE_DELAY = 3.0
MOTTO = "elementis fidelis est"


def room(obstacles):
    return tuple("".join("#" if x in (0, 16) or y in (0, 16) or (x, y) in obstacles else "."
                         for x in range(17)) for y in range(17))


@dataclass(frozen=True, slots=True)
class Level:
    name: str
    chapter: str
    subtitle: str
    theme: str
    layout: tuple[str, ...]
    enemies: tuple[tuple[float, float, str], ...]
    phase_spawners: tuple[tuple[tuple[float, float], ...], ...]
    spawn_kinds: tuple[str, ...]
    spawn_weights: tuple[int, ...]
    pickups: tuple[tuple[float, float, str, int], ...]
    story: str
    phase_lines: tuple[str, str, str]
    columns: tuple[tuple[int, int], ...] = ()

    @property
    def forest(self):
        return self.theme == "atrium"

    @property
    def alchemist(self):
        return self.theme == "alchemy"

    @property
    def menagerie(self):
        return self.theme == "menagerie"

    @property
    def keeper(self):
        return self.theme == "keeper"

    @property
    def phase_counts(self):
        return (0, 0, 0) if self.keeper else (2, 3, 4) if self.menagerie else PHASE_COUNTS

    @property
    def spawners(self):
        return self.phase_spawners[0]


COLUMNS = ((5, 5), (11, 5), (5, 11), (11, 11))
FROSTFALL = Level(
    name="The Ground Floor",
    chapter="THE TOWER    /    THE THRESHOLD",
    subtitle="Four pillars bear the weight of twenty stories. Something stirs between them.",
    theme="stone",
    layout=room(COLUMNS),
    enemies=((7.5, 5.5, "husk"), (12.5, 7.5, "husk"), (10.5, 12.5, "skitter")),
    phase_spawners=(((4.5, 4.5), (12.5, 4.5)),
                    ((4.5, 8.5), (12.5, 8.5), (8.5, 12.5)),
                    ((8.5, 5.5), (6.5, 5.5), (10.5, 5.5))),
    spawn_kinds=("husk", "skitter"), spawn_weights=(65, 35),
    pickups=((7.5, 13.5, "food", 25), (12.5, 8.5, "food", 25),
             (8.5, 6.5, "gold", 25), (5.5, 9.5, "gold", 25)),
    story=("A nameless Frost Mage, trained at Drearamore's elemental college, has wandered to The Tower. "
           "Its ground floor is a hall of worn stone and four great load-bearing columns. "
           "She remembers the college motto, 'elementis fidelis est', as the first seals begin to split."),
    phase_lines=("Two ember rifts answer the wanderer's arrival.",
                 "Three seals crack behind the pillars. Their guardians move faster.",
                 "The Oathbound Warden and two animated shields guard the threshold. Dodge Winterbreaker; strike during recovery."),
    columns=COLUMNS,
)

THORNVEIL = Level(
    name="Thornveil Atrium",
    chapter="THE TOWER    /    A FOREST UNDER GLASS",
    subtitle="Thornveil grows beneath a glass vault, far from the sun it remembers.",
    theme="atrium",
    layout=(
        "#################", "#...............#", "#.......##......#",
        "#..##...##..#...#", "#..##.......#...#", "#...............#",
        "#...............#", "#.....##........#", "#.....##...##...#",
        "#..........##...#", "#..##...........#", "#..#............#",
        "#........#......#", "#........##.....#", "#...............#",
        "#...............#", "#################",
    ),
    enemies=((6.5, 5.5, "tree"), (10.5, 7.5, "tree"),
             (6.5, 12.5, "spider"), (13.5, 10.5, "spider"),
             (8.5, 11.5, "archer"), (12.5, 6.5, "archer")),
    phase_spawners=(((4.5, 5.5), (13.5, 4.5)),
                    ((5.5, 9.5), (13.5, 8.5), (12.5, 13.5)),
                    ((8.5, 5.5), (6.5, 5.5), (10.5, 5.5))),
    spawn_kinds=("tree", "spider", "archer"), spawn_weights=(45, 35, 20),
    pickups=((7.5, 13.5, "food", 25), (13.5, 8.5, "food", 25),
             (8.5, 6.5, "gold", 25), (5.5, 9.5, "gold", 25)),
    story=("The second floor opens into a vast indoor atrium. The old gardens of Thornveil have "
           "outgrown their stone planters beneath a vaulted glass roof. Dark magic walks in the trees, "
           "and a strange chemical glow seeps down from the floor above."),
    phase_lines=("Two Blighted Hearts beat beneath Thornveil's glass roof.",
                 "Three hearts tear roots through the planters. The dead draw their bows.",
                 "The Rootbound Heart awakens with two healing Thorn Tenders. Escape Briar Cage through its glowing gap."),
)

LAB_BENCHES = ((4, 4), (5, 4), (11, 4), (12, 4),
               (7, 7), (8, 7), (4, 10), (5, 10), (11, 10), (12, 10))
ALCHEMIST = Level(
    name="The Alchemist's Workshop",
    chapter="THE TOWER    /    A MOST UNFORTUNATE SPILL",
    subtitle="The wizard's helpers spilled the potions. The furniture has opinions now.",
    theme="alchemy",
    layout=room(LAB_BENCHES),
    enemies=((6.5, 5.5, "armor"), (12.5, 8.5, "armor"),
             (7.5, 12.5, "grimoire"), (10.5, 6.5, "grimoire"),
             (8.5, 10.5, "fairy"), (13.5, 5.5, "fairy")),
    phase_spawners=(((3.5, 4.5), (13.5, 4.5)),
                    ((3.5, 8.5), (13.5, 8.5), (8.5, 12.5)),
                    ((8.5, 5.5), (6.5, 5.5), (10.5, 5.5))),
    spawn_kinds=("armor", "grimoire", "fairy"), spawn_weights=(35, 35, 30),
    pickups=((7.5, 13.5, "food", 25), (13.5, 8.5, "food", 25),
             (8.5, 5.5, "gold", 25), (5.5, 8.5, "gold", 25)),
    story=("The wizard's little helper fairies have spilled a shelf of potions and lost their senses. "
           "Enchanted armor patrols without an owner, grimoires flap through the aisles, and the stills "
           "keep making things worse. A lesson from Drearamore returns: an element obeys only a steady hand."),
    phase_lines=("Two unstable alembics belch sparks. The fairies insist this is under control.",
                 "Three stills boil over. Loose enchantments race between the benches.",
                 "The Splintered Alchemist and two volatile duplicates prepare Chain Reaction. Lure duplicates into the potion pools."),
)

PENS = ((4, 4), (5, 4), (11, 4), (12, 4), (4, 10), (12, 10))
MENAGERIE = Level(
    name="The Menagerie", chapter="THE TOWER    /    CONTAINMENT FAILURE",
    subtitle="Broken pens. Fractured runes. The feeding schedule has gone terribly wrong.",
    theme="menagerie", layout=room(PENS),
    enemies=((8.5, 5.5, "crystal"), (12.5, 8.5, "predator"), (6.5, 9.5, "arcane")),
    phase_spawners=(((3.5, 5.5), (13.5, 5.5)),
                    ((3.5, 8.5), (13.5, 8.5), (8.5, 12.5)),
                    ((3.5, 3.5), (13.5, 3.5), (3.5, 11.5), (13.5, 11.5))),
    spawn_kinds=("crystal", "predator", "arcane"), spawn_weights=(30, 35, 35),
    pickups=((7.5, 13.5, "food", 30), (13.5, 8.5, "food", 30)),
    story=("The wizard's collection has escaped its enclosures. Crystal-backed beasts grind past broken "
           "containment runes, little predators stalk the feeding stations, and arcane drifters bob above "
           "the wreckage. From upstairs comes a weary voice: 'Unauthorized specimens must return to their "
           "enclosures.' Drearamore never mentioned a caretaker."),
    phase_lines=("Two containment devices malfunction. Watch the beasts' charge lanes; Ice Patch slows them.",
                 "Three devices fail. Predators crouch before pouncing; sidestep the drifters' slow bolts.",
                 "Four devices fracture. Recover your loot before meeting the furious caretaker upstairs."),
)

KEEPER = Level(
    name="The Keeper", chapter="THE TOWER    /    A VERY LONG SHIFT",
    subtitle="He maintains five floors. You have made a mess of every one of them.",
    theme="keeper", layout=room(((3, 3), (13, 3), (3, 11), (13, 11))),
    enemies=(), phase_spawners=(), spawn_kinds=(), spawn_weights=(),
    pickups=((2.5, 8.5, "food", 30), (14.5, 8.5, "food", 30)),
    story=("The Keeper is the lower tower's enchanted caretaker, burdened with keys, potion containers, "
           "tangled vines, and a broom bigger than the wanderer. He repairs the stonework, tends Thornveil, "
           "cleans the workshop, and retrieves escaped specimens. He is furious about the damage, not "
           "the ruler of The Tower. Beyond his station, fifteen more stories remain unexplored."),
    phase_lines=("Structural Repairs, Overgrowth, Deep Cleaning, and Escaped Specimens appear separately.",
                 "Below two-thirds health, the Keeper pairs compatible duties. Never more than two at once.",
                 "Below one-third health, combinations tighten. Frost briefly arrests him; resistance prevents freeze-lock."),
)

FLOORS = (FROSTFALL, THORNVEIL, ALCHEMIST, MENAGERIE, KEEPER)
PLAYABLE_FLOORS = len(FLOORS)


def level_for_depth(depth):
    if type(depth) is not int or not 1 <= depth <= PLAYABLE_FLOORS:
        raise ValueError(f"Playable floors are 1 through {PLAYABLE_FLOORS}.")
    return FLOORS[depth - 1]


def floor_name(depth):
    return level_for_depth(depth).name if 1 <= depth <= PLAYABLE_FLOORS else f"Unexplored Floor {depth}"
