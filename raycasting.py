"""Raycasting DDA: impactos exactos y estables al caminar o girar."""

import math

from map_data import tile_at
from settings import DELTA_ANGLE, HALF_FOV, MAX_DEPTH, NUM_RAYS


def cast_one_ray(x, y, angle, keep_path=False):
    """Cruza la cuadrícula hasta el primer muro sin aproximar el impacto."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    map_x, map_y = int(x), int(y)
    delta_x = abs(1.0 / cos_a) if abs(cos_a) > 1e-12 else math.inf
    delta_y = abs(1.0 / sin_a) if abs(sin_a) > 1e-12 else math.inf

    if cos_a < 0:
        step_x = -1
        side_x = (x - map_x) * delta_x
    else:
        step_x = 1
        side_x = (map_x + 1.0 - x) * delta_x
    if sin_a < 0:
        step_y = -1
        side_y = (y - map_y) * delta_y
    else:
        step_y = 1
        side_y = (map_y + 1.0 - y) * delta_y

    path = []
    depth = 0.0
    while depth < MAX_DEPTH:
        if side_x < side_y:
            depth = side_x
            side_x += delta_x
            map_x += step_x
        else:
            depth = side_y
            side_y += delta_y
            map_y += step_y
        hit_x = x + cos_a * depth
        hit_y = y + sin_a * depth
        if keep_path:
            path.append((hit_x, hit_y))
        wall = tile_at(map_x, map_y)
        if wall != ".":
            return depth, wall, hit_x, hit_y, path

    hit_x = x + cos_a * MAX_DEPTH
    hit_y = y + sin_a * MAX_DEPTH
    return MAX_DEPTH, "1", hit_x, hit_y, path


def cast_all_rays(player):
    """Crea el abanico completo de rayos y una lista de profundidades."""
    rays = []
    depth_buffer = []
    ray_angle = player.angle - HALF_FOV

    for _ in range(NUM_RAYS):
        depth, wall, hit_x, hit_y, _ = cast_one_ray(
            player.x, player.y, ray_angle
        )

        # Corrige el efecto de ojo de pez antes de proyectar la pared.
        corrected_depth = depth * math.cos(player.angle - ray_angle)
        rays.append((corrected_depth, wall, hit_x, hit_y))
        depth_buffer.append(corrected_depth)
        ray_angle += DELTA_ANGLE

    return rays, depth_buffer
