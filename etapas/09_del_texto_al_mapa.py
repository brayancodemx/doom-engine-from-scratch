"""ETAPA 9 — La misma habitación como texto, plano 2D y escena pseudo-3D."""

import math

import pygame

WIDTH, HEIGHT = 960, 540
FOV = math.radians(66)
HALF_FOV = FOV / 2
NUM_RAYS = 240
RAY_WIDTH = WIDTH // NUM_RAYS
PROJECTION = (WIDTH // 2) / math.tan(HALF_FOV)

ROOM = (
    "11111111",
    "1......1",
    "1..22..1",
    "1......1",
    "1....3.1",
    "1......1",
    "1......1",
    "11111111",
)

PLAYER_X, PLAYER_Y = 2.5, 6.0
PLAYER_ANGLE = -math.pi / 2
COLORS = {"1": (24, 129, 174), "2": (201, 29, 129), "3": (255, 82, 43)}
WHITE = (235, 250, 255)
CYAN = (0, 235, 255)
MAGENTA = (255, 30, 160)


def room_tile(x, y):
    grid_x, grid_y = int(x), int(y)
    if 0 <= grid_y < len(ROOM) and 0 <= grid_x < len(ROOM[0]):
        return ROOM[grid_y][grid_x]
    return "1"


def cast_room():
    rays = []
    angle = PLAYER_ANGLE - HALF_FOV
    for _ in range(NUM_RAYS):
        depth = 0.0
        while depth < 15:
            hit_x = PLAYER_X + math.cos(angle) * depth
            hit_y = PLAYER_Y + math.sin(angle) * depth
            wall = room_tile(hit_x, hit_y)
            if wall != ".":
                break
            depth += 0.025
        corrected = depth * math.cos(PLAYER_ANGLE - angle)
        rays.append((corrected, wall, hit_x, hit_y))
        angle += FOV / NUM_RAYS
    return rays


def draw_map(surface, title_font, font):
    surface.fill((5, 7, 18))
    cell = 52
    start_x, start_y = 82, 78
    for y, row in enumerate(ROOM):
        for x, tile in enumerate(row):
            rect = pygame.Rect(start_x + x * cell, start_y + y * cell, cell, cell)
            if tile == ".":
                pygame.draw.rect(surface, (12, 18, 32), rect)
                pygame.draw.rect(surface, (25, 38, 52), rect, 1)
            else:
                pygame.draw.rect(surface, (16, 34, 48), rect)
                pygame.draw.rect(surface, COLORS.get(tile, CYAN), rect, 3)
        
    px, py = start_x + int(PLAYER_X * cell), start_y + int(PLAYER_Y * cell)
    pygame.draw.circle(surface, (255, 120, 45), (px, py), 10)
    pygame.draw.line(surface, WHITE, (px, py),
                     (px + int(math.cos(PLAYER_ANGLE) * 70),
                      py + int(math.sin(PLAYER_ANGLE) * 70)), 3)
    surface.blit(title_font.render("1 · PLANO 2D", True, WHITE), (550, 118))
    lines = (
        "Una habitación de 8 × 8",
        "vista desde arriba.",
        "",
        "Los colores parecen figuras,",
        "pero todavía no hay polígonos:",
        "cada cuadro viene de un carácter.",
    )
    for index, line in enumerate(lines):
        surface.blit(font.render(line, True, CYAN if index == 0 else WHITE),
                     (550, 175 + index * 34))


def draw_text_map(surface, title_font, code_font, font):
    surface.fill((5, 7, 18))
    surface.blit(title_font.render("2 · EL MAPA EN REALIDAD ES TEXTO", True, WHITE), (76, 52))
    panel = pygame.Rect(76, 112, 470, 360)
    pygame.draw.rect(surface, (2, 4, 14), panel, border_radius=12)
    pygame.draw.rect(surface, MAGENTA, panel, 2, border_radius=12)
    for index, row in enumerate(ROOM):
        colored = code_font.render(f'"{row}"', True, CYAN if index in (0, 7) else WHITE)
        surface.blit(colored, (125, 140 + index * 37))

    descriptions = (
        "'1'  pared exterior",
        "'2'  panel magenta",
        "'3'  objeto naranja",
        "'.'  suelo vacío",
        "",
        "MAP[y][x] responde:",
        "¿esta casilla está ocupada?",
    )
    for index, line in enumerate(descriptions):
        color = (255, 105, 45) if "'3'" in line else WHITE
        surface.blit(font.render(line, True, color), (590, 145 + index * 39))


def draw_3d(surface, rays, title_font, font):
    horizon = HEIGHT // 2
    for y in range(HEIGHT):
        color = (7, 10, 27) if y < horizon else (14, 10, 28)
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))
    for index in range(1, 12):
        y = horizon + int((index / 11) ** 2 * (HEIGHT - horizon))
        pygame.draw.line(surface, (38, 11, 55), (0, y), (WIDTH, y))

    for index, (depth, wall, hit_x, hit_y) in enumerate(rays):
        height = min(int(PROJECTION / max(depth, 0.001)), HEIGHT * 2)
        top = horizon - height // 2
        base = COLORS.get(wall, COLORS["1"])
        light = max(0.2, 1 - depth / 10)
        color = tuple(int(value * light) for value in base)
        pygame.draw.rect(surface, color,
                         (index * RAY_WIDTH, top, RAY_WIDTH + 1, height))

    panel = pygame.Surface((740, 78), pygame.SRCALPHA)
    panel.fill((2, 4, 14, 225))
    surface.blit(panel, (18, 18))
    surface.blit(title_font.render("3 · EL TEXTO SE CONVIERTE EN HABITACIÓN", True, WHITE),
                 (35, 28))
    surface.blit(font.render(
        "240 rayos leen ROOM[y][x] y transforman distancia en altura",
        True, CYAN), (37, 65))


def draw_navigation(surface, font, phase, automatic):
    mode = "AUTO" if automatic else "MANUAL"
    label = f"1 plano · 2 texto · 3 render · A automático   FASE {phase}/3 [{mode}]"
    shadow = font.render(label, True, (0, 0, 0))
    text = font.render(label, True, WHITE)
    rect = text.get_rect(midbottom=(WIDTH // 2, HEIGHT - 14))
    surface.blit(shadow, rect.move(2, 2))
    surface.blit(text, rect)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 9 — Del texto al mapa")
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("consolas", 25, bold=True)
    font = pygame.font.SysFont("consolas", 17, bold=True)
    code_font = pygame.font.SysFont("consolas", 27, bold=True)
    rays = cast_room()
    phase = 1
    elapsed = 0.0
    automatic = True
    running = True

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_3:
                    phase = event.key - pygame.K_0
                    elapsed = 0.0
                    automatic = False
                elif event.key == pygame.K_a:
                    automatic = not automatic
                    elapsed = 0.0

        if automatic:
            elapsed += dt
            if elapsed >= 4.5:
                phase = phase % 3 + 1
                elapsed = 0.0

        if phase == 1:
            draw_map(screen, title_font, font)
        elif phase == 2:
            draw_text_map(screen, title_font, code_font, font)
        else:
            draw_3d(screen, rays, title_font, font)
        draw_navigation(screen, font, phase, automatic)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

