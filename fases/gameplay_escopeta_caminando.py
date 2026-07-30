"""Gameplay limpio de 4 s: jugador con escopeta caminando en línea recta."""

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
from settings import HEIGHT, WIDTH


DURATION = 4.0
EXPORT_FPS = 30
START = (2.5, 2.5)
END = (11.5, 2.5)
VIEW_ANGLE = 0.0


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def position_at(time_value):
    # Aceleración y frenado muy breves para que la toma no arranque con tirón.
    progress = smoothstep(time_value / DURATION)
    return (
        START[0] + (END[0] - START[0]) * progress,
        START[1] + (END[1] - START[1]) * progress,
    )


def make_game():
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.score = 0
    game.weapon_style = "doom_shotgun"
    game.player = Player(
        x=START[0],
        y=START[1],
        angle=VIEW_ANGLE,
        health=100,
    )
    game.enemies = []
    return game


def draw_frame(surface, game, time_value):
    player_x, player_y = position_at(time_value)
    game.time = 12.0 + time_value
    game.player.x = player_x
    game.player.y = player_y
    game.player.angle = VIEW_ANGLE
    game.player.moving = True
    game.player.walk_time = time_value * 8.6
    game.camera_bob_x = math.sin(game.player.walk_time) * 1.6
    game.camera_bob_y = math.sin(game.player.walk_time * 2.0) * 2.2
    game.recoil = 0.0
    game.muzzle_flash = 0.0
    game.weapon_action_timer = 0.0
    game.draw_playing()
    surface.blit(game.frame, (0, 0))


def validate_path():
    for sample in range(161):
        progress = sample / 160
        player_x = START[0] + (END[0] - START[0]) * progress
        player_y = START[1]
        if Player._touches_wall(player_x, player_y):
            raise RuntimeError(
                f"El recorrido toca una pared en ({player_x:.2f}, {player_y:.2f})."
            )


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
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


def export(output_path, ffmpeg_path):
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


def main():
    parser = argparse.ArgumentParser(
        description="Renderiza gameplay con escopeta caminando en línea recta."
    )
    parser.add_argument("--vista", action="store_true")
    parser.add_argument(
        "--salida",
        type=Path,
        default=ROOT / "videos" / "gameplay_escopeta_recto_4s.mp4",
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
