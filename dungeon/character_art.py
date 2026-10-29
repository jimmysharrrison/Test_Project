"""Shared menu portraits displayed directly from the supplied character art."""
from functools import lru_cache
from pathlib import Path

import pygame


MAGE_FRONT = (Path(__file__).resolve().parents[1] / "Images" / "Icons" /
              "Characters" / "Frost Mage" / "frost mage front view.png")
# Relative source viewport: face, silver hair, fur collar and upper shoulders.
# The original front/back illustrations remain untouched.
MAGE_HEADSHOT = (.37, .032, .264, .264)
MAGE_SPRITES = Path(__file__).resolve().parents[1] / "Images" / "Sprites" / "frost-mage-views.png"
MAGE_HEIGHT = 70
# The extraction's front hem extends slightly past the atlas midpoint.
# Use the verified transparent gap rather than cutting the image in half.
MAGE_FRAMES = ((185, 0, 720, 887), (910, 0, 675, 887))
MAGE_WALK_FRAMES = 4
MAGE_WALK_STRIDE = 1.6  # World tiles traveled per complete two-step cycle.
MAGE_WALK_PATHS = tuple(MAGE_SPRITES.with_name(f"frost-mage-walk-{view}.png")
                        for view in ("front", "back"))


def mage_walk_frame(distance):
    return int(max(0, distance) / MAGE_WALK_STRIDE * MAGE_WALK_FRAMES) % MAGE_WALK_FRAMES


@lru_cache(maxsize=2)
def mage_walk_art(back=False):
    try:
        return pygame.image.load(str(MAGE_WALK_PATHS[int(back)]))
    except (OSError, pygame.error):
        return None


@lru_cache(maxsize=8)
def mage_walk_pose(back, index):
    atlas = mage_walk_art(back)
    if atlas is None:
        return None
    width, height = atlas.get_width() // 2, atlas.get_height() // 2
    frame = atlas.subsurface(((index % 2) * width, (index // 2) * height, width, height))
    bounds = frame.get_bounding_rect(min_alpha=32)
    if not bounds.width or not bounds.height:
        return None
    # Register the generated poses on a common center/boot baseline without
    # rescaling individual frames, which would make the mage grow and shrink.
    canvas = pygame.Surface((width, height), pygame.SRCALPHA)
    canvas.blit(frame, (round(width / 2 - bounds.centerx), height - 1 - bounds.bottom))
    return canvas


def mage_view(direction):
    """World axes project diagonally: x-y points right, x+y points down."""
    screen_x, screen_y = direction.x - direction.y, direction.x + direction.y
    back = screen_y < -1e-6
    mirrored = (screen_x < 0 if back else screen_x > 0) if abs(screen_x) > 1e-6 else False
    return back, mirrored


@lru_cache(maxsize=1)
def mage_sprite_art():
    try:
        return pygame.image.load(str(MAGE_SPRITES))
    except (OSError, pygame.error):
        return None


@lru_cache(maxsize=192)
def mage_sprite(back=False, mirrored=False, height=MAGE_HEIGHT, flash=False, walk_frame=None):
    frame = mage_walk_pose(back, walk_frame % MAGE_WALK_FRAMES) if walk_frame is not None else None
    if frame is None:
        atlas = mage_sprite_art()
        if atlas is None:
            return None
        frame = atlas.subsurface(MAGE_FRAMES[int(back)])
    # Both atlas frames share their vertical extent and boot baseline.
    width = max(1, round(frame.get_width() * height / frame.get_height()))
    sprite = pygame.transform.smoothscale(frame, (width, height))
    if mirrored:
        sprite = pygame.transform.flip(sprite, True, False)
    if flash:
        sprite.fill((145, 165, 185, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return sprite


@lru_cache(maxsize=1)
def mage_art():
    try:
        return pygame.image.load(str(MAGE_FRONT))
    except (OSError, pygame.error):
        return None


@lru_cache(maxsize=16)
def mage_portrait(size):
    source = mage_art()
    if source is None:
        return None
    width, height = source.get_size()
    x, y, w, h = MAGE_HEADSHOT
    viewport = pygame.Rect(round(width * x), round(height * y),
                           round(width * w), round(height * h))
    # Supersample the circular UI mask so small HUD portraits have smooth edges.
    diameter = size * 2
    portrait = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    portrait.blit(pygame.transform.smoothscale(source.subsurface(viewport),
                                              (diameter, diameter)), (0, 0))
    mask = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255), (size, size), size)
    portrait.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return pygame.transform.smoothscale(portrait, (size, size))
