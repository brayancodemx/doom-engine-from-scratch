"""Escenas QHD nativas basadas exclusivamente en las explicaciones del guion."""

from dataclasses import dataclass
import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from map_data import MAP
from motor_qhd import (
    AMBER, BLACK, BONE, CYAN, DARK, GREEN, RED, RUST, SCALE, STEEL,
    WHITE, Canvas, load_asset, phase, point, pulse, rect, scaled,
)
from pipeline_real_qhd import draw_pipeline_real


@dataclass(frozen=True)
class Scene:
    key: str
    filename: str
    caption: str
    duration: float
    draw: object


def frame(c):
    c.fill(BLACK)
    c.rect(DARK, (34, 34, 1212, 652), 3, 18)


def draw_player(c, position, angle=0.0, radius=18):
    c.glow(AMBER, position, radius, 10)
    direction = (
        position[0] + math.cos(angle) * 42,
        position[1] + math.sin(angle) * 42,
    )
    c.arrow(WHITE, position, direction, 4, 12)


def draw_grid(c, step=40):
    for x in range(0, 1281, step):
        c.line((28, 25, 22), (x, 0), (x, 720), 1)
    for y in range(0, 721, step):
        c.line((28, 25, 22), (0, y), (1280, y), 1)


def scene_map_data(c, t):
    frame(c)
    c.rect((12, 10, 9), (704, 104, 500, 510), radius=18)
    c.line(RUST, (704, 104), (1204, 104), 4)
    cell = 27
    ox, oy = 76, 88
    blocks = phase(t, 0.5, 3.0)
    colors = {"1": STEEL, "2": RUST, "3": GREEN,
              "4": AMBER, "5": BONE, "6": RED}

    for y, row in enumerate(MAP):
        for x, tile in enumerate(row):
            area = (ox + x * cell, oy + y * cell, cell - 1, cell - 1)
            if tile == ".":
                color = (25, 27, 26)
                border = (62, 61, 54)
            else:
                border = colors.get(tile, STEEL)
                color = tuple(int(channel * 0.42) for channel in border)
            c.rect(color, area)
            c.rect(border, area, 1)
            if blocks < 0.92:
                c.label(tile, (area[0] + cell / 2, area[1] + cell / 2),
                        16, WHITE, center=True, alpha=int(255 * (1 - blocks)))

    if t >= 3.2:
        progress = phase(t, 3.2, 6.0)
        target = (5, 5)
        row_width = (target[0] + 1) * cell * min(1.0, progress * 2)
        overlay = pygame.Surface(
            (scaled(row_width), scaled(cell)), pygame.SRCALPHA
        )
        overlay.fill((*CYAN, 55))
        c.surface.blit(overlay, point((ox, oy + target[1] * cell)))
        if progress > 0.5:
            c.rect(AMBER, (ox + target[0] * cell, oy + target[1] * cell,
                           cell - 1, cell - 1), 4)
            c.label("MAP[y][x]", (780, 168), 34, CYAN)
            c.label("MAP[5][5]  →  2", (780, 220), 28, AMBER)

    if t >= 6.1:
        exact = (ox + 2.7 * cell, oy + 4.2 * cell)
        c.rect(GREEN, (ox + 2 * cell, oy + 4 * cell, cell - 1, cell - 1), 3)
        c.glow(AMBER, exact, 8, 12)
        c.line(CYAN, exact, (ox + 2.5 * cell, oy + 4.5 * cell), 2)
        c.label("x = 2.7", (780, 310), 28)
        c.label("y = 4.2", (780, 350), 28)
        if phase(t, 6.1, 9.2) > 0.48:
            c.label("(2, 4)", (850, 420), 42, GREEN, center=True)

    if t >= 9.3:
        progress = phase(t, 9.3, 12.8)
        wall = (ox + 5.5 * cell, oy + 5.5 * cell)
        free = (ox + 7.5 * cell, oy + 4.5 * cell)
        move = phase(progress, 0.45, 0.8)
        position = (
            wall[0] + (free[0] - wall[0]) * move,
            wall[1] + (free[1] - wall[1]) * move,
        )
        c.image("assets/enemies/demon_idle.png", (58, 58), position)
        if move < 0.05:
            c.line(RED, (wall[0] - 24, wall[1] - 24),
                   (wall[0] + 24, wall[1] + 24), 7)
            c.line(RED, (wall[0] + 24, wall[1] - 24),
                   (wall[0] - 24, wall[1] + 24), 7)
        else:
            c.rect(GREEN, (ox + 7 * cell, oy + 4 * cell,
                           cell - 1, cell - 1), 4)
        c.label("is_wall", (790, 512), 30, RED if move < 0.05 else GREEN)


def scene_entities(c, t):
    frame(c)
    draw_grid(c)
    if t < 3.8:
        center = (400, 360)
        angle = -0.58
        amount = phase(t, 0.4, 2.8)
        end = (
            center[0] + math.cos(angle) * 235 * amount,
            center[1] + math.sin(angle) * 235 * amount,
        )
        draw_player(c, center, angle)
        c.arrow(AMBER, center, end, 5, 16)
        corner = (end[0], center[1])
        if amount > 0.2:
            c.arrow(CYAN, center, corner, 4, 13)
            c.arrow(GREEN, corner, end, 4, 13)
            c.label("cos(ángulo)", (430, 390), 26, CYAN)
            c.label("sin(ángulo)", (650, 270), 26, GREEN)
        return

    if t < 7.5:
        local = t - 3.8
        c.line(STEEL, (640, 72), (640, 648), 2)
        c.label("60 FPS", (320, 110), 31, CYAN, center=True)
        c.label("300 FPS", (960, 110), 31, AMBER, center=True)
        c.label("dt", (640, 605), 44, GREEN, center=True)
        progress = phase(local, 0.5, 3.1)
        y = 520 + (210 - 520) * progress
        for x, color, count in ((320, CYAN, 12), (960, AMBER, 38)):
            c.line((55, 50, 43), (x, 520), (x, 210), 5)
            for index in range(int(count * progress)):
                dot_y = 520 + (210 - 520) * index / max(1, count - 1)
                c.circle(color, (x, dot_y), 3)
            draw_player(c, (x, y), -math.pi / 2, 15)
        c.line(GREEN, (190, 210), (1090, 210), 3)
        return

    if t < 11.3:
        local = t - 7.5
        c.rect((58, 46, 38), (690, 90, 130, 550))
        for y in range(90, 640, 46):
            c.line(RUST, (690, y), (820, y), 2)
        c.rect(STEEL, (690, 90, 130, 550), 4)
        first = phase(local, 0.2, 1.8)
        start = pygame.Vector2(270, 560)
        contact = pygame.Vector2(675, 270)
        if first < 1:
            position = start.lerp(contact, first)
        else:
            position = contact.lerp((675, 125), phase(local, 1.8, 3.4))
        draw_player(c, position, -0.62)
        c.arrow(RED, position, (position.x + 95, position.y - 68), 4, 13)
        if first >= 0.75:
            c.arrow(GREEN, position, (position.x, position.y - 118), 5, 15)
        return

    local = t - 11.3
    c.rect((54, 45, 38), (545, 205, 190, 300))
    c.rect(RUST, (545, 205, 190, 300), 5)
    player = (1010, 350)
    draw_player(c, player, math.pi, 17)
    route = [(220, 350), (440, 350), (475, 555), (805, 555), player]
    progress = phase(local, 0.25, 3.4) * (len(route) - 1)
    segment = min(len(route) - 2, int(progress))
    position = pygame.Vector2(route[segment]).lerp(
        route[segment + 1], progress - segment
    )
    c.line(RED, route[0], player, 3)
    for index in range(len(route) - 1):
        color = GREEN if index <= segment else (50, 72, 48)
        c.line(color, route[index], route[index + 1], 6)
        c.circle(color, route[index], 7)
    c.image("assets/enemies/demon_walk_a.png", (78, 78), position)


def ray_grid(c):
    ox, oy, cell = 90, 90, 66
    for y in range(8):
        for x in range(10):
            wall = x == 8 or (x == 6 and 2 <= y <= 5)
            area = (ox + x * cell, oy + y * cell, cell - 1, cell - 1)
            c.rect((57, 44, 36) if wall else (18, 18, 17), area)
            c.rect(RUST if wall else (49, 46, 40), area, 1)


def scene_raycasting(c, t):
    frame(c)
    if t < 4.4:
        ray_grid(c)
        start = pygame.Vector2(189, 466.2)
        end = pygame.Vector2(618, 241.8)
        progress = phase(t, 0.4, 3.7)
        current = start.lerp(end, progress)
        c.glow(AMBER, start, 11, 12)
        c.line(CYAN, start, current, 4)
        for column in range(2, 9):
            x = 90 + column * 66
            ratio = (x - start.x) / (end.x - start.x)
            if ratio <= progress:
                y = start.y + (end.y - start.y) * ratio
                c.circle(WHITE, (x, y), 7)
                c.circle(CYAN, (x, y), 3)
        if progress >= 0.98:
            c.glow(RED, end, 10, 18)
        c.label("DDA", (905, 320), 70, CYAN, center=True)
        return

    if t < 7.5:
        ray_grid(c)
        origin = pygame.Vector2(222, 354)
        progress = phase(t - 4.4, 0.2, 2.6)
        count = 84
        for index in range(int(count * progress)):
            amount = index / (count - 1)
            angle = math.radians(-33 + amount * 66)
            end = origin + pygame.Vector2(math.cos(angle), math.sin(angle)) * 525
            color = AMBER if index == count // 2 else CYAN
            c.line(color, origin, end, 2 if color == AMBER else 1)
        c.glow(WHITE, origin, 10, 10)
        c.label("× 640", (1000, 600), 44, AMBER, center=True)
        return

    correction = phase(t - 7.5, 1.3, 4.2)
    horizon = 365
    c.rect((21, 18, 16), (70, 70, 1140, 590))
    c.rect((45, 37, 30), (70, horizon, 1140, 295))
    texture = load_asset("assets/textures/walls/wall_1_steel.png")
    columns = 128
    logical_width = 1140 / columns
    for index in range(columns):
        normalized = index / (columns - 1)
        angle = math.radians(-33 + normalized * 66)
        raw = 3.2 / max(0.2, math.cos(angle))
        corrected = raw * math.cos(angle)
        distance = raw + (corrected - raw) * correction
        height = min(520, 1280 / distance)
        destination = rect((
            70 + index * logical_width,
            horizon - height / 2,
            logical_width + 0.7,
            height,
        ))
        source_width = max(1, texture.get_width() // columns)
        source_x = min(
            texture.get_width() - source_width,
            int(normalized * (texture.get_width() - 1)),
        )
        strip = pygame.transform.scale(
            texture.subsurface(
                pygame.Rect(source_x, 0, source_width, texture.get_height())
            ),
            destination.size,
        )
        c.surface.blit(strip, destination)
        darkness = int(28 + 58 * abs(normalized - 0.5) * 2)
        shade = pygame.Surface(destination.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, darkness))
        c.surface.blit(shade, destination)
    edge = RED if correction < 0.5 else GREEN
    c.line(edge, (70, 70), (70, 660), 5)
    c.line(edge, (1210, 70), (1210, 660), 5)
    if correction > 0.18:
        c.label("× cos(Δθ)", (640, 110), 42, GREEN, center=True)


def scene_renderer(c, t):
    frame(c)
    if t < 5.0:
        origin = pygame.Vector2(220, 365)
        wall_x = 515
        progress = phase(t, 0.35, 4.5)
        count = 64
        texture = load_asset("assets/textures/walls/wall_4_hazard.png")
        c.rect((54, 43, 35), (wall_x, 105, 54, 520))
        c.rect(RUST, (wall_x, 105, 54, 520), 4)
        c.glow(AMBER, origin, 14, 12)
        c.rect((22, 20, 18), (670, 85, 520, 550))
        c.line(STEEL, (670, 360), (1190, 360), 2)
        visible = int(count * progress)
        for index in range(visible):
            amount = index / (count - 1)
            angle = math.radians(-31 + amount * 62)
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            distance = (wall_x - origin.x) / direction.x
            hit = origin + direction * distance
            c.line(CYAN, origin, hit, 1)
            height = min(530, 82000 / (distance * math.cos(angle)))
            width = 520 / count
            destination = rect((
                670 + index * width,
                360 - height / 2,
                width + 0.8,
                height,
            ))
            source_width = max(1, texture.get_width() // count)
            source_x = min(
                texture.get_width() - source_width,
                int(amount * (texture.get_width() - 1)),
            )
            strip = pygame.transform.scale(
                texture.subsurface(
                    pygame.Rect(
                        source_x, 0, source_width, texture.get_height()
                    )
                ),
                destination.size,
            )
            c.surface.blit(strip, destination)
            shade = pygame.Surface(destination.size, pygame.SRCALPHA)
            shade.fill((0, 0, 0, int(18 + abs(amount - 0.5) * 52)))
            c.surface.blit(shade, destination)
        c.label("distancia", (170, 610), 25, CYAN)
        c.label("altura", (1018, 650), 25, AMBER)
        return

    if t < 9.0:
        local = t - 5.0
        progress = phase(local, 0.2, 3.6)
        vanishing = (640, 205)
        c.rect((22, 20, 18), (70, 70, 1140, 580))
        c.rect((48, 36, 29), (70, 330, 1140, 320))

        # Paredes y suelo convergen para producir la ilusión de Ponzo:
        # los tres sprites conservan exactamente las mismas dimensiones.
        c.polygon((43, 34, 29),
                  ((70, 70), vanishing, (70, 650)))
        c.polygon((43, 34, 29),
                  ((1210, 70), vanishing, (1210, 650)))
        for edge in ((70, 70), (70, 650), (1210, 70), (1210, 650)):
            c.line(STEEL, vanishing, edge, 2)
        for index in range(1, 9):
            amount = index / 9
            y = vanishing[1] + (amount ** 2) * 445
            half_width = amount * 570
            c.line((91, 67, 49),
                   (vanishing[0] - half_width, y),
                   (vanishing[0] + half_width, y), 2)
        for x in range(140, 1210, 105):
            c.line((67, 55, 46), vanishing, (x, 650), 1)

        positions = ((285, 535), (640, 410), (995, 285))
        visible = min(3, max(0, int(progress * 4)))
        for index, position in enumerate(positions[:visible]):
            bob = math.sin(local * 4 + index) * 3
            c.image(
                "assets/enemies/demon_idle.png",
                (142, 142),
                (position[0], position[1] + bob),
                "midbottom",
            )
            if progress > 0.82:
                c.rect(
                    CYAN,
                    (position[0] - 71, position[1] - 142, 142, 142),
                    1,
                )
        return

    local = t - 9.0
    progress = phase(local, 0.25, 4.2)
    c.rect((24, 20, 18), (70, 70, 1140, 580))
    c.rect((48, 36, 29), (70, 355, 1140, 295))
    wall_right = 485 + 260 * progress
    c.image("assets/enemies/demon_idle.png", (300, 300),
            (690, 610), "midbottom")
    c.rect((72, 54, 43), (310, 145, wall_right - 310, 465))
    c.rect(RUST, (310, 145, wall_right - 310, 465), 5)
    for x in range(680):
        world_x = 310 + x
        c.line(RED if world_x < wall_right else GREEN,
               (300 + x, 95), (300 + x, 111), 1)
    c.label("depth_buffer", (640, 130), 32, CYAN, center=True)


def audio_file(c, name, position, color, amount):
    x, y = position
    c.rect((21, 20, 18), (x - 82, y - 42, 164, 84), radius=10)
    c.rect(color, (x - 82, y - 42, 164, 84), 3, 10)
    c.waveform((x - 72, y - 32, 144, 28), color, amount * 4, 0.55)
    c.label(name, (x, y + 22), 17, WHITE, center=True)


def scene_audio(c, t):
    frame(c)
    center = pygame.Rect(504, 250, 272, 220)
    sources = (
        ("disparo.mp3", (132, 160), CYAN),
        ("escopeta.mp3", (132, 290), AMBER),
        ("escopeta2.mp3", (132, 420), GREEN),
        ("monster1.mp3", (132, 550), RED),
    )
    loading = phase(t, 0.4, 4.2)
    source_states = []
    for index, (name, start, color) in enumerate(sources):
        delay = index * 0.13
        amount = phase(loading, delay, min(1.0, delay + 0.42))
        endpoint = (center.left, center.y + 38 + index * 48)
        port = (start[0] + 82, start[1])
        current = (
            port[0] + (endpoint[0] - port[0]) * amount,
            port[1] + (endpoint[1] - port[1]) * amount,
        )
        c.line(color, port, current, 4)
        c.circle(color, current, 7)
        source_states.append((name, start, color, amount))

    output = phase(t, 4.0, 7.4)
    events = (
        ("assets/weapons/doom_rifle.png", (250, 141), (952, 150), CYAN, 0.0),
        ("assets/weapons/doom_shotgun_open.png", (250, 141),
         (952, 355), AMBER, 0.18),
        ("assets/enemies/demon_attack_strike.png", (150, 150),
         (1010, 570), RED, 0.36),
    )
    event_states = []
    for path, size, position, color, delay in events:
        amount = phase(output, delay, min(1.0, delay + 0.45))
        start = center.midright
        current = (
            start[0] + (position[0] - start[0]) * amount,
            start[1] + (position[1] - start[1]) * amount,
        )
        c.line(color, start, current, 4)
        event_states.append((path, size, position, color, amount))

    # Las tarjetas y el nodo central se dibujan encima de los conectores.
    # Así las líneas parecen salir de puertos y nunca cruzan texto u ondas.
    c.rect((19, 17, 15), center, radius=22)
    c.rect(STEEL, center, 4, 22)
    c.label("Sounds", center.center, 44, WHITE, center=True)
    for name, start, color, amount in source_states:
        audio_file(c, name, start, color, amount)
    for path, size, position, color, amount in event_states:
        if amount > 0.5:
            c.image(path, size, position, alpha=int(255 * min(1, (amount - 0.5) * 3)))
            c.circle(color, position, 45 + pulse(t, 2.2) * 20, 3)

    music = phase(t, 7.4, 10.0)
    if music > 0:
        overlay = pygame.Surface((2560, 1440), pygame.SRCALPHA)
        overlay.fill((90, 14, 5, int(80 * music)))
        c.surface.blit(overlay, (0, 0))
        c.waveform((70, 625, 1140, 70), AMBER, t, music, jagged=True)
        for index in range(18):
            height = (30 + 50 * abs(math.sin(t * 4 + index))) * music
            c.rect(RUST, (90 + index * 62, 610 - height, 32, height))


def scene_main(c, t):
    frame(c)
    if t < 5.0:
        center = (640, 360)
        modules = (
            ("map_data", (175, 150), STEEL),
            ("entities", (175, 570), GREEN),
            ("raycasting", (1105, 150), CYAN),
            ("renderer", (1105, 570), AMBER),
            ("audio", (640, 100), RED),
        )
        progress = phase(t, 0.3, 4.2)
        module_states = []
        for index, (name, position, color) in enumerate(modules):
            amount = phase(progress, index * 0.12,
                           min(1.0, index * 0.12 + 0.4))
            radius = 44 + amount * 8
            direction = pygame.Vector2(center) - pygame.Vector2(position)
            if direction.length_squared() > 0:
                direction = direction.normalize()
            start = pygame.Vector2(position) + direction * radius
            destination = pygame.Vector2(center) - direction * 110
            endpoint = (
                start.x + (destination.x - start.x) * amount,
                start.y + (destination.y - start.y) * amount,
            )
            c.line(color, start, endpoint, 4)
            c.circle(color, endpoint, 7)
            module_states.append(
                (name, position, color, amount, radius)
            )

        # Los nodos cubren los extremos de las líneas y mantienen el texto
        # completamente limpio.
        c.circle((28, 23, 19), center, 110)
        c.circle(STEEL, center, 110, 5)
        c.label("Game", center, 46, WHITE, center=True)
        for name, position, color, amount, radius in module_states:
            c.glow(color, position, radius, 12 + amount * 18)
            c.label(name, (position[0], position[1] + 72),
                    20, WHITE, center=True)
        c.circle(AMBER, center, 128 + pulse(t, 1.3) * 14, 3)
        return

    local = t - 5.0
    left = pygame.Rect(90, 115, 490, 500)
    right = pygame.Rect(700, 115, 490, 500)
    c.rect((18, 17, 16), left, radius=18)
    c.rect((18, 17, 16), right, radius=18)
    c.rect(GREEN, left, 4, 18)
    c.rect(AMBER, right, 4, 18)
    c.label("update", (left.centerx, 155), 37, GREEN, center=True)
    c.label("draw", (right.centerx, 155), 37, AMBER, center=True)
    cycle = (local * 2) % 2
    updating = cycle < 1
    amount = phase(cycle if updating else cycle - 1, 0.05, 0.9)
    player = pygame.Vector2(190, 500).lerp((465, 290), amount)
    c.glow(GREEN, player, 16, 10)
    c.circle(RED, (470 - amount * 115, 410), 22)
    for index in range(6):
        angle = local * 2 + index * math.tau / 6
        c.circle(CYAN, (340 + math.cos(angle) * 85,
                        370 + math.sin(angle) * 85), 4)
    if not updating:
        for index in range(int(24 * amount)):
            x = right.x + 28 + index * 18
            height = 110 + math.sin(index * 0.42) * 54
            c.rect((113, 72, 46), (x, right.centery - height / 2, 15, height))
        c.circle(RED, (right.centerx + 90, 385), 42)
    c.rect(GREEN if updating else AMBER,
           (left if updating else right).inflate(14, 14), 3, 24)
    c.arrow(CYAN, (590, 365), (690, 365), 5, 15)
    for index in range(60):
        angle = index * math.tau / 60
        position = (640 + math.cos(angle) * 305,
                    365 + math.sin(angle) * 300)
        c.circle(CYAN if index <= int((local % 1) * 60) else (47, 48, 44),
                 position, 3)
    c.label("60 FPS", (640, 665), 28, CYAN, center=True)


def scene_pipeline(c, t):
    c.fill(BLACK)
    if t < 1.7:
        ox, oy, cell = 370, 90, 27
        for y, row in enumerate(MAP):
            for x, tile in enumerate(row):
                c.rect((79, 56, 41) if tile != "." else (20, 20, 18),
                       (ox + x * cell, oy + y * cell, cell - 1, cell - 1))
        origin = (ox + 3.4 * cell, oy + 2.7 * cell)
        count = int(80 * phase(t, 0.2, 1.6))
        for index in range(count):
            angle = 0.45 - math.radians(33) + math.radians(66) * index / 79
            length = 360
            c.line(CYAN, origin,
                   (origin[0] + math.cos(angle) * length,
                    origin[1] + math.sin(angle) * length), 1)
        c.circle(AMBER, origin, 9)
        return

    local = t - 1.7
    horizon = 350
    c.rect((24, 18, 15), (0, 0, 1280, horizon))
    c.rect((74, 48, 35), (0, horizon, 1280, 370))
    if local >= 1.0:
        # Paredes y columnas se generan directamente en QHD.
        for index in range(46):
            amount = index / 45
            height = 190 + math.sin(amount * math.pi) * 260
            shade = int(70 + 65 * math.sin(amount * math.pi))
            c.rect((shade, int(shade * 0.62), int(shade * 0.48)),
                   (index * 28, horizon - height / 2, 29, height))
        for depth in range(7):
            inset = depth * 76
            c.rect((72 - depth * 5, 45 - depth * 3, 34 - depth * 2),
                   (inset, 120 + depth * 28, 120, 420 - depth * 45))
            c.rect((72 - depth * 5, 45 - depth * 3, 34 - depth * 2),
                   (1160 - inset, 120 + depth * 28, 120, 420 - depth * 45))
    if local >= 2.1:
        c.image("assets/enemies/demon_idle.png", (250, 250),
                (470, 570), "midbottom")
        c.image("assets/enemies/demon_idle.png", (150, 150),
                (760, 480), "midbottom")
    if local >= 3.2:
        for index in range(11):
            c.line((94, 57, 38), (0, 80 + index * 24),
                   (1280, 130 + index * 19), 2)
        fog = pygame.Surface((2560, 1440), pygame.SRCALPHA)
        fog.fill((80, 25, 16, 34))
        c.surface.blit(fog, (0, 0))
    if local >= 4.2:
        offset = math.sin(t * 3) * 4
        c.line(AMBER, (0, 60 + offset), (1280, 60 + offset), 2)
    if local >= 5.0:
        for index in range(24):
            angle = index * math.tau / 24
            radius = 20 + (local - 5) * 80
            c.circle(AMBER if index % 3 else RED,
                     (640 + math.cos(angle) * radius,
                      335 + math.sin(angle) * radius), 3)
    if local >= 6.0:
        c.image("assets/weapons/doom_rifle.png", (640, 360),
                (640, 720), "midbottom")
    if local >= 7.1:
        c.circle(WHITE, (640, 360), 8, 2)
        c.line(WHITE, (620, 360), (632, 360), 2)
        c.line(WHITE, (648, 360), (660, 360), 2)
        c.rect((18, 14, 12), (0, 630, 1280, 90))
        c.rect(RUST, (0, 630, 1280, 90), 3)
        c.rect((20, 17, 14), (1125, 18, 135, 135))
        c.rect(STEEL, (1125, 18, 135, 135), 3)
    if local >= 8.3:
        red = pygame.Surface((2560, 1440), pygame.SRCALPHA)
        red.fill((190, 12, 15, 42))
        c.surface.blit(red, (0, 0))
        scanlines = pygame.Surface((2560, 1440), pygame.SRCALPHA)
        for y in range(0, 1440, 8):
            pygame.draw.line(scanlines, (0, 0, 0, 28),
                             (0, y), (2560, y), 2)
        c.surface.blit(scanlines, (0, 0))
    for index in range(10):
        active = index <= min(9, int(local / 1.05))
        c.circle(AMBER if active else (47, 40, 34),
                 (485 + index * 35, 70), 6)


SCENES = {
    "01": Scene("01", "01_map_data_matriz_qhd",
                "01 QHD — map_data.py: el mapa es una matriz",
                13.0, scene_map_data),
    "02": Scene("02", "02_entities_movimiento_qhd",
                "02 QHD — entities.py: movimiento y persecución",
                15.5, scene_entities),
    "03": Scene("03", "03_raycasting_dda_qhd",
                "03 QHD — raycasting.py: DDA y ojo de pez",
                13.0, scene_raycasting),
    "04": Scene("04", "04_renderer_proyeccion_qhd",
                "04 QHD — renderer.py: proyección y oclusión",
                14.5, scene_renderer),
    "05": Scene("05", "05_audio_carga_qhd",
                "05 QHD — audio.py: carga y eventos sonoros",
                10.5, scene_audio),
    "06": Scene("06", "06_main_bucle_qhd",
                "06 QHD — main.py: coordinación, update y draw",
                11.5, scene_main),
    "07": Scene("07", "07_pipeline_fotograma_qhd",
                "07 QHD — composición de un fotograma",
                14.0, scene_pipeline),
    "08": Scene("08", "08_pipeline_real_qhd",
                "08 QHD — pipeline real por capas",
                52.0, draw_pipeline_real),
}
