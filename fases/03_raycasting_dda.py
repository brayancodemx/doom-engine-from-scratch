"""RAYCASTING.PY — DDA, campo de visión y corrección del ojo de pez."""

import math

import pygame

from animacion_base import (
    AMBER, BLACK, CYAN, DARK, GREEN, RED, RUST, STEEL, WHITE,
    glow_circle, label, load_image, phase, run,
)

DURATION = 13.0
GRID_X = 90
GRID_Y = 90
CELL = 66
COLS = 10
ROWS = 8


def draw_grid(surface):
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(GRID_X + x * CELL, GRID_Y + y * CELL,
                               CELL - 1, CELL - 1)
            wall = x == 8 or (x == 6 and 2 <= y <= 5)
            pygame.draw.rect(surface, (57, 44, 36) if wall else (18, 18, 17), rect)
            pygame.draw.rect(surface, RUST if wall else (49, 46, 40), rect, 1)


def dda_scene(surface, local_time):
    draw_grid(surface)
    start = pygame.Vector2(GRID_X + CELL * 1.5, GRID_Y + CELL * 5.7)
    end = pygame.Vector2(GRID_X + CELL * 8.0, GRID_Y + CELL * 2.3)
    progress = phase(local_time, 0.4, 3.7)
    current = start.lerp(end, progress)
    glow_circle(surface, AMBER, (int(start.x), int(start.y)), 11, 12)
    pygame.draw.line(surface, CYAN, start, current, 4)

    # Intersecciones DDA precalculadas sobre las líneas verticales de la cuadrícula.
    for column in range(2, 9):
        x = GRID_X + column * CELL
        ratio = (x - start.x) / (end.x - start.x)
        if ratio <= progress:
            y = start.y + (end.y - start.y) * ratio
            pygame.draw.circle(surface, WHITE, (int(x), int(y)), 7)
            pygame.draw.circle(surface, CYAN, (int(x), int(y)), 3)
    if progress >= 0.98:
        glow_circle(surface, RED, (int(end.x), int(end.y)), 10, 18)
    label(surface, "DDA", (905, 320), 70, CYAN, center=True)


def fan_scene(surface, local_time):
    draw_grid(surface)
    origin = pygame.Vector2(GRID_X + CELL * 2.0, GRID_Y + CELL * 4.0)
    progress = phase(local_time, 0.2, 2.6)
    ray_count = 84
    visible = int(ray_count * progress)
    for index in range(visible):
        amount = index / max(1, ray_count - 1)
        angle = math.radians(-33 + amount * 66)
        length = 525
        end = origin + pygame.Vector2(math.cos(angle), math.sin(angle)) * length
        color = AMBER if index == ray_count // 2 else CYAN
        pygame.draw.line(surface, color, origin, end, 2 if color == AMBER else 1)
    glow_circle(surface, WHITE, (int(origin.x), int(origin.y)), 10, 10)
    label(surface, "× 640", (1000, 600), 44, AMBER, center=True)


def fisheye_scene(surface, local_time):
    correction = phase(local_time, 1.3, 4.2)
    horizon = 365
    pygame.draw.rect(surface, (21, 18, 16), (70, 70, 1140, 590))
    pygame.draw.rect(surface, (45, 37, 30), (70, horizon, 1140, 295))
    pygame.draw.line(surface, STEEL, (70, horizon), (1210, horizon), 2)
    columns = 96
    width = 1140 / columns
    texture = draw_frame.wall_texture
    for index in range(columns):
        normalized = index / (columns - 1)
        angle = math.radians(-33 + normalized * 66)
        uncorrected_distance = 3.2 / max(0.2, math.cos(angle))
        corrected_distance = uncorrected_distance * math.cos(angle)
        distance = uncorrected_distance + (
            corrected_distance - uncorrected_distance
        ) * correction
        height = min(520, 1280 / distance)
        x = 70 + int(index * width)
        rect = pygame.Rect(x, int(horizon - height / 2),
                           int(width) + 1, int(height))
        texture_x = int(normalized * (texture.get_width() - 1))
        source_width = max(1, texture.get_width() // columns)
        texture_x = min(texture.get_width() - source_width, texture_x)
        source = pygame.Rect(texture_x, 0, source_width, texture.get_height())
        strip = pygame.transform.scale(
            texture.subsurface(source), (rect.width, rect.height)
        )
        surface.blit(strip, rect)
        darkness = int(28 + 58 * abs(normalized - 0.5) * 2)
        shade = pygame.Surface(rect.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, darkness))
        surface.blit(shade, rect)
    edge_color = RED if correction < 0.5 else GREEN
    pygame.draw.line(surface, edge_color, (70, 70), (70, 660), 5)
    pygame.draw.line(surface, edge_color, (1210, 70), (1210, 660), 5)
    if correction > 0.18:
        label(surface, "× cos(Δθ)", (640, 110), 42, GREEN, center=True)


def draw_frame(surface, time_value):
    surface.fill(BLACK)
    pygame.draw.rect(surface, DARK, (34, 34, 1212, 652), 3, border_radius=18)
    if time_value < 4.4:
        dda_scene(surface, time_value)
    elif time_value < 7.5:
        fan_scene(surface, time_value - 4.4)
    else:
        fisheye_scene(surface, time_value - 7.5)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    draw_frame.wall_texture = load_image(
        "assets/textures/walls/wall_1_steel.png", (512, 512)
    )
    pygame.display.quit()
    run(draw_frame, DURATION, "03 — raycasting.py: DDA y ojo de pez")


if __name__ == "__main__":
    main()
