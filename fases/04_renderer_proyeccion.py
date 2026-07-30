"""RENDERER.PY — columnas, sprites 2D y oclusión por profundidad."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from animacion_base import (
    AMBER, BLACK, BONE, CYAN, DARK, GREEN, RED, RUST, STEEL, WHITE,
    glow_circle, label, load_image, phase, run,
)

DURATION = 14.5


def projection_scene(surface, local_time):
    origin = pygame.Vector2(220, 365)
    wall_x = 515
    progress = phase(local_time, 0.35, 4.5)
    ray_count = 64
    visible = int(ray_count * progress)

    pygame.draw.rect(surface, (54, 43, 35), (wall_x, 105, 54, 520))
    pygame.draw.rect(surface, RUST, (wall_x, 105, 54, 520), 4)
    glow_circle(surface, AMBER, (int(origin.x), int(origin.y)), 14, 12)

    view = pygame.Rect(670, 85, 520, 550)
    pygame.draw.rect(surface, (22, 20, 18), view)
    pygame.draw.line(surface, STEEL, (view.left, view.centery),
                     (view.right, view.centery), 2)

    for index in range(visible):
        amount = index / max(1, ray_count - 1)
        angle = math.radians(-31 + amount * 62)
        direction = pygame.Vector2(math.cos(angle), math.sin(angle))
        distance = (wall_x - origin.x) / max(0.15, direction.x)
        hit = origin + direction * distance
        pygame.draw.line(surface, CYAN, origin, hit, 1)
        corrected = distance * math.cos(angle)
        height = min(view.height - 20, 82000 / max(1.0, corrected))
        column_width = view.width / ray_count
        x = view.left + int(index * column_width)
        rect = pygame.Rect(
            x, int(view.centery - height / 2),
            int(column_width) + 1, int(height),
        )
        shade = int(85 + 75 * (1.0 - abs(amount - 0.5) * 2))
        pygame.draw.rect(surface, (shade, int(shade * 0.68), int(shade * 0.48)),
                         rect)
    if visible:
        index = visible - 1
        x = view.left + int(index / ray_count * view.width)
        pygame.draw.line(surface, AMBER, (x, 92), (x, 628), 3)
    label(surface, "distancia", (170, 610), 25, CYAN)
    label(surface, "altura", (1018, 650), 25, AMBER)


def billboard_scene(surface, local_time, demon):
    progress = phase(local_time, 0.2, 3.6)
    horizon = 340
    pygame.draw.rect(surface, (31, 25, 21), (70, 70, 1140, horizon - 70))
    pygame.draw.rect(surface, (58, 43, 32), (70, horizon, 1140, 310))
    for y in range(horizon, 650, 38):
        amount = (y - horizon) / 310
        pygame.draw.line(surface, (94, 65, 45),
                         (70 + int(amount * 380), y),
                         (1210 - int(amount * 380), y), 2)
    for x in range(120, 1210, 90):
        pygame.draw.line(surface, (50, 45, 39), (640, horizon), (x, 650), 1)

    distance = 6.0 - progress * 3.7
    size = int(1100 / distance)
    sprite = pygame.transform.smoothscale(demon, (size, size))
    bob = int(math.sin(local_time * 5.0) * 5)
    surface.blit(sprite, sprite.get_rect(midbottom=(640, 610 + bob)))
    pygame.draw.line(surface, CYAN, (640, 355), (640, 610), 2)
    pygame.draw.arc(surface, AMBER, (530, 240, 220, 220),
                    -0.7, 0.7, 4)


def occlusion_scene(surface, local_time, demon):
    progress = phase(local_time, 0.25, 4.2)
    pygame.draw.rect(surface, (24, 20, 18), (70, 70, 1140, 580))
    pygame.draw.rect(surface, (48, 36, 29), (70, 355, 1140, 295))

    sprite = pygame.transform.smoothscale(demon, (300, 300))
    sprite_rect = sprite.get_rect(midbottom=(690, 610))
    reveal = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
    reveal.blit(sprite, (0, 0))

    # La pared avanza sobre el sprite; la máscara actúa columna por columna.
    wall_right = int(485 + 260 * progress)
    wall = pygame.Rect(310, 145, wall_right - 310, 465)
    pygame.draw.rect(surface, (72, 54, 43), wall)
    pygame.draw.rect(surface, RUST, wall, 5)

    visible_start = max(0, wall_right - sprite_rect.left)
    if visible_start < sprite_rect.width:
        source = pygame.Rect(visible_start, 0,
                             sprite_rect.width - visible_start,
                             sprite_rect.height)
        surface.blit(reveal, (sprite_rect.left + visible_start, sprite_rect.top),
                     source)

    bar = pygame.Rect(300, 95, 680, 16)
    pygame.draw.rect(surface, (30, 28, 25), bar)
    for x in range(bar.width):
        world_x = 310 + x
        color = RED if world_x < wall_right else GREEN
        pygame.draw.line(surface, color,
                         (bar.x + x, bar.y), (bar.x + x, bar.bottom), 1)
    label(surface, "depth_buffer", (640, 130), 32, CYAN, center=True)


def draw_frame(surface, time_value):
    surface.fill(BLACK)
    pygame.draw.rect(surface, DARK, (34, 34, 1212, 652), 3, border_radius=18)
    if time_value < 5.0:
        projection_scene(surface, time_value)
    elif time_value < 9.0:
        billboard_scene(surface, time_value - 5.0, draw_frame.demon)
    else:
        occlusion_scene(surface, time_value - 9.0, draw_frame.demon)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    draw_frame.demon = load_image(
        "assets/enemies/demon_idle.png", (512, 512)
    )
    pygame.display.quit()
    run(draw_frame, DURATION, "04 — renderer.py: proyección y oclusión")


if __name__ == "__main__":
    main()
