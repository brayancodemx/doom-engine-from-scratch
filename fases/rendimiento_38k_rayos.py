"""Animación cinematográfica: qué ocurre dentro de un fotograma.

Duración: 11 segundos.
Salida: 1280x720, 30 FPS, H.264.

La pieza visualiza la cadena completa del motor:
640 rayos x 60 FPS = 38.400 rayos por segundo -> colisiones/IA -> pintura
de 921.600 píxeles -> todo dentro del presupuesto de un fotograma.
"""

import argparse
import math
from pathlib import Path
import shutil
import subprocess

import pygame

from animacion_base import (
    AMBER,
    BLACK,
    BONE,
    CYAN,
    DARK,
    GREEN,
    RED,
    RUST,
    STEEL,
    WHITE,
    HEIGHT,
    WIDTH,
    clamp,
    draw_scanlines,
    draw_watermark,
    font,
    glow_circle,
    label,
    load_image,
    phase,
    pulse,
)


ROOT = Path(__file__).resolve().parents[1]
DURATION = 11.0
EXPORT_FPS = 30


def rect_alpha(surface, color, rect, alpha, radius=0):
    layer = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    layer.fill((*color, alpha))
    surface.blit(layer, (rect[0], rect[1]))
    if radius:
        pygame.draw.rect(surface, color, rect, 1, border_radius=radius)


def draw_background(surface, t):
    surface.fill(BLACK)
    for y in range(0, HEIGHT, 12):
        glow = int(8 + 6 * (1.0 - y / HEIGHT))
        pygame.draw.line(surface, (glow + 5, glow + 4, glow + 3),
                         (0, y), (WIDTH, y), 1)
    # Perspectiva sutil de laboratorio: mantiene la estética de gameplay y da
    # profundidad sin competir con el dato principal.
    vanishing = (640 + int(math.sin(t * 0.7) * 10), 370)
    for x in range(-400, 1801, 100):
        pygame.draw.line(surface, (23, 25, 23), vanishing, (x, HEIGHT), 1)
    for y in (450, 490, 535, 590, 660):
        pygame.draw.line(surface, (23, 25, 23),
                         vanishing, (0, y), 1)
        pygame.draw.line(surface, (23, 25, 23),
                         vanishing, (WIDTH, y), 1)
    pygame.draw.rect(surface, BLACK, (0, 0, WIDTH, 23))
    pygame.draw.rect(surface, BLACK, (0, HEIGHT - 23, WIDTH, 23))
    draw_scanlines(surface, alpha=14)


def scene_header(surface, kicker, title, color, progress):
    label(surface, "NEON BREACH // FRAME PIPELINE", (74, 44), 19, BONE)
    label(surface, kicker, (1115, 44), 18, color, center=True)
    label(surface, title, (74, 78), 35, color)
    pygame.draw.line(surface, (70, 54, 40), (74, 126), (1206, 126), 2)
    pygame.draw.line(surface, color, (74, 126),
                     (74 + 1132 * clamp(progress), 126), 4)


def draw_metric(surface, value, suffix, position, color, size=86):
    label(surface, value, position, size, color, center=True)
    label(surface, suffix, (position[0], position[1] + size * 0.55),
          22, BONE, center=True)


def draw_corridor(surface, t, ray_amount=1.0, dim=0):
    """Corredor en primera persona con un abanico de rayos DDA."""
    horizon = 365
    vanishing = (640, horizon)
    pygame.draw.polygon(surface, (18, 18, 17),
                        ((160, 170), (1120, 170), (900, 650), (380, 650)))
    pygame.draw.polygon(surface, (35, 30, 25),
                        ((160, 170), vanishing, (380, 650), (100, 650)))
    pygame.draw.polygon(surface, (35, 30, 25),
                        (vanishing, (1120, 170), (1180, 650), (900, 650)))
    for depth in range(1, 8):
        amount = depth / 8
        left = (640 - 480 * amount, horizon - 195 * amount)
        right = (640 + 480 * amount, horizon - 195 * amount)
        pygame.draw.line(surface, (60, 48, 38), left, right, 2)
    for x in (160, 280, 1000, 1120):
        pygame.draw.line(surface, (76, 54, 38), vanishing, (x, 170), 3)

    ray_count = 72
    spread = math.radians(68)
    for index in range(ray_count):
        normalized = index / (ray_count - 1)
        if normalized > ray_amount:
            continue
        angle = -spread / 2 + spread * normalized
        length = 510 + 28 * math.sin(t * 8 + index * 0.7)
        end = (640 + math.cos(angle) * length,
               horizon + math.sin(angle) * length * 0.58)
        color = AMBER if index == ray_count // 2 else CYAN
        width = 3 if index == ray_count // 2 else 1
        pygame.draw.line(surface, color, vanishing, end, width)
        if index % 5 == 0:
            pygame.draw.circle(surface, WHITE, (int(end[0]), int(end[1])), 3)
    glow_circle(surface, WHITE, vanishing, 8, 18)
    if dim:
        rect_alpha(surface, BLACK, (0, 0, WIDTH, HEIGHT), dim)


def draw_rays_scene(surface, t):
    local = t - 0.8
    reveal = phase(local, 0.0, 0.9)
    scene_header(surface, "01 // RAYCASTING", "CADA FOTOGRAMA EMPIEZA CON UNA PREGUNTA",
                 CYAN, phase(local, 0.0, 2.8))
    draw_corridor(surface, t, ray_amount=clamp(local / 2.0))
    rect_alpha(surface, BLACK, (70, 155, 330, 465), 184)
    label(surface, "RAYCASTING DDA", (104, 188), 25, CYAN)
    label(surface, "La cámara mide el mundo", (104, 226), 18, BONE)
    label(surface, "rayo por rayo", (104, 252), 18, BONE)
    draw_metric(surface, "640", "rayos / frame", (225, 350), CYAN, 72)
    label(surface, "×", (225, 435), 35, AMBER, center=True)
    draw_metric(surface, "60", "FPS", (225, 500), AMBER, 72)
    label(surface, "=", (425, 350), 42, WHITE, center=True)
    count = int(38400 * clamp(local / 1.8))
    draw_metric(surface, f"{count:,}".replace(",", "."), "RAYOS / SEGUNDO",
                (915, 230), GREEN, 88)
    label(surface, "más de treinta y ocho mil mediciones", (915, 330), 21,
          BONE, center=True)
    if local > 1.8:
        label(surface, "el abanico ya cubre toda la pantalla", (915, 370), 18,
              CYAN, center=True)
    if reveal < 0.1:
        rect_alpha(surface, BLACK, (0, 0, WIDTH, HEIGHT), 255)


def draw_map(surface, t):
    x0, y0, cell = 115, 190, 43
    rows = [
        "1111111111111111",
        "1..............1",
        "1..1111........1",
        "1..1..1....22..1",
        "1..1..1........1",
        "1.....1111.....1",
        "1...........3..1",
        "1111111111111111",
    ]
    for y, row in enumerate(rows):
        for x, tile in enumerate(row):
            area = (x0 + x * cell, y0 + y * cell, cell - 2, cell - 2)
            if tile == ".":
                pygame.draw.rect(surface, (24, 27, 24), area)
                pygame.draw.rect(surface, (50, 54, 46), area, 1)
            else:
                color = {"1": RUST, "2": RED, "3": AMBER}.get(tile, STEEL)
                pygame.draw.rect(surface, tuple(int(c * 0.45) for c in color), area)
                pygame.draw.rect(surface, color, area, 2)

    player = (x0 + 2.7 * cell, y0 + 5.0 * cell)
    enemies = [
        (x0 + 11.8 * cell, y0 + 2.2 * cell),
        (x0 + 12.3 * cell, y0 + 5.8 * cell),
        (x0 + 8.5 * cell, y0 + 1.6 * cell),
    ]
    pygame.draw.circle(surface, CYAN, (int(player[0]), int(player[1])), 9)
    pygame.draw.circle(surface, WHITE, (int(player[0]), int(player[1])), 3)
    for index, enemy in enumerate(enemies):
        wobble = math.sin(t * 4 + index) * 5
        enemy_pos = (int(enemy[0] + wobble), int(enemy[1]))
        pygame.draw.line(surface, RED, (int(player[0]), int(player[1])), enemy_pos, 2)
        glow_circle(surface, RED, enemy_pos, 7, 10)
        pygame.draw.circle(surface, BONE, enemy_pos, 3)
        radius = 24 + int(10 * pulse(t * 1.2 + index))
        pygame.draw.circle(surface, AMBER, enemy_pos, radius, 2)
    label(surface, "PLAYER", (int(player[0]), int(player[1] + 28)), 16, CYAN, center=True)


def draw_collision_scene(surface, t):
    local = t - 3.55
    scene_header(surface, "02 // GAMEPLAY STATE", "COLISIONES. ENEMIGOS. DECISIONES.",
                 RED, phase(local, 0.0, 1.65))
    rect_alpha(surface, BLACK, (78, 157, 760, 452), 154)
    draw_map(surface, t)
    label(surface, "posición + colisión + IA", (150, 555), 22, RED)
    label(surface, "cada entidad cambia antes de dibujar", (150, 584), 17, BONE)
    panel = (874, 190, 290, 340)
    pygame.draw.rect(surface, (13, 13, 12), panel, border_radius=12)
    pygame.draw.rect(surface, (78, 42, 33), panel, 2, border_radius=12)
    label(surface, "UPDATE()", (900, 218), 26, RED)
    steps = [
        ("01", "leer input", CYAN),
        ("02", "mover jugador", AMBER),
        ("03", "resolver muros", GREEN),
        ("04", "mover enemigos", RED),
        ("05", "guardar estado", BONE),
    ]
    for index, (number, text, color) in enumerate(steps):
        y = 270 + index * 46
        pygame.draw.circle(surface, color, (915, y + 4), 7)
        label(surface, number, (938, y - 8), 17, color)
        label(surface, text, (982, y - 8), 17, WHITE)
    label(surface, "sin estado correcto, no hay mundo que pintar", (1019, 566),
          16, BONE, center=True)
    if local > 1.2:
        label(surface, "COLISIÓN RESUELTA", (1019, 600), 17, GREEN, center=True)


def draw_pixel_scene(surface, t):
    local = t - 5.55
    scene_header(surface, "03 // RENDER PASS", "DE DATOS A MILLONES DE PÍXELES",
                 AMBER, phase(local, 0.0, 2.1))
    view = (92, 175, 760, 405)
    pygame.draw.rect(surface, (8, 9, 9), view, border_radius=10)
    pygame.draw.rect(surface, AMBER, view, 2, border_radius=10)
    columns, rows = 38, 20
    fill_progress = phase(local, 0.0, 1.85)
    for row in range(rows):
        for column in range(columns):
            index = row * columns + column
            visible = index / (columns * rows - 1) <= fill_progress
            if not visible:
                continue
            horizon = rows * 0.48
            depth = abs(row - horizon) / horizon
            wave = math.sin(column * 0.42 + t * 4) * 8
            base = int(35 + 80 * (1.0 - depth) + wave)
            color = (max(22, base), max(20, int(base * 0.62)), max(16, int(base * 0.42)))
            if row < rows * 0.32:
                color = (max(15, int(base * 0.48)), max(18, int(base * 0.62)), max(20, int(base * 0.75)))
            cell_w = view[2] // columns
            cell_h = view[3] // rows
            pygame.draw.rect(surface, color,
                             (view[0] + column * cell_w,
                              view[1] + row * cell_h,
                              cell_w - 1, cell_h - 1))
    if fill_progress > 0.2:
        cx, cy = view[0] + view[2] // 2, view[1] + view[3] // 2
        pygame.draw.circle(surface, WHITE, (cx, cy), 5)
        for index in range(12):
            angle = index * math.tau / 12
            pygame.draw.line(surface, CYAN, (cx, cy),
                             (cx + math.cos(angle) * 120,
                              cy + math.sin(angle) * 75), 1)
    panel = (890, 175, 300, 405)
    pygame.draw.rect(surface, (13, 13, 12), panel, border_radius=12)
    pygame.draw.rect(surface, (98, 65, 37), panel, 2, border_radius=12)
    label(surface, "DRAW()", (918, 207), 28, AMBER)
    draw_metric(surface, "921.600", "PÍXELES / FRAME", (1040, 315), AMBER, 54)
    label(surface, "1280 × 720", (1040, 395), 24, WHITE, center=True)
    label(surface, "cielo · suelo · paredes", (1040, 454), 18, BONE, center=True)
    label(surface, "sprites · HUD · partículas", (1040, 483), 18, BONE, center=True)
    pygame.draw.rect(surface, (52, 41, 30), (924, 525, 232, 14), border_radius=7)
    pygame.draw.rect(surface, CYAN, (924, 525, int(232 * fill_progress), 14), border_radius=7)
    label(surface, f"pintando {int(fill_progress * 100):02d}%", (1040, 552), 16, CYAN, center=True)


def draw_budget_scene(surface, t):
    local = t - 7.75
    scene_header(surface, "04 // FRAME BUDGET", "TODO TIENE QUE CABER AQUÍ",
                 GREEN, phase(local, 0.0, 1.55))
    label(surface, "A 60 FPS, cada fotograma tiene 16,67 ms disponibles", (640, 164),
          22, BONE, center=True)
    ruler_x, ruler_y, ruler_w = 146, 267, 988
    pygame.draw.rect(surface, (12, 13, 12), (ruler_x, ruler_y, ruler_w, 160), border_radius=12)
    pygame.draw.rect(surface, (64, 52, 38), (ruler_x, ruler_y, ruler_w, 160), 2, border_radius=12)
    label(surface, "PRESUPUESTO DE UN FOTOGRAMA", (ruler_x + 28, ruler_y + 24), 21, GREEN)
    start_x, bar_y, bar_w, bar_h = ruler_x + 28, ruler_y + 78, 900, 40
    segments = [
        ("raycasting", 6.4, CYAN),
        ("colisiones + IA", 2.1, RED),
        ("render", 5.8, AMBER),
        ("audio / HUD", 0.7, GREEN),
    ]
    total = sum(value for _, value, _ in segments)
    reveal = phase(local, 0.0, 1.45)
    cursor = start_x
    consumed = 0.0
    for name, milliseconds, color in segments:
        visible = min(milliseconds, max(0.0, reveal * total - consumed))
        width = int(bar_w * visible / 16.0)
        pygame.draw.rect(surface, color, (cursor, bar_y, width, bar_h), border_radius=4)
        if width > 80:
            label(surface, name, (cursor + width / 2, bar_y + 20), 15, BLACK, center=True)
        cursor += int(bar_w * milliseconds / 16.0)
        consumed += milliseconds
    pygame.draw.line(surface, RED, (start_x + bar_w, bar_y - 18),
                     (start_x + bar_w, bar_y + bar_h + 18), 3)
    label(surface, "16 ms", (start_x + bar_w, bar_y + 70), 18, RED, center=True)
    label(surface, "15,0 ms usados", (start_x + bar_w - 5, bar_y - 31), 16, BONE, center=True)

    if local > 0.8:
        draw_metric(surface, "< 16", "MILISEGUNDOS", (640, 545), WHITE, 78)
        label(surface, "si tarda más, el jugador ve tirones", (640, 638), 21, RED, center=True)
    else:
        draw_metric(surface, "16,67", "ms DISPONIBLES", (640, 545), GREEN, 70)


def draw_final_scene(surface, t):
    local = t - 9.75
    reveal = phase(local, 0.0, 0.7)
    scene_header(surface, "05 // RESULTADO", "Y EL JUGADOR SOLO VE ESTO", GREEN, reveal)
    horizon = 350
    pygame.draw.rect(surface, (13, 18, 20), (76, 165, 1128, 440), border_radius=12)
    pygame.draw.polygon(surface, (36, 40, 38), ((76, 165), (1204, 165), (910, 605), (370, 605)))
    pygame.draw.polygon(surface, (44, 36, 28), ((76, 165), (640, horizon), (370, 605), (76, 605)))
    pygame.draw.polygon(surface, (44, 36, 28), ((640, horizon), (1204, 165), (1204, 605), (910, 605)))
    for depth in range(1, 8):
        amount = depth / 8
        y = horizon - 170 * amount
        pygame.draw.line(surface, (86, 58, 36), (640 - 470 * amount, y),
                         (640 + 470 * amount, y), 2)
    for x in (76, 220, 1060, 1204):
        pygame.draw.line(surface, (85, 55, 35), (640, horizon), (x, 165), 3)
    demon = load_image("assets/enemies/demon_idle.png", (190, 190))
    surface.blit(demon, demon.get_rect(midbottom=(640, 560)))
    rifle = load_image("assets/weapons/doom_rifle.png", (430, 240))
    surface.blit(rifle, rifle.get_rect(midbottom=(640, 720)))
    pygame.draw.circle(surface, WHITE, (640, 350), 9, 2)
    pygame.draw.line(surface, WHITE, (609, 350), (631, 350), 2)
    pygame.draw.line(surface, WHITE, (649, 350), (671, 350), 2)
    rect_alpha(surface, BLACK, (76, 165, 1128, 440), int(150 * (1 - reveal)))
    label(surface, "38.400 RAYOS / S", (640, 213), 32, CYAN, center=True)
    label(surface, "todo este mundo se calcula antes del siguiente frame", (640, 255),
          19, BONE, center=True)
    label(surface, "< 16 ms", (640, 612), 35, GREEN, center=True)
    if local > 0.7:
        label(surface, "LA ILUSIÓN ESTÁ VIVA", (640, 678), 21, AMBER, center=True)


def draw_scene(surface, t):
    draw_background(surface, t)
    if t < 3.55:
        draw_rays_scene(surface, t)
    elif t < 5.55:
        draw_collision_scene(surface, t)
    elif t < 7.75:
        draw_pixel_scene(surface, t)
    elif t < 9.75:
        draw_budget_scene(surface, t)
    else:
        draw_final_scene(surface, t)

    # Transiciones de obturador: negro breve al cambiar de sistema para que
    # la pieza se sienta editada, no como una diapositiva continua.
    cuts = (0.8, 3.55, 5.55, 7.75, 9.75)
    for cut in cuts:
        distance = abs(t - cut)
        if distance < 0.10:
            alpha = int(255 * (1.0 - distance / 0.10))
            rect_alpha(surface, BLACK, (0, 0, WIDTH, HEIGHT), alpha)


def run_preview():
    from animacion_base import run
    run(draw_scene, DURATION, "Neon Breach — 38.400 rayos por segundo")


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
            draw_watermark(surface)
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
    parser = argparse.ArgumentParser(description="Renderiza la explicación cinematográfica del pipeline por frame.")
    parser.add_argument("--vista", action="store_true", help="Abre la vista interactiva.")
    parser.add_argument("--salida", type=Path,
                        default=ROOT / "videos" / "rendimiento_38k_rayos.mp4")
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
