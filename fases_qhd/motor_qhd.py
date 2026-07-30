"""Motor común para animaciones renderizadas de forma nativa a 2560×1440."""

import argparse
import math
from pathlib import Path

import pygame

BASE_WIDTH = 1280
BASE_HEIGHT = 720
SCALE = 2
WIDTH = BASE_WIDTH * SCALE
HEIGHT = BASE_HEIGHT * SCALE
FPS = 60
EXPORT_FPS = 30

ROOT = Path(__file__).resolve().parents[1]

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

_FONT_CACHE = {}
_IMAGE_CACHE = {}


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def smooth(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def phase(time_value, start, end):
    if end <= start:
        return 1.0
    return smooth((time_value - start) / (end - start))


def pulse(time_value, speed=1.0):
    return (math.sin(time_value * speed * math.tau) + 1.0) * 0.5


def scaled(value):
    return int(round(value * SCALE))


def point(position):
    return scaled(position[0]), scaled(position[1])


def rect(value):
    if isinstance(value, pygame.Rect):
        value = (value.x, value.y, value.width, value.height)
    return pygame.Rect(*(scaled(component) for component in value))


def font(size, bold=False):
    key = (size, bold)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = pygame.font.SysFont(
            "consolas", scaled(size), bold=bold
        )
    return _FONT_CACHE[key]


def load_asset(relative_path, logical_size=None, smooth_image=False):
    key = (relative_path, logical_size, smooth_image)
    if key not in _IMAGE_CACHE:
        image = pygame.image.load(str(ROOT / relative_path)).convert_alpha()
        if logical_size:
            target = point(logical_size)
            transform = (
                pygame.transform.smoothscale
                if smooth_image else pygame.transform.scale
            )
            image = transform(image, target)
        _IMAGE_CACHE[key] = image
    return _IMAGE_CACHE[key]


class Canvas:
    """Dibuja con coordenadas lógicas 1280×720 sobre un lienzo QHD real."""

    def __init__(self, surface):
        self.surface = surface

    def fill(self, color):
        self.surface.fill(color)

    def rect(self, color, value, width=0, radius=0):
        pygame.draw.rect(
            self.surface, color, rect(value), scaled(width),
            border_radius=scaled(radius),
        )

    def line(self, color, start, end, width=1):
        pygame.draw.line(
            self.surface, color, point(start), point(end), max(1, scaled(width))
        )

    def circle(self, color, center, radius, width=0):
        pygame.draw.circle(
            self.surface, color, point(center), scaled(radius), scaled(width)
        )

    def polygon(self, color, points, width=0):
        pygame.draw.polygon(
            self.surface, color, tuple(point(item) for item in points),
            scaled(width),
        )

    def label(self, text, position, size=22, color=WHITE, center=False,
              alpha=255):
        rendered = font(size, bold=True).render(text, True, color)
        if alpha != 255:
            rendered.set_alpha(alpha)
        target = point(position)
        destination = (
            rendered.get_rect(center=target)
            if center else rendered.get_rect(topleft=target)
        )
        self.surface.blit(rendered, destination)
        return destination

    def image(self, relative_path, logical_size, position, anchor="center",
              alpha=255, smooth_image=False):
        image = load_asset(
            relative_path, logical_size, smooth_image=smooth_image
        ).copy()
        if alpha != 255:
            image.set_alpha(alpha)
        target = point(position)
        image_rect = image.get_rect()
        setattr(image_rect, anchor, target)
        self.surface.blit(image, image_rect)
        return image_rect

    def glow(self, color, center, radius, glow=18):
        layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        target = point(center)
        for extra, alpha in ((glow, 18), (glow // 2, 42), (2, 120)):
            pygame.draw.circle(
                layer, (*color, alpha), target, scaled(radius + extra)
            )
        self.surface.blit(layer, (0, 0))
        self.circle(color, center, radius)

    def arrow(self, color, start, end, width=4, head=13):
        self.line(color, start, end, width)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        left = (
            end[0] - math.cos(angle - 0.55) * head,
            end[1] - math.sin(angle - 0.55) * head,
        )
        right = (
            end[0] - math.cos(angle + 0.55) * head,
            end[1] - math.sin(angle + 0.55) * head,
        )
        self.polygon(color, (end, left, right))

    def waveform(self, area, color, time_value, strength=1.0, jagged=False):
        logical = pygame.Rect(area)
        points = []
        for x in range(logical.width):
            normalized = x / max(1, logical.width - 1)
            carrier = math.sin(
                normalized * math.tau * (12 if jagged else 6)
                + time_value * 10
            )
            detail = math.sin(
                normalized * math.tau * 31 - time_value * 7
            ) * 0.36
            envelope = math.sin(normalized * math.pi)
            y = logical.centery + (
                carrier + detail
            ) * logical.height * 0.32 * envelope * strength
            points.append(point((logical.x + x, y)))
        if len(points) > 1:
            pygame.draw.lines(self.surface, color, False, points, scaled(2))


def draw_frame(surface, scene, time_value, watermark=True):
    canvas = Canvas(surface)
    scene.draw(canvas, time_value)
    if watermark:
        draw_watermark(canvas)


def draw_watermark(canvas):
    text = font(28, bold=True).render("BrayanCode", True, WHITE)
    text.set_alpha(178)
    plate = pygame.Surface(
        (text.get_width() + scaled(38), text.get_height() + scaled(16)),
        pygame.SRCALPHA,
    )
    plate.fill((7, 7, 8, 84))
    pygame.draw.line(
        plate, (*RUST, 155),
        (scaled(10), plate.get_height() - scaled(3)),
        (plate.get_width() - scaled(10), plate.get_height() - scaled(3)),
        scaled(2),
    )
    plate.blit(text, (scaled(19), scaled(4)))
    canvas.surface.blit(
        plate, ((WIDTH - plate.get_width()) // 2, scaled(12))
    )


def initialize_hidden():
    pygame.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((1, 1), pygame.HIDDEN)


def run_scene(scene_key):
    from escenas_qhd import SCENES

    scene = SCENES[scene_key]
    parser = argparse.ArgumentParser(description=scene.caption)
    parser.add_argument("--pantalla-completa", "--fullscreen",
                        action="store_true")
    parser.add_argument("--captura", type=Path)
    parser.add_argument("--tiempo", type=float, default=scene.duration * 0.55)
    parser.add_argument("--sin-loop", action="store_true")
    args = parser.parse_args()

    pygame.init()
    if args.captura:
        pygame.display.set_mode((1, 1), pygame.HIDDEN)
        output = pygame.Surface((WIDTH, HEIGHT))
        draw_frame(output, scene, clamp(args.tiempo, 0.0, scene.duration))
        args.captura.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(output, str(args.captura))
        pygame.quit()
        return

    desktop = pygame.display.get_desktop_sizes()[0]
    if args.pantalla_completa:
        screen = pygame.display.set_mode(desktop, pygame.FULLSCREEN)
    else:
        preview = (
            min(1600, desktop[0] - 120),
            min(900, desktop[1] - 120),
        )
        screen = pygame.display.set_mode(preview, pygame.RESIZABLE)
    pygame.display.set_caption(scene.caption)
    output = pygame.Surface((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
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
                    elapsed = min(scene.duration, elapsed + 0.5)

        if not paused:
            elapsed += dt
            if elapsed >= scene.duration:
                if args.sin_loop:
                    elapsed = scene.duration
                    paused = True
                else:
                    elapsed %= scene.duration

        draw_frame(output, scene, elapsed)
        size = screen.get_size()
        ratio = min(size[0] / WIDTH, size[1] / HEIGHT)
        presented_size = (
            max(1, int(WIDTH * ratio)), max(1, int(HEIGHT * ratio))
        )
        presented = pygame.transform.smoothscale(output, presented_size)
        screen.fill(BLACK)
        screen.blit(
            presented,
            ((size[0] - presented_size[0]) // 2,
             (size[1] - presented_size[1]) // 2),
        )
        pygame.display.flip()

    pygame.quit()
