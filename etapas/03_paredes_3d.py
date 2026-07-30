"""ETAPA 3 — Muchos rayos crean la ilusión de paredes 3D."""

import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player
from raycasting import cast_all_rays
from renderer import draw_background, draw_minimap, draw_walls
from settings import CYAN, HEIGHT, WHITE, WIDTH


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 3 — Paredes 3D")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 19, bold=True)
    player = Player()
    running = True
    time_value = 0.0
    while running:
        dt = min(clock.tick(60) / 1000, 0.04)
        time_value += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
        player.update(dt)
        draw_background(screen, time_value)
        rays, _ = cast_all_rays(player)
        draw_walls(screen, rays)
        draw_minimap(screen, player, [])
        veil = pygame.Surface((560, 44), pygame.SRCALPHA)
        veil.fill((2, 4, 14, 210))
        screen.blit(veil, (15, 14))
        screen.blit(font.render("ETAPA 3 · ALTURA = PROYECCIÓN / DISTANCIA", True, WHITE), (28, 25))
        pygame.draw.line(screen, CYAN, (15, 58), (575, 58), 2)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()

