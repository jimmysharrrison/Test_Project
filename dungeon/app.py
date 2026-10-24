"""Desktop events, menus, level progression, and local armory persistence."""

import argparse
import os
from pathlib import Path

from .controls import Controls
from .geometry import Vec, unproject
from .profile import ProfileStore
from .world import World


def main():
    parser = argparse.ArgumentParser(description="Embervault — the Ice Mage build")
    parser.add_argument("--headless", action="store_true", help="Use a virtual display and begin immediately")
    parser.add_argument("--frames", type=int, help="Exit after this many frames")
    parser.add_argument("--screenshot", type=Path, help="Save the final frame as a PNG")
    parser.add_argument("--seed", type=int, help="Use a repeatable simulation")
    parser.add_argument("--no-save", action="store_true", help="Do not load or save a local character")
    parser.add_argument("--profile", type=Path, help="Use an explicit character profile path")
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
    pygame.display.set_caption("Embervault · Ice Mage · Frostbound Armory")
    canvas = pygame.Surface((WIDTH, HEIGHT))
    audio = Audio()
    store = None if args.no_save or (args.headless and args.profile is None) else ProfileStore(args.profile)
    player = store.load() if store else None
    world = World(args.seed, player=player, level=player.unlocked_level) if player else World(args.seed)
    controls = Controls(world)
    renderer = Renderer(canvas, world)
    clock = pygame.time.Clock()
    mode = "playing" if args.headless else "title"
    menu_return = "playing"
    save_timer = 0
    running = True
    frame = 0

    def enter_or_restart():
        nonlocal world, controls, mode
        if world.state == "cleared":
            world.next_level()
            controls = Controls(world)
        elif world.state != "playing":
            earned = world.player
            earned.hp, earned.mana = earned.max_hp, 100
            earned.pos = Vec(3.5, 13.5)
            earned.stasis = earned.cast_time = earned.flash = 0
            earned.invincible = 1
            earned.cooldowns = dict.fromkeys(earned.cooldowns, 0.0)
            world = World(args.seed, player=earned, level=earned.unlocked_level)
            controls = Controls(world)
        mode = "playing"

    def open_armory(tab):
        nonlocal mode, menu_return
        if mode == "title":
            return
        controls.cancel()
        if mode == tab:
            mode = menu_return
        else:
            if mode not in ("inventory", "shop"):
                menu_return = mode
            mode = tab

    try:
        while running:
            elapsed = clock.tick(60) / 1000
            dt = 1 / 60 if args.headless else min(elapsed, 1 / 30)
            ww, wh = window.get_size()
            factor = max(0.001, min(ww / WIDTH, wh / HEIGHT))
            size = (max(1, round(WIDTH * factor)), max(1, round(HEIGHT * factor)))
            view = pygame.Rect(0, 0, *size)
            view.center = (ww // 2, wh // 2)

            def logical(point):
                return (round((point[0] - view.x) * WIDTH / view.width),
                        round((point[1] - view.y) * HEIGHT / view.height))

            events = pygame.event.get()
            mouse = logical(pygame.mouse.get_pos())
            in_world = renderer.world_area(mouse)
            if in_world and mode == "playing":
                controls.point(unproject(Vec(*mouse), ORIGIN),
                               unproject(Vec(mouse[0], mouse[1] + 15), ORIGIN))
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.WINDOWFOCUSLOST and mode == "playing" and not args.headless:
                    mode = "paused"
                    controls.cancel()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if mode in ("inventory", "shop"):
                            mode = menu_return
                        elif not controls.cancel():
                            if mode == "title":
                                running = False
                            else:
                                mode = "playing" if mode == "paused" else "paused"
                    elif event.key in (pygame.K_i, pygame.K_b):
                        open_armory("inventory" if event.key == pygame.K_i else "shop")
                    elif event.key == pygame.K_m:
                        audio.toggle()
                    elif event.key == pygame.K_RETURN and mode not in ("inventory", "shop"):
                        enter_or_restart()
                    elif mode == "playing" and world.state == "playing":
                        spell_keys = {pygame.K_q: "q", pygame.K_w: "w", pygame.K_e: "e", pygame.K_r: "r"}
                        if event.key in spell_keys:
                            controls.hotkey(spell_keys[event.key])
                        elif event.key == pygame.K_1:
                            world.use_potion()
                        elif event.key == pygame.K_s:
                            world.stop()
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                    controls.right_up()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    point = logical(getattr(event, "pos", pygame.mouse.get_pos()))
                    if mode in ("inventory", "shop"):
                        if event.button == 1:
                            action = renderer.armory.click(world, point, mode)
                            mode = menu_return if action == "close" else action
                        continue
                    if event.button == 1 and renderer.gear_button.collidepoint(point):
                        open_armory("inventory")
                        continue
                    if mode != "playing" or world.state != "playing":
                        if event.button == 1 and renderer.button.collidepoint(point):
                            enter_or_restart()
                        continue
                    on_floor = renderer.world_area(point)
                    target = unproject(Vec(*point), ORIGIN)
                    if event.button == 3:
                        controls.right_down(target if on_floor else None)
                    elif event.button == 1:
                        ability = renderer.ability_at(point)
                        if ability:
                            controls.ability_button(ability)
                        elif renderer.potion_rect.collidepoint(point):
                            world.use_potion()
                        elif on_floor:
                            controls.left_world(target, renderer.pick_target(world, point),
                                                unproject(Vec(point[0], point[1] + 15), ORIGIN))
            if not running:
                break
            if mode == "playing" and world.state == "playing":
                pressed = pygame.mouse.get_pressed()
                keys = pygame.key.get_pressed()
                if not pressed[2]:
                    controls.right_up()
                controls.update(dt, controls.aim if pressed[2] and in_world else None,
                                repeat_q=bool(keys[pygame.K_q]) and in_world)
                world.update(dt, controls.aim)
            save_timer += elapsed
            if store and save_timer >= 0.5:
                store.save(world.player)
                save_timer = 0
            audio.play(world.events)
            world.events.clear()
            renderer.profile_notice = store.error if store else ""
            renderer.sound_enabled = audio.enabled
            renderer.armed = controls.armed
            renderer.aim = controls.aim
            renderer.bolt_aim = controls.bolt_aim
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
        if store:
            store.save(world.player)
            if store.error:
                print(store.error)
        pygame.quit()


if __name__ == "__main__":
    main()
