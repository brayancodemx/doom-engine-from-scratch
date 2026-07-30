"""Versión documental de la explicación del coste de un fotograma.

La pieza usa la captura real del juego como hilo visual y evita el lenguaje de
diapositivas: no hay cabecera fija, línea de progreso ni marca de agua. Las
anotaciones aparecen como lower thirds breves sobre la acción.

Duración: 18 segundos. Salida: 1280x720, 30 FPS, H.264.
"""

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys

import pygame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from animacion_base import (
    AMBER,
    BLACK,
    BONE,
    CYAN,
    GREEN,
    RED,
    RUST,
    STEEL,
    WHITE,
    HEIGHT,
    WIDTH,
    clamp,
    draw_scanlines,
    font,
    glow_circle,
    label,
    load_image,
    phase,
    pulse,
)
from map_data import MAP
from raycasting import cast_one_ray


ROOT = PROJECT_ROOT
DURATION = 18.0
EXPORT_FPS = 30
GAMEPLAY_ASSET = "assets/previews/gameplay_documental.png"
REAL_GAMEPLAY_ASSET = "assets/previews/gameplay_real_final.png"

_GAMEPLAY = None
_REAL_GAMEPLAY = None


def smoothstep(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def fade_value(t, start, end):
    return smoothstep((t - start) / max(0.001, end - start))


def alpha_layer(surface, color, alpha):
    layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    layer.fill((*color, int(clamp(alpha, 0, 255))))
    surface.blit(layer, (0, 0))


def gameplay_image():
    global _GAMEPLAY
    if _GAMEPLAY is None:
        source = load_image(GAMEPLAY_ASSET)
        _GAMEPLAY = pygame.transform.smoothscale(source, (WIDTH, HEIGHT))
    return _GAMEPLAY


def real_gameplay_image():
    """Fotograma generado por draw_playing() del juego, con HUD y minimapa."""
    global _REAL_GAMEPLAY
    if _REAL_GAMEPLAY is None:
        _REAL_GAMEPLAY = load_image(REAL_GAMEPLAY_ASSET)
    return _REAL_GAMEPLAY


def draw_gameplay(surface, darkness=0, zoom=1.0, pan=(0, 0)):
    """Pinta la captura real, con un ligero zoom documental opcional."""
    image = gameplay_image()
    if abs(zoom - 1.0) < 0.001 and pan == (0, 0):
        surface.blit(image, (0, 0))
    else:
        scaled_size = (int(WIDTH * zoom), int(HEIGHT * zoom))
        scaled = pygame.transform.smoothscale(image, scaled_size)
        x = (WIDTH - scaled_size[0]) // 2 + int(pan[0])
        y = (HEIGHT - scaled_size[1]) // 2 + int(pan[1])
        surface.blit(scaled, (x, y))
    if darkness:
        alpha_layer(surface, BLACK, darkness)


def lower_third(surface, eyebrow, text, color, progress, alpha=255):
    """Rótulo editorial de documental, no tarjeta de presentación."""
    x, y, w, h = 64, 575, 780, 88
    plate = pygame.Surface((w, h), pygame.SRCALPHA)
    plate.fill((5, 6, 6, int(190 * alpha / 255)))
    pygame.draw.rect(plate, (*color, int(210 * alpha / 255)), (0, 0, 6, h))
    plate.set_alpha(int(alpha))
    surface.blit(plate, (x, y))
    eyebrow_surface = font(17, bold=True).render(eyebrow, True, color)
    text_surface = font(28, bold=True).render(text, True, WHITE)
    eyebrow_surface.set_alpha(int(alpha))
    text_surface.set_alpha(int(alpha))
    surface.blit(eyebrow_surface, (x + 24, y + 13))
    surface.blit(text_surface, (x + 24, y + 40))
    pygame.draw.line(surface, (*color, int(120 * alpha / 255)),
                     (x + 24, y + h - 9),
                     (x + 24 + int((w - 48) * clamp(progress)), y + h - 9), 2)


def caption(surface, text, position, color=WHITE, size=20, alpha=255):
    rendered = font(size, bold=True).render(text, True, color)
    rendered.set_alpha(int(alpha))
    surface.blit(rendered, rendered.get_rect(center=position))


def draw_engine_background(surface, t):
    """Fondo propio de la animación; nunca reutiliza la captura del juego."""
    surface.fill((7, 8, 8))
    for y in range(0, HEIGHT, 18):
        shade = 12 + int(8 * (1 - y / HEIGHT))
        pygame.draw.line(surface, (shade, shade + 2, shade), (0, y), (WIDTH, y))
    vanishing = (640 + int(math.sin(t * 0.35) * 18), 390)
    for x in range(-300, 1600, 86):
        pygame.draw.line(surface, (25, 29, 26), vanishing, (x, HEIGHT), 1)
    draw_scanlines(surface, alpha=11)


def draw_opening(surface, t):
    draw_engine_background(surface, t)
    alpha_layer(surface, BLACK, 40 - 15 * pulse(t * 0.34))
    alpha = int(255 * min(1.0, fade_value(t, 0.05, 0.7)))
    caption(surface, "UN SOLO FOTOGRAMA", (640, 310), WHITE, 50, alpha)
    caption(surface, "y todo el motor trabaja antes del siguiente", (640, 365), BONE, 23, alpha)
    lower_third(surface, "LA PREGUNTA", "¿Qué ocurre en menos de 16 ms?", GREEN,
                fade_value(t, 0.1, 1.2), alpha)


def draw_world_map(surface, player, angle, rays=0, enemies=()):
    """Mapa real del juego: los rayos y enemigos comparten las mismas paredes."""
    cell = 26
    origin = (380, 92)
    for grid_y, row in enumerate(MAP):
        for grid_x, tile in enumerate(row):
            area = (origin[0] + grid_x * cell, origin[1] + grid_y * cell,
                    cell - 2, cell - 2)
            if tile == ".":
                pygame.draw.rect(surface, (18, 24, 21), area)
                pygame.draw.rect(surface, (55, 68, 57), area, 1)
            else:
                pygame.draw.rect(surface, (62, 34, 24), area)
                pygame.draw.rect(surface, RUST, area, 2)

    def project(point):
        return (int(origin[0] + point[0] * cell), int(origin[1] + point[1] * cell))

    player_point = project(player)
    for ray_index in range(rays):
        spread = math.radians(66)
        ray_angle = angle - spread / 2 + spread * ray_index / max(1, rays - 1)
        _, _, hit_x, hit_y, _ = cast_one_ray(*player, ray_angle)
        hit = project((hit_x, hit_y))
        pygame.draw.line(surface, CYAN, player_point, hit, 1)
        if ray_index % 7 == 0:
            pygame.draw.circle(surface, WHITE, hit, 2)

    for position, color in enemies:
        point = project(position)
        glow_circle(surface, color, point, 8, 16)
        pygame.draw.circle(surface, BONE, point, 3)
    glow_circle(surface, WHITE, player_point, 10, 18)
    pygame.draw.line(surface, WHITE, player_point,
                     (player_point[0] + math.cos(angle) * 32,
                      player_point[1] + math.sin(angle) * 32), 3)
    return project


def draw_rays(surface, t):
    local = t - 1.2
    draw_engine_background(surface, t)
    player = (8.5, 11.8)
    # La dirección gira y el abanico sale siempre del jugador: misma lógica
    # DDA del juego, no una línea decorativa independiente.
    angle = -1.55 + math.sin(local * 1.45) * 0.72
    reveal = fade_value(local, 0.15, 2.55)
    draw_world_map(surface, player, angle, int(88 * reveal))
    if local > 2.0:
        caption(surface, "640 rayos / frame", (1000, 210), CYAN, 34)
        caption(surface, "× 60 FPS", (1000, 258), AMBER, 28)
        caption(surface, "38.400 mediciones / segundo", (1000, 308), GREEN, 23)
    lower_third(surface, "RAYCASTING", "La cámara mide el mundo rayo por rayo",
                CYAN, fade_value(local, 0.1, 3.4), int(255 * min(1, local / 0.5)))


def point_on_route(route, amount):
    amount = clamp(amount)
    distance = amount * (len(route) - 1)
    index = min(len(route) - 2, int(distance))
    fraction = distance - index
    start, end = route[index], route[index + 1]
    return (start[0] + (end[0] - start[0]) * fraction,
            start[1] + (end[1] - start[1]) * fraction)


def draw_update(surface, t):
    local = t - 5.0
    draw_engine_background(surface, t)
    player = (8.5, 11.8)
    routes = (
        ((17.5, 3.5), (14.5, 3.5), (14.5, 8.5), (12.5, 8.5), (12.5, 11.5), (9.5, 11.5)),
        ((3.5, 16.5), (3.5, 11.5), (7.5, 11.5), (7.5, 12.5), (8.5, 12.5)),
        ((16.5, 16.5), (14.5, 16.5), (14.5, 15.5), (11.5, 15.5), (11.5, 11.5)),
    )
    progress = fade_value(local, 0.1, 3.2)
    enemies = [
        (point_on_route(route, (progress * 1.25 + index * 0.16) % 1.0), RED)
        for index, route in enumerate(routes)
    ]
    project = draw_world_map(surface, player, -1.15, enemies=enemies)
    for route in routes:
        points = [project(point) for point in route]
        pygame.draw.lines(surface, (147, 44, 27), False, points, 2)
    for index, (position, _) in enumerate(enemies):
        if index == 0:
            point = project(position)
            pygame.draw.circle(surface, AMBER, point, 28 + int(8 * pulse(t * 2)), 3)
    caption(surface, "UPDATE", (1000, 192), RED, 43)
    caption(surface, "rutas válidas: rodean los muros", (1000, 238), BONE, 18)
    lower_third(surface, "ESTADO DEL JUEGO", "Los enemigos cambian de posición antes de dibujar",
                RED, fade_value(local, 0.1, 3.6), 255)
    if local > 2.6:
        caption(surface, "la IA no es decoración: modifica el siguiente fotograma",
                (840, 540), WHITE, 18, int(255 * fade_value(local, 2.6, 3.4)))


def draw_pixel_reveal(surface, t):
    local = t - 8.8
    image = gameplay_image()
    alpha_layer(surface, BLACK, 255)
    columns, rows = 32, 18
    reveal = fade_value(local, 0.15, 3.35)
    visible_count = int(reveal * columns * rows)
    newest = min(columns * rows - 1, visible_count)
    for index in range(visible_count + 1):
        row, column = divmod(index, columns)
        source = pygame.Rect(column * WIDTH // columns,
                             row * HEIGHT // rows,
                             WIDTH // columns,
                             HEIGHT // rows)
        destination = (source.x, source.y)
        surface.blit(image, destination, source)

    # La retícula solo existe durante la explicación: se desvanece cuando el
    # frame ya está completo y deja la captura limpia para el cierre.
    grid_alpha = int(190 * (1.0 - fade_value(local, 2.8, 3.7)))
    grid = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for column in range(columns + 1):
        x = column * WIDTH // columns
        pygame.draw.line(grid, (52, 210, 224, grid_alpha), (x, 0), (x, HEIGHT), 1)
    for row in range(rows + 1):
        y = row * HEIGHT // rows
        pygame.draw.line(grid, (52, 210, 224, grid_alpha), (0, y), (WIDTH, y), 1)
    surface.blit(grid, (0, 0))
    if newest >= 0 and newest < columns * rows:
        row, column = divmod(newest, columns)
        cell = (column * WIDTH // columns, row * HEIGHT // rows,
                WIDTH // columns, HEIGHT // rows)
        flash = pygame.Surface((cell[2], cell[3]), pygame.SRCALPHA)
        flash.fill((*WHITE, int(120 * (1.0 - (visible_count % 3) / 3))))
        surface.blit(flash, cell[:2])
    label(surface, "921.600 píxeles", (66, 90), 38, AMBER)
    label(surface, "cada sector contiene una parte del mundo final", (68, 132), 19, BONE)
    lower_third(surface, "DRAW", "Cielo, suelo, paredes, sprites, HUD y partículas",
                AMBER, reveal, 255)
    caption(surface, f"sectores pintados: {visible_count:03d} / 576",
            (1080, 665), CYAN, 19)


def draw_pixels(surface, t):
    draw_pixel_reveal(surface, t)


def draw_budget(surface, t):
    local = t - 13.0
    draw_engine_background(surface, t)
    caption(surface, "60 FPS", (160, 92), CYAN, 32)
    caption(surface, "16,67 ms disponibles", (190, 132), BONE, 20)
    caption(surface, "UN FOTOGRAMA", (1085, 92), GREEN, 27)
    caption(surface, "debe volver a tiempo", (1085, 132), BONE, 18)

    x, y, w, h = 92, 470, 1096, 92
    plate = pygame.Surface((w, h), pygame.SRCALPHA)
    plate.fill((5, 6, 6, 214))
    surface.blit(plate, (x, y))
    segments = [
        ("rayos", 6.4, CYAN),
        ("colisiones + IA", 2.1, RED),
        ("pintar", 5.8, AMBER),
        ("HUD", 0.7, GREEN),
    ]
    reveal = fade_value(local, 0.1, 2.0)
    cursor = x + 26
    consumed = 0.0
    for name, milliseconds, color in segments:
        visible = min(milliseconds, max(0.0, reveal * 15.0 - consumed))
        segment_width = int(1020 * visible / 16.0)
        pygame.draw.rect(surface, color, (cursor, y + 29, segment_width, 30), border_radius=4)
        if segment_width > 92:
            caption(surface, name, (cursor + segment_width / 2, y + 44), BLACK, 16)
        cursor += int(1020 * milliseconds / 16.0)
        consumed += milliseconds
    limit = x + 26 + int(1020 * 16 / 16)
    pygame.draw.line(surface, RED, (limit, y + 13), (limit, y + 76), 4)
    caption(surface, "16 ms", (limit - 4, y + 84), RED, 17)
    caption(surface, "15,0 ms", (x + w - 122, y + 17), WHITE, 18)
    if local > 1.5:
        caption(surface, "si cruza esta marca, aparecen tirones", (640, 635), RED, 21)
    lower_third(surface, "FRAME BUDGET", "Todo sucede antes del siguiente fotograma",
                GREEN, reveal, 255)


def draw_final(surface, t):
    local = t - 15.7
    reveal = fade_value(local, 0.0, 0.9)
    surface.blit(real_gameplay_image(), (0, 0))
    alpha_layer(surface, BLACK, int(80 * (1 - reveal)))
    draw_scanlines(surface, alpha=10)
    if local > 0.75:
        caption(surface, "38.400 rayos / s", (180, 80), CYAN, 24,
                int(255 * fade_value(local, 0.75, 1.2)))
        caption(surface, "921.600 píxeles", (1080, 80), AMBER, 24,
                int(255 * fade_value(local, 0.75, 1.2)))
    if local > 1.35:
        lower_third(surface, "RESULTADO", "La ilusión está viva porque el frame llegó a tiempo",
                    GREEN, fade_value(local, 1.35, 2.3), 255)


def draw_scene(surface, t):
    if t < 1.2:
        draw_opening(surface, t)
    elif t < 5.0:
        draw_rays(surface, t)
    elif t < 8.8:
        draw_update(surface, t)
    elif t < 13.0:
        draw_pixels(surface, t)
    elif t < 15.7:
        draw_budget(surface, t)
    else:
        draw_final(surface, t)

    # Cortes muy breves, sin barra persistente ni título fijo.
    for cut in (1.2, 5.0, 8.8, 13.0, 15.7):
        distance = abs(t - cut)
        if distance < 0.09:
            alpha_layer(surface, BLACK, 255 * (1 - distance / 0.09))


def run_preview():
    from animacion_base import run
    run(draw_scene, DURATION, "Documental — el coste de un fotograma")


def export(output_path, ffmpeg_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path, "-y", "-loglevel", "error", "-f", "rawvideo",
        "-pixel_format", "rgb24", "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", str(EXPORT_FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    surface = pygame.Surface((WIDTH, HEIGHT))
    frame_count = int(DURATION * EXPORT_FPS)
    try:
        for frame_index in range(frame_count):
            draw_scene(surface, frame_index / EXPORT_FPS)
            process.stdin.write(pygame.image.tobytes(surface, "RGB"))
            if frame_index % EXPORT_FPS == 0 or frame_index + 1 == frame_count:
                percentage = (frame_index + 1) / frame_count * 100
                print(f"\r{output_path.name}: {percentage:5.1f}%", end="", flush=True)
        process.stdin.close()
        result = process.wait()
    except (BrokenPipeError, KeyboardInterrupt):
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.terminate()
        process.wait()
        raise
    print()
    if result != 0:
        raise RuntimeError(f"FFmpeg falló al crear {output_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Renderiza la versión documental del pipeline.")
    parser.add_argument("--vista", action="store_true", help="Abre la vista interactiva.")
    parser.add_argument("--salida", type=Path,
                        default=ROOT / "videos" / "rendimiento_38k_rayos_documental.mp4")
    args = parser.parse_args()
    if args.vista:
        run_preview()
        return
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise SystemExit("No se encontró FFmpeg en PATH.")
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    try:
        export(args.salida, ffmpeg_path)
        print(f"Video creado: {args.salida.resolve()}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
