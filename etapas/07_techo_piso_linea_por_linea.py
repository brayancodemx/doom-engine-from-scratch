"""ETAPA 7 — Techo y suelo se construyen con líneas horizontales."""

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from settings import BLACK, CYAN, HEIGHT, MAGENTA, WHITE, WIDTH

ROWS_PER_SECOND = 42
HORIZON = HEIGHT // 2


def draw_rows(surface, visible_rows):
    surface.fill(BLACK)
    for offset in range(visible_rows):
        top_y = HORIZON - 1 - offset
        bottom_y = HORIZON + offset

        if top_y >= 0:
            t = top_y / HORIZON
            ceiling = (5 + int(8 * t), 7 + int(8 * t), 22 + int(22 * t))
            pygame.draw.line(surface, ceiling, (0, top_y), (WIDTH, top_y))

        if bottom_y < HEIGHT:
            t = (bottom_y - HORIZON) / (HEIGHT - HORIZON)
            floor = (11 + int(5 * t), 10, 23 + int(9 * t))
            pygame.draw.line(surface, floor, (0, bottom_y), (WIDTH, bottom_y))

    # Guías luminosas para mostrar el punto de fuga del suelo.
    if visible_rows >= HORIZON:
        for index in range(1, 14):
            perspective = (index / 13) ** 2
            y = HORIZON + int(perspective * (HEIGHT - HORIZON))
            pygame.draw.line(surface, (45, 12, 62), (0, y), (WIDTH, y), 1)
        for bottom_x in range(-WIDTH, WIDTH * 2, 80):
            pygame.draw.line(surface, (10, 45, 64), (WIDTH // 2, HORIZON),
                             (bottom_x, HEIGHT), 1)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 7 — Techo y piso línea por línea")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small_font = pygame.font.SysFont("consolas", 15, bold=True)
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
            progress = min(HORIZON, progress + ROWS_PER_SECOND * dt)
        visible = int(progress)
        draw_rows(screen, visible)

        top_marker = max(0, HORIZON - visible)
        bottom_marker = min(HEIGHT - 1, HORIZON + visible)
        pygame.draw.line(screen, CYAN, (0, top_marker), (WIDTH, top_marker), 2)
        pygame.draw.line(screen, MAGENTA, (0, bottom_marker), (WIDTH, bottom_marker), 2)

        panel = pygame.Surface((WIDTH, 78), pygame.SRCALPHA)
        panel.fill((2, 4, 14, 235))
        screen.blit(panel, (0, 0))
        screen.blit(font.render(
            f"TECHO + PISO = {visible:03d} PARES DE LÍNEAS HORIZONTALES",
            True, WHITE), (22, 15))
        screen.blit(small_font.render(
            "Nacen en el horizonte y se expanden hacia los bordes",
            True, CYAN), (22, 47))
        screen.blit(small_font.render("R reinicia · ESPACIO pausa", True, WHITE),
                    (WIDTH - 270, 47))
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

