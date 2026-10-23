"""Desktop entry point and input loop."""

import argparse
import os
from pathlib import Path

from .geometry import Vec, screen_direction, unproject
from .world import World


def main():
    parser = argparse.ArgumentParser(description="Embervault — an isometric dungeon crawler")
    parser.add_argument("--headless", action="store_true", help="Use SDL's virtual display and begin immediately")
    parser.add_argument("--frames", type=int, help="Exit after this many frames (for smoke checks)")
    parser.add_argument("--screenshot", type=Path, help="Save the final frame as a PNG")
    parser.add_argument("--seed", type=int, help="Use a repeatable dungeon simulation")
    args = parser.parse_args()
    if args.frames is not None and args.frames <= 0:
        parser.error("--frames must be positive")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    from .audio import Audio
    from .render import HEIGHT, ORIGIN, WIDTH, Renderer

    pygame.display.init()
    pygame.font.init()
    window = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Embervault · The First Descent")
    canvas = pygame.Surface((WIDTH, HEIGHT))
    audio = Audio()
    world = World(args.seed)
    renderer = Renderer(canvas, world)
    clock = pygame.time.Clock()
    mode = "playing" if args.headless else "title"
    running = True
    frame = 0
    view = pygame.Rect(0, 0, 1280, 800)
    try:
        while running:
            elapsed = clock.tick(60) / 1000
            dt = 1 / 60 if args.headless else elapsed
            window_width, window_height = window.get_size()
            factor = min(window_width / WIDTH, window_height / HEIGHT)
            size = (max(1, round(WIDTH * factor)), max(1, round(HEIGHT * factor)))
            view = pygame.Rect(0, 0, *size)
            view.center = (window_width // 2, window_height // 2)
            mx, my = pygame.mouse.get_pos()
            mouse = (round((mx - view.x) / factor), round((my - view.y) / factor))
            keys = pygame.key.get_pressed()
            movement = screen_direction(
                int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
                int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP]),
            )
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.WINDOWFOCUSLOST and mode == "playing" and not args.headless:
                    mode = "paused"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if mode == "title":
                            running = False
                        else:
                            mode = "playing" if mode == "paused" else "paused"
                    elif event.key == pygame.K_m:
                        audio.toggle()
                    elif event.key == pygame.K_RETURN and mode == "title":
                        mode = "playing"
                    elif event.key == pygame.K_r and world.state != "playing":
                        world = World(args.seed)
                        mode = "playing"
                    elif mode == "playing":
                        if event.key == pygame.K_SPACE:
                            world.dash(movement)
                        elif event.key == pygame.K_e:
                            world.use_potion()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if (mode != "playing" or world.state != "playing") and hasattr(renderer, "button"):
                        if renderer.button.collidepoint(mouse):
                            if world.state != "playing":
                                world = World(args.seed)
                            mode = "playing"
            if mode == "playing":
                aim = unproject(Vec(*mouse), ORIGIN)
                attack = pygame.mouse.get_pressed()[0] and view.collidepoint(mx, my) and mouse[0] > 300
                world.update(dt, movement, aim, attack)
            pygame.mouse.set_visible(mode != "playing" or world.state != "playing" or mouse[0] <= 300)
            audio.play(world.events)
            world.events.clear()
            renderer.sound_enabled = audio.enabled
            renderer.draw(world, mouse, mode)
            window.fill((8, 12, 17))
            window.blit(pygame.transform.smoothscale(canvas, size), view)
            pygame.display.flip()
            frame += 1
            if args.frames is not None and frame >= args.frames:
                running = False
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(canvas, str(args.screenshot))
            print(f"Screenshot saved to {args.screenshot}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
