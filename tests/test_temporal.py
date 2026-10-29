"""Temporal warning, puzzle fairness, retries, persistence and progression."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from dungeon.abilities import ABILITIES
from dungeon.codex import enemy_values, species
from dungeon.geometry import Vec
from dungeon.saves import decode_world, encode_world
from dungeon.temporal import (TemporalFloor, TemporalField, TemporalEcho, TemporalPortal,
                              CHECKPOINT_POS, SURVIVAL_SECONDS, FIELD_LIFE, ECHO_CAP)
from dungeon.world import World, Projectile, IcePatch


def advance(world, seconds):
    for _ in range(round(seconds * 60)):
        world.update(1 / 60)


def quiet():
    w = World(7, level=9, completion_delay_ms=0)
    w.enemies.clear()
    w.pickups.clear()
    for s in w.spawners:
        s.timer = 999
    w.player.pos = CHECKPOINT_POS
    return w


def boss_room():
    w = quiet()
    w.spawners.clear()
    w.void.activate_boss()
    return w


def learn(w):
    advance(w, 3.2)
    assert w.void.stage_name == "practice"
    assert w.cast("r")
    advance(w, SURVIVAL_SECONDS + 1.5)
    assert w.void.stage_name == "fracture"


def expose(w):
    advance(w, 4.2)
    assert w.void.active_anchor is not None
    # Other tests and the playtest use real spell casts to destroy anchors.
    w._hit(w.void.active_anchor, 10000)
    w.update(1 / 60)
    assert w.void.stage_name == "stopped_hour"


class TemporalTests(unittest.TestCase):
    def test_roster_scope_values_and_portal_names(self):
        w = World(7, level=9)
        self.assertIsInstance(w.void, TemporalFloor)
        self.assertEqual({s.name for s in w.spawners}, {"Chronal Rift"})
        self.assertEqual({e.kind for e in w.enemies}, {"rift_warden", "chronal_scholar"})
        for kind in ("rift_warden", "chronal_scholar", "dimensional_anchor", "hourless_breach"):
            entry = species()[kind]
            self.assertEqual(enemy_values(entry, 9)["effective_health_hp"], entry.actor(9).max_hp)
        with self.assertRaises(ValueError):
            World(7, level=11)

    def test_safe_lesson_repeats_without_damage_or_progress_until_r(self):
        w = boss_room()
        hp, potions, gold = w.player.hp, w.player.potions, w.player.gold
        advance(w, 3.2 + SURVIVAL_SECONDS)
        self.assertEqual(w.void.stage_name, "practice_reset")
        self.assertFalse(w.void.lesson_complete)
        self.assertEqual(w.void.completed_anchors, 0)
        self.assertFalse(w._hurt_player(100000))
        self.assertEqual((w.player.hp, w.player.potions, w.player.gold), (hp, potions, gold))
        advance(w, 1.3)
        self.assertTrue(w.cast("r"))
        advance(w, SURVIVAL_SECONDS)
        self.assertTrue(w.void.lesson_complete)
        self.assertEqual(w.void.practice_attempts, 2)

    def test_boss_checkpoint_is_established_only_once(self):
        w = boss_room()
        boss = w.void.boss
        w.player.hp = 17
        w.void.stage_left = 1
        self.assertFalse(w.void.activate_boss())
        self.assertIs(w.void.boss, boss)
        self.assertEqual(w.enemies, [boss])
        self.assertEqual(w.player.hp, 17)
        self.assertEqual(w.void.stage_left, 1)

    def test_reserved_r_works_at_early_and_late_cue_with_zero_resources(self):
        self.assertLess(SURVIVAL_SECONDS, ABILITIES["r"].duration)
        for delay in (0, .4, 1.3):
            with self.subTest(delay=delay):
                w = boss_room()
                learn(w)
                expose(w)
                advance(w, delay)
                w.player.mana = 0
                w.player.cooldowns["r"] = 44
                w.player.cast_time = 2
                self.assertEqual(w.can_cast("r"), "")
                self.assertTrue(w.cast("r"))
                self.assertEqual(w.player.mana, 0)
                self.assertFalse(w.void.reserved_prison)
                advance(w, SURVIVAL_SECONDS - delay)
                self.assertEqual(w.void.completed_anchors, 1)
                self.assertEqual(w.void.failures, 0)

    def test_already_active_prison_covers_full_pulse(self):
        w = boss_room()
        learn(w)
        advance(w, 4.2)
        w.player.cooldowns["r"] = 0
        self.assertTrue(w.cast("r"))
        advance(w, 2.1)
        self.assertLess(w.player.stasis, SURVIVAL_SECONDS)
        w._hit(w.void.active_anchor, 10000)
        w.update(1 / 60)
        self.assertGreater(w.player.stasis, SURVIVAL_SECONDS)
        self.assertFalse(w.void.reserved_prison)
        advance(w, SURVIVAL_SECONDS)
        self.assertEqual(w.void.completed_anchors, 1)

    def test_three_cycles_required_breach_rejects_damage_and_freeze(self):
        w = boss_room()
        boss = w.void.boss
        w._hit(boss, 100000, spell="q")
        self.assertEqual(boss.hp, 3)
        self.assertFalse(w._freeze(boss, 10))
        learn(w)
        for cycle in range(3):
            expose(w)
            self.assertTrue(w.cast("r"))
            advance(w, SURVIVAL_SECONDS)
            self.assertEqual(w.void.completed_anchors, cycle + 1)
            if cycle < 2:
                self.assertFalse(w.exit_open)
                advance(w, 2)
        self.assertTrue(w.level_completed)
        self.assertTrue(w.exit_open)
        self.assertTrue(w.void.finished)
        self.assertFalse(w.void.fields or w.void.echoes or w.void.portals)
        self.assertFalse(any(e.summoned for e in w.enemies))
        w.player.pos = w.exit
        w.update(1 / 60)
        self.assertEqual(w.state, "cleared")
        self.assertTrue(w.next_level())
        self.assertEqual(w.level, 10)

    def test_failed_real_pulse_restarts_boss_without_refunding_gold_or_items(self):
        w = boss_room()
        learn(w)
        expose(w)
        w.cast("r")
        advance(w, SURVIVAL_SECONDS + 2)
        expose(w)
        w.player.stasis = 0
        advance(w, SURVIVAL_SECONDS)
        self.assertEqual(w.void.stage_name, "retry")
        self.assertEqual(w.state, "playing")
        w.player.gold = 123
        w.player.potions = 0
        w.player.mana = 0
        inventory = w.player.inventory
        advance(w, 2)
        self.assertEqual(w.void.completed_anchors, 0)
        self.assertEqual(w.void.boss.hp, 3)
        self.assertEqual(w.player.pos, CHECKPOINT_POS)
        self.assertEqual(w.player.hp, w.player.max_hp)
        self.assertEqual(w.player.mana, w.player.max_mana)
        self.assertEqual(w.player.potions, w.void.checkpoint_potions)
        self.assertEqual(w.player.gold, 123)
        self.assertIs(w.player.inventory, inventory)
        self.assertTrue(all(cd == 0 for cd in w.player.cooldowns.values()))
        self.assertFalse(w.player.timing.eligible)
        self.assertTrue(w.void.lesson_complete)

    def test_combat_death_uses_checkpoint_but_wave_death_is_normal(self):
        w = boss_room()
        learn(w)
        advance(w, 1.6)
        w.player.invincible = 0
        self.assertTrue(w._hurt_player(100000))
        self.assertEqual(w.void.stage_name, "retry")
        self.assertEqual(w.state, "playing")
        self.assertFalse(w.cast("q", Vec(8.5, 8.5)))
        advance(w, 2)
        self.assertEqual(w.player.hp, w.player.max_hp)
        wave = quiet()
        wave._hurt_player(100000)
        self.assertEqual(wave.state, "dead")

    def test_attempt_enemies_and_anchors_cannot_generate_loot(self):
        w = boss_room()
        learn(w)
        advance(w, 4.2)
        for e in w.enemies[:]:
            if e is not w.void.boss:
                w._hit(e, 10000)
        self.assertFalse(w.pickups)
        self.assertEqual(w.void.stage_name, "stop_pending")

    def test_fields_pause_both_projectile_teams_and_preserve_velocity_and_life(self):
        w = quiet()
        owner = w.make_enemy(Vec(5.5, 5.5), "chronal_scholar", cooldown=999, signature_timer=999)
        point = Vec(8.5, 8.5)
        field = TemporalField(point, owner, warning=0)
        w.void.fields.append(field)
        shots = [Projectile(point, Vec(1, 0), life=4, hostile=hostile) for hostile in (False, True)]
        w.projectiles = shots[:]
        advance(w, .5)
        for shot in shots:
            self.assertEqual((shot.pos, shot.velocity, shot.life), (point, Vec(1, 0), 4))
        advance(w, FIELD_LIFE)
        for shot in shots:
            self.assertGreater(shot.pos.x, point.x)
            self.assertEqual(shot.velocity, Vec(1, 0))
            self.assertLess(shot.life, 4)

    def test_warning_fields_do_not_stop_shots_and_freeze_cancels_only_pending_fields(self):
        w = quiet()
        owner = w.make_enemy(Vec(5.5, 5.5), "chronal_scholar", cooldown=999, signature_timer=999)
        pending = TemporalField(Vec(8.5, 8.5), owner)
        active = TemporalField(Vec(10.5, 8.5), owner, warning=0)
        w.void.fields = [pending, active]
        shot = Projectile(pending.pos, Vec(1, 0), life=4)
        self.assertFalse(w.void.shot_stopped(shot))
        w._freeze(owner, 2)
        self.assertEqual(w.void.fields, [active])
        w._hit(owner, 10000)
        self.assertIn(active, w.void.fields)
        advance(w, 2.1)
        self.assertFalse(w.void.fields)

    def test_enemy_portal_warns_and_revalidates_arrival_and_freeze_interrupts(self):
        w = quiet()
        e = w.make_enemy(Vec(8.5, 7.5), "rift_warden", signature_timer=0, cooldown=999)
        w.void.update_enemy(e, .01)
        self.assertEqual(e.action, "rift_warning")
        start, end = e.pos, e.attack_origin
        self.assertNotEqual(start, end)
        w.player.pos = end
        w.void.update_enemy(e, 1.31)
        self.assertEqual(e.pos, start)
        w.player.pos = CHECKPOINT_POS
        e.signature_timer = 0
        w.void.update_enemy(e, .01)
        w._freeze(e, 1)
        self.assertEqual(e.action, "")
        self.assertEqual(e.pos, start)

    def test_portal_arrivals_reject_newly_occupied_positions(self):
        w = quiet()
        w.void.portals.append(TemporalPortal(w.player.pos, warning=.01))
        w.update(1 / 60)
        self.assertFalse(w.enemies)
        self.assertFalse(w.void.portals)

    def test_echo_repeats_stored_shot_once_even_after_original_moves(self):
        w = quiet()
        e = w.make_enemy(Vec(8.5, 8.5), "rift_warden", signature_timer=999, cooldown=999)
        origin = e.pos
        e.action, e.action_time, e.attack_origin = "time_shot", .01, Vec(10.5, 8.5)
        w.void.update_enemy(e, .02)
        self.assertEqual(len(w.void.echoes), 1)
        w.projectiles.clear()
        e.pos = Vec(4.5, 4.5)
        w.void.update(1.31)
        self.assertEqual(len(w.projectiles), 1)
        echo = w.projectiles[0]
        self.assertEqual(echo.source, "temporal_echo")
        self.assertEqual(echo.pos, origin + Vec(.4, 0))
        self.assertEqual(echo.velocity, Vec(3.8, 0))
        w.void.update(1.31)
        self.assertEqual(len(w.projectiles), 1)
        self.assertFalse(w.void.echoes)
        for _ in range(ECHO_CAP + 2):
            e.action, e.action_time = "time_shot", .01
            w.void.update_enemy(e, .02)
        self.assertEqual(len(w.void.echoes), ECHO_CAP)

    def test_stopped_hour_freezes_world_but_r_and_player_remain_available(self):
        w = boss_room()
        learn(w)
        expose(w)
        e = w.make_enemy(Vec(6.5, 6.5), "rift_warden", frozen=2, cooldown=5)
        field = TemporalField(Vec(6.5, 8.5), e, warning=.7)
        echo = TemporalEcho(e.pos, Vec(1, 0), 10)
        w.void.fields.append(field)
        w.void.echoes.append(echo)
        shot = Projectile(Vec(6.5, 8.5), Vec(1, 0), life=5)
        w.projectiles.append(shot)
        patch = IcePatch(Vec(6.5, 6.5), life=5)
        w.ice_patches.append(patch)
        before = (e.pos, e.phase, e.frozen, e.cooldown, shot.pos, shot.life,
                  field.warning, echo.warning, patch.life, w.void.scene_time)
        w.player.cooldowns["w"] = 3
        w.request_move(Vec(10.5, 12.5), marker=False)
        advance(w, .2)
        self.assertNotEqual(w.player.pos, CHECKPOINT_POS)
        self.assertLess(w.player.cooldowns["w"], 3)
        self.assertEqual(before, (e.pos, e.phase, e.frozen, e.cooldown, shot.pos, shot.life,
                                 field.warning, echo.warning, patch.life, w.void.scene_time))
        self.assertTrue(w.cast("r"))
        advance(w, SURVIVAL_SECONDS - .2)
        self.assertEqual(w.void.completed_anchors, 1)

    @patch("dungeon.codex.datetime", wraps=datetime)
    def test_live_saves_preserve_encounter_references_and_deterministic_continuation(self, clock):
        clock.now.return_value = datetime(2026, 10, 24, tzinfo=timezone.utc)
        for stage in ("practice", "exposure", "stopped_hour", "retry"):
            with self.subTest(stage=stage):
                w = boss_room()
                if stage == "practice":
                    advance(w, 3.2)
                else:
                    learn(w)
                    advance(w, 4.2)
                    if stage in ("stopped_hour", "retry"):
                        w._hit(w.void.active_anchor, 10000)
                        w.update(1 / 60)
                    if stage == "retry":
                        advance(w, SURVIVAL_SECONDS)
                    if stage == "stopped_hour":
                        w.cast("r")
                self.assertEqual(w.void.stage_name, stage)
                restored = decode_world(json.loads(json.dumps(encode_world(w))))
                self.assertIs(restored.void.world, restored)
                self.assertIs(restored.void.boss, restored.enemies[0])
                if stage == "exposure":
                    self.assertIn(restored.void.active_anchor, restored.enemies)
                advance(w, 2)
                advance(restored, 2)
                self.assertEqual(encode_world(restored), encode_world(w))

    @patch("dungeon.codex.datetime", wraps=datetime)
    def test_pending_temporal_sources_and_reserved_r_roundtrip(self, clock):
        clock.now.return_value = datetime(2026, 10, 24, tzinfo=timezone.utc)
        w = quiet()
        owner = w.make_enemy(Vec(5.5, 5.5), "chronal_scholar", cooldown=999)
        w.void.fields.append(TemporalField(Vec(8.5, 8.5), owner))
        w.void.echoes.append(TemporalEcho(owner.pos, Vec(1, 0), 22))
        w.void.portals.append(TemporalPortal(Vec(12.5, 5.5)))
        restored = decode_world(encode_world(w))
        self.assertIs(restored.void.fields[0].owner, restored.enemies[0])
        advance(w, .3)
        advance(restored, .3)
        self.assertEqual(encode_world(restored), encode_world(w))
        w = boss_room()
        advance(w, 3.2)
        w.player.mana, w.player.cooldowns["r"], w.player.cast_time = 0, 40, 3
        restored = decode_world(encode_world(w))
        self.assertTrue(restored.void.reserved_prison)
        self.assertTrue(restored.cast("r"))
        advance(restored, SURVIVAL_SECONDS)
        self.assertTrue(restored.void.lesson_complete)

    def test_ordinary_prison_keeps_normal_mana_and_cooldown_rules(self):
        w = quiet()
        w.player.mana = 0
        self.assertFalse(w.cast("r"))
        w.player.mana = w.player.max_mana
        w.player.cooldowns["r"] = 10
        self.assertFalse(w.cast("r"))
        w.player.cooldowns["r"] = 0
        before = w.player.mana
        self.assertTrue(w.cast("r"))
        self.assertEqual(w.player.mana, before - w.player.mana_cost_for("r"))
        self.assertGreater(w.player.cooldowns["r"], 0)

    def test_old_floor_eight_winner_can_enter_new_floor(self):
        w = World(7, level=8)
        w.level_completed, w.state = True, "won"
        loaded = decode_world(encode_world(w))
        self.assertEqual(loaded.state, "cleared")
        self.assertTrue(loaded.next_level())
        self.assertEqual(loaded.level, 9)
        self.assertIsInstance(loaded.void, TemporalFloor)
        self.assertIs(loaded.void.world, loaded)


if __name__ == "__main__":
    unittest.main()
