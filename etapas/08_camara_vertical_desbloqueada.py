"""ETAPA 8 — Desbloquea una mirada vertical falsa y revela la ilusión 2.5D."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player
from raycasting import cast_all_rays
from renderer import WALL_COLORS
from settings import (
    BLACK, CYAN, HEIGHT, MAGENTA, PROJECTION_DISTANCE, RAY_WIDTH, WHITE, WIDTH,
)


def draw_shifted_background(surface, horizon):
    surface.fill(BLACK)
    for y in range(HEIGHT):
        if y < horizon:
            denominator = max(1, horizon)
            t = y / denominator
            color = (5 + int(8 * t), 7 + int(8 * t), 22 + int(22 * t))
        else:
            denominator = max(1, HEIGHT - horizon)
            t = (y - horizon) / denominator
            color = (11 + int(5 * t), 10, 23 + int(9 * t))
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))

    pygame.draw.line(surface, MAGENTA, (0, horizon), (WIDTH, horizon), 2)
    for bottom_x in range(-WIDTH, WIDTH * 2, 100):
        pygame.draw.line(surface, (11, 45, 62), (WIDTH // 2, horizon),
                         (bottom_x, HEIGHT), 1)


def draw_shifted_walls(surface, rays, horizon, pitch):
    distortion = 1.0 + abs(pitch) / 300
    for index, (depth, wall, hit_x, hit_y) in enumerate(rays):
        height = min(int(PROJECTION_DISTANCE / max(depth, 0.001) * distortion), HEIGHT * 3)
        top = horizon - height // 2
        base = WALL_COLORS.get(wall, WALL_COLORS["1"])
        light = max(0.17, 1.0 - depth / 18)
        color = tuple(int(channel * light) for channel in base)
        pygame.draw.rect(surface, color, (index * RAY_WIDTH, top, RAY_WIDTH + 1, height))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 8 — Cámara vertical desbloqueada")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small_font = pygame.font.SysFont("consolas", 15, bold=True)
    player = Player(x=2.0, y=1.6, angle=0.10)
    rays, _ = cast_all_rays(player)
    pitch = 0.0
    time_value = 0.0
    automatic = True
    running = True

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.04)
        time_value += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    automatic = not automatic
                elif event.key == pygame.K_r:
                    pitch = 0.0
                    automatic = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_DOWN]:
            automatic = False
            pitch += (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * 150 * dt
            pitch = max(-175, min(175, pitch))
        elif automatic:
            pitch = math.sin(time_value * 0.75) * 155

        horizon = int(HEIGHT // 2 + pitch)
        draw_shifted_background(screen, horizon)
        draw_shifted_walls(screen, rays, horizon, pitch)

        # La línea fija muestra que no existe geometría vertical real: solo desplazamos el horizonte.
        pygame.draw.line(screen, WHITE, (0, HEIGHT // 2), (WIDTH, HEIGHT // 2), 1)
        panel = pygame.Surface((WIDTH, 90), pygame.SRCALPHA)
        panel.fill((2, 4, 14, 235))
        screen.blit(panel, (0, 0))
        screen.blit(font.render("CÁMARA VERTICAL FALSA: NO HAY RAYOS ARRIBA/ABAJO", True, WHITE),
                    (22, 13))
        screen.blit(small_font.render(
            f"pitch = {pitch:+06.1f}px · solo movemos el horizonte y estiramos columnas",
            True, CYAN), (22, 45))
        mode = "AUTOMÁTICO" if automatic else "MANUAL"
        screen.blit(small_font.render(
            f"↑ ↓ mirar · A automático · R centrar    [{mode}]", True, MAGENTA
        ), (22, 68))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

