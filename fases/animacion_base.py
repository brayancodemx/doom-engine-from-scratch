"""Utilidades compartidas para las animaciones visuales del guion."""

import argparse
import math
from pathlib import Path

import pygame

WIDTH = 1280
HEIGHT = 720
FPS = 60

BLACK = (7, 7, 8)
DARK = (20, 16, 14)
STEEL = (112, 105, 92)
RUST = (132, 49, 27)
RED = (218, 42, 25)
AMBER = (231, 148, 55)
BONE = (218, 204, 170)
GREEN = (132, 175, 88)
CYAN = (52, 210, 224)
WHITE = (239, 233, 214)

ROOT = Path(__file__).resolve().parents[1]


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def smooth(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def phase(time_value, start, end):
    if end <= start:
        return 1.0
    return smooth((time_value - start) / (end - start))


def lerp(start, end, amount):
    return start + (end - start) * amount


def point_lerp(start, end, amount):
    return (
        int(lerp(start[0], end[0], amount)),
        int(lerp(start[1], end[1], amount)),
    )


def pulse(time_value, speed=1.0):
    return (math.sin(time_value * speed * math.tau) + 1.0) * 0.5


def font(size, bold=False):
    return pygame.font.SysFont("consolas", size, bold=bold)


def label(surface, text, position, size=22, color=WHITE, center=False):
    rendered = font(size, bold=True).render(text, True, color)
    rect = rendered.get_rect(center=position) if center else rendered.get_rect(topleft=position)
    surface.blit(rendered, rect)
    return rect


def glow_circle(surface, color, center, radius, glow=18):
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for extra, alpha in ((glow, 18), (glow // 2, 42), (2, 120)):
        pygame.draw.circle(layer, (*color, alpha), center, radius + extra)
    surface.blit(layer, (0, 0))
    pygame.draw.circle(surface, color, center, radius)


def arrow(surface, color, start, end, width=4, head=13):
    pygame.draw.line(surface, color, start, end, width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    left = (
        end[0] - math.cos(angle - 0.55) * head,
        end[1] - math.sin(angle - 0.55) * head,
    )
    right = (
        end[0] - math.cos(angle + 0.55) * head,
        end[1] - math.sin(angle + 0.55) * head,
    )
    pygame.draw.polygon(surface, color, (end, left, right))


def draw_scanlines(surface, alpha=20):
    layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for y in range(0, surface.get_height(), 4):
        pygame.draw.line(layer, (0, 0, 0, alpha), (0, y), (surface.get_width(), y))
    surface.blit(layer, (0, 0))


def load_image(relative_path, size=None):
    path = ROOT / relative_path
    image = pygame.image.load(str(path)).convert_alpha()
    if size:
        image = pygame.transform.smoothscale(image, size)
    return image


def draw_watermark(surface):
    """Añade una firma discreta y consistente a todas las animaciones."""
    text = pygame.font.SysFont("consolas", 24, bold=True).render(
        "BrayanCode", True, WHITE
    )
    text.set_alpha(170)
    plate = pygame.Surface((text.get_width() + 32, text.get_height() + 14),
                           pygame.SRCALPHA)
    plate.fill((7, 7, 8, 82))
    pygame.draw.line(
        plate, (*RUST, 145),
        (8, plate.get_height() - 3),
        (plate.get_width() - 8, plate.get_height() - 3),
        2,
    )
    plate.blit(text, (16, 4))
    surface.blit(
        plate,
        ((surface.get_width() - plate.get_width()) // 2, 12),
    )


def run(draw_frame, duration, caption):
    parser = argparse.ArgumentParser(description=caption)
    parser.add_argument("--captura", type=Path, help="Guarda un PNG y termina.")
    parser.add_argument("--tiempo", type=float, default=duration * 0.55)
    parser.add_argument("--sin-loop", action="store_true")
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(caption)
    canvas = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    if args.captura:
        draw_frame(canvas, clamp(args.tiempo, 0.0, duration))
        draw_watermark(canvas)
        args.captura.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(canvas, str(args.captura))
        pygame.quit()
        return

    elapsed = 0.0
    paused = False
    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    elapsed = 0.0
                elif event.key == pygame.K_LEFT:
                    elapsed = max(0.0, elapsed - 0.5)
                elif event.key == pygame.K_RIGHT:
                    elapsed = min(duration, elapsed + 0.5)

        if not paused:
            elapsed += dt
            if elapsed >= duration:
                if args.sin_loop:
                    elapsed = duration
                    paused = True
                else:
                    elapsed %= duration

        draw_frame(canvas, elapsed)
        draw_watermark(canvas)
        screen.blit(canvas, (0, 0))
        pygame.display.flip()

    pygame.quit()
