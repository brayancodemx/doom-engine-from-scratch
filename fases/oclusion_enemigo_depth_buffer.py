"""Escena documental de 10 s: franjas del enemigo contra el depth buffer."""

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

from entities import Enemy, Player, normalized_angle
from main import Game
from raycasting import cast_all_rays
from renderer import (
    _doom_enemy_canvas,
    _enemy_ground_screen_y_clamped,
    _enemy_projected_size,
    _sprite_visible_spans,
)
from settings import (
    DOOM_AMBER,
    DOOM_BLACK,
    DOOM_BONE,
    DOOM_PHOSPHOR,
    DOOM_RED,
    DOOM_STEEL,
    FOV,
    HEIGHT,
    NUM_RAYS,
    RAY_WIDTH,
    WIDTH,
)


DURATION = 10.0
EXPORT_FPS = 30
PLAYER_X = 4.0
PLAYER_START_Y = 6.9
PLAYER_END_Y = 7.45
ENEMY_POSITION = (7.0, 7.0)
CAMERA_OFFSET = -0.08
ANALYSIS_PLAYER_Y = 7.0


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
    draw_analysis.title_font = pygame.font.SysFont(
        "consolas", 31, bold=True
    )
    draw_analysis.code_font = pygame.font.SysFont(
        "consolas", 21, bold=True
    )
    draw_analysis.small_font = pygame.font.SysFont(
        "consolas", 15, bold=True
    )


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 300
    game.weapon_style = "doom_rifle"
    game.player = Player(
        x=PLAYER_X,
        y=PLAYER_START_Y,
        angle=0.0,
        health=88,
    )
    demon = Enemy(
        ENEMY_POSITION[0],
        ENEMY_POSITION[1],
        health=3,
        variant=0,
    )
    demon.moving = False
    game.enemies = [demon]
    return game


def camera_angle(player_y):
    target = math.atan2(
        ENEMY_POSITION[1] - player_y,
        ENEMY_POSITION[0] - PLAYER_X,
    )
    return target + CAMERA_OFFSET


def set_game_state(game, time_value, ending=False, fixed=False):
    if fixed:
        player_y = ANALYSIS_PLAYER_Y
    elif ending:
        player_y = mix(
            PLAYER_START_Y,
            PLAYER_END_Y,
            phase(time_value, 7.15, 9.65),
        )
    else:
        player_y = mix(
            PLAYER_START_Y,
            PLAYER_END_Y,
            phase(time_value, 0.12, 2.05),
        )
    game.time = 19.0 + time_value
    game.player.x = PLAYER_X
    game.player.y = player_y
    game.player.angle = camera_angle(player_y)
    game.player.moving = not fixed
    game.player.walk_time = time_value * 4.5
    game.camera_bob_x = (
        math.sin(game.player.walk_time) * 0.5 if not fixed else 0.0
    )
    game.camera_bob_y = (
        math.sin(game.player.walk_time * 2.0) * 0.7 if not fixed else 0.0
    )
    demon = game.enemies[0]
    demon.x, demon.y = ENEMY_POSITION
    demon.moving = False
    demon.animation = 5.0 + time_value * 0.8
    demon.attack_timer = 0.0


def render_gameplay(game, time_value, ending=False, fixed=False):
    set_game_state(game, time_value, ending=ending, fixed=fixed)
    game.draw_playing()
    return game.frame.copy()


def render_base_without_enemy(game, time_value):
    set_game_state(game, time_value, fixed=True)
    demon = game.enemies[0]
    game.enemies = []
    game.draw_playing()
    frame = game.frame.copy()
    game.enemies = [demon]
    return frame


def enemy_projection(game):
    player = game.player
    demon = game.enemies[0]
    dx = demon.x - player.x
    dy = demon.y - player.y
    distance = math.hypot(dx, dy)
    relative = normalized_angle(math.atan2(dy, dx) - player.angle)
    corrected = distance * math.cos(relative)
    screen_x = WIDTH // 2 + int(relative / FOV * WIDTH)
    size = _enemy_projected_size(corrected)
    sprite = _doom_enemy_canvas(demon, size, neutral=False)

    distance_light = max(
        0.38, min(1.0, 1.0 - max(0.0, corrected - 2) / 17)
    )
    shade = int(255 * distance_light)
    sprite.fill(
        (shade, shade, shade), special_flags=pygame.BLEND_RGB_MULT
    )
    ground_y = _enemy_ground_screen_y_clamped(corrected, size)
    rect = sprite.get_rect(midbottom=(screen_x, ground_y))
    return sprite, rect, corrected


def visible_column_mask(rect, enemy_depth, depth_buffer):
    mask = [False] * rect.width
    spans = _sprite_visible_spans(
        rect.left, rect.width, enemy_depth, depth_buffer
    )
    for source_x, _, span_width in spans:
        for local_x in range(source_x, min(rect.width, source_x + span_width)):
            mask[local_x] = True
    return mask


def tint_strip(strip, color, alpha):
    tinted = strip.copy()
    tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    tinted.set_alpha(int(alpha))
    return tinted


def draw_depth_map(
    surface, rect, enemy_depth, depth_buffer, scan_x, mask, alpha
):
    alpha = clamp(alpha)
    if alpha <= 0:
        return
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    graph_bottom = max(84, rect.top - 22)
    graph_height = 54
    for local_x in range(0, rect.width, 2):
        screen_x = rect.left + local_x
        ray_index = max(
            0, min(NUM_RAYS - 1, screen_x // RAY_WIDTH)
        )
        wall_depth = depth_buffer[ray_index]
        normalized = clamp(1.0 - wall_depth / 12.0)
        bar_height = max(3, int(graph_height * normalized))
        color = DOOM_PHOSPHOR if mask[local_x] else DOOM_RED
        pygame.draw.line(
            layer,
            (*color, int(105 * alpha)),
            (screen_x, graph_bottom),
            (screen_x, graph_bottom - bar_height),
            2,
        )
    pygame.draw.line(
        layer,
        (*DOOM_AMBER, int(205 * alpha)),
        (rect.left, graph_bottom - int(graph_height * (1.0 - enemy_depth / 12))),
        (rect.right, graph_bottom - int(graph_height * (1.0 - enemy_depth / 12))),
        2,
    )
    current_screen_x = rect.left + scan_x
    pygame.draw.line(
        layer,
        (*DOOM_BONE, int(235 * alpha)),
        (current_screen_x, graph_bottom - graph_height - 5),
        (current_screen_x, graph_bottom + 6),
        2,
    )
    surface.blit(layer, (0, 0))
    draw_text(
        surface,
        draw_analysis.small_font,
        "DEPTH BUFFER",
        DOOM_BONE,
        (rect.centerx, graph_bottom - graph_height - 18),
        220 * alpha,
    )


def draw_analysis(surface, game, time_value):
    base = render_base_without_enemy(game, time_value)
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 42))
    base.blit(veil, (0, 0))
    surface.blit(base, (0, 0))

    rays, depth_buffer = cast_all_rays(game.player)
    sprite, rect, enemy_depth = enemy_projection(game)
    mask = visible_column_mask(rect, enemy_depth, depth_buffer)
    scan_progress = phase(time_value, 2.72, 5.85)
    scan_x = min(rect.width - 1, int(rect.width * scan_progress))
    ghost_fade = 1.0 - phase(time_value, 5.35, 6.55)

    # Silueta completa tenue: permite entender qué parte se está descartando.
    ghost = sprite.copy()
    ghost.set_alpha(int(48 * (1.0 - phase(time_value, 5.7, 6.45))))
    surface.blit(ghost, rect)

    for local_x in range(scan_x + 1):
        strip = sprite.subsurface((local_x, 0, 1, sprite.get_height()))
        destination = (rect.left + local_x, rect.top)
        if mask[local_x]:
            surface.blit(strip, destination)
        elif ghost_fade > 0:
            discarded = tint_strip(
                strip, (255, 48, 35), 155 * ghost_fade
            )
            surface.blit(discarded, destination)

    active_visible = mask[scan_x]
    scan_color = DOOM_PHOSPHOR if active_visible else DOOM_RED
    scan_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(
        scan_layer,
        (*scan_color, 240),
        (rect.left + scan_x, rect.top - 8),
        (rect.left + scan_x, rect.bottom + 8),
        3,
    )
    surface.blit(scan_layer, (0, 0))
    draw_depth_map(
        surface,
        rect,
        enemy_depth,
        depth_buffer,
        scan_x,
        mask,
        phase(time_value, 2.45, 2.88) *
        (1.0 - phase(time_value, 6.15, 6.6)),
    )

    screen_x = rect.left + scan_x
    ray_index = max(0, min(NUM_RAYS - 1, screen_x // RAY_WIDTH))
    wall_depth = depth_buffer[ray_index]
    decision_alpha = 245 * min(
        phase(time_value, 2.62, 2.95),
        1.0 - phase(time_value, 6.08, 6.52),
    )
    draw_text(
        surface,
        draw_analysis.code_font,
        f"ENEMIGO  {enemy_depth:0.1f}",
        DOOM_AMBER,
        (1060, 246),
        decision_alpha,
    )
    draw_text(
        surface,
        draw_analysis.code_font,
        f"PARED    {wall_depth:0.1f}",
        scan_color,
        (1060, 284),
        decision_alpha,
    )
    comparator = "PARED MAS LEJOS" if active_visible else "PARED MAS CERCA"
    decision = "DIBUJAR" if active_visible else "DESCARTAR"
    draw_text(
        surface,
        draw_analysis.small_font,
        comparator,
        DOOM_STEEL,
        (1060, 325),
        decision_alpha * 0.8,
    )
    draw_text(
        surface,
        draw_analysis.title_font,
        decision,
        scan_color,
        (1060, 366),
        decision_alpha,
    )

    title_alpha = 230 * min(
        phase(time_value, 2.35, 2.7),
        1.0 - phase(time_value, 4.4, 4.8),
    )
    draw_text(
        surface,
        draw_analysis.title_font,
        "FRANJA CONTRA PROFUNDIDAD",
        DOOM_BONE,
        (WIDTH // 2, 43),
        title_alpha,
    )


def draw_vignette(surface, strength=66):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(layer, (0, 0, 0, strength), (0, 0, WIDTH, 22))
    pygame.draw.rect(
        layer, (0, 0, 0, strength), (0, HEIGHT - 22, WIDTH, 22)
    )
    surface.blit(layer, (0, 0))


def draw_frame(surface, game, time_value):
    if time_value < 2.2:
        surface.blit(render_gameplay(game, time_value), (0, 0))
        draw_vignette(surface)
        return

    if time_value < 2.58:
        gameplay = render_gameplay(game, 2.15, fixed=True)
        analysis = pygame.Surface((WIDTH, HEIGHT))
        draw_analysis(analysis, game, time_value)
        transition = phase(time_value, 2.2, 2.58)
        surface.blit(gameplay, (0, 0))
        alpha_blit(surface, analysis, 255 * transition)
        draw_vignette(surface)
        return

    if time_value < 6.65:
        draw_analysis(surface, game, time_value)
        draw_vignette(surface)
        return

    if time_value < 7.12:
        analysis = pygame.Surface((WIDTH, HEIGHT))
        draw_analysis(analysis, game, 6.6)
        gameplay = render_gameplay(game, 7.1, ending=True)
        transition = phase(time_value, 6.65, 7.12)
        surface.blit(analysis, (0, 0))
        alpha_blit(surface, gameplay, 255 * transition)
        draw_vignette(surface)
        return

    surface.blit(render_gameplay(game, time_value, ending=True), (0, 0))
    draw_vignette(surface)


def visible_ratio(game):
    set_game_state(game, 0.0, fixed=True)
    _, depth_buffer = cast_all_rays(game.player)
    _, rect, enemy_depth = enemy_projection(game)
    mask = visible_column_mask(rect, enemy_depth, depth_buffer)
    return sum(mask) / max(1, len(mask))


def validate_scene():
    game = make_game()
    ratio = visible_ratio(game)
    if not 0.35 <= ratio <= 0.65:
        raise RuntimeError(
            f"La oclusión parcial no es suficientemente clara: {ratio:.2%}."
        )
    for player_y in (PLAYER_START_Y, ANALYSIS_PLAYER_Y, PLAYER_END_Y):
        if Player._touches_wall(PLAYER_X, player_y):
            raise RuntimeError(
                f"La cámara toca una pared en y={player_y:.2f}."
            )


def save_keyframes(output_dir, game):
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    for time_value in (1.1, 2.7, 3.4, 4.5, 5.7, 6.5, 7.5, 9.4):
        draw_frame(canvas, game, time_value)
        stamp = f"{time_value:04.1f}".replace(".", "_")
        pygame.image.save(
            canvas, output_dir / f"oclusion_depth_{stamp}s.png"
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
        description="Renderiza la oclusión del enemigo contra el depth buffer."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "oclusion_enemigo_depth_buffer_10s.mp4",
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
