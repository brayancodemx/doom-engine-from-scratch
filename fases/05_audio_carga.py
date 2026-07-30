"""AUDIO.PY — carga de disparos, recarga, demonios y música."""

import math

import pygame

from animacion_base import (
    AMBER, BLACK, CYAN, DARK, GREEN, RED, RUST, STEEL, WHITE,
    label, load_image, phase, pulse, run,
)

DURATION = 10.5

SOURCES = (
    ("disparo.mp3", (132, 160), CYAN),
    ("escopeta.mp3", (132, 290), AMBER),
    ("escopeta2.mp3", (132, 420), GREEN),
    ("monster1.mp3", (132, 550), RED),
)


def waveform(surface, rect, color, time_value, strength=1.0, jagged=False):
    points = []
    for x in range(rect.width):
        normalized = x / max(1, rect.width - 1)
        carrier = math.sin(normalized * math.tau * (12 if jagged else 6)
                           + time_value * 10)
        detail = math.sin(normalized * math.tau * 31 - time_value * 7) * 0.36
        envelope = math.sin(normalized * math.pi)
        y = rect.centery + int((carrier + detail) * rect.height * 0.32
                               * envelope * strength)
        points.append((rect.x + x, y))
    if len(points) > 1:
        pygame.draw.lines(surface, color, False, points, 3)


def draw_file(surface, name, position, color, progress):
    x, y = position
    rect = pygame.Rect(x - 82, y - 42, 164, 84)
    pygame.draw.rect(surface, (21, 20, 18), rect, border_radius=10)
    pygame.draw.rect(surface, color, rect, 3, border_radius=10)
    waveform(surface, pygame.Rect(rect.x + 10, rect.y + 10,
                                  rect.width - 20, 28),
             color, progress * 4, 0.55)
    label(surface, name, (x, rect.bottom - 20), 17, WHITE, center=True)


def draw_frame(surface, time_value):
    surface.fill(BLACK)
    pygame.draw.rect(surface, DARK, (34, 34, 1212, 652), 3, border_radius=18)

    center = pygame.Rect(504, 250, 272, 220)
    pygame.draw.rect(surface, (19, 17, 15), center, border_radius=22)
    pygame.draw.rect(surface, STEEL, center, 4, border_radius=22)
    label(surface, "Sounds", center.center, 44, WHITE, center=True)

    load_progress = phase(time_value, 0.4, 4.2)
    for index, (name, start, color) in enumerate(SOURCES):
        delay = index * 0.13
        item_progress = phase(load_progress, delay, min(1.0, delay + 0.42))
        draw_file(surface, name, start, color, item_progress)
        endpoint = (center.left, center.y + 38 + index * 48)
        current = (
            int(start[0] + (endpoint[0] - start[0]) * item_progress),
            int(start[1] + (endpoint[1] - start[1]) * item_progress),
        )
        pygame.draw.line(surface, color, start, current, 4)
        pygame.draw.circle(surface, color, current, 7)

    output_progress = phase(time_value, 4.0, 7.4)
    events = (
        (draw_frame.rifle, (952, 150), CYAN, 0.0),
        (draw_frame.shotgun, (952, 355), AMBER, 0.18),
        (draw_frame.demon, (1010, 570), RED, 0.36),
    )
    for image, position, color, delay in events:
        event_progress = phase(output_progress, delay, min(1.0, delay + 0.45))
        start = (center.right, center.centery)
        current = (
            int(start[0] + (position[0] - start[0]) * event_progress),
            int(start[1] + (position[1] - start[1]) * event_progress),
        )
        pygame.draw.line(surface, color, start, current, 4)
        if event_progress > 0.5:
            alpha = int(255 * min(1.0, (event_progress - 0.5) * 3))
            copy = image.copy()
            copy.set_alpha(alpha)
            surface.blit(copy, copy.get_rect(center=position))
            radius = int(45 + pulse(time_value, 2.2) * 20)
            pygame.draw.circle(surface, color, position, radius, 3)

    # La última parte representa únicamente la música mencionada en el guion.
    music = phase(time_value, 7.4, 10.0)
    if music > 0:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((90, 14, 5, int(80 * music)))
        surface.blit(overlay, (0, 0))
        waveform(surface, pygame.Rect(70, 625, 1140, 70),
                 AMBER, time_value, music, jagged=True)
        for index in range(18):
            height = int((30 + 50 * abs(math.sin(time_value * 4 + index)))
                         * music)
            pygame.draw.rect(surface, RUST,
                             (90 + index * 62, 610 - height, 32, height))


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    draw_frame.rifle = load_image(
        "assets/weapons/doom_rifle.png", (250, 141)
    )
    draw_frame.shotgun = load_image(
        "assets/weapons/doom_shotgun_open.png", (250, 141)
    )
    draw_frame.demon = load_image(
        "assets/enemies/demon_attack_strike.png", (150, 150)
    )
    pygame.display.quit()
    run(draw_frame, DURATION, "05 — audio.py: carga y eventos sonoros")


if __name__ == "__main__":
    main()
