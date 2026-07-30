"""Escena documental de 15 s: la distancia determina la altura de cada columna."""

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
from raycasting import cast_all_rays
from renderer import (
    draw_background,
    draw_ceiling_details,
    draw_crosshair,
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
    DOOM_STEEL,
    HEIGHT,
    PROJECTION_DISTANCE,
    WIDTH,
)


DURATION = 20.0
ORIGINAL_DURATION = 15.0
EXPLANATION_DURATION = 18.0
EXPORT_FPS = 30
PLAYER_X = 14.5
PLAYER_FAR_Y = 12.4
PLAYER_NEAR_Y = 9.4
PLAYER_ANGLE = -math.pi / 2

SAMPLE_DISTANCES = (1.35, 2.25, 3.6, 5.4, 7.4)
SAMPLE_COLORS = (
    DOOM_RED,
    DOOM_AMBER,
    DOOM_BONE,
    DOOM_PHOSPHOR,
    DOOM_STEEL,
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


def prepare_fonts():
    draw_projection_space.title_font = pygame.font.SysFont(
        "consolas", 36, bold=True
    )
    draw_projection_space.formula_font = pygame.font.SysFont(
        "consolas", 30, bold=True
    )
    draw_projection_space.small_font = pygame.font.SysFont(
        "consolas", 17, bold=True
    )
    draw_column_field.title_font = draw_projection_space.title_font


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 500
    game.weapon_style = "doom_shotgun"
    game.player = Player(
        x=PLAYER_X,
        y=PLAYER_FAR_Y,
        angle=PLAYER_ANGLE,
        health=92,
    )
    game.enemies = []
    return game


def gameplay_position(time_value, closing=False):
    if closing:
        progress = phase(time_value, 12.55, 14.72)
        return mix(PLAYER_FAR_Y, PLAYER_NEAR_Y, progress)
    progress = phase(time_value, 0.15, 2.05)
    return mix(PLAYER_FAR_Y, 10.85, progress)


def blend_region(destination, source, rect, alpha):
    alpha = int(255 * clamp(alpha))
    if alpha <= 0:
        return
    region = source.subsurface(rect).copy()
    if alpha < 255:
        region.set_alpha(alpha)
    destination.blit(region, rect.topleft)


def render_gameplay(
    game,
    time_value,
    closing=False,
    ceiling_polish=0.0,
    floor_polish=0.0,
    animated=True,
    player_y=None,
):
    game.time = 21.0 + time_value
    game.player.x = PLAYER_X
    game.player.y = (
        gameplay_position(time_value, closing=closing)
        if player_y is None else player_y
    )
    game.player.angle = PLAYER_ANGLE
    game.player.moving = animated
    game.player.walk_time = time_value * 7.5
    game.camera_bob_x = (
        math.sin(game.player.walk_time) * 1.2 if animated else 0.0
    )
    game.camera_bob_y = (
        math.sin(game.player.walk_time * 2.0) * 1.8 if animated else 0.0
    )

    rays, depth_buffer = cast_all_rays(game.player)
    horizon = HEIGHT // 2
    world = pygame.Surface((WIDTH, HEIGHT))
    # Los primeros 18 s usan únicamente los colores de la referencia:
    # techo casi negro y suelo marrón, sin placas, baldosas ni perspectiva.
    world.fill((12, 10, 9))
    pygame.draw.rect(
        world, (91, 55, 34), (0, horizon, WIDTH, HEIGHT - horizon)
    )

    if ceiling_polish > 0 or floor_polish > 0:
        polished = pygame.Surface((WIDTH, HEIGHT))
        draw_background(polished, game.time, game.player, depth_buffer)
        draw_ceiling_details(
            polished, game.player, game.time, depth_buffer
        )
        blend_region(
            world,
            polished,
            pygame.Rect(0, 0, WIDTH, horizon),
            ceiling_polish,
        )
        blend_region(
            world,
            polished,
            pygame.Rect(0, horizon, WIDTH, HEIGHT - horizon),
            floor_polish,
        )

    draw_walls(world, rays, game.time)
    atmosphere_strength = min(ceiling_polish, floor_polish)
    if atmosphere_strength > 0:
        atmosphere = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_world_atmosphere(
            atmosphere, game.player, depth_buffer, game.time
        )
        atmosphere.set_alpha(int(255 * atmosphere_strength))
        world.blit(atmosphere, (0, 0))

    frame = world.copy()
    camera_x = int(game.camera_bob_x)
    camera_y = int(game.camera_bob_y)
    if camera_x or camera_y:
        shifted = pygame.Surface((WIDTH, HEIGHT))
        shifted.fill(DOOM_BLACK)
        shifted.blit(frame, (camera_x, camera_y))
        frame = shifted

    draw_weapon(
        frame,
        game.player,
        0.0,
        0.0,
        game.weapon_style,
        full_view=False,
    )
    draw_crosshair(frame, 0.0, 0.0)
    draw_hud(
        frame,
        game.player,
        game.score,
        game.weapon_style,
        game.font,
        game.small_font,
        0.0,
    )
    draw_minimap(frame, game.player, game.enemies)
    return frame


def draw_vignette(surface, strength=72):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.rect(layer, (0, 0, 0, strength), (0, 0, WIDTH, 24))
    pygame.draw.rect(
        layer, (0, 0, 0, strength + 22), (0, HEIGHT - 18, WIDTH, 18)
    )
    pygame.draw.rect(layer, (0, 0, 0, strength // 2), (0, 0, 20, HEIGHT))
    pygame.draw.rect(
        layer, (0, 0, 0, strength // 2), (WIDTH - 20, 0, 20, HEIGHT)
    )
    surface.blit(layer, (0, 0))


def projection_height(distance, maximum=530):
    raw_height = PROJECTION_DISTANCE / max(distance, 0.001)
    return max(8, min(maximum, int(raw_height)))


def sample_geometry(index, distance):
    origin = pygame.Vector2(116, 360)
    angles = (-0.43, -0.21, 0.0, 0.21, 0.43)
    angle = angles[index]
    visual_scale = 63
    endpoint = origin + pygame.Vector2(
        math.cos(angle), math.sin(angle)
    ) * distance * visual_scale
    column_x = 825 + index * 78
    return origin, endpoint, column_x


def draw_world_grid(surface, alpha):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    horizon = 360
    for index in range(1, 10):
        x = 75 + index * 70
        pygame.draw.line(
            layer, (105, 82, 61, int(alpha * 0.35)),
            (116, horizon), (x, HEIGHT - 74), 1,
        )
        pygame.draw.line(
            layer, (105, 82, 61, int(alpha * 0.22)),
            (116, horizon), (x, 74), 1,
        )
    for offset in range(42, 300, 42):
        pygame.draw.arc(
            layer,
            (114, 88, 64, int(alpha * 0.28)),
            (116 - offset * 2, horizon - offset, offset * 4, offset * 2),
            math.pi,
            math.tau,
            1,
        )
        pygame.draw.arc(
            layer,
            (114, 88, 64, int(alpha * 0.20)),
            (116 - offset * 2, horizon - offset, offset * 4, offset * 2),
            0,
            math.pi,
            1,
        )
    surface.blit(layer, (0, 0))


def textured_column(texture, width, height, texture_x):
    source_x = int(
        clamp(texture_x) * max(0, texture.get_width() - 5)
    )
    source = texture.subsurface(
        (source_x, 0, min(5, texture.get_width() - source_x),
         texture.get_height())
    )
    return pygame.transform.scale(source, (width, height))


def draw_measurement(surface, origin, endpoint, color, distance, alpha):
    alpha = int(255 * clamp(alpha))
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.line(layer, (*color, alpha), origin, endpoint, 3)
    direction = endpoint - origin
    if direction.length_squared() > 0:
        direction.scale_to_length(11)
        perpendicular = pygame.Vector2(-direction.y, direction.x)
        perpendicular.scale_to_length(5)
        pygame.draw.line(
            layer,
            (*color, alpha),
            origin - perpendicular,
            origin + perpendicular,
            2,
        )
        pygame.draw.line(
            layer,
            (*color, alpha),
            endpoint - perpendicular,
            endpoint + perpendicular,
            2,
        )
    middle = origin.lerp(endpoint, 0.52)
    badge = pygame.Surface((72, 25), pygame.SRCALPHA)
    badge.fill((7, 7, 7, int(alpha * 0.78)))
    text = draw_projection_space.small_font.render(
        f"{distance:.1f}", True, color
    )
    text.set_alpha(alpha)
    badge.blit(text, text.get_rect(center=(36, 12)))
    layer.blit(badge, badge.get_rect(center=(int(middle.x), int(middle.y - 15))))
    surface.blit(layer, (0, 0))


def draw_sample_column(
    surface, texture, column_x, distance, color, reveal, selected=False
):
    height = int(projection_height(distance) * reveal)
    if height <= 0:
        return
    width = 48 if selected else 42
    top = HEIGHT // 2 - height // 2
    strip = textured_column(texture, width, height, (column_x - 800) / 390)
    surface.blit(strip, (column_x - width // 2, top))
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, int(28 + distance * 8)))
    surface.blit(shade, (column_x - width // 2, top))
    pygame.draw.rect(
        surface,
        color,
        (column_x - width // 2, top, width, height),
        2 if selected else 1,
    )
    pygame.draw.circle(surface, color, (column_x, top), 4)
    pygame.draw.circle(surface, color, (column_x, top + height), 4)


def draw_projection_space(surface, time_value):
    surface.fill((5, 5, 5))
    grid_alpha = 255 * phase(time_value, 2.35, 2.9)
    draw_world_grid(surface, grid_alpha)

    # El plano de proyección forma parte del mismo espacio, sin panel ni marco.
    pygame.draw.line(surface, (50, 40, 33), (770, 70), (770, 650), 2)
    pygame.draw.line(
        surface, (54, 44, 35), (795, HEIGHT // 2), (1235, HEIGHT // 2), 1
    )
    origin = pygame.Vector2(116, 360)
    pygame.draw.circle(surface, DOOM_BLACK, origin, 15)
    pygame.draw.circle(surface, DOOM_AMBER, origin, 9)
    pygame.draw.line(surface, DOOM_BONE, origin, (144, 360), 3)

    for index, (distance, color) in enumerate(
        zip(SAMPLE_DISTANCES, SAMPLE_COLORS)
    ):
        start = 2.75 + index * 0.58
        ray_reveal = phase(time_value, start, start + 0.46)
        column_reveal = phase(time_value, start + 0.24, start + 0.72)
        ray_origin, endpoint, column_x = sample_geometry(index, distance)
        current = ray_origin.lerp(endpoint, ray_reveal)
        if ray_reveal > 0:
            draw_measurement(
                surface,
                ray_origin,
                current,
                color,
                distance,
                ray_reveal,
            )
            pygame.draw.circle(surface, color, current, 5)
        draw_sample_column(
            surface,
            draw_projection_space.wall_texture,
            column_x,
            distance,
            color,
            column_reveal,
        )

    # Una selección viva cambia de lejos a cerca y hace crecer la columna.
    focus = phase(time_value, 6.25, 6.65)
    if focus > 0:
        travel = phase(time_value, 6.62, 9.45)
        distance = mix(7.4, 1.35, travel)
        origin, endpoint, column_x = sample_geometry(2, distance)
        focus_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(
            focus_layer,
            (*DOOM_AMBER, int(235 * focus)),
            origin,
            endpoint,
            5,
        )
        pygame.draw.circle(
            focus_layer,
            (*DOOM_AMBER, int(245 * focus)),
            endpoint,
            10,
        )
        surface.blit(focus_layer, (0, 0))
        draw_sample_column(
            surface,
            draw_projection_space.wall_texture,
            column_x,
            distance,
            DOOM_AMBER,
            focus,
            selected=True,
        )
        draw_measurement(
            surface, origin, endpoint, DOOM_AMBER, distance, focus
        )

    near_alpha = 220 * min(
        phase(time_value, 6.9, 7.22),
        1.0 - phase(time_value, 9.15, 9.5),
    )
    if near_alpha > 0:
        draw_text(
            surface,
            draw_projection_space.small_font,
            "LEJOS  →  BAJA",
            DOOM_STEEL,
            (1050, 619),
            near_alpha,
        )
        draw_text(
            surface,
            draw_projection_space.small_font,
            "CERCA  →  ALTA",
            DOOM_AMBER,
            (1050, 92),
            near_alpha,
        )

    formula_alpha = 245 * min(
        phase(time_value, 7.15, 7.55),
        1.0 - phase(time_value, 9.28, 9.66),
    )
    draw_text(
        surface,
        draw_projection_space.formula_font,
        "ALTURA = PROYECCION / DISTANCIA",
        DOOM_BONE,
        (WIDTH // 2, 44),
        formula_alpha,
    )


def render_wall_field(game, time_value):
    game.time = 31.0 + time_value
    game.player.x = PLAYER_X
    game.player.y = 10.45
    game.player.angle = PLAYER_ANGLE
    rays, depth_buffer = cast_all_rays(game.player)

    background = pygame.Surface((WIDTH, HEIGHT))
    horizon = HEIGHT // 2
    background.fill((12, 10, 9))
    pygame.draw.rect(
        background,
        (91, 55, 34),
        (0, horizon, WIDTH, HEIGHT - horizon),
    )
    completed = background.copy()
    draw_walls(completed, rays, game.time)
    return background, completed


def draw_column_field(surface, game, time_value):
    background, completed = render_wall_field(game, time_value)
    surface.blit(background, (0, 0))
    progress = phase(time_value, 9.55, 12.35)
    # Las columnas nacen desde el centro y se propagan hacia ambos extremos.
    half_width = int(WIDTH * 0.5 * progress)
    left = WIDTH // 2 - half_width
    width = max(1, half_width * 2)
    crop = pygame.Rect(left, 0, width, HEIGHT)
    surface.blit(completed, (left, 0), crop)

    if progress < 1.0:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(
            overlay,
            (*DOOM_AMBER, int(230 * (1.0 - progress))),
            (left, 0),
            (left, HEIGHT),
            2,
        )
        pygame.draw.line(
            overlay,
            (*DOOM_AMBER, int(230 * (1.0 - progress))),
            (left + width, 0),
            (left + width, HEIGHT),
            2,
        )
        surface.blit(overlay, (0, 0))

    title_alpha = 245 * min(
        phase(time_value, 9.55, 9.95),
        1.0 - phase(time_value, 11.95, 12.35),
    )
    draw_text(
        surface,
        draw_column_field.title_font,
        "640 COLUMNAS · UN FOTOGRAMA",
        DOOM_AMBER,
        (WIDTH // 2, 54),
        title_alpha,
    )


def draw_original_sequence(surface, game, time_value):
    if time_value < 2.18:
        surface.blit(render_gameplay(game, time_value), (0, 0))
        draw_vignette(surface)
        return

    if time_value < 2.72:
        gameplay = render_gameplay(game, 2.1)
        projection = pygame.Surface((WIDTH, HEIGHT))
        draw_projection_space(projection, time_value)
        transition = phase(time_value, 2.18, 2.72)
        surface.blit(gameplay, (0, 0))
        alpha_blit(surface, projection, 255 * transition)
        return

    if time_value < 9.55:
        draw_projection_space(surface, time_value)
        draw_vignette(surface, 45)
        return

    if time_value < 12.55:
        draw_column_field(surface, game, time_value)
        draw_vignette(surface, 45)
        return

    gameplay = render_gameplay(game, time_value, closing=True)
    if time_value < 12.88:
        built = pygame.Surface((WIDTH, HEIGHT))
        draw_column_field(built, game, 12.4)
        surface.blit(built, (0, 0))
        alpha_blit(surface, gameplay, 255 * phase(time_value, 12.55, 12.88))
    else:
        surface.blit(gameplay, (0, 0))
    draw_vignette(surface)


def draw_frame(surface, game, time_value):
    if time_value < EXPLANATION_DURATION:
        original_time = (
            time_value * ORIGINAL_DURATION / EXPLANATION_DURATION
        )
        draw_original_sequence(surface, game, original_time)
        return

    # El encuadre no cambia: primero aparece el techo pulido y, unas décimas
    # después, el suelo recupera sus baldosas, profundidad y detalle final.
    ceiling_polish = phase(time_value, 18.22, 19.18)
    floor_polish = phase(time_value, 18.52, 19.65)
    surface.blit(
        render_gameplay(
            game,
            ORIGINAL_DURATION,
            closing=True,
            ceiling_polish=ceiling_polish,
            floor_polish=floor_polish,
            animated=True,
            player_y=PLAYER_NEAR_Y,
        ),
        (0, 0),
    )
    draw_vignette(surface)


def validate_path():
    for sample in range(121):
        y = mix(PLAYER_FAR_Y, PLAYER_NEAR_Y, sample / 120)
        if Player._touches_wall(PLAYER_X, y):
            raise RuntimeError(
                f"La aproximación toca una pared en ({PLAYER_X:.2f}, {y:.2f})"
            )


def save_keyframes(output_dir, game):
    output_dir.mkdir(parents=True, exist_ok=True)
    surface = pygame.Surface((WIDTH, HEIGHT))
    for time_value in (
        1.3, 4.1, 6.7, 8.7, 11.0, 13.0, 14.7, 17.3, 18.7, 19.9
    ):
        draw_frame(surface, game, time_value)
        stamp = f"{time_value:05.2f}".replace(".", "_")
        pygame.image.save(
            surface, output_dir / f"proyeccion_{stamp}s.png"
        )


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    prepare_fonts()
    draw_projection_space.wall_texture = pygame.image.load(
        ROOT / "assets" / "textures" / "walls" / "wall_1_steel.png"
    ).convert()
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
        description="Renderiza distancia inversa y altura de columnas."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "proyeccion_distancia_columnas_20s.mp4",
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
    draw_projection_space.wall_texture = pygame.image.load(
        ROOT / "assets" / "textures" / "walls" / "wall_1_steel.png"
    ).convert()
    try:
        export(args.salida, ffmpeg_path, args.fotogramas)
        print(f"Video creado: {args.salida.resolve()}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
