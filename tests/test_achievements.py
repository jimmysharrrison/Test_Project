import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dungeon.achievements import AchievementRun
from dungeon.world import World, Projectile
from dungeon.geometry import Vec
from dungeon.profile import ProfileStore

KEY = "untouched_lower_tower"

class AchievementTests(unittest.TestCase):
    def campaign(self):
        w = World(7)
        for floor in range(1, 5):
            w._complete_level()
            w.state = "cleared"
            self.assertTrue(w.next_level())
        return w

    def defeat(self, w):
        w._in_tick = True
        w._hit(w.keeper.boss, 10000)
        w.update(1 / 60)

    def test_campaign_and_duplicate_completion(self):
        w = self.campaign()
        self.defeat(w)
        date = w.player.achievements[KEY]
        self.defeat(w)
        w._complete_level()
        self.assertEqual(w.player.achievements[KEY], date)
        self.assertEqual(w.player.achievement_notifications, [KEY])

    def test_damage_healing_and_environment(self):
        for source in ("enemy", "projectile", "trap", "hazard", "damage_over_time"):
            w = self.campaign()
            w.player.invincible = 0
            w._hurt_player(3, source=source)
            w.player.hp = w.player.max_hp
            self.defeat(w)
            self.assertFalse(w.player.achievements)
            self.assertEqual(w.player.achievement_run.damage, 3)

    def test_prevented_damage(self):
        for protection in ("stasis", "invincible"):
            w = self.campaign()
            setattr(w.player, protection, 1)
            self.assertFalse(w._hurt_player(100))
            setattr(w.player, protection, 0)
            self.defeat(w)
            self.assertIn(KEY, w.player.achievements)

    def test_debug_retry_practice_skip(self):
        for invalidation in ("debug", "retry", "practice", "skip"):
            w = self.campaign()
            if invalidation == "debug":
                w.debug_invulnerable = True
                w.debug_invulnerable = False
            elif invalidation == "retry":
                w.player.achievement_run.retry()
            elif invalidation == "practice":
                w.practice_mode = True
            else:
                w.player.achievement_run.cleared = [1, 3, 4]
            self.defeat(w)
            self.assertFalse(w.player.achievements)
        w = World(7, level=5)
        self.defeat(w)
        self.assertFalse(w.player.achievements)

    def test_simultaneous_death(self):
        for reverse in (False, True):
            w = self.campaign()
            w.player.invincible = 0
            w.player.hp = 1
            shots = [Projectile(w.keeper.boss.pos, Vec(), damage=10000),
                     Projectile(w.player.pos, Vec(), damage=10000, hostile=True)]
            w.projectiles = shots[::-1] if reverse else shots
            w.update(1 / 60)
            self.assertFalse(w.player.achievements)
            self.assertEqual(w.player.achievement_run.deaths, 1)

    def test_save_continue_and_legacy(self):
        import json
        with TemporaryDirectory(dir=".test-tmp") as tmp:
            store = ProfileStore(Path(tmp) / "profile.json")
            w = self.campaign()
            identity = w.player.achievement_run.run_id
            self.assertTrue(store.save(w.player))
            p = store.load()
            self.assertEqual(p.achievement_run.run_id, identity)
            w = World(7, player=p, level=5)
            self.defeat(w)
            self.assertIn(KEY, w.player.achievements)
            store.save(w.player)
            p = store.load()
            self.assertIn(KEY, p.achievements)
            self.assertEqual(p.achievement_notifications, [KEY])
            data = json.loads(store.path.read_text())
            del data["achievement_run"]
            data["achievements"] = {}
            data["achievement_notifications"] = []
            data["cleared_floor"] = 0
            store.path.write_text(json.dumps(data))
            p = store.load()
            self.assertFalse(p.achievement_run.eligible)
            w = World(7, player=p, level=5)
            self.defeat(w)
            self.assertFalse(p.achievements)

    def test_damage_persists_and_partial_history_fails_closed(self):
        run = AchievementRun()
        run.hurt(1)
        loaded = AchievementRun.from_dict(run.to_dict(), 1)
        self.assertFalse(loaded.eligible)
        self.assertEqual(loaded.damage, 1)
        self.assertFalse(AchievementRun.from_dict({"eligible": True}, 1).eligible)

    def test_tutorial_and_replay_cannot_unlock(self):
        from dungeon.tutorial import Tutorial
        normal = World(7)
        lesson = Tutorial(normal)
        lesson.world._complete_level()
        self.assertFalse(lesson.world.player.achievements)
        self.assertEqual(normal.player.achievement_run.cleared, [])
        w = self.campaign()
        w.player.achievement_run.retry()  # shared Level Select/restart path
        w.player.cleared_floor = 0
        replay = World(7, player=w.player, level=5)
        self.defeat(replay)
        self.assertFalse(replay.player.achievements)

    def test_nonlethal_damage_on_keeper_death_tick(self):
        w = self.campaign()
        w.player.invincible = 0
        w.projectiles = [Projectile(w.keeper.boss.pos, Vec(), damage=10000),
                         Projectile(w.player.pos, Vec(), damage=1, hostile=True)]
        w.update(1 / 60)
        self.assertTrue(w.level_completed)
        self.assertFalse(w.player.achievements)
