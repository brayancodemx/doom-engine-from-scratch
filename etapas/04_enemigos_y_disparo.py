"""ETAPA 4 — Sprites, mira y selección del enemigo apuntado."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player, create_enemy, normalized_angle
from raycasting import cast_all_rays, cast_one_ray
from renderer import (
    draw_background, draw_crosshair, draw_enemies, draw_minimap, draw_walls,
)
from settings import CYAN, HEIGHT, MAGENTA, MOUSE_SENSITIVITY, WHITE, WIDTH


def find_target(player, enemies):
    wall_distance = cast_one_ray(player.x, player.y, player.angle)[0]
    candidates = []
    for enemy in enemies:
        if not enemy.alive:
            continue
        dx, dy = enemy.x - player.x, enemy.y - player.y
        distance = math.hypot(dx, dy)
        error = abs(normalized_angle(math.atan2(dy, dx) - player.angle))
        if distance < wall_distance + 0.25 and error < math.atan2(0.42, distance):
            candidates.append((error, enemy))
    return min(candidates, default=(None, None), key=lambda item: item[0])[1]


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Etapa 4 — Enemigos y disparo")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18, bold=True)
    player = Player()
    enemies = [create_enemy(6.5, 1.5), create_enemy(12.5, 1.5), create_enemy(5.5, 3.5)]
    score = 0
    flash = 0.0
    time_value = 0.0
    pygame.event.set_grab(True)
    pygame.mouse.set_visible(False)
    running = True
    while running:
        dt = min(clock.tick(60) / 1000, 0.04)
        time_value += dt
        flash = max(0.0, flash - dt)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False
            if event.type == pygame.MOUSEMOTION:
                player.angle += event.rel[0] * MOUSE_SENSITIVITY
            if (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE) or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            ):
                target = find_target(player, enemies)
                flash = 0.10
                if target:
                    target.health = 0
                    score += 100

        player.update(dt)
        for enemy in enemies:
            enemy.animation += dt * 5
        draw_background(screen, time_value)
        rays, depth_buffer = cast_all_rays(player)
        draw_walls(screen, rays)
        draw_enemies(screen, enemies, player, depth_buffer)
        if flash:
            pygame.draw.circle(screen, (255, 210, 80), (WIDTH // 2, HEIGHT // 2), 28, 4)
        draw_crosshair(screen, flash * 5)
        draw_minimap(screen, player, enemies)
        panel = pygame.Surface((630, 58), pygame.SRCALPHA)
        panel.fill((2, 4, 14, 215))
        screen.blit(panel, (12, 12))
        label = f"ETAPA 4 · SPRITES + COLISIÓN DE MIRA    PUNTOS: {score}"
        screen.blit(font.render(label, True, WHITE), (25, 23))
        screen.blit(font.render("CLIC / ESPACIO = disparar", True, CYAN), (25, 47))
        pygame.draw.line(screen, MAGENTA, (12, 70), (642, 70), 2)
        pygame.display.flip()
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    pygame.quit()


if __name__ == "__main__":
    main()

