"""Crea dos clips de gameplay para explicar el efecto de delta time.

Los dos clips muestran exactamente la misma prueba: el jugador mantiene W
durante siete segundos. La diferencia está en cómo se calcula la distancia:

    con_dt:  distancia = velocidad * segundos_transcurridos
    sin_dt:  distancia = desplazamiento_por_frame * frames

Se renderiza a 1280x720 para que los clips sean ligeros y se puedan minimizar
en una comparativa de edición.
"""

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys

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
    FPS,
    HEIGHT,
    WIDTH,
    clamp,
    draw_scanlines,
    font,
    glow_circle,
    label,
    load_image,
    phase,
)


ROOT = Path(__file__).resolve().parents[1]
DURATION = 7.0
EXPORT_FPS = 30
START_X = 236.0
END_X = 994.0
TRAVEL = END_X - START_X
PLAYER_SPEED = TRAVEL / DURATION


def draw_panel(surface, rect, title, color):
    """Dibuja un panel de gameplay con una jerarquía clara para video."""
    x, y, width, height = rect
    pygame.draw.rect(surface, (13, 12, 12), rect, border_radius=14)
    pygame.draw.rect(surface, (52, 43, 36), rect, 2, border_radius=14)
    pygame.draw.line(surface, color, (x + 18, y + 42),
                     (x + width - 18, y + 42), 3)
    label(surface, title, (x + 22, y + 12), 24, color)


def draw_game_lane(surface, lane_y, fps_label, color, player_x, hit, t):
    """Dibuja un carril de gameplay tipo arena/corredor."""
    lane_x = 178
    lane_width = 924
    floor_y = lane_y + 37
    floor_height = 93
    target_x = 1004

    pygame.draw.rect(surface, (17, 18, 17),
                     (lane_x, floor_y, lane_width, floor_height),
                     border_radius=6)
    pygame.draw.rect(surface, (41, 42, 37),
                     (lane_x, floor_y, lane_width, floor_height), 2,
                     border_radius=6)

    # Baldosas y marcas de distancia: el movimiento se lee aunque el clip se
    # reduzca mucho en la edición final.
    for index in range(13):
        x = lane_x + 20 + index * 74
        pygame.draw.line(surface, (50, 46, 38),
                         (x, floor_y + 7), (x, floor_y + floor_height - 7), 2)
    for offset in (22, 51, 80):
        pygame.draw.line(surface, (35, 37, 34),
                         (lane_x + 8, floor_y + offset),
                         (lane_x + lane_width - 8, floor_y + offset), 1)

    # Paredes laterales y salida bloqueada.
    pygame.draw.rect(surface, (55, 42, 34),
                     (lane_x, floor_y - 20, lane_width, 20))
    pygame.draw.rect(surface, (55, 42, 34),
                     (lane_x, floor_y + floor_height, lane_width, 20))
    pygame.draw.rect(surface, RED if hit else RUST,
                     (target_x, floor_y - 20, 18, floor_height + 40),
                     border_radius=4)
    for stripe_y in range(floor_y - 16, floor_y + floor_height + 20, 16):
        pygame.draw.line(surface, AMBER if not hit else WHITE,
                         (target_x - 7, stripe_y),
                         (target_x + 25, stripe_y + 10), 3)

    # Demonio objetivo: es la referencia visual de que el jugador avanza.
    demon = load_image("assets/enemies/demon_idle.png", (58, 58))
    demon_rect = demon.get_rect(center=(target_x - 40, floor_y + floor_height // 2))
    surface.blit(demon, demon_rect)

    # Rastro corto del jugador para reforzar la dirección y la velocidad.
    for trail_index in range(5, 0, -1):
        trail_x = max(START_X, player_x - trail_index * 14)
        alpha = 28 + (5 - trail_index) * 10
        trail = pygame.Surface((36, 36), pygame.SRCALPHA)
        pygame.draw.circle(trail, (*color, alpha), (18, 18), 10)
        surface.blit(trail, (int(trail_x - 18), int(floor_y + 46 - 18)))

    player_y = floor_y + floor_height // 2
    glow_circle(surface, color, (int(player_x), player_y), 12, 12)
    pygame.draw.circle(surface, WHITE, (int(player_x), player_y), 5)
    pygame.draw.line(surface, WHITE,
                     (int(player_x + 8), player_y),
                     (int(player_x + 30), player_y), 3)

    # Contador de la simulación: frames acumulados cambia mucho en el clip
    # sin dt, mientras que el tiempo real siempre es el mismo.
    frames = int(t * fps_label)
    label(surface, f"{fps_label} FPS", (lane_x + 18, floor_y + 7), 20, color)
    label(surface, f"frames: {frames:04d}",
          (lane_x + lane_width - 170, floor_y + 8), 18, BONE)
    label(surface, "W", (int(player_x), floor_y + 115), 22, color, center=True)
    if hit:
        label(surface, "IMPACTO: llegó 5× antes", (target_x - 190, floor_y - 58),
              20, RED)


def draw_formula_box(surface, mode, t):
    box = (178, 625, 924, 58)
    pygame.draw.rect(surface, (12, 12, 11), box, border_radius=10)
    pygame.draw.rect(surface, (62, 52, 42), box, 2, border_radius=10)
    if mode == "con_dt":
        label(surface, "CON dt", (198, 641), 22, GREEN)
        label(surface, "distancia = velocidad × tiempo real", (350, 641), 22, WHITE)
        label(surface, f"t = {t:0.1f}s", (935, 641), 22, CYAN)
    else:
        label(surface, "SIN dt", (198, 641), 22, RED)
        label(surface, "distancia = desplazamiento × cantidad de frames", (330, 641), 22, WHITE)
        label(surface, f"t = {t:0.1f}s", (935, 641), 22, CYAN)


def position_for(t, mode, fps):
    """Devuelve una posición reproducible para el frame exportado."""
    elapsed = clamp(t, 0.0, DURATION)
    frame_factor = 1.0 if mode == "con_dt" or fps == 60 else 5.0
    return min(END_X, START_X + PLAYER_SPEED * elapsed * frame_factor)


def draw_scene(surface, mode, t):
    surface.fill(BLACK)
    draw_scanlines(surface, alpha=13)

    pygame.draw.rect(surface, (18, 15, 13), (42, 30, WIDTH - 84, HEIGHT - 60),
                     border_radius=18)
    pygame.draw.rect(surface, (71, 49, 34), (42, 30, WIDTH - 84, HEIGHT - 60),
                     2, border_radius=18)

    mode_color = GREEN if mode == "con_dt" else RED
    mode_title = "MOVIMIENTO ESTABLE" if mode == "con_dt" else "MOVIMIENTO DEPENDIENTE DEL FPS"
    mode_tag = "CON DELTA TIME" if mode == "con_dt" else "SIN DELTA TIME"
    label(surface, "NEON BREACH // PRUEBA DE GAMEPLAY", (78, 52), 24, BONE)
    label(surface, mode_tag, (1038, 52), 24, mode_color, center=True)
    label(surface, mode_title, (78, 88), 34, mode_color)
    label(surface, "Mismo input: W sostenido  ·  misma velocidad configurada  ·  7 segundos",
          (78, 122), 18, STEEL)

    draw_panel(surface, (148, 158, 984, 432), "ARENA DE PRUEBA // JUGADOR AVANZANDO", mode_color)

    # En ambos clips los carriles están organizados igual: 60 FPS arriba y
    # 300 FPS abajo. Así se pueden superponer o cortar lado a lado.
    label(surface, "REFERENCIA DE RENDIMIENTO", (178, 204), 17, STEEL)
    draw_game_lane(
        surface, 228, 60, CYAN,
        position_for(t, mode, 60), False, t,
    )
    draw_game_lane(
        surface, 418, 300, AMBER,
        position_for(t, mode, 300),
        mode == "sin_dt" and position_for(t, mode, 300) >= END_X,
        t,
    )

    # Línea de progreso global para que el espectador compruebe que ambos
    # clips terminan exactamente al mismo tiempo.
    progress = clamp(t / DURATION)
    pygame.draw.line(surface, (62, 52, 42), (1138, 161), (1138, 590), 2)
    pygame.draw.line(surface, mode_color, (1138, 590),
                     (1138, 590 - 380 * progress), 6)
    pygame.draw.circle(surface, mode_color,
                       (1138, int(590 - 380 * progress)), 7)
    label(surface, "7s", (1150, 172), 18, BONE)
    label(surface, "0s", (1150, 570), 18, BONE)

    draw_formula_box(surface, mode, t)
    if mode == "sin_dt" and t > 1.55:
        label(surface, "La PC rápida ya chocó; la lenta sigue a mitad del pasillo",
              (640, 700), 20, RED, center=True)
    elif mode == "con_dt" and t > 5.0:
        label(surface, "Ambos jugadores llegan juntos: el tiempo manda, no los FPS",
              (640, 700), 20, GREEN, center=True)


def run_preview(mode):
    from animacion_base import run

    title = "Delta Time — " + ("con dt" if mode == "con_dt" else "sin dt")
    run(lambda surface, t: draw_scene(surface, mode, t), DURATION, title)


def export_clip(mode, output_path, ffmpeg_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pixel_format", "rgb24",
        "-video_size", f"{WIDTH}x{HEIGHT}", "-framerate", str(EXPORT_FPS),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    surface = pygame.Surface((WIDTH, HEIGHT))
    frame_count = int(DURATION * EXPORT_FPS)
    try:
        for frame_index in range(frame_count):
            draw_scene(surface, mode, frame_index / EXPORT_FPS)
            process.stdin.write(pygame.image.tobytes(surface, "RGB"))
            if frame_index % EXPORT_FPS == 0 or frame_index + 1 == frame_count:
                percent = (frame_index + 1) / frame_count * 100
                print(f"\r{output_path.name}: {percent:5.1f}%", end="", flush=True)
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


def self_test():
    same_at_1s = position_for(1.0, "con_dt", 60) == position_for(1.0, "con_dt", 300)
    fast_without_dt = position_for(1.0, "sin_dt", 300) > position_for(1.0, "sin_dt", 60)
    assert same_at_1s, "CON dt debe ser independiente de los FPS"
    assert fast_without_dt, "SIN dt debe avanzar más a mayor FPS"
    assert position_for(DURATION, "con_dt", 60) == END_X
    print("OK: comprobación de delta time superada")


def main():
    parser = argparse.ArgumentParser(description="Exporta las dos animaciones de delta time.")
    parser.add_argument("--vista", choices=("con_dt", "sin_dt"),
                        help="Abre una escena interactiva en lugar de exportar.")
    parser.add_argument("--salida", type=Path,
                        default=ROOT / "videos" / "delta_time")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return
    if args.vista:
        run_preview(args.vista)
        return

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise SystemExit("No se encontró FFmpeg en PATH.")
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    try:
        outputs = (
            args.salida / "delta_time_con_dt.mp4",
            args.salida / "delta_time_sin_dt.mp4",
        )
        for mode, output in zip(("con_dt", "sin_dt"), outputs):
            export_clip(mode, output, ffmpeg_path)
        print("\nVideos creados:")
        for output in outputs:
            print(f"  {output.resolve()}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
