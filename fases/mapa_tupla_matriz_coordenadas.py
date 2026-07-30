"""Escena documental de 19 s: tupla, matriz, MAP[y][x] y decimales."""

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


DURATION = 19.0
EXPORT_FPS = 30
CELL = 27
MAP_LEFT = (WIDTH - len(MAP[0]) * CELL) // 2
MAP_TOP = (HEIGHT - len(MAP) * CELL) // 2
TARGET_POSITION = (2.7, 4.2)
TARGET_CELL = (2, 4)

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


def mix(start, end, progress):
    return start + (end - start) * progress


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
    draw_matrix.title_font = pygame.font.SysFont(
        "consolas", 34, bold=True
    )
    draw_matrix.code_font = pygame.font.SysFont(
        "consolas", 25, bold=True
    )
    draw_matrix.small_font = pygame.font.SysFont(
        "consolas", 15, bold=True
    )
    draw_matrix.cell_font = pygame.font.SysFont(
        "consolas", 17, bold=True
    )


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 200
    game.weapon_style = "doom_rifle"
    game.player = Player(
        x=2.15,
        y=TARGET_POSITION[1],
        angle=0.12,
        health=100,
    )
    game.enemies = []
    return game


def gameplay_player_position(time_value, ending=False):
    if ending:
        return TARGET_POSITION
    progress = phase(time_value, 0.2, 2.25)
    return (
        mix(2.15, TARGET_POSITION[0], progress),
        TARGET_POSITION[1],
    )


def render_gameplay(game, time_value, ending=False):
    player_x, player_y = gameplay_player_position(time_value, ending)
    game.time = 17.0 + time_value
    game.player.x = player_x
    game.player.y = player_y
    game.player.angle = 0.12
    game.player.moving = not ending
    game.player.walk_time = time_value * 7.4
    game.camera_bob_x = (
        math.sin(game.player.walk_time) * 1.1 if not ending else 0.0
    )
    game.camera_bob_y = (
        math.sin(game.player.walk_time * 2.0) * 1.6
        if not ending else 0.0
    )
    game.draw_playing()
    return game.frame.copy()


def cell_rect(grid_x, grid_y):
    return pygame.Rect(
        MAP_LEFT + grid_x * CELL,
        MAP_TOP + grid_y * CELL,
        CELL - 1,
        CELL - 1,
    )


def world_point(x_value, y_value):
    return pygame.Vector2(
        MAP_LEFT + x_value * CELL,
        MAP_TOP + y_value * CELL,
    )


def draw_vignette(surface, strength=82):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(layer, (0, 0, 0, strength), (0, 0, WIDTH, 24))
    pygame.draw.rect(
        layer, (0, 0, 0, strength), (0, HEIGHT - 22, WIDTH, 22)
    )
    pygame.draw.rect(
        layer, (0, 0, 0, strength // 2), (0, 0, 20, HEIGHT)
    )
    pygame.draw.rect(
        layer, (0, 0, 0, strength // 2), (WIDTH - 20, 0, 20, HEIGHT)
    )
    surface.blit(layer, (0, 0))


def draw_tuple_rows(surface, time_value):
    row_progress = phase(time_value, 3.18, 5.25)
    visible_rows = row_progress * len(MAP)
    glyph_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for grid_y, row in enumerate(MAP):
        row_alpha = int(255 * clamp(visible_rows - grid_y))
        if row_alpha <= 0:
            continue
        for grid_x, tile in enumerate(row):
            rect = cell_rect(grid_x, grid_y)
            glyph = draw_matrix.cell_font.render(
                tile, True, (*DOOM_BONE, row_alpha)
            )
            glyph_layer.blit(glyph, glyph.get_rect(center=rect.center))
        comma = draw_matrix.cell_font.render(
            ",", True, (*DOOM_STEEL, row_alpha)
        )
        glyph_layer.blit(
            comma,
            comma.get_rect(
                center=(
                    MAP_LEFT + len(row) * CELL + 7,
                    MAP_TOP + grid_y * CELL + CELL // 2,
                )
            ),
        )

    bracket_alpha = int(230 * phase(time_value, 3.0, 3.5))
    draw_text(
        glyph_layer,
        draw_matrix.title_font,
        "(",
        DOOM_STEEL,
        (MAP_LEFT - 31, HEIGHT // 2),
        bracket_alpha,
    )
    draw_text(
        glyph_layer,
        draw_matrix.title_font,
        ")",
        DOOM_STEEL,
        (MAP_LEFT + len(MAP[0]) * CELL + 31, HEIGHT // 2),
        bracket_alpha,
    )
    surface.blit(glyph_layer, (0, 0))


def draw_colored_cells(surface, time_value):
    block_progress = phase(time_value, 4.85, 6.45)
    if block_progress <= 0:
        return
    blocks = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for grid_y, row in enumerate(MAP):
        for grid_x, tile in enumerate(row):
            rect = cell_rect(grid_x, grid_y)
            if tile == ".":
                fill = (18, 16, 14)
                border = (48, 42, 35)
            else:
                base = WALL_COLORS.get(tile, DOOM_STEEL)
                fill = tuple(int(channel * 0.38) for channel in base)
                border = base
            pygame.draw.rect(
                blocks, (*fill, int(255 * block_progress)), rect
            )
            pygame.draw.rect(
                blocks, (*border, int(225 * block_progress)), rect, 1
            )
    surface.blit(blocks, (0, 0))


def draw_indices(surface, alpha):
    alpha = int(210 * clamp(alpha))
    if alpha <= 0:
        return
    for grid_x in range(len(MAP[0])):
        text = draw_matrix.small_font.render(
            str(grid_x), True, DOOM_STEEL
        )
        text.set_alpha(alpha)
        surface.blit(
            text,
            text.get_rect(
                center=(
                    MAP_LEFT + grid_x * CELL + CELL // 2,
                    MAP_TOP - 18,
                )
            ),
        )
    for grid_y in range(len(MAP)):
        text = draw_matrix.small_font.render(
            str(grid_y), True, DOOM_STEEL
        )
        text.set_alpha(alpha)
        surface.blit(
            text,
            text.get_rect(
                center=(
                    MAP_LEFT - 22,
                    MAP_TOP + grid_y * CELL + CELL // 2,
                )
            ),
        )


def draw_query_selection(surface, time_value):
    query_progress = phase(time_value, 6.65, 9.1)
    if query_progress <= 0:
        return
    target_x, target_y = TARGET_CELL
    row_progress = phase(time_value, 6.72, 7.65)
    column_progress = phase(time_value, 7.55, 8.48)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    row_width = int(len(MAP[0]) * CELL * row_progress)
    pygame.draw.rect(
        layer,
        (*DOOM_PHOSPHOR, 44),
        (MAP_LEFT, MAP_TOP + target_y * CELL, row_width, CELL - 1),
    )
    column_height = int(len(MAP) * CELL * column_progress)
    pygame.draw.rect(
        layer,
        (*DOOM_AMBER, 47),
        (MAP_LEFT + target_x * CELL, MAP_TOP, CELL - 1, column_height),
    )
    if column_progress > 0.8:
        pulse = (math.sin(time_value * math.tau * 1.6) + 1.0) * 0.5
        pygame.draw.rect(
            layer,
            (*DOOM_AMBER, int(130 + pulse * 90)),
            cell_rect(target_x, target_y).inflate(12, 12),
            4,
            border_radius=4,
        )
    surface.blit(layer, (0, 0))

    syntax_alpha = 245 * min(
        phase(time_value, 6.55, 6.95),
        1.0 - phase(time_value, 8.75, 9.15),
    )
    draw_text(
        surface,
        draw_matrix.code_font,
        "MAP[y][x]",
        DOOM_BONE,
        (1090, 214),
        syntax_alpha,
    )
    draw_text(
        surface,
        draw_matrix.small_font,
        "PRIMERO FILA · DESPUES COLUMNA",
        DOOM_STEEL,
        (1090, 251),
        syntax_alpha * 0.85,
    )


def decimal_position(time_value):
    progress = phase(time_value, 9.12, 12.7)
    return (
        mix(1.35, TARGET_POSITION[0], progress),
        mix(2.35, TARGET_POSITION[1], progress),
    )


def draw_decimal_motion(surface, time_value):
    if time_value < 9.0:
        return
    x_value, y_value = decimal_position(time_value)
    point = world_point(x_value, y_value)
    trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    start = world_point(1.35, 2.35)
    pygame.draw.line(trail, (*DOOM_AMBER, 80), start, point, 4)
    steps = 18
    for index in range(steps):
        amount = index / max(1, steps - 1)
        trail_point = start.lerp(point, amount)
        pygame.draw.circle(
            trail,
            (*DOOM_AMBER, int(25 + amount * 115)),
            trail_point,
            2 + int(amount * 2),
        )
    surface.blit(trail, (0, 0))

    pygame.draw.circle(surface, DOOM_BLACK, point, 14)
    pygame.draw.circle(surface, DOOM_AMBER, point, 9)
    heading = point + pygame.Vector2(15, 2)
    pygame.draw.line(surface, DOOM_BONE, point, heading, 3)

    coordinate_alpha = 245 * min(
        phase(time_value, 9.0, 9.4),
        1.0 - phase(time_value, 13.1, 13.5),
    )
    draw_text(
        surface,
        draw_matrix.code_font,
        f"x = {x_value:.1f}",
        DOOM_AMBER,
        (1090, 335),
        coordinate_alpha,
    )
    draw_text(
        surface,
        draw_matrix.code_font,
        f"y = {y_value:.1f}",
        DOOM_AMBER,
        (1090, 374),
        coordinate_alpha,
    )


def draw_integer_conversion(surface, time_value):
    conversion = phase(time_value, 13.15, 15.75)
    if conversion <= 0:
        return
    target_rect = cell_rect(*TARGET_CELL)
    point = world_point(*TARGET_POSITION)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    guide_progress = phase(time_value, 13.15, 13.9)
    vertical = pygame.Vector2(point.x, target_rect.top)
    horizontal = pygame.Vector2(target_rect.left, point.y)
    pygame.draw.line(
        layer,
        (*DOOM_PHOSPHOR, int(220 * guide_progress)),
        point,
        point.lerp(vertical, guide_progress),
        2,
    )
    pygame.draw.line(
        layer,
        (*DOOM_PHOSPHOR, int(220 * guide_progress)),
        point,
        point.lerp(horizontal, guide_progress),
        2,
    )

    cell_progress = phase(time_value, 13.7, 14.35)
    pygame.draw.rect(
        layer,
        (*DOOM_PHOSPHOR, int(48 * cell_progress)),
        target_rect,
    )
    pygame.draw.rect(
        layer,
        (*DOOM_PHOSPHOR, int(255 * cell_progress)),
        target_rect.inflate(
            int(12 * (1.0 - cell_progress)),
            int(12 * (1.0 - cell_progress)),
        ),
        4,
    )
    surface.blit(layer, (0, 0))

    formula_alpha = 245 * min(
        phase(time_value, 13.35, 13.75),
        1.0 - phase(time_value, 15.55, 15.9),
    )
    draw_text(
        surface,
        draw_matrix.code_font,
        "int(2.7) = 2",
        DOOM_PHOSPHOR,
        (1080, 326),
        formula_alpha,
    )
    draw_text(
        surface,
        draw_matrix.code_font,
        "int(4.2) = 4",
        DOOM_PHOSPHOR,
        (1080, 369),
        formula_alpha,
    )
    draw_text(
        surface,
        draw_matrix.title_font,
        "(2, 4)",
        DOOM_BONE,
        (1080, 430),
        formula_alpha,
    )


def draw_result(surface, time_value):
    result_alpha = 255 * min(
        phase(time_value, 15.75, 16.2),
        1.0 - phase(time_value, 17.35, 17.75),
    )
    if result_alpha <= 0:
        return
    target_rect = cell_rect(*TARGET_CELL)
    pulse = (math.sin(time_value * math.tau * 1.5) + 1.0) * 0.5
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(
        overlay,
        (*DOOM_PHOSPHOR, int((45 + pulse * 30) * result_alpha / 255)),
        target_rect,
    )
    pygame.draw.rect(
        overlay,
        (*DOOM_PHOSPHOR, int(result_alpha)),
        target_rect,
        4,
    )
    surface.blit(overlay, (0, 0))
    draw_text(
        surface,
        draw_matrix.code_font,
        'MAP[4][2]  →  "."',
        DOOM_AMBER,
        (1070, 354),
        result_alpha,
    )
    draw_text(
        surface,
        draw_matrix.small_font,
        "CELDA LIBRE",
        DOOM_PHOSPHOR,
        (1070, 393),
        result_alpha * 0.9,
    )


def draw_matrix(surface, time_value):
    surface.fill((5, 5, 5))
    draw_tuple_rows(surface, time_value)
    draw_colored_cells(surface, time_value)
    draw_indices(surface, phase(time_value, 5.8, 6.65))
    draw_query_selection(surface, time_value)
    draw_decimal_motion(surface, time_value)
    draw_integer_conversion(surface, time_value)
    draw_result(surface, time_value)

    tuple_alpha = 230 * min(
        phase(time_value, 3.05, 3.45),
        1.0 - phase(time_value, 5.15, 5.55),
    )
    matrix_alpha = 235 * min(
        phase(time_value, 5.25, 5.7),
        1.0 - phase(time_value, 8.75, 9.15),
    )
    draw_text(
        surface,
        draw_matrix.title_font,
        "TUPLA",
        DOOM_STEEL,
        (WIDTH // 2, 45),
        tuple_alpha,
    )
    draw_text(
        surface,
        draw_matrix.title_font,
        "MATRIZ VISUAL",
        DOOM_AMBER,
        (WIDTH // 2, 45),
        matrix_alpha,
    )
    draw_vignette(surface, 54)


def draw_frame(surface, game, time_value):
    if time_value < 2.42:
        surface.blit(render_gameplay(game, time_value), (0, 0))
        draw_vignette(surface)
        return

    if time_value < 3.15:
        gameplay = render_gameplay(game, 2.4)
        matrix = pygame.Surface((WIDTH, HEIGHT))
        draw_matrix(matrix, time_value)
        transition = phase(time_value, 2.42, 3.15)
        surface.blit(gameplay, (0, 0))
        alpha_blit(surface, matrix, 255 * transition)
        return

    if time_value < 17.58:
        draw_matrix(surface, time_value)
        return

    matrix = pygame.Surface((WIDTH, HEIGHT))
    draw_matrix(matrix, 17.5)
    gameplay = render_gameplay(game, time_value, ending=True)
    transition = phase(time_value, 17.58, 18.28)
    surface.blit(matrix, (0, 0))
    alpha_blit(surface, gameplay, 255 * transition)
    if transition < 0.96:
        target_rect = cell_rect(*TARGET_CELL)
        outline = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(
            outline,
            (*DOOM_PHOSPHOR, int(180 * (1.0 - transition))),
            target_rect,
            3,
        )
        surface.blit(outline, (0, 0))
    draw_vignette(surface)


def validate_scene():
    if tile_at(*TARGET_POSITION) != ".":
        raise RuntimeError("La posición decimal elegida no es una celda libre.")
    if (int(TARGET_POSITION[0]), int(TARGET_POSITION[1])) != TARGET_CELL:
        raise RuntimeError("La conversión decimal no coincide con TARGET_CELL.")
    for sample in range(81):
        progress = sample / 80
        x_value = mix(2.15, TARGET_POSITION[0], progress)
        if Player._touches_wall(x_value, TARGET_POSITION[1]):
            raise RuntimeError(
                f"El recorrido de gameplay toca una pared en x={x_value:.2f}."
            )


def save_keyframes(output_dir, game):
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    for time_value in (
        1.2, 3.8, 5.7, 7.6, 10.2, 12.7, 14.2, 16.4, 18.0, 18.7
    ):
        draw_frame(canvas, game, time_value)
        stamp = f"{time_value:05.2f}".replace(".", "_")
        pygame.image.save(
            canvas, output_dir / f"mapa_matriz_{stamp}s.png"
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
        description="Renderiza la tupla MAP como matriz y consulta MAP[y][x]."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "mapa_tupla_matriz_19s.mp4",
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
