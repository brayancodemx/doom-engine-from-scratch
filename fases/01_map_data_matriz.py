"""MAP_DATA.PY — texto, matriz, coordenadas y casillas válidas."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from map_data import MAP
from animacion_base import (
    AMBER, BLACK, BONE, CYAN, DARK, GREEN, RED, RUST, STEEL, WHITE,
    glow_circle, label, load_image, phase, pulse, run,
)

DURATION = 13.0
CELL = 27
MAP_X = 76
MAP_Y = 88


def tile_rect(x, y):
    return pygame.Rect(MAP_X + x * CELL, MAP_Y + y * CELL, CELL - 1, CELL - 1)


def draw_map(surface, time_value):
    block_progress = phase(time_value, 0.5, 3.0)
    char_alpha = int(255 * (1.0 - block_progress))
    block_alpha = int(255 * block_progress)
    chars = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    blocks = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    char_font = pygame.font.SysFont("consolas", 17, bold=True)

    for y, row in enumerate(MAP):
        for x, tile in enumerate(row):
            rect = tile_rect(x, y)
            if tile == ".":
                color = (25, 27, 26, block_alpha)
                border = (62, 61, 54, block_alpha)
            else:
                wall_colors = {"1": STEEL, "2": RUST, "3": GREEN,
                               "4": AMBER, "5": BONE, "6": RED}
                base = wall_colors.get(tile, STEEL)
                color = (*tuple(int(channel * 0.42) for channel in base), block_alpha)
                border = (*base, block_alpha)
            pygame.draw.rect(blocks, color, rect)
            pygame.draw.rect(blocks, border, rect, 1)
            glyph = char_font.render(tile, True, (*WHITE, char_alpha))
            chars.blit(glyph, glyph.get_rect(center=rect.center))

    surface.blit(chars, (0, 0))
    surface.blit(blocks, (0, 0))


def draw_query(surface, time_value):
    progress = phase(time_value, 3.2, 6.0)
    if progress <= 0:
        return
    target_x, target_y = 5, 5
    row_progress = min(1.0, progress * 2.0)
    column_progress = max(0.0, progress * 2.0 - 1.0)

    row_y = MAP_Y + target_y * CELL
    row_width = int((target_x + 1) * CELL * row_progress)
    row = pygame.Surface((row_width, CELL), pygame.SRCALPHA)
    row.fill((*CYAN, 55))
    surface.blit(row, (MAP_X, row_y))

    if column_progress > 0:
        rect = tile_rect(target_x, target_y)
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*AMBER, int(80 + 110 * pulse(time_value, 2.0))),
                         rect.inflate(12, 12), border_radius=4)
        surface.blit(glow, (0, 0))
        pygame.draw.rect(surface, AMBER, rect, 4)
        label(surface, "MAP[y][x]", (780, 168), 34, CYAN)
        label(surface, "MAP[5][5]  →  2", (780, 220), 28, AMBER)


def draw_decimal_position(surface, time_value):
    progress = phase(time_value, 6.1, 9.2)
    if progress <= 0:
        return
    x_value, y_value = 2.7, 4.2
    exact = (MAP_X + int(x_value * CELL), MAP_Y + int(y_value * CELL))
    cell = tile_rect(2, 4)
    pygame.draw.rect(surface, GREEN, cell, 3)
    glow_circle(surface, AMBER, exact, 8, 12)
    pygame.draw.line(surface, CYAN, exact, cell.center, 2)
    label(surface, "x = 2.7", (780, 310), 28, WHITE)
    label(surface, "y = 4.2", (780, 350), 28, WHITE)
    if progress > 0.48:
        label(surface, "(2, 4)", (850, 420), 42, GREEN, center=True)


def draw_spawn_check(surface, time_value, demon):
    progress = phase(time_value, 9.3, 12.8)
    if progress <= 0:
        return
    wall = tile_rect(5, 5).center
    free = tile_rect(7, 4).center
    move = phase(progress, 0.45, 0.8)
    position = (
        int(wall[0] + (free[0] - wall[0]) * move),
        int(wall[1] + (free[1] - wall[1]) * move),
    )
    image = demon.copy()
    image.set_alpha(int(255 * min(1.0, progress * 3.0)))
    surface.blit(image, image.get_rect(center=position))
    if move < 0.05:
        pygame.draw.line(surface, RED, (wall[0] - 24, wall[1] - 24),
                         (wall[0] + 24, wall[1] + 24), 7)
        pygame.draw.line(surface, RED, (wall[0] + 24, wall[1] - 24),
                         (wall[0] - 24, wall[1] + 24), 7)
    else:
        pygame.draw.rect(surface, GREEN, tile_rect(7, 4), 4)
    label(surface, "is_wall", (790, 512), 30, RED if move < 0.05 else GREEN)


def draw_frame(surface, time_value):
    surface.fill(BLACK)
    pygame.draw.rect(surface, DARK, (48, 52, 600, 610), border_radius=14)
    pygame.draw.rect(surface, STEEL, (48, 52, 600, 610), 2, border_radius=14)
    pygame.draw.rect(surface, (12, 10, 9), (704, 104, 500, 510), border_radius=18)
    pygame.draw.line(surface, RUST, (704, 104), (1204, 104), 4)

    draw_map(surface, time_value)
    draw_query(surface, time_value)
    draw_decimal_position(surface, time_value)
    draw_spawn_check(surface, time_value, draw_frame.demon)

    # El flujo inferior resume la pregunta que comparten colisiones y spawns.
    if time_value > 4.8:
        x = 786
        y = 590
        pygame.draw.circle(surface, CYAN, (x, y), 8)
        pygame.draw.line(surface, CYAN, (x + 8, y), (1110, y), 3)
        pygame.draw.polygon(surface, CYAN,
                            ((1110, y), (1092, y - 9), (1092, y + 9)))


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    draw_frame.demon = load_image(
        "assets/enemies/demon_idle.png", (58, 58)
    )
    pygame.display.quit()
    run(draw_frame, DURATION, "01 — map_data.py: el mapa es una matriz")


if __name__ == "__main__":
    main()
