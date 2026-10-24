"""Discovery, spoiler boundaries, definition parity and read-only developer views."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
from dungeon.codex import (Codex, species, observe_enemy, observe_visible, observe_items,
                           enemy_values, item_values, item_templates, load_discoveries)
from dungeon.geometry import Vec
from dungeon.world import World, Enemy, ENEMY_STATS
from dungeon.profile import ProfileStore
from dungeon.items import Item, Inventory


class CodexTests(unittest.TestCase):
    def test_registry_includes_every_definition_and_variant(self):
        from dungeon.encounters import BOSSES, COMPANIONS, MINIBOSS_IDS
        registry = species()
        self.assertTrue(set(ENEMY_STATS) <= registry.keys())
        for floor, (name, kind, _) in BOSSES.items():
            self.assertEqual(registry[MINIBOSS_IDS[floor]].name, name)
            self.assertEqual(registry[MINIBOSS_IDS[floor]].kind, kind)
            self.assertIn(COMPANIONS[floor][0], registry)
        self.assertEqual(registry['keeper'].category, 'boss')

    def test_spawn_is_not_discovery_visible_contact_and_defeat_are(self):
        world = World(11)
        self.assertFalse(world.player.bestiary)
        enemy = world.enemies[0]
        world.player.pos = enemy.pos + Vec(.7, 0)
        observe_visible(world)
        self.assertIn(enemy.kind, world.player.bestiary)
        record = world.player.bestiary[enemy.kind]
        self.assertEqual(record['defeats'], 0)
        self.assertFalse(record['defeated'])
        first = record['first_encounter']
        world._hit(enemy, 100000)
        world._hit(enemy, 100000)
        observe_enemy(world, enemy, defeated=True)
        self.assertEqual(record['defeats'], 1)
        self.assertEqual(record['first_encounter'], first)
        self.assertTrue(record['first_defeat'])
        second = world.make_enemy(Vec(8, 8), enemy.kind)
        world._hit(second, 100000)
        self.assertEqual(record['defeats'], 2)

    def test_distant_and_occluded_enemies_remain_unknown(self):
        world = World(3)
        enemy = Enemy(Vec(14, 2), 'husk')
        world.enemies = [enemy]
        observe_visible(world)
        self.assertFalse(world.player.bestiary)
        enemy.pos = Vec(5.5, 4.5)
        world.player.pos = Vec(5.5, 6.5)  # pillar at 5,5 occludes
        observe_visible(world)
        self.assertFalse(world.player.bestiary)

    def test_practice_debug_excluded_summons_share_species(self):
        for flag in ('practice_mode', 'debug_mode', 'debug_invulnerable'):
            world = World(2)
            setattr(world, flag, True)
            enemy = world.enemies[0]
            observe_enemy(world, enemy, True)
            self.assertFalse(world.player.bestiary)
        world = World(2)
        enemy = world.make_enemy(Vec(8, 8), 'crystal', summoned=True)
        observe_enemy(world, enemy, True)
        self.assertEqual(list(world.player.bestiary), ['crystal'])
        self.assertEqual(world.player.bestiary['crystal']['defeats'], 1)
        debug = world.make_enemy(Vec(8, 8), 'arcane', debug_only=True)
        observe_enemy(world, debug, True)
        self.assertNotIn('arcane', world.player.bestiary)

    def test_locked_output_and_filters_never_reveal_ids_names_or_floors(self):
        world = World(2)
        codex = Codex()
        self.assertEqual(len(codex.rows(world.player)), len(species()))
        for row in codex.rows(world.player):
            self.assertTrue(row['locked'])
            details = '\n'.join(codex.details(world.player, row['id']))
            self.assertNotIn(species()[row['id']].name, details)
            self.assertNotIn(row['id'], details)
        for attr, value in [('category', 'boss'), ('floor_filter', 5), ('query', 'Keeper')]:
            setattr(codex, attr, value)
            self.assertEqual(codex.rows(world.player), [])
            setattr(codex, attr, '' if attr == 'query' else None)
        enemy = world.enemies[0]
        observe_enemy(world, enemy)
        text = '\n'.join(codex.details(world.player, enemy.kind))
        self.assertIn(enemy.name, text)
        self.assertNotIn('base health', text)
        self.assertNotIn('Mechanics / advice', text)
        self.assertNotIn('damage', text)
        observe_enemy(world, enemy, True)
        self.assertNotIn('Keeper', '\n'.join(codex.details(world.player, enemy.kind)))
        codex.floor_filter = 1
        self.assertEqual([row['id'] for row in codex.rows(world.player)], [enemy.kind])

    def test_developer_override_is_ephemeral_and_restores_immediately(self):
        world = World(4)
        codex = Codex(True)
        before = copy.deepcopy(world.player)
        self.assertFalse(codex.show_undiscovered)
        codex.show_undiscovered = True
        for tab in ('Bestiary', 'Item Catalog'):
            codex.tab = tab
            for row in codex.rows(world.player):
                self.assertFalse(row['locked'])
                codex.selected = row['id']
                self.assertIn(row['id'], codex.copy_details(world.player))
        codex.tab = 'Bestiary'
        codex.show_undiscovered = False
        self.assertTrue(all(row['locked'] for row in codex.rows(world.player)))
        self.assertEqual(world.player.bestiary, before.bestiary)
        self.assertEqual(world.player.inventory.to_dict(), before.inventory.to_dict())
        self.assertEqual(world.player.achievements, before.achievements)
        self.assertEqual(world.player.item_discoveries, before.item_discoveries)
        normal = Codex(False)
        normal.show_undiscovered = True
        self.assertFalse(normal.developer_view)

    def test_previews_match_gameplay_properties_and_fixed_attack_rules(self):
        for entry in species().values():
            for floor in range(1, 6):
                for phase in range(1, 4):
                    values = enemy_values(entry, floor, phase)
                    actor = entry.actor(floor, phase)
                    self.assertEqual(values['effective_health_hp'], actor.max_hp)
                    self.assertAlmostEqual(values['effective_speed_tiles_per_second'], 0 if entry.id == 'rootbound_heart' else actor.move_speed)
                    if entry.kind in ('crystal', 'predator'):
                        self.assertEqual(next(iter(values['effective_damage_hp_per_hit'].values())), ENEMY_STATS[entry.kind][3])
        for key, template in item_templates().items():
            for rank in range(6):
                values = item_values(key, rank)
                if (3 if template.set_id else 1) <= rank <= template.max_rank:
                    from dataclasses import replace
                    self.assertEqual(values['effective_stats'], replace(template, rank=rank).lines)
                else:
                    self.assertIn('Unavailable', values['availability'])
        codex = Codex(True)
        codex.show_undiscovered = True
        codex.selected = 'keeper'
        codex.floor, codex.phase, codex.stage, codex.patch = 5, 3, 3, True
        text = codex.copy_details(World(1).player)
        self.assertIn('floor=5, phase=3, Keeper stage=3', text)
        self.assertIn('Ice Patch=True', text)
        self.assertIn('dungeon/', text)
        self.assertIn('effective attack interval seconds: 3.66667', text)

    def test_sort_search_and_item_filters(self):
        player = World(2).player
        codex = Codex(True)
        codex.show_undiscovered = True
        for sort in ('health', 'damage', 'speed'):
            codex.sort = sort
            values = [row['metric'] for row in codex.rows(player)]
            self.assertEqual(values, sorted(values, reverse=True))
        codex.query = 'keeper'
        self.assertEqual([r['id'] for r in codex.rows(player)], ['keeper'])
        codex.query = ''
        codex.tab = 'Item Catalog'
        codex.slot = 'helm'
        self.assertEqual(len(codex.rows(player)), 5)
        codex.rank_filter = codex.rank = 5
        self.assertEqual(len(codex.rows(player)), 1)
        self.assertTrue(all('rank=5' in '\n'.join(codex.details(player, r['id'])) for r in codex.rows(player)))

    def test_save_load_old_save_and_no_developer_write(self):
        with tempfile.TemporaryDirectory(dir='.test-tmp') as folder:
            store = ProfileStore(Path(folder) / 'profile.json')
            world = World(5)
            observe_enemy(world, world.enemies[0], True)
            item = world.player.inventory.create('helm', 3)
            world.player.inventory.add(item)
            self.assertTrue(store.save(world.player))
            saved = store.path.read_text()
            codex = Codex(True)
            codex.show_undiscovered = True
            codex.selected = 'keeper'
            codex.copy_details(world.player)
            store.save(world.player)
            self.assertEqual(saved, store.path.read_text())
            loaded = ProfileStore(store.path).load()
            self.assertEqual(loaded.bestiary, world.player.bestiary)
            self.assertIn('standard:helm', loaded.item_discoveries)
            # More defeats must be saved even with nested dictionaries mutated.
            observe_enemy(world, world.make_enemy(Vec(8, 8), 'husk'), True)
            store.save(world.player)
            self.assertEqual(ProfileStore(store.path).load().bestiary['husk']['defeats'], 2)
            old = json.loads(saved)
            old.pop('bestiary'); old.pop('item_discoveries')
            old['kills'] = 500
            store.path.write_text(json.dumps(old))
            loaded = ProfileStore(store.path).load()
            self.assertEqual(loaded.bestiary, {})
            self.assertIn('standard:helm', loaded.item_discoveries)

    def test_sold_items_keep_discovery_and_validation_rejects_bad_history(self):
        world = World(2)
        inv = world.player.inventory
        item = inv.create('boots', 1)
        inv.add(item, auto_equip=False)
        inv.remove(item.uid)
        observe_items(world.player)
        self.assertIn('standard:boots', world.player.item_discoveries)
        restored = Inventory.from_dict(inv.to_dict())
        self.assertIn('standard:boots', restored.catalog_seen)
        with self.assertRaises(ValueError):
            load_discoveries({'bestiary': {'keeper': {'encountered': True, 'defeated': True, 'defeats': -1}}})

class CodexDesktopTests(unittest.TestCase):
    def run_app(self, *args, **kwargs):
        from test_desktop import DesktopTests
        return DesktopTests.run_app(self, *args, **kwargs)

    def test_entire_simulation_pauses_and_returns_to_existing_pause(self):
        import pygame
        from test_desktop import key
        samples = []
        def observe(frame, world, renderer):
            if frame == 1:
                world.player.mana = 20
                world.player.cooldowns['q'] = 2
                world.enemies[0].frozen = 3
                world.intermission = 2
            samples.append((world.time, world.player.timing.total_seconds, world.player.mana,
                world.player.cooldowns['q'], world.enemies[0].frozen, world.intermission))
        _, frames = self.run_app([[], [key(pygame.K_c)], [], [key(pygame.K_ESCAPE)],
            [key(pygame.K_ESCAPE)], [key(pygame.K_c)], [], [key(pygame.K_ESCAPE)], [],
            [key(pygame.K_ESCAPE)]], observe, extra_args=('--headless',))
        self.assertEqual(samples[0], samples[1])
        self.assertEqual(samples[1], samples[2])
        self.assertGreater(samples[3][0], samples[2][0])
        self.assertTrue(all(sample == samples[4] for sample in samples[4:9]))
        self.assertEqual(frames[7][0], 'paused')
        self.assertGreater(samples[9][0], samples[8][0])

    def test_dead_encounter_and_custom_binding_menu_button(self):
        import pygame
        from test_desktop import key, click
        states = []
        def observe(frame, world, renderer):
            if frame == 1:
                world.state = 'dead'
                world.player.hp = 0
            states.append((world.state, world.time))
        _, frames = self.run_app([[], [key(pygame.K_k)], [], [key(pygame.K_ESCAPE)], []],
            observe, extra_args=('--headless', '--codex-key', 'k'))
        self.assertEqual(frames[1][0], 'codex')
        self.assertEqual(states[1:], [states[0]] * 4)
        _, frames = self.run_app([[click(1, (820, 127))], [key(pygame.K_ESCAPE)]], extra_args=('--headless',))
        self.assertEqual(frames[0][0], 'codex')
        self.assertEqual(frames[1][0], 'playing')
        from unittest.mock import patch
        with self.assertRaises(SystemExit), patch("sys.stderr"):
            self.run_app([[]], extra_args=('--headless', '--codex-key', 'q'))

    def test_development_control_hidden_and_copy_context_uses_plain_text(self):
        import pygame
        from unittest.mock import patch
        from dungeon.render import Renderer
        pygame.display.init(); pygame.font.init()
        pygame.display.set_mode((1440, 900))
        world = World(4)
        renderer = Renderer(pygame.Surface((1440, 900)), world)
        for development in (False, True):
            renderer.codex = Codex(development)
            renderer.draw(world, (0, 0), 'codex')
            self.assertEqual(any(action == 'developer' for action, _ in renderer.codex.buttons), development)
            self.assertFalse(any(action == 'stage' for action, _ in renderer.codex.buttons))
        codex = renderer.codex
        codex.show_undiscovered = True
        codex.selected = 'keeper'
        codex.stage, codex.patch = 3, True
        renderer.draw(world, (0, 0), 'codex')
        rect = next(rect for action, rect in codex.buttons if action == 'copy')
        with patch('pygame.scrap.get_init', return_value=True), patch('pygame.scrap.put_text') as put:
            codex.click(world.player, rect.center)
            self.assertIn('Keeper stage=3', put.call_args.args[0])
            self.assertIn('3.66667', put.call_args.args[0])
        pygame.quit()

    def test_new_run_keeps_profile_discoveries_and_counts(self):
        import pygame
        from test_desktop import key, click
        def observe(frame, world, renderer):
            if frame == 1:
                observe_enemy(world, world.enemies[0], True)
        worlds, frames = self.run_app([[], [key(pygame.K_ESCAPE)], [click(1, (850, 614))],
            [click(1, (950, 302))], [click(1, (915, 554))], [click(1, (915, 554))]],
            observe, extra_args=('--headless',))
        self.assertEqual(len(worlds), 2)
        self.assertEqual(worlds[-1].player.bestiary['husk']['defeats'], 1)

    def test_completed_encounter_restores_overlay_without_restarting(self):
        import pygame
        from test_desktop import key
        for state in ('cleared', 'won'):
            with self.subTest(state=state):
                samples = []
                def observe(frame, world, renderer):
                    if frame == 1:
                        world.state = state
                    samples.append((world.state, world.time))
                _, frames = self.run_app([[], [key(pygame.K_c)], [], [key(pygame.K_ESCAPE)], []], observe, extra_args=('--headless',))
                self.assertEqual(samples, [samples[0]] * len(samples))
                self.assertEqual(frames[3][0], 'playing')

    def test_floor_clear_overlay_and_title_are_restored(self):
        import pygame
        from test_desktop import key
        # Use the same actual app event path; completed-floor dismissal cannot
        # accidentally occur while Codex handles Escape.
        def observe(frame, world, renderer):
            if frame == 1:
                world.enemies.clear()
                world.spawners.clear()
                world.level_completed = True
                world.floor_clear_notice = True
        _, frames = self.run_app([[], [], [key(pygame.K_c)], [key(pygame.K_ESCAPE)]], observe, extra_args=('--headless',))
        self.assertEqual([m for m, _ in frames], ['playing', 'floor_clear', 'codex', 'floor_clear'])
        _, frames = self.run_app([[key(pygame.K_c)], [key(pygame.K_ESCAPE)]])
        self.assertEqual([m for m, _ in frames], ['codex', 'title'])

class CodexCombatParityTests(unittest.TestCase):
    def test_displayed_attack_damage_matches_real_releases(self):
        from unittest.mock import patch
        from dungeon.creatures import update_creature
        from dungeon.levels import PHASE_SPEEDS
        for floor in (1, 3, 5):
            for key in ('husk', 'skitter', 'tree', 'spider', 'armor', 'grimoire', 'archer', 'fairy', 'arcane', 'crystal', 'predator'):
                with self.subTest(floor=floor, key=key):
                    world = World(7, level=floor)
                    world.keeper = None
                    world.spawners.clear()
                    world.enemies.clear()
                    enemy = world.make_enemy(world.player.pos, key)
                    values = enemy_values(species()[key], floor)
                    displayed = next(iter(values['effective_damage_hp_per_hit'].values()))
                    if key in ('archer', 'fairy'):
                        enemy.windup = .01
                        enemy.shot_target = world.player.pos + Vec(.1, 0)
                        world._archer(enemy, .02)
                        self.assertEqual(world.projectiles[-1].damage, displayed)
                    elif key == 'arcane':
                        enemy.action, enemy.action_time, enemy.attack_direction = 'warning', .01, Vec(1, 0)
                        update_creature(world, enemy, .02)
                        self.assertEqual(world.projectiles[-1].damage, displayed)
                    elif key in ('crystal', 'predator'):
                        enemy.action, enemy.action_time, enemy.attack_direction = 'lunge', .5, Vec(1, 0)
                        with patch.object(world, '_hurt_player', return_value=True) as hurt:
                            update_creature(world, enemy, .02)
                        self.assertEqual(hurt.call_args.args[0], displayed)
                    else:
                        with patch.object(world, '_hurt_player', return_value=True) as hurt:
                            world._update_simulation(.02)
                        self.assertEqual(hurt.call_args.args[0], displayed)
        root = enemy_values(species()['rootbound_heart'], 2)
        self.assertEqual(set(root['effective_damage_hp_per_hit']), {'Briar Cage'})
        self.assertEqual(root['base_speed_tiles_per_second'], 0)
