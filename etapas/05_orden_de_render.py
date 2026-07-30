"""ETAPA 5 — Una escena quieta aparece capa por capa."""

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player, create_enemy
from raycasting import cast_all_rays
from renderer import draw_background, draw_enemies, draw_walls, draw_weapon
from settings import BLACK, CYAN, HEIGHT, MAGENTA, ORANGE, WHITE, WIDTH

STEP_SECONDS = 3.0


def draw_explanation(surface, active_step, font, small_font, paused):
    panel = pygame.Surface((435, 184), pygame.SRCALPHA)
    panel.fill((2, 4, 15, 225))
    pygame.draw.rect(panel, CYAN, panel.get_rect(), 2, border_radius=10)
    surface.blit(panel, (18, 18))

    surface.blit(font.render("JERARQUÍA VISUAL DE LA ESCENA", True, WHITE), (36, 33))
    layers = (
        (1, "PAREDES · columnas verticales", CYAN),
        (2, "TECHO Y PISO · fondo", MAGENTA),
        (3, "OBJETOS · enemigo billboard", ORANGE),
        (4, "ARMA · primer plano", WHITE),
    )
    for index, label, color in layers:
        is_active = index <= active_step
        marker = "●" if is_active else "○"
        text_color = color if is_active else (78, 82, 100)
        surface.blit(small_font.render(f"{marker} {index}) {label}", True, text_color),
                     (39, 68 + (index - 1) * 27))

    status = "PAUSA" if paused else "AUTOMÁTICO"
    surface.blit(small_font.render(
        f"1–4 elegir · R reiniciar · ESPACIO pausa [{status}]", True, WHITE
    ), (36, 176))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 5 — Orden de render")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20, bold=True)
    small_font = pygame.font.SysFont("consolas", 15, bold=True)

    player = Player(x=2.0, y=1.6, angle=0.10)
    enemy = create_enemy(6.4, 1.6)
    enemy.animation = 1.3
    enemies = [enemy]
    rays, depth_buffer = cast_all_rays(player)
    step = 1
    elapsed = 0.0
    paused = False
    running = True

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.04)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            elif event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_4:
                    step = event.key - pygame.K_0
                    elapsed = 0.0
                    paused = True
                elif event.key == pygame.K_r:
                    step, elapsed, paused = 1, 0.0, False
                elif event.key == pygame.K_SPACE:
                    paused = not paused

        if not paused and step < 4:
            elapsed += dt
            if elapsed >= STEP_SECONDS:
                elapsed = 0.0
                step += 1

        # Paso 1: aislamos las paredes sobre negro.
        screen.fill(BLACK)
        if step == 1:
            draw_walls(screen, rays)

        # Paso 2: para añadir un fondo debe pintarse antes y reconstruir paredes encima.
        if step >= 2:
            draw_background(screen, 0.0)
            draw_walls(screen, rays)

        # El enemigo es un plano 2D que siempre mira directamente a la cámara.
        if step >= 3:
            draw_enemies(screen, enemies, player, depth_buffer)

        # El arma siempre se dibuja al final, por eso nunca queda detrás del mundo.
        if step >= 4:
            draw_weapon(screen, player, recoil=0.0, muzzle_flash=0.0)

        draw_explanation(screen, step, font, small_font, paused)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

