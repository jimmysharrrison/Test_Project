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
    def void(self):
        return self.theme in ("void", "tentacles", "cosmic", "temporal", "maw")

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
           "the ruler of The Tower. His real duty has been holding back the void above. With his attention "
           "fixed on that barrier, the lower five floors have fallen into chaos without oversight. "
           "The Arcanist Wizard oversees the void experiments from floors eleven through fifteen."),
    phase_lines=("Structural Repairs, Overgrowth, Deep Cleaning, and Escaped Specimens appear separately.",
                 "Below two-thirds health, the Keeper pairs compatible duties. Never more than two at once.",
                 "Below one-third health, combinations tighten. Frost briefly arrests him; resistance prevents freeze-lock."),
)

BROKEN_CONTAINMENT = Level(
    name="Broken Containment", chapter="THE TOWER    /    THE FIRST BREACH",
    subtitle="The Keeper's barrier ends here. Above it, the bindings have failed.",
    theme="void", layout=room(((3, 4), (13, 4), (3, 10), (13, 10))),
    enemies=((7.5, 6.5, "voidling"), (12.5, 9.5, "voidling"), (11.5, 6.5, "binder")),
    phase_spawners=(((4.5, 5.5), (12.5, 5.5)),
                    ((4.5, 8.5), (12.5, 8.5), (8.5, 11.5)),
                    ((8.5, 5.5), (5.5, 5.5), (11.5, 5.5))),
    spawn_kinds=("voidling", "binder"), spawn_weights=(70, 30),
    pickups=((2.5, 8.5, "food", 30), (14.5, 8.5, "food", 30)),
    story=("Broken binding circles bear the seal of the Arcanist Wizard, master of floors eleven through "
           "fifteen and overseer of the void experiments. His researchers tried to subjugate a Voidwalker. "
           "It broke loose, and something larger is reaching through the damage. The Keeper on floor five "
           "was the only thing preventing the void from spreading downward; containing it left the lower "
           "floors without oversight. Surviving binders still attempt to reclaim their furious captive."),
    phase_lines=("Break two binding circles. Leave gold warnings; pillar discharges can hit escaped creatures too.",
                 "Three more circles fracture. Freeze binders to interrupt their dark rituals; active pools expire.",
                 "The Unbound Voidwalker hunts mage and binder alike. Sidestep Rift Lunge, escape Rending Sweep, and punish recovery."),
)

CONSUMING_DARK = Level(
    name="The Consuming Dark", chapter="THE TOWER    /    A WILL THAT IS NOT YOUR OWN",
    subtitle="The researchers still speak. Something behind their eyes supplies the words.",
    theme="tentacles", layout=room(((3, 4), (13, 4), (3, 11), (13, 11))),
    enemies=((7.5, 6.5, "lasher"), (11.5, 8.5, "grasper"), (11.5, 5.5, "thrall")),
    phase_spawners=(((4.5, 5.5), (12.5, 5.5)),
                    ((4.5, 8.5), (12.5, 8.5), (8.5, 12.5)),
                    ((8.5, 5.5), (5.5, 5.5), (11.5, 5.5))),
    spawn_kinds=("lasher", "grasper", "thrall", "anchor"), spawn_weights=(25, 20, 40, 15),
    pickups=((2.5, 8.5, "food", 35), (14.5, 8.5, "food", 35)),
    story=("Above the broken containment room, tentacles have threaded the Arcanist's research halls. "
           "The wizards he left here are enthralled by the Many-Eyed Oracle. Lashers block lanes, "
           "graspers seize intruders, and anchor tentacles draw them into darkness. The Keeper kept "
           "this influence from reaching the lower tower. Now the voice calls upward, toward the observatory."),
    phase_lines=("Break two enthrallment seals. Sidestep lash lanes; attack or freeze a grasping limb to escape.",
                 "Three seals feed the Oracle. Destroy anchor tentacles to stop their pull into darkness.",
                 "The Many-Eyed Oracle commands its thralls. Break or freeze channelers to expose it; dodge the sweeping gaze."),
)

FALLEN_OBSERVATORY = Level(
    name="The Fallen Observatory", chapter="THE TOWER    /    STARS THAT SHOULD NOT MOVE",
    subtitle="The sky bends around an unseen weight. The observatory bends with it.",
    theme="cosmic", layout=room(((4, 3), (12, 3), (4, 12), (12, 12))),
    enemies=((8.5, 6.5, "gravity_adept"), (12.5, 9.5, "repulsor"), (6.5, 8.5, "star_fragment")),
    phase_spawners=(((3.5, 5.5), (13.5, 5.5)),
                    ((3.5, 9.5), (13.5, 9.5), (8.5, 12.5)),
                    ((8.5, 5.5), (5.5, 5.5), (11.5, 5.5))),
    spawn_kinds=("gravity_adept", "repulsor", "star_fragment"), spawn_weights=(40, 25, 35),
    pickups=((2.5, 8.5, "food", 35), (14.5, 8.5, "food", 35)),
    story=("The Arcanist's astronomer believed the approaching presence was a celestial revelation. "
           "His instrument shattered as the breach bent the sky. Now he hangs inside its broken rings, "
           "drawing stars and stone into impossible orbits. The gravity is strongest near him, but "
           "the fractures in the ceiling hint at something stranger still above."),
    phase_lines=("Break two celestial foci. Move away from attraction wells; repulsors warn before pushing.",
                 "Three foci fracture. Watch the fragments' circular paths and the arrows marking gravity.",
                 "The Fallen Astronomer alternates pull and push. Reposition during the warning; avoid orbiting ruin and collapsing stars."),
)

FRACTURED_HOUR = Level(
    name="The Fractured Hour", chapter="THE TOWER    /    A MOMENT WITHOUT AN END",
    subtitle="The wardens remember a disaster that has not finished happening.",
    theme="temporal", layout=room(((3, 3), (13, 3), (3, 11), (13, 11))),
    enemies=((7.5, 6.5, "rift_warden"), (12.5, 8.5, "rift_warden"), (9.5, 5.5, "chronal_scholar")),
    phase_spawners=(((4.5, 5.5), (12.5, 5.5)),
                    ((4.5, 8.5), (12.5, 8.5), (8.5, 11.5)),
                    ((8.5, 5.5), (5.5, 5.5), (11.5, 5.5))),
    spawn_kinds=("rift_warden", "chronal_scholar"), spawn_weights=(70, 30),
    pickups=((2.5, 8.5, "food", 35), (14.5, 8.5, "food", 35)),
    story=("Elven wardens tried to close the Arcanist's breach and became trapped in its repeating hours. "
           "Their portals reveal an exit before they arrive; pale echoes repeat a shot once, and stasis "
           "circles briefly hold projectiles. Beyond the seals, a surviving warden teaches Glacial Prison: "
           "when time stops, ice anchors the mage against the Hourless Breach. Three anchors must fall, "
           "and three Stopped Hours must be survived. Failed attempts return to the nearby checkpoint."),
    phase_lines=("Break two chronal rifts. Portals warn before wardens arrive; echoes repeat their locked shot once.",
                 "Three rifts fracture. Projectiles pause inside stasis circles, then resume. Watch the release countdown.",
                 "Learn the ice anchor safely, then break three dimensional anchors. When time stops, use R immediately."),
)

MAW_BETWEEN_WORLDS = Level(
    name="The Maw Between Worlds", chapter="THE TOWER    /    WHAT THE ARCANIST OPENED",
    subtitle="Only half the creature has crossed the floor. The rest presses against another world.",
    theme="maw", layout=room(((3, 3), (13, 3), (3, 12), (13, 12))),
    enemies=((6.5, 7.5, "voidling"), (11.5, 8.5, "lasher"), (9.5, 5.5, "rift_warden")),
    phase_spawners=(((4.5, 5.5), (12.5, 5.5)),
                    ((4.5, 9.5), (12.5, 9.5), (8.5, 12.5)),
                    ((8.5, 5.5), (5.5, 5.5), (11.5, 5.5))),
    spawn_kinds=("voidling", "binder", "lasher", "thrall", "gravity_adept", "rift_warden", "chronal_scholar"),
    spawn_weights=(25, 10, 15, 15, 10, 15, 10),
    pickups=((2.5, 8.5, "food", 40), (14.5, 8.5, "food", 40)),
    story=("The Hourless Breach was only a seam in the prison. Above it, a colossal tentacled presence "
           "has forced its head and shoulders through the floor. Its lower body remains in another "
           "dimension. The Threshold Devourer cannot move, but draws intruders into its maw and calls "
           "the escaped creatures, enthralled researchers, gravity servants and elven wardens of the "
           "previous floors. This is the source the Keeper held back. Beyond it rise the Arcanist's "
           "five floors, where the wizard who oversaw the experiments still waits."),
    phase_lines=("Break two breach seals. The void creatures and displaced elves now fight together.",
                 "Three seals remain. Interrupt casters and watch stasis releases before approaching the rupture.",
                 "The Threshold Devourer is fixed in the floor. Flee the warned gravity draw, dodge its tentacles, and control its summons."),
)

FLOORS = (FROSTFALL, THORNVEIL, ALCHEMIST, MENAGERIE, KEEPER, BROKEN_CONTAINMENT,
          CONSUMING_DARK, FALLEN_OBSERVATORY, FRACTURED_HOUR, MAW_BETWEEN_WORLDS)
PLAYABLE_FLOORS = len(FLOORS)


def level_for_depth(depth):
    if type(depth) is not int or not 1 <= depth <= PLAYABLE_FLOORS:
        raise ValueError(f"Playable floors are 1 through {PLAYABLE_FLOORS}.")
    return FLOORS[depth - 1]


def floor_name(depth):
    return level_for_depth(depth).name if 1 <= depth <= PLAYABLE_FLOORS else f"Unexplored Floor {depth}"
