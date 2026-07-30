"""ETAPA 1 — El mapa visto como una cuadrícula 2D."""

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player
from map_data import MAP
from settings import CYAN, MAGENTA, ORANGE, WHITE

WINDOW = (1050, 620)
CELL = 34
OFFSET = (28, 38)


def draw_map(screen, player, title_font, font):
    screen.fill((5, 7, 18))
    screen.blit(title_font.render("ETAPA 1 · EL MAPA ES UNA MATRIZ", True, WHITE), (28, 9))

    for y, row in enumerate(MAP):
        for x, tile in enumerate(row):
            rect = pygame.Rect(OFFSET[0] + x * CELL, OFFSET[1] + y * CELL, CELL, CELL)
            if tile == ".":
                pygame.draw.rect(screen, (12, 18, 32), rect)
                pygame.draw.rect(screen, (21, 36, 49), rect, 1)
            else:
                color = CYAN if tile in "136" else MAGENTA
                pygame.draw.rect(screen, (15, 35, 49), rect)
                pygame.draw.rect(screen, color, rect, 2)
                screen.blit(font.render(tile, True, color),
                            font.render(tile, True, color).get_rect(center=rect.center))

    px = OFFSET[0] + int(player.x * CELL)
    py = OFFSET[1] + int(player.y * CELL)
    pygame.draw.circle(screen, ORANGE, (px, py), 10)
    pygame.draw.circle(screen, WHITE, (px, py), 10, 2)
    pygame.draw.line(screen, WHITE, (px, py),
                     (px + int(pygame.math.Vector2(CELL, 0).rotate_rad(player.angle).x),
                      py + int(pygame.math.Vector2(CELL, 0).rotate_rad(player.angle).y)), 3)

    panel_x = 610
    pygame.draw.rect(screen, (8, 12, 28), (panel_x, 75, 405, 450), border_radius=12)
    pygame.draw.rect(screen, CYAN, (panel_x, 75, 405, 450), 2, border_radius=12)
    explanations = (
        ("MAPA[y][x]", MAGENTA),
        ("'1'...'6' = pared", WHITE),
        ("'.' = espacio libre", WHITE),
        ("", WHITE),
        ("El jugador guarda:", CYAN),
        (f"x = {player.x:05.2f}", WHITE),
        (f"y = {player.y:05.2f}", WHITE),
        (f"ángulo = {player.angle:05.2f}", WHITE),
        ("", WHITE),
        ("WASD: moverse", ORANGE),
        ("← →: girar", ORANGE),
        ("ESC: salir", ORANGE),
    )
    for index, (line, color) in enumerate(explanations):
        text = font.render(line, True, color)
        screen.blit(text, (panel_x + 27, 105 + index * 31))


def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW)
    pygame.display.set_caption("Etapa 1 — Mapa 2D")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    title_font = pygame.font.SysFont("consolas", 26, bold=True)
    player = Player()
    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        player.update(dt)
        draw_map(screen, player, title_font, font)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
