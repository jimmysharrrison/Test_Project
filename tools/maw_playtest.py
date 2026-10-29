"""Headless full-floor spell/movement clears of the final void encounter.

No direct damage, invulnerability, reserved charges or R casts. The bot reads
warning geometry, so this verifies completion and resource flow, not human skill.
"""
import json
from math import cos, sin, pi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dungeon.geometry import Vec
from dungeon.maw import BOSS_POS
from dungeon.void_depths import FORCES
from dungeon.world import World
from void_depths_playtest import danger as depth_danger
from temporal_playtest import danger as temporal_danger


def danger(w, point):
    return depth_danger(w, point) + temporal_danger(w, point)


def order(w):
    p, f = w.player, w.void
    if w.level_completed:
        w.request_move(w.exit, marker=False)
        return
    if p.hp < p.max_hp * .6 and p.potions:
        w.use_potion()
    if f.rooted:
        targets = [f.root_owner]
        w.cast("w", feedback=False)
    elif w.spawners:
        targets = w.spawners
    else:
        adds = [e for e in w.enemies if e is not f.boss]
        close = [e for e in adds if (e.pos - p.pos).length() < 3.5]
        targets = close or adds if len(adds) >= 2 or close else [f.boss] if f.boss else []
    target = min(targets, key=lambda e: (e.pos - p.pos).length(), default=None)
    if sum((e.pos - p.pos).length() < 2.6 for e in w.enemies) >= 2:
        w.cast("w", feedback=False)
    if target and p.mana > 55:
        w.cast("e", p.pos, feedback=False)
    if target and (target.pos - p.pos).length() < 8 and w._line_clear(p.pos, target.pos):
        w.cast("q", target.pos, feedback=False)
    if w.time % .15 >= 1 / 60:
        return
    if danger(w, p.pos) > 1:
        choices = [p.pos + Vec(cos(i * pi / 8), sin(i * pi / 8)) * d
                   for d in (1.5, 3) for i in range(16)]
        clear = [v for v in choices if w.walkable(v, .3) and w._line_clear(p.pos, v)]
        if clear:
            w.request_move(min(clear, key=lambda v: danger(w, v) +
                               ((v - target.pos).length() * .1 if target else 0)), marker=False)
    elif target and ((target.pos - p.pos).length() > 5.5 or not w._line_clear(p.pos, target.pos)):
        w.request_move(target.pos, marker=False)


def run(seed, loadout):
    w = World(seed, level=10, completion_delay_ms=0)
    inv = w.player.inventory
    for slot in ("helm", "chest", "legs", "gloves", "boots"):
        template = "frostweave:" + slot if loadout == "frostweave" or slot == "helm" else "standard:" + slot
        item = inv.create_template(template, 3 if template.startswith("frostweave:") else 2, w.loot_rng, "shop")
        inv.add(item)
        inv.equip(item.uid)
    w.player.hp = w.player.max_hp
    w.player.frostweave_unlocked = True
    patterns, arrivals, damage = set(), set(), []
    peak = minions = warnings = forces = fields = echoes = 0
    fixed = True

    class Recorder:
        def event(self, current, event, **data):
            if event == "maw_pattern":
                patterns.add(data["attack"])
            elif event == "maw_summon_arrival":
                arrivals.add(data["kind"])
            elif event == "player_damage":
                damage.append(data)
        def tick(self, current, dt):
            pass

    w.telemetry = Recorder()
    for _ in range(300 * 60):
        order(w)
        w.update(1 / 60)
        peak = max(peak, len(w.enemies))
        minions = max(minions, sum(e.summoned for e in w.enemies))
        warnings = max(warnings, len(w.void.arrivals))
        forces = max(forces, sum(m.kind in FORCES for m in w.void.mechanics))
        fields = max(fields, len(w.void.fields))
        echoes = max(echoes, len(w.void.echoes))
        if w.void.boss:
            fixed = fixed and w.void.boss.pos == BOSS_POS
        if w.state in ("dead", "won", "cleared"):
            break
    return dict(level=10, seed=seed, loadout=loadout, state=w.state, seconds=round(w.time, 2),
                hp=round(w.player.hp, 2), potions=w.player.potions, phase=w.phase,
                boss_hp=w.void.boss.hp if w.void.boss else None, boss_always_fixed=fixed,
                peak_enemies=peak, peak_minions=minions, peak_arrivals=warnings, peak_forces=forces,
                peak_fields=fields, peak_echoes=echoes, damage_events=len(damage),
                patterns=sorted(patterns), summoned_kinds=sorted(arrivals), used_glacial_prison=False)


if __name__ == "__main__":
    results = [run(seed, loadout) for loadout in ("keeper_reward", "frostweave") for seed in (3, 7, 19)]
    Path("docs/maw-playtest.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    raise SystemExit(any(r["state"] != "won" or not r["boss_always_fixed"] for r in results))
