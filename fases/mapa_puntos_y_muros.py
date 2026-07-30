"""Escena documental de 7 s: punto libre y cualquier número como muro."""

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

from entities import Player
from main import Game
from map_data import MAP, tile_at
from settings import (
    DOOM_AMBER,
    DOOM_BLACK,
    DOOM_BONE,
    DOOM_PHOSPHOR,
    DOOM_RED,
    DOOM_RUST,
    DOOM_STEEL,
    HEIGHT,
    WIDTH,
)


DURATION = 7.0
EXPORT_FPS = 30
CELL = 27
MAP_LEFT = (WIDTH - len(MAP[0]) * CELL) // 2
MAP_TOP = (HEIGHT - len(MAP) * CELL) // 2
PLAYER_POSITION = (3.45, 5.5)
PLAYER_ANGLE = 0.0
FREE_CELL = (3, 5)
WALL_CELL = (5, 5)

WALL_COLORS = {
    "1": DOOM_STEEL,
    "2": DOOM_RUST,
    "3": DOOM_PHOSPHOR,
    "4": DOOM_AMBER,
    "5": DOOM_BONE,
    "6": DOOM_RED,
}


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def smoothstep(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def phase(time_value, start, end):
    if end <= start:
        return float(time_value >= end)
    return smoothstep((time_value - start) / (end - start))


def alpha_blit(destination, source, alpha):
    if alpha <= 0:
        return
    if alpha >= 255:
        destination.blit(source, (0, 0))
        return
    faded = source.copy()
    faded.set_alpha(int(alpha))
    destination.blit(faded, (0, 0))


def draw_text(surface, font, text, color, center, alpha=255):
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


def prepare_fonts():
    draw_data_world.title_font = pygame.font.SysFont(
        "consolas", 32, bold=True
    )
    draw_data_world.code_font = pygame.font.SysFont(
        "consolas", 27, bold=True
    )
    draw_data_world.small_font = pygame.font.SysFont(
        "consolas", 16, bold=True
    )
    draw_data_world.cell_font = pygame.font.SysFont(
        "consolas", 17, bold=True
    )


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 200
    game.weapon_style = "doom_rifle"
    game.player = Player(
        x=PLAYER_POSITION[0],
        y=PLAYER_POSITION[1],
        angle=PLAYER_ANGLE,
        health=100,
    )
    game.enemies = []
    return game


def render_gameplay(game, time_value):
    game.time = 15.0 + time_value
    game.player.x, game.player.y = PLAYER_POSITION
    game.player.angle = PLAYER_ANGLE
    game.player.moving = False
    game.camera_bob_x = 0.0
    game.camera_bob_y = 0.0
    game.draw_playing()
    return game.frame.copy()


def cell_rect(grid_x, grid_y):
    return pygame.Rect(
        MAP_LEFT + grid_x * CELL,
        MAP_TOP + grid_y * CELL,
        CELL - 1,
        CELL - 1,
    )


def world_point(position):
    return pygame.Vector2(
        MAP_LEFT + position[0] * CELL,
        MAP_TOP + position[1] * CELL,
    )


def draw_vignette(surface, strength=72):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(layer, (0, 0, 0, strength), (0, 0, WIDTH, 22))
    pygame.draw.rect(
        layer, (0, 0, 0, strength), (0, HEIGHT - 22, WIDTH, 22)
    )
    pygame.draw.rect(
        layer, (0, 0, 0, strength // 2), (0, 0, 18, HEIGHT)
    )
    pygame.draw.rect(
        layer, (0, 0, 0, strength // 2), (WIDTH - 18, 0, 18, HEIGHT)
    )
    surface.blit(layer, (0, 0))


def draw_tuple_characters(surface, time_value):
    reveal = phase(time_value, 0.0, 1.05)
    visible_rows = reveal * len(MAP)
    fade = 1.0 - phase(time_value, 1.35, 3.65) * 0.72
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for grid_y, row in enumerate(MAP):
        row_alpha = int(255 * clamp(visible_rows - grid_y) * fade)
        if row_alpha <= 0:
            continue
        for grid_x, tile in enumerate(row):
            rect = cell_rect(grid_x, grid_y)
            color = DOOM_BONE if tile == "." else WALL_COLORS.get(
                tile, DOOM_STEEL
            )
            glyph = draw_data_world.cell_font.render(
                tile, True, color
            )
            glyph.set_alpha(row_alpha)
            layer.blit(glyph, glyph.get_rect(center=rect.center))
    surface.blit(layer, (0, 0))


def draw_free_floor(surface, time_value):
    progress = phase(time_value, 1.05, 2.45)
    if progress <= 0:
        return
    floor = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for grid_y, row in enumerate(MAP):
        for grid_x, tile in enumerate(row):
            if tile != ".":
                continue
            rect = cell_rect(grid_x, grid_y)
            pygame.draw.rect(
                floor, (20, 18, 15, int(255 * progress)), rect
            )
            pygame.draw.rect(
                floor, (55, 48, 39, int(210 * progress)), rect, 1
            )
    surface.blit(floor, (0, 0))

    label_alpha = 255 * min(
        phase(time_value, 1.12, 1.42),
        1.0 - phase(time_value, 2.35, 2.65),
    )
    draw_text(
        surface,
        draw_data_world.code_font,
        '"."  →  PASILLO LIBRE',
        DOOM_PHOSPHOR,
        (1080, 290),
        label_alpha,
    )


def draw_number_walls(surface, time_value):
    progress = phase(time_value, 2.35, 4.15)
    if progress <= 0:
        return
    walls = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    lift = int(7 * progress)
    for grid_y, row in enumerate(MAP):
        for grid_x, tile in enumerate(row):
            if tile == ".":
                continue
            rect = cell_rect(grid_x, grid_y)
            color = WALL_COLORS.get(tile, DOOM_STEEL)
            # Tres contornos desplazados dan volumen sin abandonar la matriz.
            for level in range(lift, 0, -2):
                raised = rect.move(-level, -level)
                pygame.draw.rect(
                    walls,
                    (*tuple(int(channel * 0.25) for channel in color),
                     int(190 * progress)),
                    raised,
                )
                pygame.draw.rect(
                    walls, (*color, int(100 * progress)), raised, 1
                )
            top = rect.move(-lift, -lift)
            pygame.draw.rect(
                walls,
                (*tuple(int(channel * 0.48) for channel in color),
                 int(255 * progress)),
                top,
            )
            pygame.draw.rect(
                walls, (*color, int(245 * progress)), top, 2
            )
            glyph = draw_data_world.cell_font.render(tile, True, DOOM_BONE)
            glyph.set_alpha(int(255 * progress))
            walls.blit(glyph, glyph.get_rect(center=top.center))
    surface.blit(walls, (0, 0))

    label_alpha = 255 * min(
        phase(time_value, 2.5, 2.85),
        1.0 - phase(time_value, 4.05, 4.38),
    )
    draw_text(
        surface,
        draw_data_world.code_font,
        "1–6  →  MURO",
        DOOM_RED,
        (1080, 350),
        label_alpha,
    )
    draw_text(
        surface,
        draw_data_world.small_font,
        "CUALQUIER NUMERO BLOQUEA",
        DOOM_STEEL,
        (1080, 388),
        label_alpha * 0.85,
    )


def draw_player_check(surface, time_value):
    progress = phase(time_value, 4.05, 5.55)
    if progress <= 0:
        return
    start = pygame.Vector2(2.4, 5.5)
    end = pygame.Vector2(*PLAYER_POSITION)
    position = start.lerp(end, progress)
    point = world_point(position)
    wall_center = pygame.Vector2(cell_rect(*WALL_CELL).center)
    free_rect = cell_rect(*FREE_CELL)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(
        layer, (*DOOM_PHOSPHOR, int(46 * progress)), free_rect
    )
    pygame.draw.rect(
        layer, (*DOOM_PHOSPHOR, int(220 * progress)), free_rect, 3
    )
    pygame.draw.line(
        layer, (*DOOM_AMBER, 110), world_point(start), point, 4
    )
    pygame.draw.line(
        layer, (*DOOM_RED, int(190 * progress)), point, wall_center, 2
    )
    pygame.draw.circle(layer, (0, 0, 0, 255), point, 14)
    pygame.draw.circle(layer, (*DOOM_AMBER, 255), point, 9)
    pygame.draw.line(
        layer, (*DOOM_BONE, 255), point, point + pygame.Vector2(18, 0), 3
    )
    pygame.draw.line(
        layer,
        (*DOOM_RED, int(245 * progress)),
        (wall_center.x - 9, wall_center.y - 9),
        (wall_center.x + 9, wall_center.y + 9),
        4,
    )
    pygame.draw.line(
        layer,
        (*DOOM_RED, int(245 * progress)),
        (wall_center.x + 9, wall_center.y - 9),
        (wall_center.x - 9, wall_center.y + 9),
        4,
    )
    surface.blit(layer, (0, 0))


def draw_data_world(surface, time_value):
    surface.fill((5, 5, 5))
    draw_tuple_characters(surface, time_value)
    draw_free_floor(surface, time_value)
    draw_number_walls(surface, time_value)
    draw_player_check(surface, time_value)
    title_alpha = 230 * min(
        phase(time_value, 0.1, 0.42),
        1.0 - phase(time_value, 1.1, 1.45),
    )
    draw_text(
        surface,
        draw_data_world.title_font,
        "TUPLA DEL MAPA",
        DOOM_AMBER,
        (WIDTH // 2, 46),
        title_alpha,
    )
    draw_vignette(surface, 50)


def draw_frame(surface, game, time_value):
    if time_value < 5.55:
        draw_data_world(surface, time_value)
        return

    data_world = pygame.Surface((WIDTH, HEIGHT))
    draw_data_world(data_world, 5.5)
    gameplay = render_gameplay(game, time_value)
    transition = phase(time_value, 5.55, 6.28)
    surface.blit(data_world, (0, 0))
    alpha_blit(surface, gameplay, 255 * transition)
    draw_vignette(surface)


def validate_scene():
    if tile_at(*PLAYER_POSITION) != ".":
        raise RuntimeError("El jugador no está sobre un pasillo libre.")
    if tile_at(*WALL_CELL) == ".":
        raise RuntimeError("La celda elegida no representa un muro.")
    if Player._touches_wall(*PLAYER_POSITION):
        raise RuntimeError("La posición de gameplay toca una pared.")


def save_keyframes(output_dir, game):
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    for time_value in (0.7, 1.7, 2.8, 3.8, 4.8, 5.7, 6.6):
        draw_frame(canvas, game, time_value)
        stamp = f"{time_value:04.1f}".replace(".", "_")
        pygame.image.save(
            canvas, output_dir / f"puntos_muros_{stamp}s.png"
        )


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    prepare_fonts()
    validate_scene()
    game = make_game()
    screen = pygame.display.get_surface()
    canvas = pygame.Surface((WIDTH, HEIGHT))
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
        draw_frame(canvas, game, elapsed % DURATION)
        screen.blit(canvas, (0, 0))
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
    validate_scene()
    game = make_game()
    canvas = pygame.Surface((WIDTH, HEIGHT))
    frame_count = int(DURATION * EXPORT_FPS)
    try:
        for frame_index in range(frame_count):
            draw_frame(canvas, game, frame_index / EXPORT_FPS)
            process.stdin.write(pygame.image.tobytes(canvas, "RGB"))
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
        description="Renderiza puntos libres y números como muros."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "mapa_puntos_y_muros_7s.mp4",
    )
    parser.add_argument(
        "--fotogramas",
        type=Path,
        default=None,
        help="Carpeta opcional para guardar fotogramas de revisión.",
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
