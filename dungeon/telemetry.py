"""Local-only gameplay journals and uploadable session bundles. No network I/O."""
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import traceback
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

from .abilities import (ABILITIES, ICE_PATCH_RADIUS, ICE_PATCH_MOVE_FACTOR,
                        ICE_PATCH_ATTACK_FACTOR, ICE_PATCH_FROST_BONUS)
from .keeper import TUNING
from .levels import PHASE_SPEEDS

ROOT = Path(__file__).resolve().parents[1]


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def equipment(player):
    return {slot: {"name": item.name, "rank": item.rank, "set": item.set_id, "template_id": item.catalog_id, "quality": item.quality, "enchantment_value": item.enchantment_value} if item else None
            for slot in player.inventory.equipped
            for item in [player.inventory.worn(slot)]}


def player_state(world):
    p = world.player
    return {"hp": p.hp, "max_hp": p.max_hp, "mana": round(p.mana, 2), "potions": p.potions,
            "gold": p.gold, "kills": p.kills, "gear": equipment(p), "stats": asdict(p.inventory.stats)}


class RunRecorder:
    """One session may contain multiple floor attempts and explicit replays.

    Creation is lazy: browsing the title does not create a gameplay session.
    Writer failures disable logging with a notice, without breaking the game.
    """
    def __init__(self, directory=None, enabled=True, headless=False):
        self.directory = Path(directory) if directory else ROOT / "logs"
        self.enabled, self.headless = enabled, headless
        self.session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        self.folder = self.directory / ("frost-mage-" + self.session_id)
        self.archive = self.folder.with_suffix(".zip")
        self.notice = ""
        self.stream = None
        self.closed = False
        self.active = None
        self.world = None
        self.attempts = []
        self.sequence = 0
        self.next_sample = 0
        self.next_checkpoint = 5
        self.last_gear = None
        self.frame_counts = Counter()
        self.wall_seconds = Counter()
        self.slow_frames = 0
        self.report = {"schema_version": 1, "session_id": self.session_id, "started_utc": None,
                       "ended_utc": None, "complete": False,
                       "input_mode": "headless" if headless else "interactive",
                       "attempts": self.attempts,
                       "notes": ["Simulation seconds exclude paused/menu time.",
                                 "Damage uses effective HP lost, excluding overkill.",
                                 "Unresolved spells are not counted as misses.",
                                 "Previously cleared rooms are not new victories."]}

    def attach(self, world, reason="continue"):
        world.telemetry = self if self.enabled else None
        world.telemetry_reason = reason

    def _open(self):
        if self.stream or not self.enabled or self.closed:
            return
        self.folder.mkdir(parents=True, exist_ok=False)
        self.stream = (self.folder / "events.jsonl").open("x", encoding="utf-8")
        sources = ("world.py", "abilities.py", "levels.py", "items.py", "keeper.py", "creatures.py", "encounters.py")
        digest = sha256()
        for name in sources:
            digest.update(name.encode())
            digest.update((ROOT / "dungeon" / name).read_bytes())
        from .world import ENEMY_STATS
        from .items import DEFINITIONS
        self.report.update(started_utc=utc_now(), build_fingerprint=digest.hexdigest()[:16],
                           tuning={"spells": {key: asdict(value) for key, value in ABILITIES.items()},
                                   "keeper": asdict(TUNING), "enemy_stats": ENEMY_STATS,
                                   "item_definitions": {key: asdict(value) for key, value in DEFINITIONS.items()},
                                   "phase_speeds": PHASE_SPEEDS,
                                   "ice_patch": {"radius": ICE_PATCH_RADIUS, "move_factor": ICE_PATCH_MOVE_FACTOR,
                                                 "attack_rate": ICE_PATCH_ATTACK_FACTOR, "frost_bonus": ICE_PATCH_FROST_BONUS}})
        self._write("session_start", input_mode=self.report["input_mode"], build=self.report["build_fingerprint"])
        print(f"Local playthrough logging: {self.folder}")

    def _write(self, event, **data):
        self.sequence += 1
        row = {"sequence": self.sequence, "utc": utc_now(), "event": event, **data}
        self.stream.write(json.dumps(row, ensure_ascii=True, allow_nan=False) + "\n")
        self.stream.flush()

    def _disable(self):
        self.enabled = False
        self.notice = "Playthrough logging unavailable. Check write access to the logs folder."
        if self.stream:
            try:
                self.stream.close()
            except OSError:
                pass
            self.stream = None

    def _ensure(self, world):
        self._open()
        if self.active and self.world is world and self.active["floor"] == world.level:
            return
        self.world = world
        state = player_state(world)
        self.active = {"attempt_id": len(self.attempts) + 1, "floor": world.level,
                       "floor_name": world.level_data.name, "seed": world.seed,
                       "start_reason": world.telemetry_reason, "restored_cleared": world.level_completed,
                       "outcome": "in_progress", "simulation_seconds": 0.0, "combat_seconds": 0.0,
                       "phase_seconds": {}, "damage_taken": 0, "damage_dealt": 0, "boss_damage": 0,
                       "incoming_hits": 0, "critical_hits": 0, "kills": 0, "spawners_destroyed": 0,
                       "gold_earned": 0, "gold_spent": 0, "environmental_damage": 0,
                       "damage_sources": {}, "spells": {}, "healing": {}, "boss_attacks": {},
                       "low_health_seconds": 0.0, "low_mana_seconds": 0.0,
                       "ice_patch_seconds": 0.0, "stasis_seconds": 0.0,
                       "minimum_hp_fraction": state["hp"] / max(1, state["max_hp"]),
                       "peak_enemies": len(world.enemies), "start": state, "end": state}
        self.attempts.append(self.active)
        self.next_sample, self.next_checkpoint = 0, 5
        self.last_gear = equipment(world.player)
        self._write("floor_start", attempt_id=self.active["attempt_id"], floor=world.level,
                    phase=world.phase, simulation_time=round(world.time, 4), reason=world.telemetry_reason,
                    restored_cleared=world.level_completed, player=state,
                    enemies=[world._actor_info(e) for e in world.enemies],
                    spawners=[world._actor_info(s) for s in world.spawners])
        self._checkpoint()

    def event(self, world, event, **data):
        if not self.enabled or self.closed:
            return
        try:
            self._ensure(world)
            self._write(event, attempt_id=self.active["attempt_id"], floor=world.level, phase=world.phase,
                        simulation_time=round(world.time, 4), **data)
            self._aggregate(event, data)
            self._minimum_hp(world)
            if event in ("floor_cleared", "player_died"):
                self.active["outcome"] = "cleared" if event == "floor_cleared" else "died"
                self.active["end"] = player_state(world)
                self._checkpoint()
        except Exception:
            self._disable()

    def _aggregate(self, event, data):
        a = self.active
        if event == "player_damage":
            a["damage_taken"] += data["effective_damage"]
            a["incoming_hits"] += 1
            key = data["source"] + " / " + data["attack"]
            source = a["damage_sources"].setdefault(key, {"hits": 0, "damage": 0, "largest_hit": 0})
            source["hits"] += 1
            source["damage"] += data["effective_damage"]
            source["largest_hit"] = max(source["largest_hit"], data["effective_damage"])
        elif event == "target_damage":
            if data["spell"] == "environment":
                a["environmental_damage"] += data["effective_damage"]
                return
            a["damage_dealt"] += data["effective_damage"]
            a["critical_hits"] += int(data["critical"])
            if data["target"]["role"] in ("boss", "keeper"):
                a["boss_damage"] += data["effective_damage"]
            if data["spell"] in a["spells"]:
                a["spells"][data["spell"]]["damage"] += data["effective_damage"]
        elif event == "spell_cast":
            spell = a["spells"].setdefault(data["spell"], {"casts": 0, "resolved": 0, "casts_hitting_targets": 0,
                                                        "targets_hit": 0, "damage": 0, "boosted_casts": 0})
            spell["casts"] += 1
            spell["boosted_casts"] += int(data["frost_multiplier"] > 1)
        elif event == "spell_resolved" and data["spell"] in a["spells"]:
            spell = a["spells"][data["spell"]]
            spell["resolved"] += 1
            spell["casts_hitting_targets"] += int(data["targets_hit"] > 0)
            spell["targets_hit"] += data["targets_hit"]
        elif event == "healing":
            heal = a["healing"].setdefault(data["source"], {"uses": 0, "hp_restored": 0})
            heal["uses"] += 1
            heal["hp_restored"] += data["hp_restored"]
        elif event == "enemy_defeated":
            a["kills"] += 1
        elif event == "spawner_destroyed":
            a["spawners_destroyed"] += 1
        elif event == "boss_attack":
            a["boss_attacks"][data["attack"]] = a["boss_attacks"].get(data["attack"], 0) + 1
        elif event == "gold_change":
            a["gold_earned" if data["amount"] > 0 else "gold_spent"] += abs(data["amount"])

    def _minimum_hp(self, world):
        self.active["minimum_hp_fraction"] = min(self.active["minimum_hp_fraction"],
                                                   world.player.hp / max(1, world.player.max_hp))

    def tick(self, world, dt):
        if not self.enabled or self.closed:
            return
        try:
            self._ensure(world)
            a = self.active
            a["simulation_seconds"] += dt
            if not world.level_completed:
                a["combat_seconds"] += dt
                phase = str(world.phase)
                a["phase_seconds"][phase] = a["phase_seconds"].get(phase, 0) + dt
                a["low_health_seconds"] += dt * (world.player.hp / max(1, world.player.max_hp) <= .35)
                a["low_mana_seconds"] += dt * (world.player.mana < ABILITIES["w"].mana)
                a["ice_patch_seconds"] += dt * (world.frost_multiplier > 1)
                a["stasis_seconds"] += dt * (world.player.stasis > 0)
            self._minimum_hp(world)
            a["peak_enemies"] = max(a["peak_enemies"], len(world.enemies))
            gear = equipment(world.player)
            if gear != self.last_gear:
                self.event(world, "equipment_changed", gear=gear, stats=asdict(world.player.inventory.stats))
                self.last_gear = gear
            if world.time >= self.next_sample:
                self.next_sample = world.time + 1
                boss = next((e for e in world.enemies if e.boss_role in ("boss", "keeper")), None)
                self.event(world, "sample", hp=world.player.hp, max_hp=world.player.max_hp,
                           mana=round(world.player.mana, 2), position=world._point(world.player.pos),
                           enemies=len(world.enemies), spawners=len(world.spawners),
                           ice_patch=world.frost_multiplier > 1,
                           boss_hp=boss.hp if boss else None,
                           keeper_duties=sorted(world.keeper.active_kinds) if world.keeper else [])
            if world.time >= self.next_checkpoint:
                self.next_checkpoint = world.time + 5
                a["end"] = player_state(world)
                self._checkpoint()
        except Exception:
            self._disable()

    def frame(self, elapsed, mode):
        if self.stream and not self.closed:
            self.frame_counts[mode] += 1
            self.wall_seconds[mode] += elapsed
            self.slow_frames += int(mode == "playing" and elapsed > 1 / 30)

    def end_attempt(self, world, reason="quit"):
        if not self.active or self.world is not world or not self.enabled:
            return
        try:
            a = self.active
            if a["restored_cleared"]:
                a["outcome"] = "previously_cleared"
            elif a["outcome"] == "in_progress":
                a["outcome"] = "crashed" if reason == "crashed" else "abandoned" if reason != "quit" else "quit"
            a["end_reason"] = reason
            a["end"] = player_state(world)
            a["effective_dps_including_travel"] = round(a["damage_dealt"] / max(.001, a["combat_seconds"]), 2)
            for spell in a["spells"].values():
                spell["unresolved_casts"] = max(0, spell["casts"] - spell["resolved"])
            self._write("floor_end", attempt_id=a["attempt_id"], floor=world.level,
                        simulation_time=round(world.time, 4), outcome=a["outcome"], reason=reason, player=a["end"])
            self.active = None
            self._checkpoint()
        except Exception:
            self._disable()

    def _checkpoint(self):
        self.report["performance"] = {"wall_seconds_by_mode": dict(self.wall_seconds),
                                      "frames_by_mode": dict(self.frame_counts), "playing_frames_over_33ms": self.slow_frames}
        temporary = self.folder / "summary.tmp"
        temporary.write_text(json.dumps(self.report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(self.folder / "summary.json")

    def crash(self, world, error):
        try:
            stack = [{"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
                     for f in traceback.extract_tb(error.__traceback__)]
            message = str(error)
            for path, replacement in ((ROOT, "<project>"), (Path.home(), "<home>")):
                message = message.replace(str(path), replacement).replace(path.as_posix(), replacement)
            self.event(world, "crash", error_type=type(error).__name__, message=message, stack=stack)
            self.report["crash"] = {"type": type(error).__name__, "message": message, "stack": stack}
        except Exception:
            self._disable()

    def close(self, world, crashed=False):
        if self.closed:
            return
        if not self.stream:
            self.closed = True
            return
        try:
            self.end_attempt(world, "crashed" if crashed else "quit")
            if not self.stream:
                return
            self.report.update(ended_utc=utc_now(), complete=True, ended_by="crash" if crashed else "quit")
            self._write("session_end", ended_by=self.report["ended_by"])
            self._checkpoint()
            lines = ["FROST MAGE PLAYTHROUGH", f"Session: {self.session_id}",
                     f"Mode: {self.report['input_mode']} | Ended by: {self.report['ended_by']}",
                     "Combat time excludes menus and pauses. Damage excludes overkill.", ""]
            for a in self.attempts:
                lines += [f"Attempt {a['attempt_id']} | Floor {a['floor']} {a['floor_name']} | {a['outcome']}",
                          f"  Combat: {a['combat_seconds']:.1f}s | Incoming damage: {a['damage_taken']} in {a['incoming_hits']} hits",
                          f"  Minimum health: {a['minimum_hp_fraction']:.0%} | Low-health time: {a['low_health_seconds']:.1f}s",
                          f"  Damage dealt: {a['damage_dealt']} | Boss damage: {a['boss_damage']} | Peak enemies: {a['peak_enemies']}",
                          f"  Healing: {json.dumps(a['healing'])}", f"  Spells: {json.dumps(a['spells'])}",
                          f"  Damage sources: {json.dumps(a['damage_sources'])}", ""]
            (self.folder / "summary.txt").write_text("\n".join(lines), encoding="utf-8")
            self.stream.close()
            self.stream = None
            with ZipFile(self.archive, "x", compression=ZIP_DEFLATED) as bundle:
                for name in ("events.jsonl", "summary.json", "summary.txt"):
                    bundle.write(self.folder / name, arcname=name)
            print(f"Playthrough log saved. Upload this file: {self.archive}")
        except Exception:
            self.notice = "Playthrough archive could not be completed; existing raw logs are kept."
        finally:
            if self.stream:
                try:
                    self.stream.close()
                except OSError:
                    pass
                self.stream = None
            self.closed = True
