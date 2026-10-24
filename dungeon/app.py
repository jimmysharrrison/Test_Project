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
    parser.add_argument("--level", type=int, help="Choose a reached level; headless previews may use any level")
    parser.add_argument("--no-save", action="store_true", help="Do not load or save a local character")
    parser.add_argument("--profile", type=Path, help="Use an explicit character profile path")
    args = parser.parse_args()
    if args.frames is not None and args.frames <= 0:
        parser.error("--frames must be positive")
    if args.level is not None and args.level <= 0:
        parser.error("--level must be positive")
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame

    from .audio import Audio
    from .menus import FRONTEND_MODES
    from .render import HEIGHT, ORIGIN, WIDTH, Renderer

    pygame.display.init()
    pygame.font.init()
    window = pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    pygame.display.set_caption("Embervault · Ice Mage · Thornveil Forest")
    canvas = pygame.Surface((WIDTH, HEIGHT))
    audio = Audio()
    store = None if args.no_save or (args.headless and args.profile is None) else ProfileStore(args.profile)
    player = store.load() if store else None
    has_character = player is not None or args.headless
    current_level = player.current_level if player else 1
    unlocked_level = player.unlocked_level if player else 1
    locked_request = args.level is not None and args.level > unlocked_level and not args.headless
    start_level = args.level if args.level is not None and not locked_request else current_level
    world = World(args.seed, player=player, level=start_level)
    controls = Controls(world)
    renderer = Renderer(canvas, world)
    renderer.menu.has_character = has_character
    if locked_request:
        renderer.menu.notice = f"Level {args.level} is locked. Reach it through the portal first."
    clock = pygame.time.Clock()
    mode = "playing" if args.headless else "title"
    menu_return = "playing"
    help_return = "title"
    save_timer = 0
    running = True
    frame = 0

    def begin_level(level, fresh=False):
        nonlocal world, controls, mode, menu_return, has_character
        if fresh:
            world = World(args.seed)
        else:
            earned = world.player
            earned.hp, earned.mana = earned.max_hp, 100
            earned.pos = Vec(3.5, 13.5)
            earned.stasis = earned.cast_time = earned.flash = 0
            earned.invincible = 1
            earned.cooldowns = dict.fromkeys(earned.cooldowns, 0.0)
            world = World(args.seed, player=earned, level=level)
        controls = Controls(world)
        renderer.armory.cancel_destroy()
        renderer.armory.selected_uid = None
        renderer.armory.page = 0
        renderer.menu.notice = ""
        renderer.menu.has_character = has_character = True
        mode = menu_return = "playing"
        if store:
            store.save(world.player)

    def enter_or_restart():
        nonlocal world, controls, mode
        if world.state == "cleared":
            world.next_level()
            controls = Controls(world)
        elif world.state != "playing":
            begin_level(world.level)
        mode = "playing"

    def menu_action(action):
        nonlocal mode, help_return, running, has_character
        if action == "start":
            if has_character:
                mode = "confirm_new"
            else:
                # The initial level is already prepared, but has never ticked.
                mode = "playing"
                renderer.menu.has_character = has_character = True
                renderer.menu.notice = ""
        elif action == "confirm_new":
            begin_level(1, fresh=True)
        elif action == "cancel_new":
            mode = "title"
        elif action == "continue" and has_character:
            mode = "playing"
        elif action == "levels":
            renderer.menu.page = 0
            mode = "levels"
        elif action and action.startswith("level:"):
            level = int(action.split(":")[1])
            if 1 <= level <= world.player.unlocked_level:
                begin_level(level)
        elif action == "howto":
            help_return, mode = mode, "howto"
        elif action == "back":
            mode = help_return if mode == "howto" else "title"
        elif action == "resume":
            mode = "playing"
        elif action == "main_menu":
            controls.cancel()
            controls.right_up()
            world.stop()
            mode = "title"
        elif action == "previous":
            renderer.menu.page = max(0, renderer.menu.page - 1)
        elif action == "next":
            renderer.menu.page += 1
        elif action == "quit":
            running = False

    def open_armory(tab):
        nonlocal mode, menu_return
        if mode in FRONTEND_MODES:
            return
        controls.cancel()
        renderer.armory.cancel_destroy()
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
                        if mode == "howto":
                            mode = help_return
                        elif mode in ("levels", "confirm_new"):
                            mode = "title"
                        elif mode == "title":
                            running = False
                        elif mode in ("inventory", "shop"):
                            if not renderer.armory.cancel_destroy():
                                mode = menu_return
                        elif not controls.cancel():
                            mode = "playing" if mode == "paused" else "paused"
                    elif event.key == pygame.K_m:
                        audio.toggle()
                    elif mode in FRONTEND_MODES or mode == "paused":
                        if event.key in (pygame.K_UP, pygame.K_DOWN):
                            renderer.menu.move_focus(world, mode, -1 if event.key == pygame.K_UP else 1)
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            menu_action(renderer.menu.activate(world, mode))
                        elif mode == "paused" and event.key in (pygame.K_i, pygame.K_b):
                            open_armory("inventory" if event.key == pygame.K_i else "shop")
                    elif event.key in (pygame.K_i, pygame.K_b):
                        open_armory("inventory" if event.key == pygame.K_i else "shop")
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
                    if mode in FRONTEND_MODES or mode == "paused":
                        if event.button == 1:
                            menu_action(renderer.menu.click(world, mode, point))
                        continue
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
            if store and has_character and save_timer >= 0.5:
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
        if store and has_character:
            store.save(world.player)
            if store.error:
                print(store.error)
        pygame.quit()


if __name__ == "__main__":
    main()
