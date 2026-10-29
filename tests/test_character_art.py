"""Directional art follows movement independently of aim and survives saves."""
import json
import os
import unittest

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from dungeon.character_art import (mage_sprite, mage_sprite_art, mage_view, MAGE_HEIGHT,
                                   mage_walk_frame, MAGE_WALK_STRIDE)
from dungeon.geometry import Vec
from dungeon.saves import decode_world, encode_world
from dungeon.world import World


class CharacterArtTests(unittest.TestCase):
    def quiet_world(self):
        world = World(7)
        world.enemies.clear()
        world.player.pos = Vec(8.5, 8.5)
        for spawner in world.spawners:
            spawner.timer = 999
        return world

    def test_isometric_direction_mapping(self):
        for direction, expected in ((Vec(1, 0), (False, True)),
                                    (Vec(0, 1), (False, False)),
                                    (Vec(-1, 0), (True, True)),
                                    (Vec(0, -1), (True, False)),
                                    (Vec(1, 1), (False, False)),
                                    (Vec(-1, -1), (True, False)),
                                    (Vec(1, -1), (False, True)),
                                    (Vec(-1, 1), (False, False))):
            self.assertEqual(mage_view(direction), expected)

    def test_movement_faces_travel_even_when_mouse_aims_opposite(self):
        for direction in (Vec(1, 0), Vec(0, 1), Vec(-1, 0), Vec(0, -1)):
            world = self.quiet_world()
            world.request_move(world.player.pos + direction * 2)
            aim = world.player.pos - direction * 5
            world.update(1 / 60, aim=aim)
            self.assertEqual(world.player.visual_facing, direction)
            self.assertLess(world.player.facing.x * direction.x + world.player.facing.y * direction.y, 0)

    def test_stopping_keeps_last_direction_instead_of_following_cursor(self):
        world = self.quiet_world()
        world.request_move(world.player.pos + Vec(-2, 0))
        world.update(1 / 60)
        world.stop()
        world.update(1 / 60, aim=world.player.pos + Vec(5, 5))
        self.assertEqual(world.player.visual_facing, Vec(-1, 0))

    def test_cast_turns_idle_mage_but_keeps_walking_direction(self):
        for walking in (False, True):
            world = self.quiet_world()
            world.player.visual_facing = Vec(0, 1)
            if walking:
                world.request_move(world.player.pos + Vec(0, 2))
            target = world.player.pos + Vec(0, -4)
            self.assertTrue(world.cast("q", target))
            self.assertEqual(world.player.visual_facing, Vec(0, 1) if walking else Vec(0, -1))
            self.assertLess(world.projectiles[0].velocity.y, 0)

    def test_prison_prevents_movement_and_preserves_direction(self):
        world = self.quiet_world()
        world.player.visual_facing = Vec(-1, 0)
        world.request_move(world.player.pos + Vec(2, 0))
        start = world.player.pos
        self.assertTrue(world.cast("r"))
        world.update(1 / 60, aim=start + Vec(4, 0))
        self.assertEqual(world.player.pos, start)
        self.assertEqual(world.player.visual_facing, Vec(-1, 0))

    def test_live_save_roundtrip_keeps_visual_facing_and_movement(self):
        world = self.quiet_world()
        world.request_move(world.player.pos + Vec(0, -2))
        world.update(1 / 60)
        loaded = decode_world(json.loads(json.dumps(encode_world(world))))
        self.assertEqual(loaded.player.visual_facing, Vec(0, -1))
        world.update(1 / 60)
        loaded.update(1 / 60)
        self.assertEqual(loaded.player.pos, world.player.pos)
        self.assertEqual(loaded.player.visual_facing, world.player.visual_facing)

    def test_older_snapshot_without_visual_facing_loads(self):
        world = self.quiet_world()
        # A shared Vec reference lets the simulated old snapshot omit the field
        # without removing a numbered node used by the snapshot reference graph.
        world.player.visual_facing = world.player.facing
        snapshot = encode_world(world)
        del snapshot["world"]["data"]["player"]["data"]["visual_facing"]
        loaded = decode_world(snapshot)
        self.assertEqual(loaded.player.visual_facing, loaded.player.facing)
        loaded.update(1 / 60)

    def test_sprite_views_are_transparent_distinct_and_use_same_baseline(self):
        atlas = mage_sprite_art()
        self.assertIsNotNone(atlas)
        self.assertEqual(atlas.get_at((0, 0)).a, 0)
        front, back = mage_sprite(), mage_sprite(True)
        self.assertEqual(front.get_height(), MAGE_HEIGHT)
        self.assertEqual(back.get_height(), MAGE_HEIGHT)
        self.assertEqual(front.get_at((0, 0)).a, 0)
        self.assertEqual(back.get_at((0, 0)).a, 0)
        self.assertLessEqual(abs(front.get_bounding_rect().bottom - back.get_bounding_rect().bottom), 1)
        self.assertNotEqual(pygame.image.tobytes(front, "RGBA"), pygame.image.tobytes(back, "RGBA"))
        flipped = mage_sprite(False, True)
        self.assertEqual(pygame.image.tobytes(flipped, "RGBA"),
                         pygame.image.tobytes(pygame.transform.flip(front, True, False), "RGBA"))
        flashed = mage_sprite(False, False, MAGE_HEIGHT, True)
        self.assertEqual(pygame.mask.from_surface(front).count(), pygame.mask.from_surface(flashed).count())

    def test_walk_cycle_visits_four_poses_then_loops(self):
        self.assertEqual([mage_walk_frame(MAGE_WALK_STRIDE * n / 4 + .00001)
                          for n in range(5)], [0, 1, 2, 3, 0])

    def test_walk_distance_tracks_actual_travel_and_slow(self):
        distances = []
        for slowed in (False, True):
            world = self.quiet_world()
            if slowed:
                world.player.apply_slow(.5, 5)
            world.request_move(world.player.pos + Vec(3, 0))
            start = world.player.pos
            for _ in range(30):
                world.update(1 / 60)
            actual = (world.player.pos - start).length()
            self.assertTrue(world.player.walking)
            self.assertAlmostEqual(world.player.walk_distance, actual)
            distances.append(actual)
        self.assertAlmostEqual(distances[1], distances[0] * .5)

    def test_idle_stop_blocked_and_prison_do_not_advance_walk_cycle(self):
        world = self.quiet_world()
        world.request_move(world.player.pos + Vec(3, 0))
        world.update(1 / 60)
        distance = world.player.walk_distance
        world.stop()
        world.update(1 / 60)
        self.assertFalse(world.player.walking)
        self.assertEqual(world.player.walk_distance, distance)
        world.player.pos = Vec(8.75, 8.5)
        world.walls.add((9, 8))
        world.path = [Vec(10.5, 8.5)]
        world.update(1 / 60)
        self.assertFalse(world.player.walking)
        self.assertEqual(world.player.walk_distance, distance)
        world.walls.remove((9, 8))
        self.assertTrue(world.cast("r"))
        world.update(1 / 60)
        self.assertFalse(world.player.walking)
        self.assertEqual(world.player.walk_distance, distance)

    def test_animation_progress_roundtrips_and_old_snapshots_default_to_idle(self):
        world = self.quiet_world()
        world.request_move(world.player.pos + Vec(3, 0))
        for _ in range(15):
            world.update(1 / 60)
        snapshot = encode_world(world)
        loaded = decode_world(json.loads(json.dumps(snapshot)))
        self.assertEqual(loaded.player.walk_distance, world.player.walk_distance)
        self.assertTrue(loaded.player.walking)
        for key in ("walking", "walk_distance"):
            del snapshot["world"]["data"]["player"]["data"][key]
        legacy = decode_world(snapshot)
        self.assertFalse(legacy.player.walking)
        self.assertEqual(legacy.player.walk_distance, 0)
        self.assertEqual(legacy.player.visual_facing, world.player.visual_facing)

    def test_walk_frames_are_distinct_transparent_and_registered_to_the_ground(self):
        for back in (False, True):
            poses = [mage_sprite(back, False, MAGE_HEIGHT, False, i) for i in range(4)]
            self.assertEqual(len({pygame.image.tobytes(p, "RGBA") for p in poses}), 4)
            self.assertTrue(all(p.get_at((0, 0)).a == 0 for p in poses))
            bottoms = [p.get_bounding_rect().bottom for p in poses]
            self.assertLessEqual(max(bottoms) - min(bottoms), 1)
            self.assertLessEqual(abs(bottoms[0] - mage_sprite(back).get_bounding_rect().bottom), 1)


if __name__ == "__main__":
    unittest.main()
