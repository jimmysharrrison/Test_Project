"""Reproducible mana rotation and encounter comparisons; no profile writes."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dungeon.abilities import ABILITIES
from dungeon.world import World
from dungeon.items import SLOTS
from lower_tower_playtest import order


def setup(rate, rank, level=1):
    w = World(7, level=level, mana_regen=rate)
    if rank:
        for slot in SLOTS:
            item = w.player.inventory.create(slot, rank, 'shop')
            w.player.inventory.add(item)
            w.player.inventory.equip(item.uid)
    w.player.hp = w.player.max_hp
    return w


def rotation(rate, rank, keys):
    w = setup(rate, rank)
    w.enemies.clear()
    for s in w.spawners:
        s.timer = 10000
    first_denial = None
    counts = dict.fromkeys(keys, 0)
    for frame in range(180 * 120):
        p = w.player
        for key in keys:
            if p.cooldowns[key] <= 1e-8 and p.cast_time <= 1e-8 and p.stasis <= 1e-8:
                if p.mana + 1e-8 < ABILITIES[key].mana:
                    if first_denial is None:
                        first_denial = round(w.time, 3)
                elif w.cast(key, p.pos, feedback=False):
                    counts[key] += 1
        w.update(1 / 120)
    return dict(first_mana_denial=first_denial, casts=counts, mana=round(p.mana, 2))


def encounter(rate, rank, level):
    w = setup(rate, rank, level)
    minimum = 100
    for frame in range(240 * 60):
        order(w)
        w.update(1 / 60)
        minimum = min(minimum, w.player.mana)
        if w.state == 'dead' or w.exit_open:
            break
    return dict(floor=level, cleared=w.exit_open, state=w.state, seconds=round(w.time, 2), hp=w.player.hp, minimum_mana=round(minimum, 2))


def main():
    report = []
    for rank in (0, 5):
        for rate in (8, 6):
            report.append(dict(rank=rank, regen=rate,
                rotations={keys: rotation(rate, rank, keys) for keys in ('w', 'we', 'wer')},
                encounters=[encounter(rate, rank, level) for level in (1, 5)]))
    path = Path('docs/mana-measurements.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(path.read_text())

if __name__ == '__main__':
    main()
