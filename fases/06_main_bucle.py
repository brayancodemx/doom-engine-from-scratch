"""MAIN.PY — Game coordina update y draw sesenta veces por segundo."""

import math

import pygame

from animacion_base import (
    AMBER, BLACK, CYAN, DARK, GREEN, RED, RUST, STEEL, WHITE,
    arrow, glow_circle, label, phase, pulse, run,
)

DURATION = 11.5

MODULES = (
    ("map_data", (175, 150), STEEL),
    ("entities", (175, 570), GREEN),
    ("raycasting", (1105, 150), CYAN),
    ("renderer", (1105, 570), AMBER),
    ("audio", (640, 100), RED),
)


def module(surface, name, position, color, active):
    radius = 44 + int(active * 8)
    glow_circle(surface, color, position, radius, int(12 + active * 18))
    label(surface, name, (position[0], position[1] + 72),
          20, WHITE, center=True)


def coordinator_scene(surface, local_time):
    center = (640, 360)
    pygame.draw.circle(surface, (28, 23, 19), center, 110)
    pygame.draw.circle(surface, STEEL, center, 110, 5)
    label(surface, "Game", center, 46, WHITE, center=True)
    progress = phase(local_time, 0.3, 4.2)
    for index, (name, position, color) in enumerate(MODULES):
        activation = phase(progress, index * 0.12, min(1.0, index * 0.12 + 0.4))
        module(surface, name, position, color, activation)
        endpoint = (
            int(position[0] + (center[0] - position[0]) * activation),
            int(position[1] + (center[1] - position[1]) * activation),
        )
        pygame.draw.line(surface, color, position, endpoint, 4)
        pygame.draw.circle(surface, color, endpoint, 7)

    ring = 128 + int(pulse(local_time, 1.3) * 14)
    pygame.draw.circle(surface, AMBER, center, ring, 3)


def loop_scene(surface, local_time):
    left = pygame.Rect(90, 115, 490, 500)
    right = pygame.Rect(700, 115, 490, 500)
    pygame.draw.rect(surface, (18, 17, 16), left, border_radius=18)
    pygame.draw.rect(surface, (18, 17, 16), right, border_radius=18)
    pygame.draw.rect(surface, GREEN, left, 4, border_radius=18)
    pygame.draw.rect(surface, AMBER, right, 4, border_radius=18)
    label(surface, "update", (left.centerx, 155), 37, GREEN, center=True)
    label(surface, "draw", (right.centerx, 155), 37, AMBER, center=True)

    cycle = (local_time * 2.0) % 2.0
    update_active = cycle < 1.0
    cycle_progress = cycle if update_active else cycle - 1.0
    amount = phase(cycle_progress, 0.05, 0.9)

    # update: los datos cambian sin pintar todavía un fotograma nuevo.
    player_start = pygame.Vector2(190, 500)
    player_end = pygame.Vector2(465, 290)
    data_position = player_start.lerp(player_end, amount)
    glow_circle(surface, GREEN,
                (int(data_position.x), int(data_position.y)), 16, 10)
    enemy_x = int(470 - amount * 115)
    pygame.draw.circle(surface, RED, (enemy_x, 410), 22)
    for index in range(6):
        angle = local_time * 2 + index * math.tau / 6
        pygame.draw.circle(surface, CYAN,
                           (int(340 + math.cos(angle) * 85),
                            int(370 + math.sin(angle) * 85)), 4)

    # draw: una fotografía de esos datos se convierte en columnas visibles.
    column_count = int(24 * amount) if not update_active else 0
    for index in range(column_count):
        x = right.x + 28 + index * 18
        height = 110 + int(math.sin(index * 0.42) * 54)
        pygame.draw.rect(surface, (113, 72, 46),
                         (x, right.centery - height // 2, 15, height))
    if not update_active:
        pygame.draw.circle(surface, RED, (right.centerx + 90, 385), 42)
        pygame.draw.circle(surface, WHITE, (right.centerx, 370), 8, 2)

    active_rect = left if update_active else right
    active_color = GREEN if update_active else AMBER
    pygame.draw.rect(surface, active_color, active_rect.inflate(14, 14),
                     3, border_radius=24)
    arrow(surface, CYAN, (590, 365), (690, 365), 5, 15)

    # Sesenta pulsos circulares hacen visible el ritmo del bucle.
    for index in range(60):
        angle = index * math.tau / 60
        position = (
            640 + int(math.cos(angle) * 305),
            365 + int(math.sin(angle) * 300),
        )
        active = index <= int((local_time % 1.0) * 60)
        pygame.draw.circle(surface, CYAN if active else (47, 48, 44),
                           position, 3)
    label(surface, "60 FPS", (640, 665), 28, CYAN, center=True)


def draw_frame(surface, time_value):
    surface.fill(BLACK)
    pygame.draw.rect(surface, DARK, (34, 34, 1212, 652), 3, border_radius=18)
    if time_value < 5.0:
        coordinator_scene(surface, time_value)
    else:
        loop_scene(surface, time_value - 5.0)


def main():
    run(draw_frame, DURATION, "06 — main.py: coordinación, update y draw")


if __name__ == "__main__":
    main()
