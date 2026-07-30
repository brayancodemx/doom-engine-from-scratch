"""ENTITIES.PY — trigonometría, dt, colisión deslizante y persecución."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from animacion_base import (
    AMBER, BLACK, BONE, CYAN, DARK, GREEN, RED, RUST, STEEL, WHITE,
    arrow, glow_circle, label, load_image, phase, run,
)

DURATION = 15.5


def grid(surface):
    for x in range(0, 1280, 40):
        pygame.draw.line(surface, (28, 25, 22), (x, 0), (x, 720))
    for y in range(0, 720, 40):
        pygame.draw.line(surface, (28, 25, 22), (0, y), (1280, y))


def draw_player(surface, position, angle=0.0, radius=18):
    glow_circle(surface, AMBER, position, radius, 10)
    direction = (
        position[0] + int(math.cos(angle) * 42),
        position[1] + int(math.sin(angle) * 42),
    )
    arrow(surface, WHITE, position, direction, 4, 12)


def trig_scene(surface, local_time):
    center = (400, 360)
    angle = -0.58
    amount = phase(local_time, 0.4, 2.8)
    length = int(235 * amount)
    end = (
        center[0] + int(math.cos(angle) * length),
        center[1] + int(math.sin(angle) * length),
    )
    draw_player(surface, center, angle)
    arrow(surface, AMBER, center, end, 5, 16)
    corner = (end[0], center[1])
    if amount > 0.2:
        arrow(surface, CYAN, center, corner, 4, 13)
        arrow(surface, GREEN, corner, end, 4, 13)
        label(surface, "cos(ángulo)", (430, 390), 26, CYAN)
        label(surface, "sin(ángulo)", (650, 270), 26, GREEN)
    pygame.draw.arc(surface, RUST, (center[0] - 74, center[1] - 74, 148, 148),
                    angle, 0, 4)


def dt_scene(surface, local_time):
    divider = 640
    pygame.draw.line(surface, STEEL, (divider, 72), (divider, 648), 2)
    label(surface, "60 FPS", (320, 110), 31, CYAN, center=True)
    label(surface, "300 FPS", (960, 110), 31, AMBER, center=True)
    label(surface, "dt", (640, 605), 44, GREEN, center=True)
    progress = phase(local_time, 0.5, 3.1)
    start_y, end_y = 520, 210
    y = int(start_y + (end_y - start_y) * progress)
    for side_x, color, count in ((320, CYAN, 12), (960, AMBER, 38)):
        pygame.draw.line(surface, (55, 50, 43), (side_x, start_y),
                         (side_x, end_y), 5)
        visible = int(count * progress)
        for index in range(visible):
            dot_y = int(start_y + (end_y - start_y) * index / max(1, count - 1))
            pygame.draw.circle(surface, color, (side_x, dot_y), 3)
        draw_player(surface, (side_x, y), -math.pi / 2, 15)
    pygame.draw.line(surface, GREEN, (190, end_y), (1090, end_y), 3)


def collision_scene(surface, local_time):
    wall = pygame.Rect(690, 90, 130, 550)
    pygame.draw.rect(surface, (58, 46, 38), wall)
    for y in range(wall.top, wall.bottom, 46):
        pygame.draw.line(surface, RUST, (wall.left, y), (wall.right, y), 2)
    pygame.draw.rect(surface, STEEL, wall, 4)

    start = pygame.Vector2(270, 560)
    target = pygame.Vector2(785, 190)
    first = phase(local_time, 0.2, 1.8)
    contact = pygame.Vector2(675, 270)
    if first < 1.0:
        position = start.lerp(contact, first)
    else:
        slide = phase(local_time, 1.8, 3.4)
        position = contact.lerp((675, 125), slide)
    draw_player(surface, (int(position.x), int(position.y)), -0.62)
    arrow(surface, RED, (int(position.x), int(position.y)),
          (int(position.x + 95), int(position.y - 68)), 4, 13)
    if first >= 0.75:
        arrow(surface, GREEN, (int(position.x), int(position.y)),
              (int(position.x), int(position.y - 118)), 5, 15)
        pygame.draw.line(surface, (90, 35, 26),
                         (wall.left, int(position.y)),
                         (wall.left + 60, int(position.y)), 6)


def path_scene(surface, local_time, demon):
    pillar = pygame.Rect(545, 205, 190, 300)
    pygame.draw.rect(surface, (54, 45, 38), pillar)
    pygame.draw.rect(surface, RUST, pillar, 5)
    player = (1010, 350)
    draw_player(surface, player, math.pi, 17)
    route = [(220, 350), (440, 350), (475, 555), (805, 555), player]
    progress = phase(local_time, 0.25, 3.4)
    total_segments = len(route) - 1
    segment_value = progress * total_segments
    segment = min(total_segments - 1, int(segment_value))
    segment_progress = segment_value - segment
    position = pygame.Vector2(route[segment]).lerp(route[segment + 1],
                                                   segment_progress)
    pygame.draw.line(surface, RED, route[0], player, 3)
    for index in range(total_segments):
        color = GREEN if index <= segment else (50, 72, 48)
        pygame.draw.line(surface, color, route[index], route[index + 1], 6)
        pygame.draw.circle(surface, color, route[index], 7)
    image = demon.copy()
    surface.blit(image, image.get_rect(center=(int(position.x), int(position.y))))


def draw_frame(surface, time_value):
    surface.fill(BLACK)
    grid(surface)
    pygame.draw.rect(surface, DARK, (34, 34, 1212, 652), 3, border_radius=18)
    if time_value < 3.8:
        trig_scene(surface, time_value)
    elif time_value < 7.5:
        dt_scene(surface, time_value - 3.8)
    elif time_value < 11.3:
        collision_scene(surface, time_value - 7.5)
    else:
        path_scene(surface, time_value - 11.3, draw_frame.demon)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    draw_frame.demon = load_image(
        "assets/enemies/demon_walk_a.png", (78, 78)
    )
    pygame.display.quit()
    run(draw_frame, DURATION, "02 — entities.py: movimiento y persecución")


if __name__ == "__main__":
    main()
