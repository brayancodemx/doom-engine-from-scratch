"""Toma corta de gameplay: demonio caminando, bugueado dentro de una pared."""

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

from main import Game
from settings import HEIGHT, WIDTH


DURATION = 4.0
EXPORT_FPS = 30


def make_game():
    """Prepara una vista auténtica del juego frente a una columna central."""
    game = Game()
    game.state = "playing"
    game.show_hud = True
    game.player.x = 7.5
    game.player.y = 12.5
    game.player.angle = -0.983
    game.enemies = []
    return game


def load_bug_sprites():
    assets = ROOT / "assets" / "enemies"
    sprites = []
    for name in ("demon_walk_a.png", "demon_walk_b.png"):
        sprite = pygame.image.load(str(assets / name)).convert_alpha()
        sprite = pygame.transform.scale(sprite, (270, 270))
        sprites.append(sprite)
    return tuple(sprites)


def draw_frame(surface, game, sprites, time_value):
    """Compone un frame del juego y oculta parte del demonio con su pared."""
    game.time = 8.0 + time_value
    game.player.angle = -0.983 + math.sin(time_value * 1.1) * 0.009
    game.draw_playing()
    surface.blit(game.frame, (0, 0))

    # Esta franja pertenece a una columna real y está frente al demonio. Al
    # restaurarla después de cada pose de caminar, el spawn queda enterrado
    # dentro del bloque y no puede escapar visualmente de la geometría.
    wall_foreground = surface.subsurface((560, 120, WIDTH - 560, 510)).copy()
    sprite = sprites[int(time_value * 6.0) % 2]
    jitter_x = int(math.sin(time_value * math.tau * 3.4) * 7)
    jitter_y = int(abs(math.sin(time_value * math.tau * 3.4)) * 5)
    sprite_rect = sprite.get_rect(midbottom=(580 + jitter_x, 570 + jitter_y))
    surface.blit(sprite, sprite_rect)
    surface.blit(wall_foreground, (560, 120))


def preview():
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    game = make_game()
    sprites = load_bug_sprites()
    screen = pygame.display.get_surface()
    surface = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    elapsed = 0.0
    running = True
    while running:
        elapsed += min(clock.tick(60) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
        draw_frame(surface, game, sprites, elapsed % DURATION)
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
    game = make_game()
    sprites = load_bug_sprites()
    surface = pygame.Surface((WIDTH, HEIGHT))
    frame_count = int(DURATION * EXPORT_FPS)
    try:
        for frame_index in range(frame_count):
            draw_frame(surface, game, sprites, frame_index / EXPORT_FPS)
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
    parser = argparse.ArgumentParser(description="Renderiza al demonio atorado en una pared.")
    parser.add_argument("--vista", action="store_true")
    parser.add_argument("--salida", type=Path,
                        default=ROOT / "videos" / "demonio_atorado_pared.mp4")
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
