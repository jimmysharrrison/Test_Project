"""Final void floor: stationary boss, familiar minions, fair force and persistence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dungeon.abilities import ABILITIES
from dungeon.codex import species, enemy_values
from dungeon.geometry import Vec
from dungeon.levels import PLAYABLE_FLOORS
from dungeon.maw import (MawFloor, BOSS_POS, MAW_HEALTH, MINION_CAP, ARRIVAL_CAP,
                         PULL_STRENGTHS, SUMMON_ROSTER, VoidArrival)
from dungeon.saves import SaveSlots, decode_world, encode_world
from dungeon.temporal import TemporalField, TemporalEcho
from dungeon.void_depths import FORCES, MECHANIC_CAP
from dungeon.world import World, Projectile, IcePatch


def advance(w, seconds):
    for _ in range(round(seconds * 60)):
        w.update(1 / 60)


def quiet():
    w = World(7, level=10, completion_delay_ms=0)
    w.enemies.clear()
    w.pickups.clear()
    w.player.pos = Vec(8.5, 12.5)
    for s in w.spawners:
        s.timer = 999
    return w


def boss_room():
    w = quiet()
    w.spawners.clear()
    w.void.activate_boss()
    w.void.boss.cooldown = 999
    return w


class MawTests(unittest.TestCase):
    def test_scope_story_and_roster(self):
        w = World(7, level=10)
        self.assertEqual(PLAYABLE_FLOORS, 10)
        self.assertIsInstance(w.void, MawFloor)
        self.assertEqual({s.name for s in w.spawners}, {"Breach Seal"})
        self.assertIn("lower body remains in another dimension", w.level_data.story)
        self.assertIn("Arcanist", w.level_data.story)
        self.assertTrue({"voidling", "binder", "lasher", "grasper", "thrall", "anchor",
                         "gravity_adept", "repulsor", "star_fragment", "rift_warden",
                         "chronal_scholar"}.issubset(SUMMON_ROSTER))
        with self.assertRaises(ValueError):
            World(7, level=11)

    def test_two_waves_then_fixed_boss_without_resource_reset_or_repeat_spawn(self):
        w = quiet()
        w.player.hp, w.player.mana, w.player.potions = 57, 20, 1
        for _ in range(2):
            for spawner in w.spawners[:]:
                w._hit(spawner, 100000)
            advance(w, 3.05)
        self.assertEqual(w.phase, 3)
        self.assertEqual(w.void.boss.pos, BOSS_POS)
        self.assertEqual(w.void.boss.max_hp, MAW_HEALTH)
        self.assertEqual((w.player.hp, w.player.potions), (57, 1))
        self.assertLess(w.player.mana, w.player.max_mana)
        self.assertFalse(w.void.activate_boss())
        self.assertEqual(sum(e.kind == "devourer" for e in w.enemies), 1)

    def test_boss_never_moves_through_patterns_or_player_pursuit(self):
        w = boss_room()
        for stage in (1, 2, 3):
            w.void.boss.hp = MAW_HEALTH * (1 if stage == 1 else .6 if stage == 2 else .3)
            for seq in range(4):
                w.void.mechanics.clear()
                w.void.arrivals.clear()
                w.void.sequence = seq
                w.void.boss.cooldown = 0
                w.player.stasis = 20
                advance(w, .1)
                self.assertEqual(w.void.boss.pos, BOSS_POS)
                self.assertEqual(w.void.stage, stage)
        self.assertEqual(w.void.boss.move_speed, 0)

    def test_summons_warn_then_arrive_and_cover_entire_previous_roster(self):
        w = boss_room()
        boss = w.void.boss
        seen = set()
        for _ in range(4):
            w.enemies[:] = [boss]
            self.assertTrue(w.void._summon(boss))
            self.assertLessEqual(len(w.void.arrivals), ARRIVAL_CAP)
            self.assertEqual(w.enemies, [boss])
            advance(w, 2.05)
            seen.update(e.kind for e in w.enemies if e.summoned)
            for e in w.enemies:
                if e.summoned:
                    self.assertTrue(w.walkable(e.pos, .4))
                    self.assertGreaterEqual((e.pos - w.player.pos).length(), 2)
                    self.assertGreater(e.summon_life, 20)
        self.assertTrue(set(SUMMON_ROSTER).issubset(seen), seen)

    def test_summon_cap_and_occupied_or_walled_arrivals(self):
        w = boss_room()
        for _ in range(2):
            self.assertTrue(w.void._summon(w.void.boss))
            advance(w, 2.05)
        self.assertEqual(sum(e.summoned for e in w.enemies), MINION_CAP)
        self.assertFalse(w.void._summon(w.void.boss))
        for point in (w.player.pos, Vec(.5, .5), w.void.boss.pos):
            w.void.arrivals.append(VoidArrival(point, "voidling", w.void.boss, .01))
        before = len(w.enemies)
        w.update(1 / 60)
        self.assertLessEqual(len(w.enemies), before)
        self.assertFalse(w.void.arrivals)

    def test_release_rechecks_player_occupancy_even_when_capacity_is_available(self):
        w = boss_room()
        w.void.arrivals.append(VoidArrival(w.player.pos, "voidling", w.void.boss, .01))
        w.update(1 / 60)
        self.assertEqual(w.enemies, [w.void.boss])
        self.assertFalse(w.void.arrivals)

    def test_freeze_interrupts_pending_summons_then_resists_repeated_freeze(self):
        w = boss_room()
        w.void._summon(w.void.boss)
        self.assertTrue(w._freeze(w.void.boss, 5))
        self.assertLessEqual(w.void.boss.frozen, .55)
        self.assertFalse(w.void.arrivals)
        self.assertFalse(w._freeze(w.void.boss, 5))

    def test_gravity_moves_toward_fixed_boss_and_prison_blocks_it(self):
        w = boss_room()
        f, p = w.void, w.player
        f.sequence = 1
        f.stage = 3
        f.boss_attack(f.boss)
        pull = f.mechanics[0]
        self.assertEqual(pull.strength, PULL_STRENGTHS[2])
        self.assertGreaterEqual(pull.warning, 2)
        pull.warning = 0
        start = p.pos
        advance(w, .2)
        self.assertLess((p.pos - BOSS_POS).length(), (start - BOSS_POS).length())
        self.assertTrue(w.cast("r"))
        anchored = p.pos
        advance(w, 1)
        self.assertEqual(p.pos, anchored)

    def test_running_outward_escapes_strongest_pull_without_prison(self):
        w = boss_room()
        w.player.pos = Vec(8.5, 9.5)
        f = w.void
        f.stage, f.sequence = 3, 1
        f.boss_attack(f.boss)
        w.request_move(Vec(8.5, 15.4), marker=False)
        advance(w, 5.6)
        self.assertGreater((w.player.pos - BOSS_POS).length(), 1.5)
        self.assertEqual(w.player.hp, w.player.max_hp)
        self.assertEqual(w.player.cooldowns["r"], 0)

    def test_pull_and_grab_do_not_overlap(self):
        w = boss_room()
        f = w.void
        grasper = w.make_enemy(Vec(5.5, 9.5), "grasper", cooldown=999)
        f.root_owner, f.root_left = grasper, 2
        f.sequence = 1
        f.boss_attack(f.boss)
        self.assertFalse(f.mechanics)
        f.root_left = 0
        f.boss_attack(f.boss)
        self.assertEqual(len(f.mechanics), 1)
        self.assertFalse(f.warn("grasp", grasper, w.player.pos))

    def test_later_health_stages_lock_multiple_strikes_and_keep_caps(self):
        for seq in (2, 3):
            w = boss_room()
            w.void.stage, w.void.sequence = 3, seq
            w.void.boss_attack(w.void.boss)
            self.assertEqual(len(w.void.mechanics), 3)
            locked = [(m.pos, m.end) for m in w.void.mechanics]
            w.player.pos = Vec(12.5, 13.5)
            advance(w, .2)
            self.assertEqual([(m.pos, m.end) for m in w.void.mechanics], locked)
            self.assertLessEqual(len(w.void.mechanics), MECHANIC_CAP)
            self.assertLessEqual(sum(m.kind in FORCES for m in w.void.mechanics), 1)

    def test_damage_is_avoidable_after_warning_and_recovery_rewards_offense(self):
        w = boss_room()
        f = w.void
        w.player.pos = Vec(8.5, 10.5)
        f.stage, f.sequence = 1, 2
        f.boss_attack(f.boss)
        advance(w, 1)
        self.assertEqual(w.player.hp, w.player.max_hp)
        w.player.pos = Vec(12.5, 10.5)
        advance(w, 1.1)
        self.assertEqual(w.player.hp, w.player.max_hp)
        self.assertGreater(f.boss.recovery, 0)
        before = f.boss.hp
        w._hit(f.boss, 100, environmental=True)
        self.assertGreater(before - f.boss.hp, 100)

    def test_temporal_summons_use_fields_and_echoes_without_floor_nine_puzzle(self):
        w = boss_room()
        f = w.void
        scholar = w.make_enemy(Vec(5.5, 8.5), "chronal_scholar", signature_timer=999)
        f.update_enemy(scholar, .01)
        self.assertEqual(len(f.fields), 1)
        shot = Projectile(w.player.pos, Vec(1, 0), life=4)
        f.fields[0].warning = 0
        w.projectiles.append(shot)
        advance(w, .2)
        self.assertEqual(shot.pos, f.fields[0].pos)
        self.assertEqual(shot.life, 4)
        elf = w.make_enemy(Vec(8.5, 9.5), "rift_warden", signature_timer=999)
        elf.action, elf.action_time, elf.attack_origin = "time_shot", .01, w.player.pos
        f.update_enemy(elf, .02)
        self.assertTrue(f.echoes)
        self.assertFalse(f.checkpoint_active or f.reserved_prison or f.stopped)
        w.player.mana, w.player.cooldowns["r"] = 0, 44
        self.assertFalse(w.cast("r"))

    def test_wave_and_boss_deaths_are_normal_and_cleanup_all_mechanics(self):
        w = boss_room()
        f = w.void
        f._summon(f.boss)
        owner = w.make_enemy(Vec(5.5, 5.5), "chronal_scholar", summoned=True, summon_life=20)
        f.fields.append(TemporalField(Vec(8.5, 8.5), owner, warning=0))
        f.echoes.append(TemporalEcho(owner.pos, Vec(1, 0), 18))
        w._hurt_player(100000)
        self.assertEqual(w.state, "dead")
        self.assertTrue(f.finished)
        self.assertFalse(f.arrivals or f.fields or f.echoes or f.mechanics or f.zones)
        self.assertFalse(any(e.summoned for e in w.enemies))

    def test_victory_cleans_summons_and_opens_final_stair_once(self):
        w = boss_room()
        f = w.void
        f._summon(f.boss)
        advance(w, 2.05)
        w._hit(f.boss, 100000)
        self.assertTrue(w.level_completed)
        self.assertTrue(w.exit_open)
        self.assertFalse(w.enemies or f.arrivals or f.fields or f.mechanics)
        rewards = [(p.kind, p.value) for p in w.pickups]
        w._hit(f.boss, 100000)
        self.assertEqual([(p.kind, p.value) for p in w.pickups], rewards)
        w.player.pos = w.exit
        w.update(1 / 60)
        self.assertEqual(w.state, "won")
        self.assertFalse(w.next_level())

    def test_same_tick_death_takes_precedence_over_victory(self):
        w = boss_room()
        w.player.hp = 1
        w.projectiles = [Projectile(BOSS_POS, Vec(), damage=100000),
                         Projectile(w.player.pos, Vec(), hostile=True, damage=100000)]
        w.update(1 / 60)
        self.assertEqual(w.state, "dead")
        self.assertFalse(w.level_completed)

    @patch("dungeon.codex.datetime", wraps=datetime)
    def test_live_warning_and_minion_sources_roundtrip_and_slot_load(self, clock):
        clock.now.return_value = datetime(2026, 10, 24, tzinfo=timezone.utc)
        w = boss_room()
        f = w.void
        f._summon(f.boss)
        owner = w.make_enemy(Vec(5.5, 7.5), "chronal_scholar", cooldown=999)
        f.fields.append(TemporalField(Vec(6.5, 9.5), owner))
        f.echoes.append(TemporalEcho(owner.pos, Vec(1, 0), 18))
        loaded = decode_world(json.loads(json.dumps(encode_world(w))))
        self.assertIs(loaded.void.arrivals[0].owner, loaded.void.boss)
        self.assertIs(loaded.void.fields[0].owner, loaded.enemies[1])
        advance(w, 3)
        advance(loaded, 3)
        self.assertEqual(encode_world(loaded), encode_world(w))
        with TemporaryDirectory() as folder:
            slots = SaveSlots(Path(folder) / "profile.json")
            self.assertTrue(slots.save(1, w), slots.error)
            loaded = slots.load(1)
            self.assertIsInstance(loaded.void, MawFloor)
            self.assertEqual(loaded.level, 10)

    def test_old_floor_nine_ending_can_continue_into_floor_ten(self):
        w = World(7, level=9)
        w.level_completed, w.state = True, "won"
        loaded = decode_world(encode_world(w))
        self.assertEqual(loaded.state, "cleared")
        self.assertTrue(loaded.next_level())
        self.assertIsInstance(loaded.void, MawFloor)
        self.assertIs(loaded.void.world, loaded)

    def test_codex_matches_immobile_health_and_shared_attack_damage(self):
        entry = species()["devourer"]
        values = enemy_values(entry, 10)
        self.assertEqual(values["effective_health_hp"], MAW_HEALTH)
        self.assertEqual(values["effective_speed_tiles_per_second"], 0)
        self.assertEqual(values["modifiers"]["health_per_floor"], 0)
        self.assertEqual(values["effective_damage_hp_per_hit"]["Inward Convergence"], 18)


if __name__ == "__main__":
    unittest.main()
