"""Escena documental de 13 s: UPDATE congela el estado y DRAW crea el frame."""

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys

import pygame


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from entities import Enemy, Player
from main import Game
from map_data import MAP
from raycasting import cast_all_rays
from renderer import (
    draw_background,
    draw_ceiling_details,
    draw_crosshair,
    draw_enemies,
    draw_hud,
    draw_minimap,
    draw_walls,
    draw_weapon,
    draw_world_atmosphere,
)
from settings import (
    DOOM_AMBER,
    DOOM_BLACK,
    DOOM_BONE,
    DOOM_PHOSPHOR,
    DOOM_RED,
    DOOM_RUST,
    HEIGHT,
    WIDTH,
)


DURATION = 13.0
EXPORT_FPS = 30

PLAYER_START = (16.2, 12.4)
PLAYER_FINAL = (14.5, 12.4)
PLAYER_ANGLE = -math.pi / 2

ENEMY_STARTS = (
    (14.5, 7.7),
    (11.6, 8.6),
    (17.4, 8.8),
)
ENEMY_FINALS = (
    (14.5, 9.35),
    (12.25, 9.65),
    (16.65, 9.75),
)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def smoothstep(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def phase(time_value, start, end):
    if end <= start:
        return float(time_value >= end)
    return smoothstep((time_value - start) / (end - start))


def mix(a, b, progress):
    return a + (b - a) * progress


def mix_position(start, end, progress):
    return (
        mix(start[0], end[0], progress),
        mix(start[1], end[1], progress),
    )


def alpha_blit(destination, source, alpha, position=(0, 0)):
    if alpha <= 0:
        return
    if alpha >= 255:
        destination.blit(source, position)
        return
    faded = source.copy()
    faded.set_alpha(int(alpha))
    destination.blit(faded, position)


def draw_text_glow(surface, font, text, color, center, alpha=255):
    alpha = int(clamp(alpha / 255.0) * 255)
    if alpha <= 0:
        return
    shadow = font.render(text, True, (0, 0, 0))
    label = font.render(text, True, color)
    shadow.set_alpha(alpha)
    label.set_alpha(alpha)
    rect = label.get_rect(center=center)
    surface.blit(shadow, rect.move(4, 5))
    surface.blit(label, rect)


def ease_motion(time_value):
    """Progreso del cálculo: primero física, después IA y colisión."""
    return phase(time_value, 2.05, 4.65)


def state_at(time_value):
    progress = ease_motion(time_value)
    player = mix_position(PLAYER_START, PLAYER_FINAL, progress)
    enemies = [
        mix_position(start, end, progress)
        for start, end in zip(ENEMY_STARTS, ENEMY_FINALS)
    ]
    return player, enemies


def set_game_state(game, time_value, animated=False):
    player_position, enemy_positions = state_at(5.0)
    game.time = 18.0 + time_value
    game.player.x, game.player.y = player_position
    game.player.angle = PLAYER_ANGLE
    game.player.health = 86
    game.player.moving = animated
    game.player.walk_time = time_value * 2.4 if animated else 7.2
    game.camera_bob_x = math.sin(time_value * 2.0) * 0.8 if animated else 0.0
    game.camera_bob_y = math.sin(time_value * 4.0) * 1.2 if animated else 0.0
    for index, (enemy, position) in enumerate(
        zip(game.enemies, enemy_positions)
    ):
        enemy.x, enemy.y = position
        enemy.moving = animated
        enemy.animation = 12.0 + (
            time_value * (1.3 + index * 0.12) if animated else index * 0.7
        )
        enemy.attack_timer = 0.0


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 400
    game.weapon_style = "doom_shotgun"
    game.player = Player(
        x=PLAYER_FINAL[0],
        y=PLAYER_FINAL[1],
        angle=PLAYER_ANGLE,
        health=86,
    )
    game.enemies = [
        Enemy(x, y, health=3, variant=index % 3)
        for index, (x, y) in enumerate(ENEMY_FINALS)
    ]
    return game


def prepare_fonts():
    draw_update_map.title_font = pygame.font.SysFont(
        "consolas", 39, bold=True
    )
    draw_update_map.caption_font = pygame.font.SysFont(
        "consolas", 18, bold=True
    )
    draw_draw_stage.title_font = draw_update_map.title_font
    draw_draw_stage.caption_font = draw_update_map.caption_font


def render_gameplay(game, time_value, animated=True):
    set_game_state(game, time_value, animated=animated)
    game.draw_playing()
    return game.frame.copy()


def draw_cinematic_gameplay(surface, game, time_value):
    frame = render_gameplay(game, time_value, animated=True)
    surface.blit(frame, (0, 0))
    # Viñeta leve de lente; mantiene la toma como gameplay, no como tarjeta.
    vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (0, 0, 0, 72), (0, 0, WIDTH, 24))
    pygame.draw.rect(vignette, (0, 0, 0, 96), (0, HEIGHT - 20, WIDTH, 20))
    surface.blit(vignette, (0, 0))


def map_geometry():
    scale = 27
    map_width = len(MAP[0]) * scale
    map_height = len(MAP) * scale
    return scale, (WIDTH - map_width) // 2, (HEIGHT - map_height) // 2


def map_point(position):
    scale, offset_x, offset_y = map_geometry()
    return (
        int(offset_x + position[0] * scale),
        int(offset_y + position[1] * scale),
    )


def draw_map_grid(surface, reveal):
    scale, offset_x, offset_y = map_geometry()
    map_width = len(MAP[0]) * scale
    map_height = len(MAP) * scale
    surface.fill((5, 5, 5))

    frame = pygame.Surface((map_width, map_height), pygame.SRCALPHA)
    for row_index, row in enumerate(MAP):
        for column_index, tile in enumerate(row):
            rect = pygame.Rect(
                column_index * scale,
                row_index * scale,
                scale - 1,
                scale - 1,
            )
            if tile == ".":
                color = (17, 15, 13, 255)
                edge = (31, 27, 23, 210)
            else:
                color = (61, 46, 36, 255)
                edge = (126, 72, 39, 230)
            pygame.draw.rect(frame, color, rect)
            pygame.draw.rect(frame, edge, rect, 1)

    visible_height = int(map_height * reveal)
    if visible_height > 0:
        crop = pygame.Rect(0, 0, map_width, visible_height)
        surface.blit(frame, (offset_x, offset_y), crop)
        scan_y = offset_y + visible_height
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(
            glow,
            (*DOOM_AMBER, int(190 * (1.0 - reveal) + 35)),
            (offset_x, scan_y),
            (offset_x + map_width, scan_y),
            2,
        )
        surface.blit(glow, (0, 0))


def draw_path(surface, start, end, progress, color):
    start_px = map_point(start)
    end_px = map_point(end)
    current = (
        int(mix(start_px[0], end_px[0], progress)),
        int(mix(start_px[1], end_px[1], progress)),
    )
    pygame.draw.line(surface, (48, 39, 31), start_px, end_px, 7)
    pygame.draw.line(surface, color, start_px, current, 2)
    for step in range(5):
        marker_progress = step / 4
        marker = (
            int(mix(start_px[0], end_px[0], marker_progress)),
            int(mix(start_px[1], end_px[1], marker_progress)),
        )
        pygame.draw.circle(surface, color, marker, 2)


def draw_update_map(surface, time_value, map_reveal=1.0):
    draw_map_grid(surface, map_reveal)
    motion = ease_motion(time_value)
    player_position, enemy_positions = state_at(time_value)

    if map_reveal < 0.75:
        return

    trail_alpha = phase(time_value, 1.85, 2.3)
    paths = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_path(
        paths,
        PLAYER_START,
        PLAYER_FINAL,
        motion,
        (*DOOM_PHOSPHOR, int(215 * trail_alpha)),
    )
    for start, end in zip(ENEMY_STARTS, ENEMY_FINALS):
        draw_path(
            paths,
            start,
            end,
            motion,
            (*DOOM_RED, int(190 * trail_alpha)),
        )
    surface.blit(paths, (0, 0))

    # Posiciones anteriores: fantasmas de los datos antes de UPDATE.
    for start in ENEMY_STARTS:
        ghost = map_point(start)
        pygame.draw.circle(surface, (63, 27, 22), ghost, 9, 2)
    pygame.draw.circle(surface, (43, 63, 35), map_point(PLAYER_START), 8, 2)

    player_px = map_point(player_position)
    pygame.draw.circle(surface, (10, 10, 8), player_px, 12)
    pygame.draw.circle(surface, DOOM_PHOSPHOR, player_px, 9)
    facing = (
        player_px[0] + int(math.cos(PLAYER_ANGLE) * 17),
        player_px[1] + int(math.sin(PLAYER_ANGLE) * 17),
    )
    pygame.draw.line(surface, DOOM_BONE, player_px, facing, 4)

    for index, position in enumerate(enemy_positions):
        point = map_point(position)
        radius = 10 + index
        pygame.draw.circle(surface, (14, 8, 7), point, radius + 4)
        pygame.draw.circle(surface, DOOM_RED, point, radius)
        pygame.draw.circle(surface, DOOM_BONE, point, max(2, radius // 3))

    # La llegada de los monstruos queda resuelta y congelada como un pulso.
    collision = phase(time_value, 4.35, 4.72) * (
        1.0 - phase(time_value, 4.72, 5.15)
    )
    if collision > 0:
        pulse = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        radius = int(18 + collision * 34)
        pygame.draw.circle(
            pulse,
            (*DOOM_AMBER, int(220 * collision)),
            map_point(ENEMY_FINALS[0]),
            radius,
            3,
        )
        surface.blit(pulse, (0, 0))

    update_alpha = 255 * min(
        phase(time_value, 1.75, 2.12),
        1.0 - phase(time_value, 4.82, 5.18),
    )
    draw_text_glow(
        surface,
        draw_update_map.title_font,
        "UPDATE",
        DOOM_AMBER,
        (WIDTH // 2, 53),
        update_alpha,
    )
    caption_alpha = 210 * min(
        phase(time_value, 2.25, 2.55),
        1.0 - phase(time_value, 4.65, 5.0),
    )
    draw_text_glow(
        surface,
        draw_update_map.caption_font,
        "FISICA  ·  IA  ·  COLISIONES",
        DOOM_BONE,
        (WIDTH // 2, HEIGHT - 48),
        caption_alpha,
    )


def build_draw_layers(game, time_value):
    set_game_state(game, time_value, animated=False)
    rays, depth_buffer = cast_all_rays(game.player)

    background = pygame.Surface((WIDTH, HEIGHT))
    draw_background(background, game.time, game.player, depth_buffer)

    architecture = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_ceiling_details(
        architecture, game.player, game.time, depth_buffer
    )
    draw_walls(architecture, rays, game.time)

    monsters = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_enemies(
        monsters, game.enemies, game.player, depth_buffer, neutral=True
    )

    atmosphere = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_world_atmosphere(
        atmosphere, game.player, depth_buffer, game.time
    )

    interface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    draw_weapon(
        interface,
        game.player,
        0.0,
        0.0,
        game.weapon_style,
        full_view=False,
    )
    draw_crosshair(interface, 0.0, 0.0)
    draw_hud(
        interface,
        game.player,
        game.score,
        game.weapon_style,
        game.font,
        game.small_font,
        0.0,
    )
    draw_minimap(interface, game.player, game.enemies)
    return background, architecture, monsters, atmosphere, interface


def reveal_layer(surface, layer, progress):
    progress = clamp(progress)
    if progress <= 0:
        return
    if progress >= 1:
        surface.blit(layer, (0, 0))
        return
    # Barrido vertical con un borde luminoso breve, como un buffer que se llena.
    width = int(WIDTH * progress)
    crop = pygame.Rect(0, 0, width, HEIGHT)
    surface.blit(layer, (0, 0), crop)
    edge = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(
        edge,
        (*DOOM_AMBER, int(210 * (1.0 - progress))),
        (width, 0),
        (width, HEIGHT),
        2,
    )
    surface.blit(edge, (0, 0))


def draw_draw_stage(surface, game, time_value):
    layers = build_draw_layers(game, time_value)
    starts = (6.15, 7.03, 7.92, 8.82, 9.72)
    ends = (6.95, 7.83, 8.72, 9.62, 10.74)
    names = ("FONDO", "PAREDES", "MONSTRUOS", "ATMOSFERA", "ARMA + HUD")

    surface.fill(DOOM_BLACK)
    for layer, start, end in zip(layers, starts, ends):
        reveal_layer(surface, layer, phase(time_value, start, end))

    draw_alpha = 255 * min(
        phase(time_value, 5.92, 6.24),
        1.0 - phase(time_value, 10.55, 10.95),
    )
    draw_text_glow(
        surface,
        draw_draw_stage.title_font,
        "DRAW",
        DOOM_AMBER,
        (WIDTH // 2, 53),
        draw_alpha,
    )

    for name, start, end in zip(names, starts, ends):
        label_alpha = 225 * min(
            phase(time_value, start, start + 0.18),
            1.0 - phase(time_value, end - 0.08, end + 0.22),
        )
        if label_alpha > 0:
            draw_text_glow(
                surface,
                draw_draw_stage.caption_font,
                name,
                DOOM_BONE,
                (WIDTH // 2, HEIGHT - 122),
                label_alpha,
            )


def draw_snapshot(surface, time_value):
    """Congela el estado y lo convierte visualmente en el frame que leerá DRAW."""
    draw_update_map(surface, 5.0)
    shutter = phase(time_value, 5.05, 5.48)
    top_height = int(HEIGHT * 0.5 * shutter)
    pygame.draw.rect(surface, DOOM_BLACK, (0, 0, WIDTH, top_height))
    pygame.draw.rect(
        surface,
        DOOM_BLACK,
        (0, HEIGHT - top_height, WIDTH, top_height),
    )
    line_alpha = int(255 * (1.0 - shutter))
    if line_alpha > 0:
        line = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(
            line,
            (*DOOM_BONE, line_alpha),
            (0, top_height),
            (WIDTH, top_height),
            2,
        )
        pygame.draw.line(
            line,
            (*DOOM_BONE, line_alpha),
            (0, HEIGHT - top_height),
            (WIDTH, HEIGHT - top_height),
            2,
        )
        surface.blit(line, (0, 0))


def draw_frame(surface, game, time_value):
    if time_value < 1.15:
        draw_cinematic_gameplay(surface, game, time_value)
        return

    if time_value < 1.75:
        gameplay = render_gameplay(game, time_value, animated=True)
        update = pygame.Surface((WIDTH, HEIGHT))
        draw_update_map(update, time_value, phase(time_value, 1.15, 1.72))
        transition = phase(time_value, 1.15, 1.75)
        surface.blit(gameplay, (0, 0))
        alpha_blit(surface, update, 255 * transition)
        return

    if time_value < 5.05:
        draw_update_map(surface, time_value)
        return

    if time_value < 5.55:
        draw_snapshot(surface, time_value)
        return

    if time_value < 6.15:
        surface.fill(DOOM_BLACK)
        aperture = phase(time_value, 5.55, 6.15)
        glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(
            glow,
            (*DOOM_AMBER, int(95 * math.sin(aperture * math.pi))),
            (WIDTH // 2, HEIGHT // 2),
            int(40 + aperture * 520),
            4,
        )
        surface.blit(glow, (0, 0))
        return

    if time_value < 11.05:
        draw_draw_stage(surface, game, time_value)
        return

    final_frame = render_gameplay(game, time_value - 11.05, animated=True)
    if time_value < 11.35:
        built = pygame.Surface((WIDTH, HEIGHT))
        draw_draw_stage(built, game, 11.0)
        surface.blit(built, (0, 0))
        alpha_blit(
            surface,
            final_frame,
            255 * phase(time_value, 11.05, 11.35),
        )
    else:
        surface.blit(final_frame, (0, 0))


def validate_positions():
    positions = (
        PLAYER_START,
        PLAYER_FINAL,
        *ENEMY_STARTS,
        *ENEMY_FINALS,
    )
    for x, y in positions:
        if Player._touches_wall(x, y):
            raise RuntimeError(f"Posición inválida dentro de pared: {x}, {y}")


def save_keyframes(output_dir, game):
    output_dir.mkdir(parents=True, exist_ok=True)
    surface = pygame.Surface((WIDTH, HEIGHT))
    for time_value in (0.6, 3.25, 5.28, 6.65, 8.35, 10.25, 12.1):
        draw_frame(surface, game, time_value)
        stamp = f"{time_value:05.2f}".replace(".", "_")
        name = f"update_draw_{stamp}s.png"
        pygame.image.save(surface, output_dir / name)


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    prepare_fonts()
    validate_positions()
    game = make_game()
    screen = pygame.display.get_surface()
    surface = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    elapsed = 0.0
    running = True
    while running:
        elapsed += min(clock.tick(60) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        draw_frame(surface, game, elapsed % DURATION)
        screen.blit(surface, (0, 0))
        pygame.display.flip()
    pygame.quit()


def export(output_path, ffmpeg_path, keyframes_dir=None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        f"{WIDTH}x{HEIGHT}",
        "-framerate",
        str(EXPORT_FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    validate_positions()
    game = make_game()
    surface = pygame.Surface((WIDTH, HEIGHT))
    frame_count = int(DURATION * EXPORT_FPS)
    try:
        for frame_index in range(frame_count):
            draw_frame(surface, game, frame_index / EXPORT_FPS)
            process.stdin.write(pygame.image.tobytes(surface, "RGB"))
        process.stdin.close()
        result = process.wait()
    except (BrokenPipeError, KeyboardInterrupt):
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.terminate()
        process.wait()
        raise
    if result != 0:
        raise RuntimeError(f"FFmpeg falló al crear {output_path.name}")
    if keyframes_dir:
        save_keyframes(keyframes_dir, game)


def main():
    parser = argparse.ArgumentParser(
        description="Renderiza la separación cinematográfica de UPDATE y DRAW."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "update_draw_cinematico_13s.mp4",
    )
    parser.add_argument(
        "--fotogramas",
        type=Path,
        default=None,
        help="Carpeta opcional para guardar siete fotogramas de revisión.",
    )
    args = parser.parse_args()
    if args.vista:
        preview()
        return

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise SystemExit("No se encontró FFmpeg en PATH.")

    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    prepare_fonts()
    try:
        export(args.salida, ffmpeg_path, args.fotogramas)
        print(f"Video creado: {args.salida.resolve()}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
