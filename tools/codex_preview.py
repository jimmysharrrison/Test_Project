"""Deterministic Codex screenshots using disposable players, never a real profile.
Run: .venv/Scripts/python tools/codex_preview.py
"""
import os
from pathlib import Path
import sys
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from dungeon.codex import Codex, observe_enemy
from dungeon.world import World
from dungeon.render import Renderer, WIDTH, HEIGHT


def main():
    pygame.display.init(); pygame.font.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    output = Path(__file__).resolve().parents[1] / 'docs' / 'codex'
    output.mkdir(parents=True, exist_ok=True)
    world = World(7)
    r = Renderer(pygame.Surface((WIDTH, HEIGHT)), world)
    r.draw(world, (0, 0), 'codex')
    pygame.image.save(r.screen, str(output / 'locked.png'))
    enemy = world.enemies[0]
    observe_enemy(world, enemy)
    r.codex.selected = enemy.kind
    r.draw(world, (0, 0), 'codex')
    pygame.image.save(r.screen, str(output / 'encountered.png'))
    observe_enemy(world, enemy, defeated=True)
    r.codex.selected = enemy.kind
    r.draw(world, (0, 0), 'codex')
    pygame.image.save(r.screen, str(output / 'bestiary.png'))
    r.codex = Codex(True)
    r.codex.show_undiscovered = True
    r.codex.selected = 'keeper'
    r.codex.scroll = 8
    r.codex.floor, r.codex.phase, r.codex.stage, r.codex.patch = 5, 3, 3, True
    r.draw(world, (0, 0), 'codex')
    pygame.image.save(r.screen, str(output / 'developer-enemy.png'))
    (output / 'keeper-details.txt').write_text(r.codex.copy_details(world.player), encoding='utf-8')
    r.codex.detail_scroll = 36
    r.draw(world, (0, 0), 'codex')
    pygame.image.save(r.screen, str(output / 'developer-stats.png'))
    r.codex.tab = 'Item Catalog'
    r.codex.selected = 'frostweave:boots'
    r.codex.detail_scroll = 0
    r.codex.rank = 5
    r.draw(world, (0, 0), 'codex')
    pygame.image.save(r.screen, str(output / 'developer-items.png'))
    (output / 'item-details.txt').write_text(r.codex.copy_details(world.player), encoding='utf-8')
    pygame.quit()


if __name__ == '__main__':
    main()
