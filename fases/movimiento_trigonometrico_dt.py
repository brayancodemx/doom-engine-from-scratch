"""Escena documental de 15 s: coseno, seno, velocidad, dt y FPS."""

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
from map_data import MAP
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


DURATION = 15.0
EXPORT_FPS = 30
START = pygame.Vector2(2.4, 3.2)
END = pygame.Vector2(8.3, 4.9)
DISPLACEMENT = END - START
ANGLE = math.atan2(DISPLACEMENT.y, DISPLACEMENT.x)
TRAVEL_DISTANCE = DISPLACEMENT.length()

VIEW_X = 1
VIEW_Y = 0
VIEW_COLS = 10
VIEW_ROWS = 8
CELL = 70
GRID_LEFT = 245
GRID_TOP = 80

FPS_LANES = (
    (30, DOOM_RED, -0.24),
    (60, DOOM_AMBER, 0.0),
    (120, DOOM_PHOSPHOR, 0.24),
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


def draw_arrow(surface, color, start, end, width=3, alpha=255):
    alpha = int(clamp(alpha / 255.0) * 255)
    if alpha <= 0:
        return
    start = pygame.Vector2(start)
    end = pygame.Vector2(end)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(layer, (*color, alpha), start, end, width)
    direction = end - start
    if direction.length_squared() > 4:
        direction.normalize_ip()
        perpendicular = pygame.Vector2(-direction.y, direction.x)
        head = end - direction * 14
        pygame.draw.polygon(
            layer,
            (*color, alpha),
            (
                end,
                head + perpendicular * 7,
                head - perpendicular * 7,
            ),
        )
    surface.blit(layer, (0, 0))


def prepare_fonts():
    draw_vector_scene.title_font = pygame.font.SysFont(
        "consolas", 33, bold=True
    )
    draw_vector_scene.formula_font = pygame.font.SysFont(
        "consolas", 21, bold=True
    )
    draw_vector_scene.small_font = pygame.font.SysFont(
        "consolas", 15, bold=True
    )


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 300
    game.weapon_style = "doom_rifle"
    game.player = Player(
        x=START.x,
        y=START.y,
        angle=ANGLE,
        health=94,
    )
    game.enemies = []
    return game


def gameplay_progress(time_value, ending=False):
    if ending:
        return phase(time_value, 12.55, 14.72)
    return 0.32 * phase(time_value, 0.18, 2.08)


def render_gameplay(game, time_value, ending=False):
    progress = gameplay_progress(time_value, ending)
    position = START.lerp(END, progress)
    game.time = 26.0 + time_value
    game.player.x = position.x
    game.player.y = position.y
    game.player.angle = ANGLE
    game.player.moving = progress < 0.995
    game.player.walk_time = time_value * 7.6
    game.camera_bob_x = math.sin(game.player.walk_time) * 1.2
    game.camera_bob_y = math.sin(game.player.walk_time * 2.0) * 1.7
    game.draw_playing()
    return game.frame.copy()


def world_point(position):
    return pygame.Vector2(
        GRID_LEFT + (position.x - VIEW_X) * CELL,
        GRID_TOP + (position.y - VIEW_Y) * CELL,
    )


def draw_vignette(surface, strength=72):
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


def draw_local_map(surface, alpha=1.0):
    alpha = int(255 * clamp(alpha))
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for local_y in range(VIEW_ROWS):
        map_y = VIEW_Y + local_y
        for local_x in range(VIEW_COLS):
            map_x = VIEW_X + local_x
            tile = MAP[map_y][map_x]
            rect = pygame.Rect(
                GRID_LEFT + local_x * CELL,
                GRID_TOP + local_y * CELL,
                CELL - 1,
                CELL - 1,
            )
            if tile == ".":
                fill = (16, 14, 13)
                border = (45, 39, 33)
            else:
                fill = (59, 45, 35)
                border = DOOM_RUST
            pygame.draw.rect(layer, (*fill, alpha), rect)
            pygame.draw.rect(
                layer, (*border, int(alpha * 0.82)), rect, 1
            )
            if tile != ".":
                inset = rect.inflate(-14, -14)
                pygame.draw.rect(
                    layer, (21, 18, 16, int(alpha * 0.75)), inset
                )
                pygame.draw.line(
                    layer,
                    (*DOOM_STEEL, int(alpha * 0.65)),
                    inset.topleft,
                    inset.bottomright,
                    2,
                )
    surface.blit(layer, (0, 0))


def draw_axes(surface, alpha):
    alpha = int(215 * clamp(alpha))
    if alpha <= 0:
        return
    origin = world_point(pygame.Vector2(VIEW_X + 0.3, VIEW_Y + 7.35))
    draw_arrow(
        surface,
        DOOM_PHOSPHOR,
        origin,
        origin + pygame.Vector2(126, 0),
        2,
        alpha,
    )
    draw_arrow(
        surface,
        DOOM_RED,
        origin,
        origin - pygame.Vector2(0, 105),
        2,
        alpha,
    )
    draw_text(
        surface,
        draw_vector_scene.small_font,
        "x",
        DOOM_PHOSPHOR,
        (origin.x + 143, origin.y),
        alpha,
    )
    draw_text(
        surface,
        draw_vector_scene.small_font,
        "y",
        DOOM_RED,
        (origin.x, origin.y - 122),
        alpha,
    )


def draw_player_marker(surface, position, color, alpha=255, radius=10):
    alpha = int(clamp(alpha / 255.0) * 255)
    point = world_point(position)
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(layer, (0, 0, 0, alpha), point, radius + 5)
    pygame.draw.circle(layer, (*color, alpha), point, radius)
    heading = point + pygame.Vector2(
        math.cos(ANGLE), math.sin(ANGLE)
    ) * (radius + 12)
    pygame.draw.line(layer, (*DOOM_BONE, alpha), point, heading, 3)
    surface.blit(layer, (0, 0))


def draw_vector_decomposition(surface, time_value):
    progress = mix(0.32, 1.0, phase(time_value, 3.0, 6.45))
    start_px = world_point(START)
    end_position = START.lerp(END, progress)
    end_px = world_point(end_position)
    corner = pygame.Vector2(end_px.x, start_px.y)
    reveal = phase(time_value, 2.82, 3.25)

    trail = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(
        trail, (*DOOM_AMBER, int(65 * reveal)), start_px, end_px, 9
    )
    surface.blit(trail, (0, 0))
    draw_arrow(
        surface, DOOM_AMBER, start_px, end_px, 4, 245 * reveal
    )
    draw_arrow(
        surface, DOOM_PHOSPHOR, start_px, corner, 4, 235 * reveal
    )
    draw_arrow(
        surface, DOOM_RED, corner, end_px, 4, 235 * reveal
    )
    draw_player_marker(surface, end_position, DOOM_AMBER, 255 * reveal)

    arc_rect = pygame.Rect(
        int(start_px.x - 43), int(start_px.y - 43), 86, 86
    )
    arc_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.arc(
        arc_layer,
        (*DOOM_BONE, int(220 * reveal)),
        arc_rect,
        0,
        ANGLE,
        3,
    )
    surface.blit(arc_layer, (0, 0))
    draw_text(
        surface,
        draw_vector_scene.small_font,
        "θ",
        DOOM_BONE,
        (start_px.x + 51, start_px.y + 13),
        230 * reveal,
    )

    formula_alpha = 245 * min(
        phase(time_value, 3.42, 3.82),
        1.0 - phase(time_value, 6.45, 6.85),
    )
    draw_text(
        surface,
        draw_vector_scene.formula_font,
        "Δx = cos(θ) · velocidad · dt",
        DOOM_PHOSPHOR,
        (1082, 296),
        formula_alpha,
    )
    draw_text(
        surface,
        draw_vector_scene.formula_font,
        "Δy = sin(θ) · velocidad · dt",
        DOOM_RED,
        (1082, 343),
        formula_alpha,
    )
    draw_text(
        surface,
        draw_vector_scene.small_font,
        "HORIZONTAL",
        DOOM_PHOSPHOR,
        (1082, 384),
        formula_alpha * 0.8,
    )
    draw_text(
        surface,
        draw_vector_scene.small_font,
        "VERTICAL",
        DOOM_RED,
        (1082, 411),
        formula_alpha * 0.8,
    )


def lane_position(start, end, amount, offset):
    direction = end - start
    normal = pygame.Vector2(-direction.y, direction.x)
    if normal.length_squared() > 0:
        normal.normalize_ip()
    return start.lerp(end, amount) + normal * offset


def draw_fps_paths(surface, time_value):
    elapsed = clamp(time_value - 7.0, 0.0, 3.45)
    simulation_duration = 3.15
    progress = clamp(elapsed / simulation_duration)
    merge = phase(time_value, 10.35, 11.35)
    path_alpha = phase(time_value, 6.75, 7.12)

    for fps, color, base_offset in FPS_LANES:
        offset = base_offset * (1.0 - merge)
        completed_frames = min(
            int(elapsed * fps),
            int(simulation_duration * fps),
        )
        dot_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # Cada punto es un frame real. Más FPS produce pasos más pequeños.
        for frame_index in range(completed_frames + 1):
            amount = min(
                1.0,
                (frame_index / fps) / simulation_duration,
            )
            position = lane_position(START, END, amount, offset)
            point = world_point(position)
            radius = 2 if fps <= 60 else 1
            pygame.draw.circle(
                dot_layer,
                (*color, int((80 if fps == 30 else 58) * path_alpha)),
                point,
                radius,
            )
        surface.blit(dot_layer, (0, 0))

        marker_position = lane_position(
            START, END, min(progress, 1.0), offset
        )
        draw_player_marker(
            surface,
            marker_position,
            color,
            245 * path_alpha,
            radius=8,
        )
        label_point = world_point(
            lane_position(START, END, 0.08, base_offset)
        )
        draw_text(
            surface,
            draw_vector_scene.small_font,
            f"{fps} FPS",
            color,
            (label_point.x - 58, label_point.y - 10),
            225 * path_alpha * (1.0 - merge * 0.65),
        )

    dt_alpha = 240 * min(
        phase(time_value, 7.12, 7.48),
        1.0 - phase(time_value, 10.35, 10.8),
    )
    draw_text(
        surface,
        draw_vector_scene.formula_font,
        "dt = 1 / FPS",
        DOOM_BONE,
        (1085, 305),
        dt_alpha,
    )
    draw_text(
        surface,
        draw_vector_scene.small_font,
        "MAS FRAMES · PASOS MAS PEQUEÑOS",
        DOOM_STEEL,
        (1085, 345),
        dt_alpha * 0.85,
    )

    result_alpha = 245 * min(
        phase(time_value, 10.7, 11.1),
        1.0 - phase(time_value, 12.0, 12.42),
    )
    draw_text(
        surface,
        draw_vector_scene.title_font,
        "MISMO TIEMPO",
        DOOM_AMBER,
        (1080, 309),
        result_alpha,
    )
    draw_text(
        surface,
        draw_vector_scene.title_font,
        "MISMA DISTANCIA",
        DOOM_PHOSPHOR,
        (1080, 354),
        result_alpha,
    )


def draw_vector_scene(surface, time_value):
    surface.fill((5, 5, 5))
    draw_local_map(surface, phase(time_value, 2.38, 2.9))
    draw_axes(surface, phase(time_value, 2.65, 3.15))

    if time_value < 6.88:
        draw_vector_decomposition(surface, time_value)
    else:
        draw_fps_paths(surface, time_value)

    title_alpha = 230 * min(
        phase(time_value, 2.65, 3.05),
        1.0 - phase(time_value, 5.95, 6.42),
    )
    draw_text(
        surface,
        draw_vector_scene.title_font,
        "UN VECTOR · DOS EJES",
        DOOM_AMBER,
        (WIDTH // 2, 44),
        title_alpha,
    )
    draw_vignette(surface, 50)


def draw_frame(surface, game, time_value):
    if time_value < 2.25:
        surface.blit(render_gameplay(game, time_value), (0, 0))
        draw_vignette(surface)
        return

    if time_value < 2.9:
        gameplay = render_gameplay(game, 2.22)
        vector = pygame.Surface((WIDTH, HEIGHT))
        draw_vector_scene(vector, time_value)
        transition = phase(time_value, 2.25, 2.9)
        surface.blit(gameplay, (0, 0))
        alpha_blit(surface, vector, 255 * transition)
        return

    if time_value < 12.35:
        draw_vector_scene(surface, time_value)
        return

    vector = pygame.Surface((WIDTH, HEIGHT))
    draw_vector_scene(vector, 12.3)
    gameplay = render_gameplay(game, time_value, ending=True)
    transition = phase(time_value, 12.35, 12.88)
    surface.blit(vector, (0, 0))
    alpha_blit(surface, gameplay, 255 * transition)
    draw_vignette(surface)


def validate_path():
    for sample in range(161):
        position = START.lerp(END, sample / 160)
        if Player._touches_wall(position.x, position.y):
            raise RuntimeError(
                "La trayectoria trigonométrica toca una pared en "
                f"({position.x:.2f}, {position.y:.2f})."
            )


def save_keyframes(output_dir, game):
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    for time_value in (
        1.2, 3.2, 4.6, 6.3, 7.6, 8.8, 10.2, 11.3, 13.3, 14.7
    ):
        draw_frame(canvas, game, time_value)
        stamp = f"{time_value:05.2f}".replace(".", "_")
        pygame.image.save(
            canvas, output_dir / f"trigonometria_dt_{stamp}s.png"
        )


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    prepare_fonts()
    validate_path()
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
    validate_path()
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
        description="Renderiza coseno, seno, velocidad y delta time."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "movimiento_trigonometrico_dt_15s.mp4",
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
