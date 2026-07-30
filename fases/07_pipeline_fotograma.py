"""Un fotograma — las capas narradas por el guion aparecen en orden."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player, create_enemy
from map_data import MAP
from raycasting import cast_all_rays
from renderer import (
    Particle,
    draw_background,
    draw_ceiling_details,
    draw_crosshair,
    draw_enemies,
    draw_hud,
    draw_minimap,
    draw_particles,
    draw_scanlines,
    draw_walls,
    draw_weapon,
    draw_world_atmosphere,
)
from animacion_base import (
    AMBER, BLACK, CYAN, RED, RUST, WHITE, phase, run,
)

DURATION = 14.0


def map_scan(surface, player, rays, progress):
    surface.fill(BLACK)
    scale = 27
    ox, oy = 370, 90
    for y, row in enumerate(MAP):
        for x, tile in enumerate(row):
            rect = pygame.Rect(ox + x * scale, oy + y * scale,
                               scale - 1, scale - 1)
            pygame.draw.rect(surface,
                             (79, 56, 41) if tile != "." else (20, 20, 18),
                             rect)
    origin = (ox + int(player.x * scale), oy + int(player.y * scale))
    visible = int(len(rays) * progress)
    for index in range(0, visible, 10):
        _, _, hit_x, hit_y = rays[index]
        endpoint = (ox + int(hit_x * scale), oy + int(hit_y * scale))
        pygame.draw.line(surface, CYAN, origin, endpoint, 1)
    pygame.draw.circle(surface, AMBER, origin, 9)


def particles_for(time_value):
    particles = []
    age = max(0.0, time_value - 7.0)
    if age > 0.7:
        return particles
    for index in range(28):
        angle = index * math.tau / 28 + 0.13
        speed = 80 + (index % 6) * 18
        particles.append(Particle(
            640 + math.cos(angle) * speed * age,
            335 + math.sin(angle) * speed * age + age * age * 42,
            0.0, 0.0, max(0.02, 0.72 - age),
            AMBER if index % 3 else RED,
            3 + index % 3,
        ))
    return particles


def draw_frame(surface, time_value):
    player = draw_frame.player
    enemies = draw_frame.enemies
    for enemy in enemies:
        enemy.animation = time_value * 4.0
    rays, depth_buffer = cast_all_rays(player)

    if time_value < 1.7:
        map_scan(surface, player, rays, phase(time_value, 0.2, 1.6))
        return

    stage_time = time_value - 1.7
    world = pygame.Surface(surface.get_size())
    world.fill(BLACK)

    if stage_time >= 0.0:
        draw_background(world, time_value)
    if stage_time >= 1.0:
        draw_walls(world, rays, time_value)
    if stage_time >= 2.1:
        draw_enemies(world, enemies, player, depth_buffer, neutral=True)
    if stage_time >= 3.2:
        draw_ceiling_details(world, player, time_value, depth_buffer)
        atmosphere = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        draw_world_atmosphere(atmosphere, player, depth_buffer, time_value)
        world.blit(atmosphere, (0, 0))

    surface.fill(BLACK)
    camera_x = int(math.sin(time_value * 3.0) * 7) if stage_time >= 4.2 else 0
    camera_y = int(abs(math.cos(time_value * 3.0)) * 5) if stage_time >= 4.2 else 0
    surface.blit(world, (camera_x, camera_y))

    muzzle = max(0.0, 0.16 - abs(stage_time - 5.4))
    recoil = max(0.0, 1.0 - abs(stage_time - 5.4) / 0.48)
    if stage_time >= 5.0:
        if muzzle > 0:
            flash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            flash.fill((255, 82, 18, int(95 * muzzle / 0.16)))
            surface.blit(flash, (0, 0))
        draw_particles(surface, particles_for(time_value))
    if stage_time >= 6.0:
        draw_weapon(surface, player, recoil, muzzle, style="doom_rifle")
    if stage_time >= 7.1:
        draw_crosshair(surface, recoil)
        draw_hud(surface, player, 500, "doom_rifle",
                 draw_frame.hud_font, draw_frame.small_font, 0.0)
        draw_minimap(surface, player, enemies)
    if stage_time >= 8.3:
        damage = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        damage.fill((190, 12, 15, 42))
        surface.blit(damage, (0, 0))
        draw_scanlines(surface)

    # Una hilera de diez luces muestra el orden sin convertirlo en texto.
    for index in range(10):
        active = index <= min(9, int(stage_time / 1.05))
        color = AMBER if active else (47, 40, 34)
        pygame.draw.circle(surface, color, (485 + index * 35, 70), 6)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    draw_frame.player = Player(x=3.4, y=2.7, angle=0.45, health=72)
    first = create_enemy(7.3, 5.1)
    second = create_enemy(6.0, 3.5)
    first.variant = second.variant = 2
    draw_frame.enemies = [first, second]
    draw_frame.hud_font = pygame.font.SysFont("consolas", 27, bold=True)
    draw_frame.small_font = pygame.font.SysFont("consolas", 15, bold=True)
    pygame.display.quit()
    run(draw_frame, DURATION, "07 — composición de un fotograma")


if __name__ == "__main__":
    main()
