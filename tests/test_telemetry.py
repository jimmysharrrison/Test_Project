"""Local logging must be useful for balance analysis and never alter combat."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from dungeon.geometry import Vec
from dungeon.telemetry import RunRecorder
from dungeon.world import IcePatch, Player, World


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def quiet_world():
    world = World(7)
    world.enemies.clear()
    world.pickups.clear()
    for spawner in world.spawners:
        spawner.timer = 999
    world.combat_rng.random = lambda: 1
    return world


def read_bundle(recorder):
    with ZipFile(recorder.archive) as bundle:
        summary = json.loads(bundle.read("summary.json"))
        rows = [json.loads(line) for line in bundle.read("events.jsonl").decode().splitlines()]
        return summary, rows, bundle.namelist()


class TelemetryTests(unittest.TestCase):
    def test_menu_only_and_disabled_logging_create_no_files(self):
        with TemporaryDirectory() as folder:
            for enabled in (True, False):
                world = quiet_world()
                recorder = RunRecorder(folder, enabled=enabled)
                recorder.attach(world)
                recorder.frame(10, "title")
                recorder.close(world)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_bundle_has_flushed_events_tuning_build_and_readable_summary(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            recorder = RunRecorder(folder)
            recorder.attach(world, "new_game")
            world.update(1 / 60)
            self.assertTrue(world.cast("q", Vec(8.5, 13.5)))
            rows = [json.loads(line) for line in (recorder.folder / "events.jsonl").read_text().splitlines()]
            self.assertEqual(rows[-1]["event"], "spell_cast")
            self.assertFalse(json.loads((recorder.folder / "summary.json").read_text())["complete"])
            recorder.close(world)
            summary, rows, names = read_bundle(recorder)
            self.assertEqual(set(names), {"events.jsonl", "summary.json", "summary.txt"})
            self.assertTrue(summary["complete"])
            self.assertEqual(summary["input_mode"], "interactive")
            self.assertEqual(summary["tuning"]["spells"]["e"]["name"], "Ice Patch")
            self.assertEqual(len(summary["build_fingerprint"]), 16)
            self.assertEqual([r["sequence"] for r in rows], list(range(1, len(rows) + 1)))

    def test_effective_damage_excludes_overkill_and_healing_counts_actual_hp(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            enemy = world.make_enemy(world.player.pos + Vec(2, 0), "armor", frozen=10)
            enemy.hp = 5
            recorder = RunRecorder(folder)
            recorder.attach(world)
            world.cast("q", enemy.pos)
            advance(world, .4)
            world._hurt_player(20, source="keeper", attack="Structural Repairs")
            world._hurt_player(20, source="keeper", attack="Structural Repairs")  # Hit immunity.
            world.use_potion()
            recorder.close(world)
            summary, rows, _ = read_bundle(recorder)
            attempt = summary["attempts"][0]
            self.assertEqual(attempt["damage_dealt"], 5)
            self.assertEqual(attempt["damage_taken"], 20)
            self.assertEqual(attempt["incoming_hits"], 1)
            self.assertEqual(attempt["healing"]["potion"], {"uses": 1, "hp_restored": 20})
            self.assertEqual(attempt["damage_sources"]["keeper / Structural Repairs"]["damage"], 20)
            self.assertEqual(attempt["spells"]["q"]["targets_hit"], 1)
            self.assertEqual(attempt["spells"]["q"]["damage"], 5)

    def test_bolt_misses_resolve_once_for_terrain_and_expiry(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            recorder = RunRecorder(folder)
            recorder.attach(world)
            world.player.pos = Vec(1.5, 13.5)
            world.cast("q", Vec(0, 13.5))
            advance(world, .4)
            world.cast("q", Vec(12.5, 13.5))
            advance(world, 1.2)
            recorder.close(world)
            summary, rows, _ = read_bundle(recorder)
            resolved = [r for r in rows if r["event"] == "spell_resolved"]
            self.assertEqual([r["reason"] for r in resolved], ["terrain", "expired"])
            self.assertEqual(summary["attempts"][0]["spells"]["q"]["resolved"], 2)
            self.assertEqual(summary["attempts"][0]["spells"]["q"]["casts_hitting_targets"], 0)

    def test_ice_patch_placement_resolves_and_interrupted_prison_is_unresolved(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            recorder = RunRecorder(folder)
            recorder.attach(world)
            world.cast("e", world.player.pos)
            advance(world, .2)
            world.cast("r")
            recorder.close(world)
            summary, rows, _ = read_bundle(recorder)
            spells = summary["attempts"][0]["spells"]
            self.assertEqual(spells["e"]["unresolved_casts"], 0)
            self.assertEqual(spells["r"]["unresolved_casts"], 1)
            self.assertEqual(spells["r"]["boosted_casts"], 1)

    def test_floor_transition_preserves_recorder_and_separates_attempts(self):
        with TemporaryDirectory() as folder:
            world = World(7, level=4)
            world.enemies.clear()
            recorder = RunRecorder(folder)
            recorder.attach(world, "level_select")
            world.update(1 / 60)
            for phase in range(1, 4):
                for spawner in world.spawners[:]:
                    world._hit(spawner, 10000)
                if phase < 3:
                    advance(world, 3.05)
            world.player.pos = world.exit
            world.update(1 / 60)
            self.assertTrue(world.next_level())
            self.assertIs(world.telemetry, recorder)
            world.update(1 / 60)
            recorder.close(world)
            summary, rows, _ = read_bundle(recorder)
            self.assertEqual([a["floor"] for a in summary["attempts"]], [4, 5])
            self.assertEqual([a["outcome"] for a in summary["attempts"]], ["cleared", "quit"])
            self.assertEqual(summary["attempts"][0]["spawners_destroyed"], 9)
            self.assertEqual(len([r for r in rows if r["event"] == "floor_start"]), 2)

    def test_death_retry_and_restored_clear_are_distinct_outcomes(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            recorder = RunRecorder(folder)
            recorder.attach(world)
            world._hurt_player(1000, source="crystal", attack="charge")
            recorder.end_attempt(world, "retry")
            retry = quiet_world()
            recorder.attach(retry, "retry")
            retry.update(1 / 60)
            recorder.end_attempt(retry, "level_select")
            restored = World(7, player=Player(current_level=5, unlocked_level=5,
                                             cleared_floor=5, lower_tower_completed=True), level=5)
            recorder.attach(restored, "continue")
            restored.update(1 / 60)
            recorder.close(restored)
            summary, _, _ = read_bundle(recorder)
            self.assertEqual([a["outcome"] for a in summary["attempts"]],
                             ["died", "abandoned", "previously_cleared"])
            self.assertEqual(summary["attempts"][-1]["combat_seconds"], 0)

    def test_pause_does_not_inflate_combat_and_patch_uptime(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            world.player.hp = 20
            world.ice_patches.append(IcePatch(world.player.pos, life=.5))
            recorder = RunRecorder(folder, headless=True)
            recorder.attach(world)
            advance(world, 1)
            recorder.frame(10, "paused")
            recorder.close(world)
            summary, _, _ = read_bundle(recorder)
            attempt = summary["attempts"][0]
            self.assertAlmostEqual(attempt["combat_seconds"], 1)
            self.assertAlmostEqual(attempt["low_health_seconds"], 1)
            self.assertAlmostEqual(attempt["ice_patch_seconds"], .5)
            self.assertEqual(summary["performance"]["wall_seconds_by_mode"]["paused"], 10)
            self.assertEqual(summary["input_mode"], "headless")

    def test_unwritable_destination_and_writer_bug_do_not_break_gameplay(self):
        with TemporaryDirectory() as folder:
            blocked = Path(folder) / "file"
            blocked.write_text("occupied")
            for root in (blocked, Path(folder) / "other"):
                world = quiet_world()
                recorder = RunRecorder(root)
                recorder.attach(world)
                with patch.object(recorder, "_write", side_effect=RuntimeError("writer failed")):
                    self.assertTrue(world.cast("q", Vec(8.5, 13.5)))
                self.assertEqual(len(world.projectiles), 1)
                self.assertFalse(recorder.enabled)
                self.assertTrue(recorder.notice)
                recorder.close(world)

    def test_crash_bundle_keeps_stack_without_home_or_project_paths(self):
        with TemporaryDirectory() as folder:
            world = quiet_world()
            recorder = RunRecorder(folder)
            recorder.attach(world)
            world.update(1 / 60)
            try:
                raise ValueError(str(Path.home() / "test.txt"))
            except ValueError as error:
                recorder.crash(world, error)
            recorder.close(world, crashed=True)
            summary, rows, _ = read_bundle(recorder)
            self.assertEqual(summary["ended_by"], "crash")
            self.assertEqual(summary["attempts"][0]["outcome"], "crashed")
            self.assertIn("<home>", summary["crash"]["message"])
            self.assertNotIn(str(Path.home()), json.dumps(summary))
            self.assertTrue(any(r["event"] == "crash" for r in rows))

    def test_logging_does_not_change_combat_or_random_sequences(self):
        with TemporaryDirectory() as folder:
            plain, logged = World(41), World(41)
            recorder = RunRecorder(folder)
            recorder.attach(logged)
            for frame in range(180):
                for world in (plain, logged):
                    if frame % 30 == 0:
                        world.cast("q", Vec(8.5, 13.5))
                    world.update(1 / 60)
            recorder.close(logged)
            for attr in ("hp", "mana", "gold", "kills", "pos"):
                self.assertEqual(getattr(plain.player, attr), getattr(logged.player, attr))
            self.assertEqual([(e.kind, e.hp, e.pos) for e in plain.enemies],
                             [(e.kind, e.hp, e.pos) for e in logged.enemies])
            for attr in ("rng", "combat_rng", "proc_rng", "loot_rng"):
                self.assertEqual(getattr(plain, attr).getstate(), getattr(logged, attr).getstate())


if __name__ == "__main__":
    unittest.main()
