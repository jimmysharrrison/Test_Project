"""Render reproducible guidance screenshots at the desktop's letterboxed sizes.

Run from the project root: python -m tools.tutorial_preview
"""

import os
from pathlib import Path

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from dungeon.render import HEIGHT, WIDTH, Renderer
from dungeon.tutorial import LESSONS, Tutorial
from dungeon.world import World


def main():
    pygame.display.init()
    pygame.font.init()
    folder = Path("docs/tutorial")
    folder.mkdir(parents=True, exist_ok=True)
    t = Tutorial(World(7))
    canvas = pygame.Surface((WIDTH, HEIGHT))
    r = Renderer(canvas, t.world)
    for lesson, mode in (("bolt", "playing"), ("patch", "playing"), ("equip", "inventory")):
        t.index = next(i for i, row in enumerate(LESSONS) if row[0] == lesson)
        t.retry()
        if lesson == "equip":
            r.armory.selected_uid = t.item.uid
        r.draw(t.world, None, mode)
        t.draw(r, mode)
        for ww, wh in ((1024, 768), (1280, 800), (1440, 900), (1920, 1080)):
            factor = min(ww / WIDTH, wh / HEIGHT)
            size = (round(WIDTH * factor), round(HEIGHT * factor))
            window = pygame.Surface((ww, wh))
            window.fill((8, 12, 17))
            image = pygame.transform.smoothscale(canvas, size)
            window.blit(image, image.get_rect(center=window.get_rect().center))
            pygame.image.save(window, str(folder / f"{lesson}-{ww}x{wh}.png"))
    pygame.quit()
    print(f"Saved spell and equipment guidance to {folder.resolve()}")


if __name__ == "__main__":
    main()
