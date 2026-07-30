"""ETAPA 2 — Un solo rayo avanza hasta encontrar una pared."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from map_data import MAP
from raycasting import cast_one_ray
from settings import CYAN, MAGENTA, ORANGE, WHITE

WINDOW = (1050, 620)
CELL = 34
OFFSET = (28, 38)


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW)
    pygame.display.set_caption("Etapa 2 — Un rayo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    title_font = pygame.font.SysFont("consolas", 26, bold=True)
    x, y, angle = 2.0, 1.6, 0.25
    running = True

    while running:
        dt = min(clock.tick(60) / 1000, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        keys = pygame.key.get_pressed()
        angle += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 1.6 * dt
        depth, wall, hit_x, hit_y, path = cast_one_ray(x, y, angle, keep_path=True)

        screen.fill((5, 7, 18))
        screen.blit(title_font.render("ETAPA 2 · LANZAMOS UN SOLO RAYO", True, WHITE), (28, 9))
        for row_y, row in enumerate(MAP):
            for column_x, tile in enumerate(row):
                rect = pygame.Rect(OFFSET[0] + column_x * CELL, OFFSET[1] + row_y * CELL,
                                   CELL, CELL)
                color = (12, 18, 32) if tile == "." else (22, 43, 61)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (19, 40, 53), rect, 1)

        # Puntos del recorrido: hacen visible el bucle while del raycaster.
        for index, (ray_x, ray_y) in enumerate(path):
            if index % 3 == 0:
                pygame.draw.circle(screen, MAGENTA,
                    (OFFSET[0] + int(ray_x * CELL), OFFSET[1] + int(ray_y * CELL)), 2)
        start = (OFFSET[0] + int(x * CELL), OFFSET[1] + int(y * CELL))
        hit = (OFFSET[0] + int(hit_x * CELL), OFFSET[1] + int(hit_y * CELL))
        pygame.draw.line(screen, CYAN, start, hit, 3)
        pygame.draw.circle(screen, ORANGE, start, 10)
        pygame.draw.circle(screen, WHITE, hit, 11, 3)

        panel_x = 610
        pygame.draw.rect(screen, (8, 12, 28), (panel_x, 75, 405, 450), border_radius=12)
        pygame.draw.rect(screen, MAGENTA, (panel_x, 75, 405, 450), 2, border_radius=12)
        lines = (
            "depth = 0",
            "while depth < MAX_DEPTH:",
            "  x = px + cos(a) * depth",
            "  y = py + sin(a) * depth",
            "  if hay_pared(x, y): break",
            "  depth += PASO",
            "",
            f"ángulo:    {math.degrees(angle):06.1f}°",
            f"distancia: {depth:06.2f}",
            f"pared:     tipo '{wall}'",
            "",
            "← → cambia el ángulo",
            "ESC sale",
        )
        for index, line in enumerate(lines):
            color = ORANGE if index >= 11 else (CYAN if index in (0, 7) else WHITE)
            screen.blit(font.render(line, True, color), (panel_x + 23, 105 + index * 30))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()

