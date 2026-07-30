"""Gameplay de 8 s: semivuelta alrededor de un demonio 2D inmóvil."""

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
from settings import HEIGHT, WIDTH


DURATION = 8.0
EXPORT_FPS = 30
DEMON_POSITION = (14.5, 10.0)
ORBIT_RADIUS = 2.35


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def orbit_state(time_value):
    """Posición y mirada para una órbita de exactamente media vuelta."""
    progress = smoothstep(time_value / DURATION)
    orbit_angle = -math.pi / 2 + math.pi * progress
    player_x = DEMON_POSITION[0] + math.cos(orbit_angle) * ORBIT_RADIUS
    player_y = DEMON_POSITION[1] + math.sin(orbit_angle) * ORBIT_RADIUS
    view_angle = math.atan2(
        DEMON_POSITION[1] - player_y,
        DEMON_POSITION[0] - player_x,
    )
    return player_x, player_y, view_angle


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    demon = Enemy(
        DEMON_POSITION[0],
        DEMON_POSITION[1],
        health=3,
        variant=0,
    )
    demon.moving = False
    demon.attack_timer = 0.0
    game.enemies = [demon]
    return game


def draw_frame(surface, game, time_value):
    player_x, player_y, view_angle = orbit_state(time_value)
    game.time = 10.0 + time_value
    game.player.x = player_x
    game.player.y = player_y
    game.player.angle = view_angle
    game.player.moving = True
    game.player.walk_time = time_value * 7.2
    game.camera_bob_x = math.sin(game.player.walk_time) * 2.4
    game.camera_bob_y = math.sin(game.player.walk_time * 2.0) * 3.2

    demon = game.enemies[0]
    demon.x, demon.y = DEMON_POSITION
    demon.moving = False
    demon.animation = time_value * 1.2
    demon.attack_timer = 0.0

    game.draw_playing()
    surface.blit(game.frame, (0, 0))


def validate_orbit():
    for sample in range(121):
        time_value = DURATION * sample / 120
        player_x, player_y, _ = orbit_state(time_value)
        if Player._touches_wall(player_x, player_y):
            raise RuntimeError(
                f"La órbita toca una pared en ({player_x:.2f}, {player_y:.2f})"
            )


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    validate_orbit()
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
    validate_orbit()
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


def main():
    parser = argparse.ArgumentParser(
        description="Renderiza una semivuelta alrededor de un demonio billboard."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "demonio_billboard_semivuelta.mp4",
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
    try:
        export(args.salida, ffmpeg_path)
        print(f"Video creado: {args.salida.resolve()}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
