"""ETAPA 6 — Las 240 columnas de pared aparecen lentamente una a una."""

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player
from raycasting import cast_all_rays
from renderer import draw_background, draw_walls
from settings import CYAN, HEIGHT, NUM_RAYS, RAY_WIDTH, WHITE, WIDTH

LINES_PER_SECOND = 34


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 6 — Paredes línea por línea")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small_font = pygame.font.SysFont("consolas", 15, bold=True)
    player = Player(x=2.0, y=1.6, angle=0.10)
    rays, _ = cast_all_rays(player)
    progress = 0.0
    paused = False
    running = True

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    progress = 0.0
                elif event.key == pygame.K_SPACE:
                    paused = not paused

        if not paused:
            progress = min(NUM_RAYS, progress + LINES_PER_SECOND * dt)
        visible = int(progress)

        draw_background(screen, 0.0)
        draw_walls(screen, rays[:visible])

        # Marca la próxima columna para que el avance se entienda incluso en pausa.
        next_x = min(WIDTH - 1, visible * RAY_WIDTH)
        pygame.draw.line(screen, WHITE, (next_x, 76), (next_x, HEIGHT), 1)

        panel = pygame.Surface((WIDTH, 76), pygame.SRCALPHA)
        panel.fill((2, 4, 14, 235))
        screen.blit(panel, (0, 0))
        title = f"PARED = {visible:03d} COLUMNAS VERTICALES DE {NUM_RAYS}"
        screen.blit(font.render(title, True, WHITE), (22, 13))
        screen.blit(small_font.render(
            "Cada rayo aporta distancia → altura → una línea en pantalla",
            True, CYAN), (22, 43))
        screen.blit(small_font.render("R reinicia · ESPACIO pausa · ESC sale", True, WHITE),
                    (WIDTH - 360, 43))
        pygame.draw.rect(screen, (24, 28, 45), (22, 64, WIDTH - 44, 7), border_radius=4)
        pygame.draw.rect(screen, CYAN,
                         (22, 64, int((WIDTH - 44) * visible / NUM_RAYS), 7), border_radius=4)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

