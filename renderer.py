"""Todo lo visible: paredes, enemigos, arma, HUD, minimapa y partículas."""

from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
import random

import numpy as np
import pygame

from entities import normalized_angle
from map_data import MAP
from settings import (
    BLACK, CYAN, DOOM_AMBER, DOOM_BLACK, DOOM_BLOOD, DOOM_BONE,
    DOOM_DARK, DOOM_PHOSPHOR, DOOM_RED, DOOM_RUST, DOOM_STEEL,
    ENEMY_MAX_RENDER_SIZE, FOV, HALF_FOV, HEIGHT, MAGENTA, NAVY, NUM_RAYS, ORANGE,
    PROJECTION_DISTANCE, RAY_WIDTH, SHOTGUN_BREAK_START, SHOTGUN_CYCLE,
    TARGET_SCORE, WHITE, WIDTH,
)

ROOT = Path(__file__).resolve().parent

ACTIVE_WEAPON_STYLES = ("doom_rifle", "doom_shotgun")
LEGACY_WEAPON_STYLES = ("rifle", "shotgun", "shotgun_prototype")
WEAPON_ASSET_PATHS = {
    "doom_rifle": ROOT / "assets" / "weapons" / "doom_rifle.png",
    "doom_shotgun": ROOT / "assets" / "weapons" / "doom_shotgun_closed.png",
    "doom_shotgun_open": ROOT / "assets" / "weapons" / "doom_shotgun_open.png",
}
ENEMY_ASSET_PATHS = {
    state: ROOT / "assets" / "enemies" / f"demon_{state}.png"
    for state in (
        "idle", "walk_a", "walk_b", "attack_prepare", "attack_strike",
        "hurt", "death_impact", "death_fall", "corpse",
    )
}
WALL_TEXTURE_ASSET_PATHS = {
    "1": ROOT / "assets" / "textures" / "walls" / "wall_1_steel.png",
    "2": ROOT / "assets" / "textures" / "walls" / "wall_2_blood.png",
    "3": ROOT / "assets" / "textures" / "walls" / "wall_3_toxic.png",
    "4": ROOT / "assets" / "textures" / "walls" / "wall_4_hazard.png",
    "5": ROOT / "assets" / "textures" / "walls" / "wall_5_bone.png",
    "6": ROOT / "assets" / "textures" / "walls" / "wall_6_rust.png",
}
FLOOR_TEXTURE_ASSET_PATHS = {
    "steel": ROOT / "assets" / "textures" / "floors" / "floor_steel.png",
    "grate": ROOT / "assets" / "textures" / "floors" / "floor_grate.png",
    "dirty": ROOT / "assets" / "textures" / "floors" / "floor_dirty.png",
}
CEILING_TEXTURE_ASSET_PATHS = {
    "steel": ROOT / "assets" / "textures" / "ceilings" / "ceiling_steel.png",
    "grate": ROOT / "assets" / "textures" / "ceilings" / "ceiling_grate.png",
    "rust": ROOT / "assets" / "textures" / "ceilings" / "ceiling_rust.png",
}
ENVIRONMENT_TEXTURE_SIZE = 512

WALL_COLORS = {
    # Paleta del mundo: acero quemado, hormigón, óxido y señales de peligro.
    # El HUD conserva su propia paleta neón; estos colores sólo pertenecen al escenario.
    "1": (95, 85, 70),
    "2": (101, 68, 52),
    "3": (84, 92, 73),
    "4": (116, 85, 47),
    "5": (94, 81, 66),
    "6": (103, 72, 50),
}

MINIMAP_WALL_COLORS = {
    "1": (95, 111, 72),
    "2": (129, 55, 34),
    "3": (113, 125, 82),
    "4": (181, 119, 45),
    "5": (131, 114, 83),
    "6": (143, 69, 37),
}
DOOM_LAMP = (255, 190, 86)

RADAR_FONT = None
WALL_TEXTURES = None
WALL_TEXTURE_ARRAYS = None
WALL_MIPMAPS = None
WALL_SHADE_SURFACE = None
FLOOR_TEXTURES = None
CEILING_TEXTURES = None
BACKGROUND_GRADIENT = None
FOG_OVERLAY = None
SCANLINE_OVERLAYS = {}
WEAPON_SPRITES = None
ENEMY_SPRITES = None
DAMAGE_OVERLAYS = {}


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple
    size: int

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 110 * dt
        self.life -= dt


def make_particles(x, y, color, amount=14, speed=240):
    particles = []
    for _ in range(amount):
        angle = random.uniform(0, math.tau)
        force = random.uniform(speed * 0.25, speed)
        particles.append(
            Particle(x, y, math.cos(angle) * force, math.sin(angle) * force,
                     random.uniform(0.18, 0.5), color, random.randint(2, 5))
        )
    return particles


def _scaled_color(color, factor):
    return tuple(max(0, min(255, int(channel * factor))) for channel in color)


def _mix_color(color_a, color_b, amount):
    amount = max(0.0, min(1.0, amount))
    return tuple(
        int(start + (end - start) * amount)
        for start, end in zip(color_a, color_b)
    )


def _smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _load_environment_texture(asset_path, size=ENVIRONMENT_TEXTURE_SIZE):
    """Normaliza un PNG opaco sin conservar el original grande en memoria."""
    texture = pygame.image.load(str(asset_path))
    if pygame.display.get_surface() is not None:
        texture = texture.convert()
    if texture.get_size() != (size, size):
        texture = pygame.transform.smoothscale(texture, (size, size))
    return texture


def _load_wall_textures():
    global WALL_TEXTURES
    if WALL_TEXTURES is None:
        WALL_TEXTURES = {
            tile: _load_environment_texture(asset_path)
            for tile, asset_path in WALL_TEXTURE_ASSET_PATHS.items()
        }
    return WALL_TEXTURES


def _load_wall_texture_arrays():
    global WALL_TEXTURE_ARRAYS
    if WALL_TEXTURE_ARRAYS is None:
        WALL_TEXTURE_ARRAYS = {
            tile: pygame.surfarray.array3d(texture)
            for tile, texture in _load_wall_textures().items()
        }
    return WALL_TEXTURE_ARRAYS


def _load_wall_mipmaps():
    """Precalcula niveles filtrados para que la textura lejana no parpadee."""
    global WALL_MIPMAPS
    if WALL_MIPMAPS is None:
        WALL_MIPMAPS = {}
        for wall, texture in _load_wall_textures().items():
            WALL_MIPMAPS[wall] = (
                texture,
                pygame.transform.smoothscale(texture, (256, 256)),
                pygame.transform.smoothscale(texture, (128, 128)),
                pygame.transform.smoothscale(texture, (64, 64)),
            )
    return WALL_MIPMAPS


def _load_floor_textures():
    global FLOOR_TEXTURES
    if FLOOR_TEXTURES is None:
        FLOOR_TEXTURES = {
            name: _load_environment_texture(asset_path)
            for name, asset_path in FLOOR_TEXTURE_ASSET_PATHS.items()
        }
    return FLOOR_TEXTURES


def _load_ceiling_textures():
    global CEILING_TEXTURES
    if CEILING_TEXTURES is None:
        CEILING_TEXTURES = {
            name: _load_environment_texture(asset_path)
            for name, asset_path in CEILING_TEXTURE_ASSET_PATHS.items()
        }
    return CEILING_TEXTURES


def _draw_wall_skull(texture, center_x, center_y, bone_color):
    """Sello de calavera pixelado para romper la repetición de las placas."""
    mask = (
        "  ####  ",
        " ###### ",
        "## ## ##",
        "########",
        "## ## ##",
        "## ## ##",
        " ###### ",
        "  ####  ",
    )
    pixel = 1
    left = center_x - len(mask[0]) * pixel // 2
    top = center_y - len(mask) * pixel // 2
    shadow = _scaled_color(DOOM_BLACK, 0.92)
    for row, line in enumerate(mask):
        for column, filled in enumerate(line):
            if filled == "#":
                rect = (left + column * pixel, top + row * pixel, pixel, pixel)
                pygame.draw.rect(texture, shadow, rect)
                pygame.draw.rect(texture, bone_color,
                                 (rect[0], rect[1], max(1, pixel - 1),
                                  max(1, pixel - 1)))
    # Órbitas y nariz oscuras: se leen incluso con la pared lejos.
    for eye_x in (center_x - 2, center_x + 1):
        pygame.draw.rect(texture, DOOM_BLACK, (eye_x, center_y - 2, 2, 2))
    pygame.draw.rect(texture, DOOM_BLACK, (center_x, center_y + 1, 1, 2))


def _create_wall_texture(tile, base_color):
    """Construye placas gruesas y gastadas con lenguaje visual de DOOM."""
    texture = pygame.Surface((64, 64))
    dark = _scaled_color(base_color, 0.34)
    shadow = _scaled_color(base_color, 0.50)
    light = _scaled_color(base_color, 1.25)
    texture.fill(dark)

    # Cuatro placas grandes: bloques irregulares, bisel grueso y juntas negras.
    for row in range(2):
        for column in range(2):
            x, y = column * 32 + 2, row * 32 + 2
            panel_color = _scaled_color(
                base_color, 0.72 + 0.08 * ((row + column) % 2)
            )
            pygame.draw.rect(texture, panel_color, (x, y, 28, 28))
            pygame.draw.line(texture, light, (x, y), (x + 27, y), 2)
            pygame.draw.line(texture, light, (x, y), (x, y + 27), 2)
            pygame.draw.line(texture, shadow, (x, y + 27), (x + 27, y + 27), 2)
            pygame.draw.line(texture, shadow, (x + 27, y), (x + 27, y + 27), 2)

    pygame.draw.rect(texture, _scaled_color(DOOM_BLACK, 0.90), (30, 0, 4, 64))
    pygame.draw.rect(texture, _scaled_color(DOOM_BLACK, 0.90), (0, 30, 64, 4))
    pygame.draw.line(texture, _scaled_color(base_color, 0.82), (34, 0), (34, 63))
    pygame.draw.line(texture, _scaled_color(base_color, 0.82), (0, 34), (63, 34))

    accent = {
        "1": DOOM_STEEL, "2": DOOM_BLOOD, "3": (126, 143, 104),
        "4": DOOM_AMBER, "5": (157, 143, 117), "6": DOOM_RUST,
    }.get(tile, DOOM_STEEL)

    # Cada tipo de pared recibe un detalle reconocible, sin volver al neón.
    if tile in "13":
        for y in (11, 43):
            pygame.draw.rect(texture, _scaled_color(accent, 0.28), (7, y, 18, 6))
            pygame.draw.line(texture, accent, (9, y + 1), (22, y + 1), 2)
            pygame.draw.rect(texture, _scaled_color(accent, 0.28), (39, y, 18, 6))
            pygame.draw.line(texture, accent, (41, y + 1), (54, y + 1), 2)
    elif tile == "2":
        pygame.draw.rect(texture, _scaled_color(accent, 0.30), (26, 4, 12, 56))
        pygame.draw.rect(texture, accent, (30, 5, 4, 54))
        for y in (9, 22, 41, 54):
            pygame.draw.circle(texture, _scaled_color(DOOM_AMBER, 0.72), (32, y), 1)
    elif tile == "4":
        for x in range(-16, 80, 16):
            pygame.draw.polygon(texture, accent,
                                ((x, 20), (x + 7, 20), (x - 2, 29), (x - 9, 29)))
            pygame.draw.polygon(texture, accent,
                                ((x, 52), (x + 7, 52), (x - 2, 61), (x - 9, 61)))
    elif tile == "5":
        pygame.draw.line(texture, accent, (7, 24), (24, 7), 2)
        pygame.draw.line(texture, accent, (40, 25), (56, 9), 2)
        pygame.draw.line(texture, accent, (7, 56), (24, 39), 2)
        pygame.draw.line(texture, accent, (40, 57), (56, 41), 2)
    else:
        for y in (9, 18, 41, 50):
            pygame.draw.line(texture, accent, (7, y), (25, y), 2)
            pygame.draw.line(texture, accent, (39, y), (57, y), 2)

    # Moteado de metal oxidado, siempre determinista para que no parpadee.
    rng = random.Random(int(tile) * 913)
    for _ in range(48):
        x, y = rng.randrange(4, 59), rng.randrange(4, 59)
        width = rng.randrange(1, 4)
        patch_color = _mix_color(
            _scaled_color(base_color, 0.42),
            _scaled_color(DOOM_RUST, 0.64),
            rng.random() * 0.55,
        )
        pygame.draw.rect(texture, patch_color, (x, y, width, rng.randrange(1, 3)))

    if tile in "12356":
        bone = (151, 137, 112) if tile not in "26" else (131, 101, 72)
        for center_x, center_y in ((16, 16), (48, 16), (16, 48), (48, 48)):
            _draw_wall_skull(texture, center_x, center_y, bone)

    # Remaches, golpes y óxido deterministas: aspecto pixelado estable entre cuadros.
    for x, y in ((5, 5), (27, 5), (37, 5), (59, 5),
                 (5, 37), (27, 37), (37, 37), (59, 37)):
        pygame.draw.circle(texture, DOOM_STEEL, (x, y), 1)
        pygame.draw.circle(texture, DOOM_BLACK, (x + 1, y + 1), 1)

    for _ in range(24):
        x, y = rng.randrange(5, 57), rng.randrange(6, 59)
        length = rng.randrange(2, 7)
        scratch_color = _scaled_color(
            DOOM_RUST if rng.random() < 0.42 else base_color,
            rng.uniform(0.28, 0.58),
        )
        pygame.draw.line(texture, scratch_color,
                         (x, y), (min(60, x + length), y), 1)
    return texture


def _wall_texture_coordinate(hit_x, hit_y):
    """Elige el eje de la textura según la cara de pared alcanzada."""
    fraction_x = hit_x % 1
    fraction_y = hit_y % 1
    distance_to_x_edge = min(fraction_x, 1 - fraction_x)
    distance_to_y_edge = min(fraction_y, 1 - fraction_y)
    if distance_to_x_edge < distance_to_y_edge:
        return (hit_y * 0.5) % 1.0, 1.0
    return (hit_x * 0.5) % 1.0, 0.78


def _project_world_point(player, world_x, world_y, world_z):
    """Proyecta un punto del mundo; z=0 es piso y z=1 es techo."""
    dx = world_x - player.x
    dy = world_y - player.y
    cos_angle = math.cos(player.angle)
    sin_angle = math.sin(player.angle)
    depth = dx * cos_angle + dy * sin_angle
    if depth <= 0.12:
        return None
    lateral = -dx * sin_angle + dy * cos_angle
    screen_x = WIDTH // 2 + lateral / depth * PROJECTION_DISTANCE
    screen_y = HEIGHT // 2 + (0.5 - world_z) / depth * PROJECTION_DISTANCE
    return int(screen_x), int(screen_y), depth


def _project_world_shape(player, points, world_z):
    projected = [_project_world_point(player, x, y, world_z) for x, y in points]
    if any(point is None for point in projected):
        return None
    return [(point[0], point[1]) for point in projected]


def _background_gradient():
    global BACKGROUND_GRADIENT
    if BACKGROUND_GRADIENT is not None:
        return BACKGROUND_GRADIENT

    horizon = HEIGHT // 2
    gradient = pygame.Surface((WIDTH, HEIGHT))
    for y in range(horizon):
        amount = y / max(1, horizon - 1)
        color = _mix_color((5, 5, 6), (30, 25, 22), amount)
        pygame.draw.line(gradient, color, (0, y), (WIDTH, y))
    for y in range(horizon, HEIGHT):
        amount = (y - horizon) / max(1, HEIGHT - horizon - 1)
        color = _mix_color((76, 49, 33), (34, 22, 17), amount)
        pygame.draw.line(gradient, color, (0, y), (WIDTH, y))

    # El fondo sólo conserva el degradado. Los detalles del techo y suelo se
    # dibujan abajo en coordenadas del mundo para que no queden pegados a la cámara.
    BACKGROUND_GRADIENT = gradient
    return BACKGROUND_GRADIENT


def _draw_floor_grate(layer, player, grid_x, grid_y, alpha):
    center = _project_world_point(player, grid_x + 0.5, grid_y + 0.5, 0.012)
    if not center or center[2] < 1.15:
        return
    margin = 0.18
    corners = (
        (grid_x + margin, grid_y + margin),
        (grid_x + 1 - margin, grid_y + margin),
        (grid_x + 1 - margin, grid_y + 1 - margin),
        (grid_x + margin, grid_y + 1 - margin),
    )
    polygon = _project_world_shape(player, corners, 0.012)
    if not polygon:
        return
    polygon_x = [point[0] for point in polygon]
    polygon_y = [point[1] for point in polygon]
    if (max(polygon_x) - min(polygon_x) > WIDTH * 0.70 or
            max(polygon_y) - min(polygon_y) > HEIGHT * 0.55):
        return
    strength = alpha / 180
    pygame.draw.polygon(layer, _scaled_color((23, 8, 8), strength), polygon)
    border_width = 3 if center[2] < 4.5 else 2
    pygame.draw.lines(
        layer, _scaled_color((122, 111, 93), strength), True, polygon,
        border_width,
    )
    if len(polygon) >= 2:
        pygame.draw.line(layer, _scaled_color(DOOM_BLOOD, strength),
                         polygon[0], polygon[1], 2)
    for offset in (0.34, 0.50, 0.66):
        horizontal = _project_world_shape(
            player,
            ((grid_x + margin, grid_y + offset),
             (grid_x + 1 - margin, grid_y + offset)),
            0.016,
        )
        vertical = _project_world_shape(
            player,
            ((grid_x + offset, grid_y + margin),
             (grid_x + offset, grid_y + 1 - margin)),
            0.016,
        )
        if horizontal:
            pygame.draw.line(layer, _scaled_color((62, 56, 49), strength),
                             horizontal[0], horizontal[1], 1)
        if vertical:
            pygame.draw.line(layer, _scaled_color((42, 38, 34), strength),
                             vertical[0], vertical[1], 1)


def _draw_floor_tile(layer, player, grid_x, grid_y, alpha):
    """Marca losas de hormigón para que el suelo tenga peso y escala."""
    center = _project_world_point(player, grid_x + 0.5, grid_y + 0.5, 0.006)
    if not center or center[2] < 0.90:
        return
    margin = 0.035
    corners = (
        (grid_x + margin, grid_y + margin),
        (grid_x + 1 - margin, grid_y + margin),
        (grid_x + 1 - margin, grid_y + 1 - margin),
        (grid_x + margin, grid_y + 1 - margin),
    )
    polygon = _project_world_shape(player, corners, 0.006)
    if not polygon:
        return
    polygon_x = [point[0] for point in polygon]
    polygon_y = [point[1] for point in polygon]
    if (max(polygon_x) - min(polygon_x) > WIDTH * 1.30 or
            max(polygon_y) - min(polygon_y) > HEIGHT * 0.75):
        return
    strength = alpha / 190
    tile_variant = (grid_x * 17 + grid_y * 31) % 5
    tile_color = (54 + tile_variant * 4, 35 + tile_variant * 2, 27 + tile_variant)
    pygame.draw.polygon(layer, _scaled_color(tile_color, 0.88 + strength * 0.10), polygon)
    edge_width = 2 if center[2] < 5.5 else 1
    pygame.draw.lines(
        layer, _scaled_color((76, 49, 39), strength), True, polygon,
        edge_width,
    )

    # Bisel interior: una arista clara y otra oscura definen la placa sin textura.
    inset = 0.10
    inner = _project_world_shape(
        player,
        ((grid_x + inset, grid_y + inset),
         (grid_x + 1 - inset, grid_y + inset),
         (grid_x + 1 - inset, grid_y + 1 - inset),
         (grid_x + inset, grid_y + 1 - inset)),
        0.010,
    )
    if inner:
        pygame.draw.line(layer, _scaled_color((112, 72, 50), strength),
                         inner[0], inner[1], 1)
        pygame.draw.line(layer, _scaled_color((25, 18, 16), strength),
                         inner[2], inner[3], 1)

    # Una junta central rota evita que el espacio se vea como una textura plana.
    seam = _project_world_shape(
        player,
        ((grid_x + 0.50, grid_y + 0.08), (grid_x + 0.50, grid_y + 0.92)),
        0.008,
    )
    if seam:
        pygame.draw.line(layer, _scaled_color((35, 27, 24), strength),
                         seam[0], seam[1], 1)
    if tile_variant % 2 == 0:
        cross_seam = _project_world_shape(
            player,
            ((grid_x + 0.08, grid_y + 0.50),
             (grid_x + 0.92, grid_y + 0.50)),
            0.008,
        )
        if cross_seam:
            pygame.draw.line(layer, _scaled_color((31, 23, 21), strength),
                             cross_seam[0], cross_seam[1], 1)

    if center[2] < 8.0:
        for bolt_x, bolt_y in (
            (grid_x + 0.13, grid_y + 0.13),
            (grid_x + 0.87, grid_y + 0.13),
            (grid_x + 0.87, grid_y + 0.87),
            (grid_x + 0.13, grid_y + 0.87),
        ):
            bolt = _project_world_point(player, bolt_x, bolt_y, 0.014)
            if bolt:
                radius = 2 if bolt[2] < 3.5 else 1
                pygame.draw.circle(layer, (16, 12, 11), bolt[:2], radius + 1)
                pygame.draw.circle(
                    layer, _scaled_color((128, 101, 72), strength),
                    bolt[:2], radius,
                )

    # Grietas cortas deterministas: pequeñas, pero visibles en losas cercanas.
    seed = grid_x * 37 + grid_y * 101
    for index in range(3 if center[2] < 5.0 else 2):
        start_x = grid_x + 0.14 + ((seed + index * 19) % 58) / 100
        start_y = grid_y + 0.18 + ((seed + index * 31) % 54) / 100
        end_x = start_x + (0.10 + ((seed + index * 7) % 8) / 100)
        end_y = start_y + (-0.04 if index % 2 else 0.03)
        crack = _project_world_shape(
            player, ((start_x, start_y), (end_x, end_y)), 0.010
        )
        if crack:
            pygame.draw.line(layer, _scaled_color((23, 15, 12), strength),
                             crack[0], crack[1], 1)


def _draw_floor_puddle(layer, player, center_x, center_y, alpha):
    center = _project_world_point(player, center_x, center_y, 0.009)
    if not center or center[2] < 0.90:
        return
    points = []
    for index in range(12):
        angle = index * math.tau / 12
        radius = 1.0 + 0.13 * math.sin(index * 2.7)
        points.append((center_x + math.cos(angle) * 0.31 * radius,
                       center_y + math.sin(angle) * 0.18 * radius))
    polygon = _project_world_shape(player, points, 0.009)
    if not polygon:
        return
    strength = alpha / 180
    pygame.draw.polygon(layer, _scaled_color((52, 8, 10), strength), polygon)
    pygame.draw.lines(layer, _scaled_color((98, 20, 18), strength), False,
                      polygon + [polygon[0]], 1)
    highlight = _project_world_shape(
        player,
        ((center_x - 0.18, center_y - 0.04),
         (center_x + 0.12, center_y - 0.04)),
        0.014,
    )
    if highlight:
        pygame.draw.line(layer, _scaled_color((187, 47, 29), strength),
                         highlight[0], highlight[1], 1)


def _draw_floor_cable(layer, player, grid_x, grid_y, alpha):
    points = []
    for index in range(7):
        amount = index / 6
        points.append((grid_x + 0.08 + amount * 0.84,
                       grid_y + 0.50 + math.sin(amount * math.tau) * 0.10))
    projected = [_project_world_point(player, x, y, 0.022) for x, y in points]
    if any(point is None for point in projected):
        return
    if any(abs(point[0]) > WIDTH * 2 or abs(point[1]) > HEIGHT * 2
           for point in projected):
        return
    screen_points = [(point[0], point[1]) for point in projected]
    strength = alpha / 180
    pygame.draw.lines(layer, (7, 5, 5), False, screen_points, 4)
    pygame.draw.lines(layer, _scaled_color((112, 23, 20), strength),
                      False, screen_points, 2)


def _draw_ceiling_lamp(layer, player, grid_x, grid_y, time_value, alpha):
    center_x, center_y = grid_x + 0.5, grid_y + 0.5
    long_axis_x = abs(math.cos(player.angle)) < abs(math.sin(player.angle))
    if long_axis_x:
        corners = ((center_x - 0.34, center_y - 0.11),
                   (center_x + 0.34, center_y - 0.11),
                   (center_x + 0.34, center_y + 0.11),
                   (center_x - 0.34, center_y + 0.11))
    else:
        corners = ((center_x - 0.11, center_y - 0.34),
                   (center_x + 0.11, center_y - 0.34),
                   (center_x + 0.11, center_y + 0.34),
                   (center_x - 0.11, center_y + 0.34))
    polygon = _project_world_shape(player, corners, 0.975)
    if not polygon:
        return
    polygon_x = [point[0] for point in polygon]
    polygon_y = [point[1] for point in polygon]
    if (max(polygon_x) - min(polygon_x) > WIDTH * 0.58 or
            max(polygon_y) - min(polygon_y) > HEIGHT * 0.30):
        return

    phase = time_value * 7.0 + grid_x * 1.7 + grid_y * 2.3
    flicker = 0.70 + 0.30 * max(0.0, math.sin(phase))
    if int(time_value * 3 + grid_x + grid_y) % 19 == 0:
        flicker *= 0.42
    glow_alpha = int(alpha * flicker)
    strength = glow_alpha / 210
    pygame.draw.polygon(layer, _scaled_color((12, 9, 8), strength), polygon)
    pygame.draw.lines(layer, _scaled_color((115, 91, 65), strength), True, polygon, 2)
    if long_axis_x:
        inner_corners = ((center_x - 0.27, center_y - 0.060),
                         (center_x + 0.27, center_y - 0.060),
                         (center_x + 0.27, center_y + 0.060),
                         (center_x - 0.27, center_y + 0.060))
    else:
        inner_corners = ((center_x - 0.060, center_y - 0.27),
                         (center_x + 0.060, center_y - 0.27),
                         (center_x + 0.060, center_y + 0.27),
                         (center_x - 0.060, center_y + 0.27))
    inner = _project_world_shape(player, inner_corners, 0.972)
    if inner:
        pygame.draw.polygon(layer, _scaled_color((175, 14, 10), strength), inner)
        pygame.draw.lines(layer, _scaled_color(DOOM_AMBER, strength), True, inner, 2)
        pygame.draw.line(layer, _scaled_color((235, 28, 12), strength),
                         inner[0], inner[1], 3)
    center = _project_world_point(player, center_x, center_y, 0.965)
    if center:
        radius = max(1, min(20, int(PROJECTION_DISTANCE / center[2] * 0.018)))
        pygame.draw.circle(layer, _scaled_color(DOOM_LAMP, strength),
                           (center[0], center[1]), radius)


def _draw_ceiling_beam(layer, player, grid_x, grid_y, alpha):
    """Vigas bajas que rompen el techo plano y dan escala de búnker."""
    center_x, center_y = grid_x + 0.5, grid_y + 0.5
    center = _project_world_point(player, center_x, center_y, 0.992)
    # Las esquinas de una celda demasiado cercana cruzan la cámara y
    # producirían un polígono enorme que taparía el resto del escenario.
    if not center or center[2] < 1.25:
        return
    long_axis_x = abs(math.cos(player.angle)) < abs(math.sin(player.angle))
    if long_axis_x:
        corners = ((center_x - 0.48, center_y - 0.065),
                   (center_x + 0.48, center_y - 0.065),
                   (center_x + 0.48, center_y + 0.065),
                   (center_x - 0.48, center_y + 0.065))
    else:
        corners = ((center_x - 0.065, center_y - 0.48),
                   (center_x + 0.065, center_y - 0.48),
                   (center_x + 0.065, center_y + 0.48),
                   (center_x - 0.065, center_y + 0.48))
    polygon = _project_world_shape(player, corners, 0.992)
    if not polygon:
        return
    polygon_x = [point[0] for point in polygon]
    polygon_y = [point[1] for point in polygon]
    if (max(abs(point[0]) for point in polygon) > WIDTH * 2 or
            max(polygon_x) - min(polygon_x) > WIDTH * 0.58 or
            max(polygon_y) - min(polygon_y) > HEIGHT * 0.30):
        return
    strength = alpha / 190
    pygame.draw.polygon(layer, _scaled_color((19, 15, 14), strength), polygon)
    pygame.draw.lines(layer, _scaled_color((91, 49, 34), strength), True, polygon, 2)
    if len(polygon) >= 2:
        pygame.draw.line(layer, _scaled_color(DOOM_BLOOD, strength * 0.78),
                         polygon[0], polygon[1], 1)


def _draw_ceiling_panel(layer, player, grid_x, grid_y, alpha):
    """Placa de techo proyectada, con variación de hormigón y juntas metálicas."""
    center = _project_world_point(player, grid_x + 0.5, grid_y + 0.5, 0.998)
    if not center or center[2] < 1.25:
        return
    margin = 0.035
    corners = (
        (grid_x + margin, grid_y + margin),
        (grid_x + 1 - margin, grid_y + margin),
        (grid_x + 1 - margin, grid_y + 1 - margin),
        (grid_x + margin, grid_y + 1 - margin),
    )
    polygon = _project_world_shape(player, corners, 0.998)
    if not polygon:
        return
    polygon_x = [point[0] for point in polygon]
    polygon_y = [point[1] for point in polygon]
    if (max(polygon_x) - min(polygon_x) > WIDTH * 0.75 or
            max(polygon_y) - min(polygon_y) > HEIGHT * 0.34):
        return

    variant = (grid_x * 23 + grid_y * 41) % 5
    base = (25 + variant * 3, 19 + variant * 2, 16 + variant)
    strength = max(0.35, min(0.90, alpha / 170))
    pygame.draw.polygon(layer, _scaled_color(base, strength), polygon)
    edge_width = 2 if center[2] < 5.5 else 1
    pygame.draw.lines(layer, _scaled_color((73, 47, 33), strength), True,
                      polygon, edge_width)

    inset = 0.11
    inner = _project_world_shape(
        player,
        ((grid_x + inset, grid_y + inset),
         (grid_x + 1 - inset, grid_y + inset),
         (grid_x + 1 - inset, grid_y + 1 - inset),
         (grid_x + inset, grid_y + 1 - inset)),
        0.996,
    )
    if inner:
        pygame.draw.line(layer, _scaled_color((99, 66, 46), strength),
                         inner[0], inner[1], 1)
        pygame.draw.line(layer, _scaled_color((11, 9, 8), strength),
                         inner[2], inner[3], 1)

    seam = _project_world_shape(
        player,
        ((grid_x + 0.08, grid_y + 0.50),
         (grid_x + 0.92, grid_y + 0.50)),
        0.999,
    )
    if seam:
        pygame.draw.line(layer, _scaled_color((12, 10, 9), strength),
                         seam[0], seam[1], 1)

    if variant % 2:
        rib = _project_world_shape(
            player,
            ((grid_x + 0.50, grid_y + 0.10),
             (grid_x + 0.50, grid_y + 0.90)),
            0.995,
        )
        if rib:
            pygame.draw.line(layer, _scaled_color((46, 30, 24), strength),
                             rib[0], rib[1], 2 if center[2] < 4.5 else 1)

    # Las cuatro fijaciones sólo ganan volumen cerca de la cámara.
    for bolt_x, bolt_y in (
        (grid_x + 0.12, grid_y + 0.12),
        (grid_x + 0.88, grid_y + 0.12),
        (grid_x + 0.88, grid_y + 0.88),
        (grid_x + 0.12, grid_y + 0.88),
    ):
        bolt = _project_world_point(player, bolt_x, bolt_y, 0.996)
        if bolt:
            radius = max(1, min(3, int(PROJECTION_DISTANCE / bolt[2] * 0.006)))
            pygame.draw.circle(layer, (7, 6, 6), (bolt[0], bolt[1]), radius + 1)
            pygame.draw.circle(layer, _scaled_color(DOOM_STEEL, strength),
                               (bolt[0], bolt[1]), radius)


def _visible_world_cells(player, depth_buffer=None):
    """Devuelve celdas libres visibles, reutilizable para suelo y techo."""
    visible_cells = []
    for grid_y, row in enumerate(MAP):
        for grid_x, tile in enumerate(row):
            if tile != ".":
                continue
            center = _project_world_point(player, grid_x + 0.5, grid_y + 0.5, 0.0)
            if center and 0.65 < center[2] < 15:
                screen_margin = PROJECTION_DISTANCE / center[2]
                if -screen_margin < center[0] < WIDTH + screen_margin:
                    if depth_buffer and 0 <= center[0] < WIDTH:
                        ray_index = max(0, min(NUM_RAYS - 1,
                                               center[0] // RAY_WIDTH))
                        if center[2] > depth_buffer[ray_index] + 0.75:
                            continue
                    visible_cells.append((center[2], grid_x, grid_y))
    return sorted(visible_cells, reverse=True)


def _draw_world_details(surface, player, time_value, depth_buffer=None):
    """Decora el piso con losas, rejillas, cables y manchas de sangre."""
    previous_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(0, HEIGHT // 2 - 6, WIDTH, HEIGHT // 2 + 8))
    try:
        for depth, grid_x, grid_y in _visible_world_cells(player, depth_buffer):
            alpha = max(22, min(150, int(175 - depth * 10)))
            _draw_floor_tile(surface, player, grid_x, grid_y, alpha)
            if (grid_x + 2 * grid_y) % 5 == 0:
                _draw_floor_grate(surface, player, grid_x, grid_y, alpha)
            elif (3 * grid_x + grid_y) % 11 == 0:
                _draw_floor_puddle(surface, player, grid_x + 0.5, grid_y + 0.5, alpha)
            elif (grid_x + 4 * grid_y) % 13 == 0:
                _draw_floor_cable(surface, player, grid_x, grid_y, alpha)
    finally:
        surface.set_clip(previous_clip)


def draw_ceiling_details(surface, player, time_value, depth_buffer=None):
    """Proyecta paneles, vigas y luces antes de que los muros los oculten."""
    previous_clip = surface.get_clip()
    surface.set_clip(pygame.Rect(0, 0, WIDTH, HEIGHT // 2 + 18))
    try:
        for depth, grid_x, grid_y in _visible_world_cells(player, depth_buffer):
            alpha = max(22, min(150, int(175 - depth * 10)))
            _draw_ceiling_panel(surface, player, grid_x, grid_y, alpha)
            if (grid_x + 3 * grid_y) % 7 == 0:
                _draw_ceiling_beam(surface, player, grid_x, grid_y, alpha)
            if (grid_x + 2 * grid_y) % 6 == 0:
                _draw_ceiling_lamp(surface, player, grid_x, grid_y,
                                   time_value, min(210, alpha + 65))
    finally:
        surface.set_clip(previous_clip)


def draw_background(surface, time_value, player=None, depth_buffer=None):
    """Construye el fondo y el piso procedural antes de cualquier muro."""
    surface.blit(_background_gradient(), (0, 0))
    if player is not None:
        _draw_world_details(surface, player, time_value, depth_buffer)


@lru_cache(maxsize=1024)
def _scaled_wall_column(wall, texture_x, wall_height):
    """Elige un mipmap filtrado y escala la columna en código nativo."""
    levels = _load_wall_mipmaps().get(wall, _load_wall_mipmaps()["1"])
    if wall_height >= 384:
        texture = levels[0]
    elif wall_height >= 192:
        texture = levels[1]
    elif wall_height >= 96:
        texture = levels[2]
    else:
        texture = levels[3]
    mip_x = min(
        texture.get_width() - 1,
        texture_x * texture.get_width() // ENVIRONMENT_TEXTURE_SIZE,
    )
    source = texture.subsurface((mip_x, 0, 1, texture.get_height()))
    return pygame.transform.scale(source, (RAY_WIDTH, wall_height))


def draw_walls(surface, rays, time_value=0.0):
    """Proyecta una columna de textura por rayo, como un raycaster clásico."""
    global WALL_SHADE_SURFACE
    textures = _load_wall_textures()
    if WALL_SHADE_SURFACE is None:
        WALL_SHADE_SURFACE = pygame.Surface((WIDTH, HEIGHT))
    WALL_SHADE_SURFACE.fill((255, 255, 255))

    for ray_index, (depth, wall, hit_x, hit_y) in enumerate(rays):
        wall_height = min(int(PROJECTION_DISTANCE / max(depth, 0.001)), HEIGHT * 2)
        wall_height = max(1, wall_height)
        texture = textures.get(wall, textures["1"])
        texture_u, side_light = _wall_texture_coordinate(hit_x, hit_y)
        texture_x = min(
            texture.get_width() - 1, int(texture_u * texture.get_width())
        )

        # Luz estable: evita que el detalle fino parpadee durante una captura.
        light = max(0.20, 1.0 - depth / 18) * side_light
        shade = max(25, min(255, int(255 * light)))
        x = ray_index * RAY_WIDTH
        left, right = x, min(WIDTH, x + RAY_WIDTH)
        top = HEIGHT // 2 - wall_height // 2
        screen_top = max(0, top)
        screen_bottom = min(HEIGHT, top + wall_height)
        if screen_bottom <= screen_top:
            continue
        surface.blit(_scaled_wall_column(wall, texture_x, wall_height), (left, top))
        pygame.draw.rect(
            WALL_SHADE_SURFACE, (shade, shade, shade),
            (left, screen_top, right - left, screen_bottom - screen_top),
        )
    surface.blit(WALL_SHADE_SURFACE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


def _fog_overlay():
    global FOG_OVERLAY
    if FOG_OVERLAY is not None:
        return FOG_OVERLAY

    atmosphere = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    horizon = HEIGHT // 2
    for offset in range(0, 112, 8):
        strength = 1.0 - offset / 112
        alpha = int(22 * strength * strength)
        pygame.draw.rect(atmosphere, (45, 24, 18, alpha),
                         (0, horizon - offset - 8, WIDTH, 16))
        pygame.draw.rect(atmosphere, (40, 18, 16, alpha // 2),
                         (0, horizon + offset, WIDTH, 12))
    FOG_OVERLAY = atmosphere
    return FOG_OVERLAY


def draw_world_atmosphere(surface, player, depth_buffer, time_value):
    """Añade niebla de profundidad y vapor animado sin afectar arma ni HUD."""
    surface.blit(_fog_overlay(), (0, 0))

    # Respiraderos fijos: cada columna de vapor sube, deriva y vuelve a empezar.
    steam_sources = ((5.5, 5.5), (10.5, 10.5), (4.5, 12.5))
    for source_index, (source_x, source_y) in enumerate(steam_sources):
        for puff_index in range(4):
            cycle = (time_value * 0.38 + source_index * 0.31 + puff_index * 0.23) % 1.0
            drift = math.sin(cycle * math.tau + source_index) * 0.07
            projected = _project_world_point(
                player, source_x + drift, source_y, 0.08 + cycle * 0.62
            )
            if not projected:
                continue
            screen_x, screen_y, depth = projected
            if not (0 <= screen_x < WIDTH and 0 <= screen_y < HEIGHT):
                continue
            ray_index = max(0, min(NUM_RAYS - 1, screen_x // RAY_WIDTH))
            if depth > depth_buffer[ray_index] + 0.05:
                continue
            radius = max(2, min(28, int(PROJECTION_DISTANCE / depth *
                                        (0.018 + cycle * 0.026))))
            alpha = max(0, int(48 * (1.0 - cycle)))
            puff = pygame.Surface((radius * 2, radius), pygame.SRCALPHA)
            pygame.draw.ellipse(
                puff, (129, 113, 94, alpha),
                (0, 0, radius * 2, radius),
            )
            pygame.draw.ellipse(
                puff, (193, 158, 113, alpha // 2),
                (radius // 2, radius // 6, radius, max(2, radius // 2)),
            )
            surface.blit(puff, (screen_x - radius, screen_y - radius // 2))



def _enemy_death_canvas(base, enemy):
    """Convierte el sprite vivo en una secuencia de impacto, ruptura y restos."""
    width, height = base.get_size()
    result = pygame.Surface((width, height), pygame.SRCALPHA)
    duration = enemy.DEATH_ANIMATION_TIME
    progress = min(1.0, enemy.death_timer / duration)

    # Tras la caída, el montón permanece un instante y pierde su energía.
    linger = max(0.0, enemy.death_timer - duration)
    linger_alpha = max(0, int(255 * (1.0 - linger / enemy.CORPSE_LINGER_TIME)))

    if progress < 0.12:
        # Primer fotograma: retroceso luminoso, grande y fácil de leer al disparar.
        impact = progress / 0.12
        scale = 1.0 + math.sin(impact * math.pi) * 0.10
        struck = pygame.transform.smoothscale(
            base, (int(width * scale), int(height * scale))
        )
        struck.fill((150, 105, 70, 0), special_flags=pygame.BLEND_RGB_ADD)
        rect = struck.get_rect(midbottom=(width // 2, height - 7 - int((1 - impact) * 8)))
        result.blit(struck, rect)
        flash_radius = max(8, int(42 * (1.0 - impact)))
        pygame.draw.circle(result, (255, 245, 205, int(220 * (1 - impact))),
                           (width // 2, 164), flash_radius)
        pygame.draw.circle(result, (255, 82, 20, int(180 * (1 - impact))),
                           (width // 2, 164), flash_radius + 18, 5)

    elif progress < 0.60:
        # La silueta se abre en dos bloques, como los fotogramas de muerte clásicos.
        fall = (progress - 0.12) / 0.48
        eased = fall * fall * (3.0 - 2.0 * fall)
        burst_radius = int(74 - 34 * eased)
        pygame.draw.circle(result, (255, 45, 12, int(105 * (1 - fall))),
                           (width // 2, 158), burst_radius)
        pygame.draw.circle(result, (255, 184, 45, int(180 * (1 - fall))),
                           (width // 2, 158), max(5, int(27 * (1 - fall))))

        left = base.subsurface((0, 18, width // 2, height - 32)).copy()
        right = base.subsurface((width // 2, 18, width // 2, height - 32)).copy()
        left = pygame.transform.rotate(left, 20 * eased)
        right = pygame.transform.rotate(right, -20 * eased)
        pieces_alpha = max(80, int(255 * (1.0 - fall * 0.42)))
        left.set_alpha(pieces_alpha)
        right.set_alpha(pieces_alpha)
        drop = int(24 * eased + 30 * fall * fall)
        spread = int(34 * eased)
        result.blit(left, left.get_rect(midbottom=(105 - spread, 257 + drop)))
        result.blit(right, right.get_rect(midbottom=(135 + spread, 257 + drop)))

        # Fragmentos deterministas: no parpadean ni cambian de trayectoria por cuadro.
        colors = (DOOM_BLOOD, DOOM_RUST, DOOM_BONE, DOOM_STEEL)
        for index in range(14):
            angle = -2.85 + index * 0.41 + enemy.variant * 0.13
            reach = (34 + (index * 17) % 58) * eased
            fragment_x = int(width / 2 + math.cos(angle) * reach)
            fragment_y = int(158 + math.sin(angle) * reach + 92 * fall * fall)
            fragment_size = 2 + index % 4
            color = colors[(index + enemy.variant) % len(colors)]
            pygame.draw.polygon(
                result, (*color, max(30, int(255 * (1 - fall)))),
                ((fragment_x, fragment_y - fragment_size),
                 (fragment_x + fragment_size + 2, fragment_y),
                 (fragment_x - 1, fragment_y + fragment_size + 3)),
            )

    else:
        # Últimos fotogramas: perfil ancho y bajo, claramente distinto a un enemigo vivo.
        settle = min(1.0, (progress - 0.60) / 0.40)
        rubble_source = base.subsurface((25, 82, width - 50, height - 102)).copy()
        rubble_height = max(34, int(76 - 34 * settle))
        rubble = pygame.transform.smoothscale(rubble_source, (205, rubble_height))
        shade = max(65, int(150 - 55 * settle))
        rubble.fill((shade, shade, shade, 255), special_flags=pygame.BLEND_RGBA_MULT)
        rubble.set_alpha(linger_alpha)
        result.blit(rubble, rubble.get_rect(midbottom=(width // 2, 263)))

        fragment_color = (*DOOM_BLOOD, linger_alpha)
        for fragment in (
            ((30, 252), (55, 242), (73, 263)),
            ((166, 263), (184, 243), (213, 256)),
            ((72, 258), (98, 247), (112, 266)),
        ):
            pygame.draw.polygon(result, fragment_color, fragment)

        energy = max(0, int((1.0 - settle * 0.75) * linger_alpha))
        pygame.draw.circle(result, (*DOOM_BLOOD, energy), (120, 246), 17)
        pygame.draw.circle(result, (*DOOM_BONE, energy), (120, 246), 6)

    return result


def _enemy_canvas(enemy, size):
    """Construye un cazador mecánico angular que siempre mira a cámara."""
    canvas = pygame.Surface((240, 280), pygame.SRCALPHA)
    pulse = (math.sin(enemy.animation * 1.35) + 1) / 2
    sway = int(math.sin(enemy.animation * 0.8) * 4)
    palettes = (
        ((112, 86, 4), (245, 201, 20), (255, 248, 92)),
        ((128, 25, 8), (240, 65, 22), (255, 152, 35)),
        ((112, 121, 128), (222, 235, 238), (255, 52, 34)),
    )
    display_tier = max(1, enemy.tier)
    tier_index = max(0, min(len(palettes) - 1, display_tier - 1))
    armor, armor_light, energy = palettes[tier_index]
    if enemy.hurt_timer > 0:
        # El blanco dura sólo al comienzo; después revela gradualmente el nuevo color.
        flash = min(1.0, enemy.hurt_timer / 0.24)
        flash = flash * flash
        armor = _mix_color(armor, (220, 230, 238), flash * 0.92)
        armor_light = _mix_color(armor_light, WHITE, flash)
        energy = _mix_color(energy, WHITE, flash)
    armor_dark = _scaled_color(armor, 0.38)
    black_metal = (7, 9, 17)

    # Sombra y halo energético; varias capas evitan el antiguo aspecto de círculo plano.
    pygame.draw.ellipse(canvas, (0, 0, 0, 150), (38, 246, 164, 24))
    pygame.draw.circle(canvas, (*energy, 22), (120, 137), 101)
    pygame.draw.circle(canvas, (*energy, 48), (120, 137), 88, 3)
    pygame.draw.circle(canvas, (*energy, 30), (120, 137), 76, 2)

    # Cuernos y silueta posterior.
    pygame.draw.polygon(canvas, armor_dark,
                        ((83, 77), (25, 31), (43, 91), (69, 108)))
    pygame.draw.polygon(canvas, armor_dark,
                        ((157, 77), (215, 31), (197, 91), (171, 108)))
    pygame.draw.polygon(canvas, armor_light,
                        ((76, 72), (41, 45), (66, 87)))
    pygame.draw.polygon(canvas, armor_light,
                        ((164, 72), (199, 45), (174, 87)))

    # Piernas articuladas y pies pesados.
    pygame.draw.polygon(canvas, black_metal,
                        ((77, 190), (111, 198), (105, 251), (58, 254), (65, 235)))
    pygame.draw.polygon(canvas, black_metal,
                        ((163, 190), (129, 198), (135, 251), (182, 254), (175, 235)))
    pygame.draw.polygon(canvas, armor,
                        ((73, 193), (106, 201), (99, 237), (67, 239)))
    pygame.draw.polygon(canvas, armor,
                        ((167, 193), (134, 201), (141, 237), (173, 239)))
    pygame.draw.line(canvas, armor_light, (70, 231), (98, 230), 3)
    pygame.draw.line(canvas, armor_light, (142, 230), (170, 231), 3)

    # Brazos laterales, hombreras y garras animadas.
    pygame.draw.polygon(canvas, black_metal,
                        ((70, 113), (31, 124), (19 + sway, 199), (48 + sway, 219), (77, 166)))
    pygame.draw.polygon(canvas, black_metal,
                        ((170, 113), (209, 124), (221 - sway, 199), (192 - sway, 219), (163, 166)))
    pygame.draw.polygon(canvas, armor,
                        ((69, 108), (30, 119), (37, 158), (73, 151)))
    pygame.draw.polygon(canvas, armor,
                        ((171, 108), (210, 119), (203, 158), (167, 151)))
    pygame.draw.line(canvas, armor_light, (36, 126), (68, 117), 3)
    pygame.draw.line(canvas, armor_light, (204, 126), (172, 117), 3)
    for claw_x, direction in ((25 + sway, -1), (215 - sway, 1)):
        pygame.draw.polygon(canvas, energy,
                            ((claw_x, 197), (claw_x + direction * 13, 213),
                             (claw_x + direction * 3, 208)))
        pygame.draw.polygon(canvas, energy,
                            ((claw_x + direction * -5, 202),
                             (claw_x + direction * 7, 221),
                             (claw_x + direction * -2, 214)))

    # Torso por capas, núcleo y placas abdominales.
    pygame.draw.polygon(canvas, black_metal,
                        ((74, 105), (166, 105), (180, 198), (151, 225),
                         (89, 225), (60, 198)))
    pygame.draw.polygon(canvas, armor,
                        ((82, 113), (158, 113), (166, 190), (145, 211),
                         (95, 211), (74, 190)))
    pygame.draw.polygon(canvas, armor_light,
                        ((88, 119), (152, 119), (145, 134), (95, 134)))
    pygame.draw.circle(canvas, (*energy, 35), (120, 171), 28)
    pygame.draw.circle(canvas, black_metal, (120, 171), 18)
    pygame.draw.circle(canvas, energy, (120, 171), 9 + int(pulse * 3))
    pygame.draw.circle(canvas, WHITE, (117, 168), 3)
    for y in (192, 200):
        pygame.draw.line(canvas, armor_dark, (99, y), (141, y), 4)

    # Casco angular y máscara, sin la antigua boca caricaturesca.
    pygame.draw.polygon(canvas, black_metal,
                        ((78, 67), (94, 39), (146, 39), (162, 67),
                         (157, 119), (143, 137), (97, 137), (83, 119)))
    pygame.draw.polygon(canvas, armor,
                        ((84, 68), (99, 47), (141, 47), (156, 68),
                         (151, 105), (138, 124), (102, 124), (89, 105)))
    pygame.draw.line(canvas, armor_light, (99, 50), (141, 50), 3)
    pygame.draw.polygon(canvas, (4, 5, 11),
                        ((91, 73), (149, 73), (143, 108), (97, 108)))
    eye_color = WHITE if enemy.hurt_timer > 0 else energy
    pygame.draw.polygon(canvas, eye_color, ((96, 82), (116, 86), (99, 94)))
    pygame.draw.polygon(canvas, eye_color, ((144, 82), (124, 86), (141, 94)))
    pygame.draw.rect(canvas, (18, 22, 30), (103, 111, 34, 13), border_radius=3)
    for vent_x in (108, 115, 122, 129):
        pygame.draw.line(canvas, armor_light, (vent_x, 114), (vent_x, 120), 2)
    pygame.draw.circle(canvas, energy, (88, 103), 3)
    pygame.draw.circle(canvas, energy, (152, 103), 3)

    # Cada nivel cambia también sus marcas, no sólo el tono general del blindaje.
    if display_tier == 1:
        pygame.draw.polygon(canvas, energy,
                            ((112, 55), (128, 55), (120, 67)))
        pygame.draw.line(canvas, energy, (83, 146), (104, 157), 4)
        pygame.draw.line(canvas, energy, (157, 146), (136, 157), 4)
        pygame.draw.arc(canvas, armor_light, (102, 153, 36, 36),
                        math.pi * 0.15, math.pi * 0.85, 3)
    elif display_tier == 2:
        for offset in (0, 9):
            pygame.draw.line(canvas, energy,
                             (42 + offset, 128), (55 + offset, 151), 4)
            pygame.draw.line(canvas, energy,
                             (198 - offset, 128), (185 - offset, 151), 4)
        pygame.draw.arc(canvas, energy, (94, 145, 52, 52),
                        math.pi * 0.10, math.pi * 0.90, 4)
        pygame.draw.rect(canvas, armor_light, (108, 59, 24, 4), border_radius=2)
    else:
        pygame.draw.polygon(canvas, armor_light,
                            ((103, 49), (120, 42), (137, 49),
                             (131, 57), (109, 57)))
        for shoulder_x, direction in ((44, 1), (196, -1)):
            pygame.draw.line(canvas, energy,
                             (shoulder_x, 126),
                             (shoulder_x + direction * 22, 142), 5)
            pygame.draw.line(canvas, WHITE,
                             (shoulder_x + direction * 5, 119),
                             (shoulder_x + direction * 25, 133), 3)
        pygame.draw.circle(canvas, energy, (120, 171), 23, 4)
        pygame.draw.polygon(canvas, energy,
                            ((110, 201), (120, 208), (130, 201), (120, 214)))

    # Los diodos del pecho hacen legible el nivel incluso durante el cambio de color.
    for pip in range(3):
        pip_x = 108 + pip * 12
        pip_color = energy if pip < enemy.tier else (28, 31, 40)
        pygame.draw.rect(canvas, pip_color, (pip_x, 217, 7, 4), border_radius=2)

    if not enemy.alive:
        canvas = _enemy_death_canvas(canvas, enemy)

    return pygame.transform.smoothscale(
        canvas, (max(2, size), max(2, int(size * 1.18)))
    )


def _legacy_doom_enemy_canvas(enemy, size):
    """Demonio biomecánico frontal con tres niveles de resistencia legibles."""
    canvas = pygame.Surface((240, 280), pygame.SRCALPHA)
    pulse = (math.sin(enemy.animation * 1.45) + 1.0) / 2.0
    sway = int(math.sin(enemy.animation * 0.82) * 4)
    attack = max(0.0, min(1.0, (enemy.attack_timer - 0.48) / 0.37))

    # El nivel alto lleva placas óseas; al perder vida quedan expuestos músculo
    # rojo y, por último, cuero ocre. La silueta permanece idéntica para no
    # alterar colisiones, puntería ni oclusión.
    palettes = (
        ((91, 61, 35), (156, 105, 54), (103, 91, 63), DOOM_AMBER),
        ((111, 29, 22), (190, 55, 34), (112, 75, 47), (248, 92, 28)),
        ((95, 52, 42), (157, 83, 62), DOOM_BONE, DOOM_RED),
    )
    display_tier = max(1, enemy.tier)
    flesh, flesh_light, plate, eye = palettes[display_tier - 1]
    if enemy.hurt_timer > 0:
        flash = min(1.0, enemy.hurt_timer / 0.24) ** 2
        flesh = _mix_color(flesh, (235, 225, 199), flash * 0.86)
        flesh_light = _mix_color(flesh_light, WHITE, flash)
        plate = _mix_color(plate, WHITE, flash * 0.92)
        eye = _mix_color(eye, WHITE, flash)

    flesh_dark = _scaled_color(flesh, 0.42)
    plate_dark = _scaled_color(plate, 0.48)
    metal = (55, 53, 46)
    metal_dark = (17, 15, 14)
    bone = _mix_color(DOOM_BONE, plate, 0.34 if display_tier < 3 else 0.72)

    pygame.draw.ellipse(canvas, (0, 0, 0, 165), (31, 248, 178, 23))

    # Cuernos y columna posterior crean una silueta infernal incluso a distancia.
    pygame.draw.polygon(canvas, plate_dark,
                        ((84, 74), (48, 12), (58, 78), (78, 108)))
    pygame.draw.polygon(canvas, plate_dark,
                        ((156, 74), (192, 12), (182, 78), (162, 108)))
    pygame.draw.polygon(canvas, bone,
                        ((77, 69), (55, 24), (64, 78)))
    pygame.draw.polygon(canvas, bone,
                        ((163, 69), (185, 24), (176, 78)))
    pygame.draw.line(canvas, plate_dark, (63, 70), (55, 24), 3)
    pygame.draw.line(canvas, plate_dark, (177, 70), (185, 24), 3)

    # Patas digitígradas con tendones visibles y botas/pezuñas metálicas.
    pygame.draw.polygon(canvas, metal_dark,
                        ((77, 187), (111, 196), (103, 247), (55, 258), (67, 224)))
    pygame.draw.polygon(canvas, metal_dark,
                        ((163, 187), (129, 196), (137, 247), (185, 258), (173, 224)))
    pygame.draw.polygon(canvas, flesh_dark,
                        ((75, 190), (106, 199), (98, 237), (66, 243)))
    pygame.draw.polygon(canvas, flesh_dark,
                        ((165, 190), (134, 199), (142, 237), (174, 243)))
    for foot in (((55, 249), (104, 238), (99, 264), (48, 264)),
                 ((185, 249), (136, 238), (141, 264), (192, 264))):
        pygame.draw.polygon(canvas, metal_dark, foot)
        pygame.draw.lines(canvas, DOOM_STEEL, False, foot[:3], 2)

    # Brazos largos; durante el ataque las garras avanzan hacia el centro.
    claw_reach = int(17 * attack)
    left_hand = 24 + sway + claw_reach
    right_hand = 216 - sway - claw_reach
    pygame.draw.polygon(canvas, metal_dark,
                        ((76, 112), (38, 119), (18 + sway, 197),
                         (45 + sway, 222), (82, 160)))
    pygame.draw.polygon(canvas, metal_dark,
                        ((164, 112), (202, 119), (222 - sway, 197),
                         (195 - sway, 222), (158, 160)))
    pygame.draw.polygon(canvas, flesh,
                        ((72, 116), (42, 124), (35 + sway, 171),
                         (53 + sway, 185), (79, 153)))
    pygame.draw.polygon(canvas, flesh,
                        ((168, 116), (198, 124), (205 - sway, 171),
                         (187 - sway, 185), (161, 153)))
    pygame.draw.line(canvas, flesh_light, (44, 130), (69, 122), 3)
    pygame.draw.line(canvas, flesh_light, (196, 130), (171, 122), 3)
    for claw_x, direction in ((left_hand, -1), (right_hand, 1)):
        pygame.draw.polygon(canvas, bone,
                            ((claw_x, 190), (claw_x + direction * 17, 216),
                             (claw_x + direction * 3, 207)))
        pygame.draw.polygon(canvas, bone,
                            ((claw_x - direction * 5, 195),
                             (claw_x + direction * 8, 224),
                             (claw_x - direction * 2, 213)))
        pygame.draw.polygon(canvas, DOOM_BLOOD,
                            ((claw_x, 189), (claw_x + direction * 4, 203),
                             (claw_x - direction * 4, 202)))

    # Torso de músculo y arnés industrial, sin el núcleo de energía neón.
    pygame.draw.polygon(canvas, metal_dark,
                        ((72, 100), (168, 100), (181, 193), (151, 225),
                         (89, 225), (59, 193)))
    pygame.draw.polygon(canvas, flesh,
                        ((81, 108), (159, 108), (169, 184), (145, 210),
                         (95, 210), (71, 184)))
    pygame.draw.polygon(canvas, flesh_light,
                        ((88, 114), (152, 114), (145, 128), (95, 128)))
    pygame.draw.polygon(canvas, plate,
                        ((91, 132), (112, 142), (103, 194), (82, 177)))
    pygame.draw.polygon(canvas, plate,
                        ((149, 132), (128, 142), (137, 194), (158, 177)))
    pygame.draw.lines(canvas, plate_dark, False,
                      ((91, 132), (112, 142), (103, 194)), 3)
    pygame.draw.lines(canvas, plate_dark, False,
                      ((149, 132), (128, 142), (137, 194)), 3)

    # Respiradero mecánico incrustado en el esternón.
    pygame.draw.circle(canvas, metal_dark, (120, 169), 23)
    pygame.draw.circle(canvas, metal, (120, 169), 18)
    pygame.draw.circle(canvas, DOOM_BLOOD, (120, 169), 9 + int(pulse * 2))
    pygame.draw.circle(canvas, DOOM_AMBER, (117, 166), 3)
    for angle in (0, math.pi / 2, math.pi, math.pi * 1.5):
        start = (120 + int(math.cos(angle) * 13), 169 + int(math.sin(angle) * 13))
        end = (120 + int(math.cos(angle) * 20), 169 + int(math.sin(angle) * 20))
        pygame.draw.line(canvas, DOOM_STEEL, start, end, 3)

    # Cabeza hundida con mandíbula ósea y ojos rojos.
    pygame.draw.polygon(canvas, metal_dark,
                        ((77, 61), (94, 37), (146, 37), (163, 61),
                         (155, 119), (139, 139), (101, 139), (85, 119)))
    pygame.draw.polygon(canvas, flesh_dark,
                        ((84, 64), (99, 46), (141, 46), (156, 64),
                         (150, 108), (136, 126), (104, 126), (90, 108)))
    pygame.draw.polygon(canvas, bone,
                        ((91, 69), (106, 54), (134, 54), (149, 69),
                         (141, 103), (99, 103)))
    pygame.draw.polygon(canvas, plate_dark,
                        ((96, 75), (117, 80), (100, 91)))
    pygame.draw.polygon(canvas, plate_dark,
                        ((144, 75), (123, 80), (140, 91)))
    pygame.draw.polygon(canvas, eye, ((99, 79), (116, 83), (101, 90)))
    pygame.draw.polygon(canvas, eye, ((141, 79), (124, 83), (139, 90)))
    pygame.draw.rect(canvas, metal_dark, (103, 104, 34, 17))
    for tooth_x in range(107, 136, 7):
        pygame.draw.polygon(canvas, bone,
                            ((tooth_x, 106), (tooth_x + 5, 106),
                             (tooth_x + 3, 116 + int(attack * 4))))

    # Costuras, tubos y tres marcas de nivel integran carne y maquinaria.
    pygame.draw.line(canvas, metal, (83, 142), (68, 194), 4)
    pygame.draw.line(canvas, metal, (157, 142), (172, 194), 4)
    pygame.draw.circle(canvas, DOOM_STEEL, (82, 143), 3)
    pygame.draw.circle(canvas, DOOM_STEEL, (158, 143), 3)
    for pip in range(3):
        pip_color = DOOM_AMBER if pip < enemy.tier else (45, 31, 25)
        pygame.draw.rect(canvas, pip_color, (108 + pip * 10, 215, 6, 5))

    if not enemy.alive:
        canvas = _enemy_death_canvas(canvas, enemy)

    return pygame.transform.smoothscale(
        canvas, (max(2, size), max(2, int(size * 1.18)))
    )


def _load_enemy_sprites():
    """Carga y normaliza una sola vez los fotogramas RGBA del demonio."""
    global ENEMY_SPRITES
    if ENEMY_SPRITES is None:
        ENEMY_SPRITES = {}
        for state, asset_path in ENEMY_ASSET_PATHS.items():
            sprite = pygame.image.load(str(asset_path))
            if sprite.get_masks()[3] == 0:
                raise ValueError(f"El sprite del enemigo no tiene alfa: {asset_path}")
            if pygame.display.get_surface() is not None:
                sprite = sprite.convert_alpha()
            # Los originales son grandes; 512 px conserva más detalle del que
            # puede mostrar el juego y reduce drásticamente la memoria activa.
            if sprite.get_size() != (512, 512):
                sprite = pygame.transform.scale(sprite, (512, 512))
            ENEMY_SPRITES[state] = sprite
    return ENEMY_SPRITES


def _enemy_frame_name(enemy):
    """Selecciona un fotograma estable a partir del estado real del enemigo."""
    if not enemy.alive:
        if enemy.death_timer < 0:
            return "hurt"
        duration = enemy.DEATH_ANIMATION_TIME
        if enemy.death_timer < duration * 0.18:
            return "death_impact"
        if enemy.death_timer < duration * 0.72:
            return "death_fall"
        return "corpse"
    if enemy.hurt_pose_timer > 0:
        return "hurt"
    if enemy.attack_timer > 0.68:
        return "attack_strike"
    if enemy.attack_timer > 0.40:
        return "attack_prepare"
    if enemy.moving:
        return (
            "walk_a"
            if int(enemy.animation * 0.45) % 2 == 0
            else "walk_b"
        )
    return "idle"


@lru_cache(maxsize=192)
def _scaled_enemy_sprite(state, tier, size):
    """Reutiliza escalas cuantizadas y aplica el nivel de daño una sola vez."""
    # Cada PNG tiene márgenes y poses diferentes. Recortar antes de escalar y
    # fijar la altura evita que un ataque parezca encoger al demonio cercano.
    source = _load_enemy_sprites()[state]
    visible = source.get_bounding_rect(min_alpha=8)
    source = source.subsurface(visible)
    state_height_scales = {
        "death_fall": 0.58,
        "corpse": 0.36,
    }
    target_height = max(
        8, int(size * 1.14 * state_height_scales.get(state, 1.0))
    )
    target_width = max(
        8, int(target_height * source.get_width() / source.get_height())
    )
    sprite = pygame.transform.scale(source, (target_width, target_height))

    # Los tres niveles siguen siendo legibles sin tapar el detalle del arte.
    damage_tints = {
        1: (225, 168, 150),
        2: (255, 220, 208),
        3: (255, 255, 255),
    }
    sprite.fill(damage_tints[max(1, min(3, tier))],
                special_flags=pygame.BLEND_RGB_MULT)
    return sprite


def _doom_enemy_canvas(enemy, size, neutral=False):
    """Devuelve el sprite activo, escalado con caché y listo para iluminación."""
    state = _enemy_frame_name(enemy)
    tier = enemy.tier if enemy.alive else 3
    quantized_size = max(8, int(round(size / 8.0)) * 8)
    sprite = _scaled_enemy_sprite(state, tier, quantized_size).copy()
    if enemy.alive and enemy.hurt_timer > 0:
        flash = _smoothstep(enemy.hurt_timer / 0.24)
        sprite.fill(
            (255, int(255 - 78 * flash), int(255 - 92 * flash)),
            special_flags=pygame.BLEND_RGB_MULT,
        )
        sprite.fill(
            (int(38 * flash), 0, 0), special_flags=pygame.BLEND_RGB_ADD
        )
    if not enemy.alive and enemy.death_timer > enemy.DEATH_ANIMATION_TIME:
        linger = enemy.death_timer - enemy.DEATH_ANIMATION_TIME
        alpha = max(0, int(255 * (1.0 - linger / enemy.CORPSE_LINGER_TIME)))
        sprite.set_alpha(alpha)
    if neutral:
        # La escena educativa necesita una referencia neutra: el color rojo
        # de una variante de combate distrae de la decisión del depth_buffer.
        sprite = pygame.transform.grayscale(sprite)
    return sprite


def _sprite_visible_spans(sprite_left, sprite_width, sprite_depth, depth_buffer):
    """Devuelve las franjas horizontales que no quedan tapadas por una pared."""
    screen_left = max(0, sprite_left)
    screen_right = min(WIDTH, sprite_left + sprite_width)
    if screen_left >= screen_right:
        return []

    first_ray = max(0, screen_left // RAY_WIDTH)
    last_ray = min(NUM_RAYS - 1, (screen_right - 1) // RAY_WIDTH)
    spans = []
    for ray_index in range(first_ray, last_ray + 1):
        ray_left = ray_index * RAY_WIDTH
        destination_x = max(screen_left, ray_left)
        destination_right = min(screen_right, ray_left + RAY_WIDTH)
        if (destination_right > destination_x and
                sprite_depth <= depth_buffer[ray_index] + 0.04):
            spans.append((
                destination_x - sprite_left,
                destination_x,
                destination_right - destination_x,
            ))
    return spans


def _blit_depth_clipped_sprite(surface, sprite, rect, sprite_depth, depth_buffer):
    """Pinta sólo las columnas del enemigo que están delante de la pared."""
    for source_x, destination_x, span_width in _sprite_visible_spans(
            rect.left, rect.width, sprite_depth, depth_buffer):
        source = pygame.Rect(source_x, 0, span_width, sprite.get_height())
        surface.blit(sprite, (destination_x, rect.top), source)


def _enemy_ground_screen_y(depth):
    """Proyecta el apoyo del enemigo sobre el mismo piso que las paredes."""
    wall_height = min(
        int(PROJECTION_DISTANCE / max(depth, 0.001)), HEIGHT * 2
    )
    return HEIGHT // 2 + wall_height // 2


def _enemy_ground_screen_y_clamped(depth, projected_size):
    """Evita que el anclaje cercano hunda todo el sprite fuera de pantalla."""
    projected_ground = _enemy_ground_screen_y(depth)
    close_limit = HEIGHT + int(projected_size * 0.08)
    return min(projected_ground, close_limit)


def _enemy_projected_size(depth):
    """Mantiene crecimiento continuo hasta una escala cercana segura."""
    return min(
        ENEMY_MAX_RENDER_SIZE,
        int(PROJECTION_DISTANCE / max(depth, 0.001) * 0.72),
    )


def draw_enemies(surface, enemies, player, depth_buffer, neutral=False):
    visible = []
    for enemy in enemies:
        if not enemy.alive and not enemy.death_visible:
            continue
        dx, dy = enemy.x - player.x, enemy.y - player.y
        distance = math.hypot(dx, dy)
        relative = normalized_angle(math.atan2(dy, dx) - player.angle)
        if abs(relative) < HALF_FOV + 0.25 and distance > 0.2:
            visible.append((distance, relative, enemy))

    # Primero lo lejano: lo cercano queda pintado encima.
    for distance, relative, enemy in sorted(visible, reverse=True, key=lambda item: item[0]):
        screen_x = WIDTH // 2 + int(relative / FOV * WIDTH)
        corrected = distance * math.cos(relative)
        size = _enemy_projected_size(corrected)
        sprite = _doom_enemy_canvas(enemy, size, neutral=neutral)
        distance_light = max(0.38, min(1.0, 1.0 - max(0.0, corrected - 2) / 17))
        shade = int(255 * distance_light)
        sprite.fill((shade, shade, shade), special_flags=pygame.BLEND_RGB_MULT)
        fog_amount = max(0.0, min(1.0, (corrected - 5) / 15))
        sprite.fill((int(7 * fog_amount), int(11 * fog_amount),
                     int(17 * fog_amount)), special_flags=pygame.BLEND_RGB_ADD)
        ground_y = _enemy_ground_screen_y_clamped(corrected, size)
        rect = sprite.get_rect(midbottom=(screen_x, ground_y))
        _blit_depth_clipped_sprite(surface, sprite, rect, corrected, depth_buffer)


def _shotgun_action_curves(action_timer, recoil):
    elapsed = SHOTGUN_CYCLE - min(SHOTGUN_CYCLE, action_timer)
    firing = action_timer > 0
    blast_curve = max(0.0, 1.0 - elapsed / 0.18) if firing else 0.0
    kick_curve = max(0.0, 1.0 - elapsed / 0.48) if firing else 0.0
    if not firing or elapsed < SHOTGUN_BREAK_START:
        break_amount = 0.0
    elif elapsed < 0.62:
        break_amount = _smoothstep(
            (elapsed - SHOTGUN_BREAK_START) /
            (0.62 - SHOTGUN_BREAK_START)
        )
    elif elapsed < 0.92:
        break_amount = 1.0
    elif elapsed < 1.34:
        break_amount = 1.0 - _smoothstep((elapsed - 0.92) / 0.42)
    else:
        break_amount = 0.0
    fire_curve = max(math.sin(min(1.0, recoil) * math.pi / 2), kick_curve)
    return elapsed, firing, blast_curve, break_amount, fire_curve


def _weapon_switch_curve(progress):
    """Curva 0→1→0 para guardar un arma y levantar la siguiente."""
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.5:
        return _smoothstep(progress * 2.0)
    return 1.0 - _smoothstep((progress - 0.5) * 2.0)


def _draw_double_t_cannon(surface, player, recoil, muzzle_flash,
                          action_timer=0.0):
    """Escopeta basada en el arma original de canales cian y magenta."""
    elapsed, firing, _, break_amount, fire_curve = _shotgun_action_curves(
        action_timer, recoil
    )
    bob_x = math.sin(player.walk_time) * 8 if player.moving else 0
    bob_y = abs(math.cos(player.walk_time)) * 6 if player.moving else 0
    kick = fire_curve * 62 + break_amount * 18
    surface_width, surface_height = surface.get_size()
    cx = surface_width // 2 + int(bob_x)
    bottom = surface_height + int(bob_y + kick)

    if muzzle_flash > 0:
        strength = min(1.0, muzzle_flash / 0.10)
        radius = int(54 + strength * 34)
        center = (radius * 2, radius * 2)
        glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 45, 5, int(45 * strength)), center, radius * 2)
        pygame.draw.circle(glow, (255, 135, 20, int(95 * strength)), center, radius)

        # Estrella irregular y núcleo blanco: más legible que un único círculo.
        points = []
        for index in range(16):
            angle = -math.pi / 2 + index * math.pi / 8
            point_radius = radius if index % 2 == 0 else radius * 0.34
            points.append((center[0] + math.cos(angle) * point_radius,
                           center[1] + math.sin(angle) * point_radius))
        pygame.draw.polygon(glow, (255, 112, 12, int(225 * strength)), points)
        pygame.draw.circle(glow, (255, 238, 170, int(255 * strength)),
                           (center[0] - 14, center[1]),
                           max(5, int(radius * 0.22)))
        pygame.draw.circle(glow, (255, 238, 170, int(255 * strength)),
                           (center[0] + 14, center[1]),
                           max(5, int(radius * 0.22)))
        pygame.draw.circle(glow, (255, 255, 245, int(255 * strength)), center,
                           max(2, int(radius * 0.10)))
        for angle in (-1.85, -1.32, -0.55, -2.55):
            spark_end = (center[0] + math.cos(angle) * radius * 1.45,
                         center[1] + math.sin(angle) * radius * 1.45)
            pygame.draw.line(glow, (255, 192, 55, int(220 * strength)),
                             center, spark_end, 2)
        surface.blit(glow, glow.get_rect(center=(cx, bottom - 215)))

    if firing and 0.28 < elapsed < 1.32:
        for puff_index in range(6):
            cycle = (elapsed * 1.45 + puff_index * 0.19) % 1.0
            side = -1 if puff_index % 2 == 0 else 1
            radius = 3 + int(cycle * 8)
            alpha = int(72 * (1.0 - cycle))
            puff = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(puff, (185, 210, 215, alpha),
                               (radius, radius), radius)
            surface.blit(
                puff,
                (cx + side * (18 + int(cycle * 22)) - radius,
                 bottom - 220 - int(cycle * 45) - radius),
            )

    # Silueta exterior y manos: una base ancha da peso al arma.
    pygame.draw.polygon(surface, (4, 5, 12),
                        [(cx - 125, bottom), (cx - 88, bottom - 120),
                         (cx - 38, bottom - 170), (cx + 38, bottom - 170),
                         (cx + 88, bottom - 120), (cx + 125, bottom)])
    pygame.draw.polygon(surface, (20, 29, 42),
                        [(cx - 82, bottom), (cx - 58, bottom - 126),
                         (cx - 26, bottom - 180), (cx + 26, bottom - 180),
                         (cx + 58, bottom - 126), (cx + 82, bottom)])
    pygame.draw.polygon(surface, (47, 61, 76),
                        [(cx - 58, bottom - 126), (cx - 26, bottom - 180),
                         (cx + 26, bottom - 180), (cx + 58, bottom - 126),
                         (cx + 44, bottom - 52), (cx - 44, bottom - 52)])

    # Canales de energía asimétricos: cian a la izquierda y magenta a la derecha.
    pygame.draw.polygon(surface, (10, 210, 230),
                        [(cx - 42, bottom - 86), (cx - 31, bottom - 151),
                         (cx - 22, bottom - 162), (cx - 28, bottom - 83)])
    pygame.draw.polygon(surface, MAGENTA,
                        [(cx + 42, bottom - 86), (cx + 31, bottom - 151),
                         (cx + 22, bottom - 162), (cx + 28, bottom - 83)])
    pygame.draw.line(surface, (101, 124, 142),
                     (cx - 43, bottom - 52), (cx + 43, bottom - 52), 2)
    pygame.draw.circle(surface, CYAN, (cx - 47, bottom - 68), 4)
    pygame.draw.circle(surface, MAGENTA, (cx + 47, bottom - 68), 4)

    # La recámara usa dos actuadores laterales independientes. Al comenzar el
    # segundo sonido se separan en cian y magenta, mientras los cañones apenas
    # retroceden: así el movimiento se lee como un mecanismo de recarga y no
    # como la corredera vertical del fusil.
    barrel_spread = int(2 * break_amount)
    barrel_y = bottom - 214 + int(4 * break_amount)
    actuator_slide = int(25 * break_amount)
    actuator_drop = int(6 * break_amount)
    rail_y = barrel_y + 35 + actuator_drop
    left_actuator_x = cx - 47 - actuator_slide
    right_actuator_x = cx + 47 + actuator_slide

    # Rieles telescópicos visibles únicamente al abrirse la recámara.
    for start_x, end_x, rail_color in (
        (cx - 29, left_actuator_x + 9, (10, 210, 230)),
        (cx + 29, right_actuator_x - 9, MAGENTA),
    ):
        pygame.draw.line(surface, (3, 5, 11),
                         (start_x, rail_y), (end_x, rail_y), 9)
        pygame.draw.line(surface, rail_color,
                         (start_x, rail_y), (end_x, rail_y), 4)

    # Pestillo central: revela dientes naranjas durante el ciclo mecánico.
    lock_extension = int(13 * break_amount)
    pygame.draw.rect(surface, (5, 7, 14),
                     (cx - 9, barrel_y + 25, 18, 31 + lock_extension),
                     border_radius=4)
    pygame.draw.rect(surface, (72, 87, 101),
                     (cx - 9, barrel_y + 25, 18, 31 + lock_extension), 2,
                     border_radius=4)
    for tooth_y in range(barrel_y + 32, barrel_y + 44 + lock_extension, 7):
        pygame.draw.line(surface, ORANGE,
                         (cx - 3, tooth_y), (cx + 3, tooth_y), 3)

    # Los cañones permanecen centrados; son las cubiertas de recámara las que
    # se desplazan lateralmente con el sonido de bombeo.
    for barrel_x in (cx - 20 - barrel_spread, cx + 20 + barrel_spread):
        pygame.draw.rect(surface, (3, 4, 10),
                         (barrel_x - 19, barrel_y, 38, 54), border_radius=8)
        pygame.draw.rect(surface, (76, 91, 105),
                         (barrel_x - 19, barrel_y, 38, 54), 2,
                         border_radius=8)
        pygame.draw.ellipse(surface, (1, 2, 6),
                            (barrel_x - 14, barrel_y + 8, 28, 19))
        pygame.draw.ellipse(surface, ORANGE,
                            (barrel_x - 9, barrel_y + 13, 18, 8))
        pygame.draw.ellipse(surface, (255, 220, 135),
                            (barrel_x - 3, barrel_y + 15, 6, 3))

    # Cubiertas angulares de la recámara. Sus colores continúan los canales
    # del cuerpo y hacen evidente qué piezas son las que ciclan.
    left_cover = [
        (left_actuator_x + 16, barrel_y + 8 + actuator_drop),
        (left_actuator_x - 8, barrel_y + 5 + actuator_drop),
        (left_actuator_x - 18, barrel_y + 16 + actuator_drop),
        (left_actuator_x - 13, barrel_y + 45 + actuator_drop),
        (left_actuator_x + 10, barrel_y + 50 + actuator_drop),
        (left_actuator_x + 19, barrel_y + 35 + actuator_drop),
    ]
    right_cover = [
        (right_actuator_x - 16, barrel_y + 8 + actuator_drop),
        (right_actuator_x + 8, barrel_y + 5 + actuator_drop),
        (right_actuator_x + 18, barrel_y + 16 + actuator_drop),
        (right_actuator_x + 13, barrel_y + 45 + actuator_drop),
        (right_actuator_x - 10, barrel_y + 50 + actuator_drop),
        (right_actuator_x - 19, barrel_y + 35 + actuator_drop),
    ]
    for cover, color, pivot_x in (
        (left_cover, (10, 210, 230), left_actuator_x - 1),
        (right_cover, MAGENTA, right_actuator_x + 1),
    ):
        pygame.draw.polygon(surface, (4, 7, 14), cover)
        pygame.draw.polygon(surface, color, cover, 3)
        pygame.draw.line(surface, color,
                         cover[1], cover[4], 2)
        pygame.draw.circle(surface, (4, 7, 14),
                           (pivot_x, barrel_y + 29 + actuator_drop), 7)
        pygame.draw.circle(surface, color,
                           (pivot_x, barrel_y + 29 + actuator_drop), 4)

    # Destello de energía en el punto de máxima apertura.
    if break_amount > 0.65:
        pulse_radius = 2 + int(2 * break_amount)
        pygame.draw.circle(surface, (190, 255, 255),
                           (left_actuator_x - 1,
                            barrel_y + 29 + actuator_drop), pulse_radius)
        pygame.draw.circle(surface, (255, 205, 245),
                           (right_actuator_x + 1,
                            barrel_y + 29 + actuator_drop), pulse_radius)


def _draw_vanguard_weapon(surface, player, recoil, muzzle_flash,
                          action_timer=0.0, full_view=False, prototype=False):
    """Familia Vanguardia: fusil original o escopeta prototipo preservada."""
    ticks = pygame.time.get_ticks() / 1000.0
    idle_breath = math.sin(ticks * 2.2)

    if prototype:
        elapsed, firing, blast_curve, break_amount, fire_curve = (
            _shotgun_action_curves(action_timer, recoil)
        )
    else:
        elapsed = 0.0
        firing = False
        blast_curve = 0.0
        break_amount = 0.0
        fire_curve = math.sin(min(1.0, recoil) * math.pi / 2)

    if player.moving:
        walk_x = math.sin(player.walk_time) * 11
        walk_y = abs(math.cos(player.walk_time)) * 8
        walk_tilt = math.sin(player.walk_time) * 2.4
    else:
        walk_x = idle_breath * 1.2
        walk_y = idle_breath * 1.6
        walk_tilt = idle_breath * 0.35

    weapon = pygame.Surface((440, 350), pygame.SRCALPHA)
    cx = weapon.get_width() // 2
    slide = int((19 if prototype else 17) * fire_curve + 24 * break_amount)
    pulse = (math.sin(ticks * 4.8) + 1.0) / 2.0

    # El fusil conserva su fogonazo único; el prototipo dispara ambos cañones.
    if muzzle_flash > 0:
        strength = min(1.0, muzzle_flash / (0.18 if prototype else 0.10))
        flash_y = 37 + slide
        if prototype:
            pygame.draw.circle(weapon, (255, 48, 5, int(55 * strength)),
                               (cx, flash_y), int(102 * strength))
            flash_centers = (cx - 25, cx + 25)
            rays = 16
            long_radius, short_radius = 62, 16
        else:
            pygame.draw.circle(weapon, (255, 55, 8, int(35 * strength)),
                               (cx, flash_y), int(76 * strength))
            pygame.draw.circle(weapon, (255, 142, 22, int(90 * strength)),
                               (cx, flash_y), int(42 * strength))
            flash_centers = (cx,)
            rays = 20
            long_radius, short_radius = 54, 15

        for barrel_x in flash_centers:
            points = []
            for index in range(rays):
                angle = index * math.tau / rays
                radius = (long_radius if index % 2 == 0 else short_radius) * strength
                points.append((barrel_x + math.cos(angle) * radius,
                               flash_y + math.sin(angle) * radius))
            pygame.draw.polygon(
                weapon, (255, 112, 10, int(235 * strength)), points
            )
            pygame.draw.circle(
                weapon, (255, 249, 210, int(255 * strength)),
                (barrel_x, flash_y), max(4, int(13 * strength)),
            )
        if prototype:
            pygame.draw.line(weapon, (255, 205, 92, int(220 * strength)),
                             (cx + 22, flash_y + 10),
                             (cx + 132, flash_y + 38), 4)
            pygame.draw.line(weapon, (255, 205, 92, int(220 * strength)),
                             (cx - 22, flash_y + 10),
                             (cx - 118, flash_y + 52), 3)

    # Durante la apertura, ambos cañones expulsan vapor y calor residual.
    if prototype and firing and 0.28 < elapsed < 1.32:
        for puff_index in range(7):
            cycle = (elapsed * 1.45 + puff_index * 0.17) % 1.0
            side = -1 if puff_index % 2 == 0 else 1
            puff_x = cx + side * (25 + int(cycle * 24))
            puff_y = 61 + slide - int(cycle * 48)
            radius = 3 + int(cycle * 9)
            alpha = int(90 * (1.0 - cycle))
            pygame.draw.circle(weapon, (185, 210, 215, alpha),
                               (puff_x, puff_y), radius)

    # Antebrazos y guantes sostienen el arma; se mueven junto con todo el conjunto.
    pygame.draw.polygon(weapon, (18, 24, 34),
                        ((55, 350), (76, 284), (142, 244), (174, 286), (158, 350)))
    pygame.draw.polygon(weapon, (18, 24, 34),
                        ((385, 350), (364, 284), (298, 244), (266, 286), (282, 350)))
    pygame.draw.polygon(weapon, (78, 48, 42),
                        ((91, 307), (124, 262), (163, 254), (177, 287), (145, 324)))
    pygame.draw.polygon(weapon, (78, 48, 42),
                        ((349, 307), (316, 262), (277, 254), (263, 287), (295, 324)))
    for glove_x in (116, 300):
        pygame.draw.rect(weapon, (27, 38, 49), (glove_x, 273, 25, 38), border_radius=7)
        pygame.draw.line(weapon, (76, 93, 108),
                         (glove_x + 4, 280), (glove_x + 21, 280), 2)

    # Silueta principal: culata ancha, empuñadura central y hombros mecánicos.
    pygame.draw.polygon(weapon, (3, 5, 10),
                        ((122, 339), (132, 260), (157, 211), (167, 154),
                         (190, 126), (250, 126), (273, 154), (283, 211),
                         (308, 260), (318, 339)))
    pygame.draw.polygon(weapon, (19, 28, 39),
                        ((139, 337), (146, 266), (171, 220), (180, 164),
                         (198, 141), (242, 141), (260, 164), (269, 220),
                         (294, 266), (301, 337)))

    # Placas laterales con bisel y sombreado; la forma es más técnica que la clásica.
    pygame.draw.polygon(weapon, (42, 58, 73),
                        ((146, 264), (171, 220), (185, 170), (205, 185),
                         (199, 272), (168, 319)))
    pygame.draw.polygon(weapon, (34, 46, 61),
                        ((294, 264), (269, 220), (255, 170), (235, 185),
                         (241, 272), (272, 319)))
    pygame.draw.line(weapon, (103, 126, 143), (158, 260), (182, 218), 3)
    pygame.draw.line(weapon, (82, 101, 119), (282, 260), (258, 218), 3)
    pygame.draw.line(weapon, CYAN, (166, 250), (187, 207), 3)
    pygame.draw.line(weapon, MAGENTA, (274, 250), (253, 207), 3)

    # Cámara energética del fusil; el prototipo se calienta tras el doble disparo.
    pygame.draw.polygon(weapon, (5, 8, 15),
                        ((190, 172), (250, 172), (260, 233), (244, 266),
                         (196, 266), (180, 233)))
    pygame.draw.polygon(weapon, (63, 79, 94),
                        ((196, 181), (244, 181), (250, 230), (238, 253),
                         (202, 253), (190, 230)), 3)
    pygame.draw.polygon(weapon, (9, 22, 31),
                        ((201, 188), (239, 188), (244, 227), (234, 245),
                         (206, 245), (196, 227)))
    if prototype:
        core_color = _mix_color(
            CYAN, (255, 100, 24), pulse * 0.18 + blast_curve * 0.82
        )
    else:
        core_color = _mix_color(
            CYAN, (255, 245, 185), pulse * 0.28 + fire_curve * 0.62
        )
    pygame.draw.circle(weapon, (*core_color, 38), (220, 218), 30)
    pygame.draw.circle(weapon, core_color, (220, 218), 15 + int(pulse * 3))
    pygame.draw.circle(weapon, WHITE, (216, 213), 4)
    pygame.draw.arc(weapon, MAGENTA, (194, 192, 52, 52), 0.2, 2.6, 3)
    pygame.draw.arc(weapon, CYAN, (194, 192, 52, 52), 3.3, 5.8, 3)

    # El bloque superior retrocede y baja mientras se abre el cierre doble.
    upper_y = slide
    pygame.draw.polygon(weapon, (2, 4, 9),
                        ((166, 158 + upper_y), (176, 91 + upper_y),
                         (194, 66 + upper_y), (246, 66 + upper_y),
                         (264, 91 + upper_y), (274, 158 + upper_y)))
    pygame.draw.polygon(weapon, (38, 53, 67),
                        ((179, 151 + upper_y), (187, 98 + upper_y),
                         (201, 79 + upper_y), (239, 79 + upper_y),
                         (253, 98 + upper_y), (261, 151 + upper_y)))
    pygame.draw.polygon(weapon, (66, 84, 101),
                        ((188, 101 + upper_y), (201, 82 + upper_y),
                         (239, 82 + upper_y), (249, 101 + upper_y)))
    pygame.draw.line(weapon, (130, 151, 166),
                     (202, 84 + upper_y), (238, 84 + upper_y), 3)

    if prototype:
        # Dos bocas independientes preservan la variante experimental.
        barrel_spread = int(7 * break_amount)
        for barrel_x in (cx - 25 - barrel_spread, cx + 25 + barrel_spread):
            pygame.draw.rect(weapon, (3, 4, 8),
                             (barrel_x - 22, 54 + upper_y, 44, 47),
                             border_radius=10)
            pygame.draw.rect(weapon, (93, 109, 121),
                             (barrel_x - 22, 54 + upper_y, 44, 47), 3,
                             border_radius=10)
            pygame.draw.ellipse(weapon, (1, 2, 5),
                                (barrel_x - 16, 63 + upper_y, 32, 20))
            pygame.draw.ellipse(weapon, ORANGE,
                                (barrel_x - 10, 69 + upper_y, 20, 8))
            pygame.draw.ellipse(weapon, (255, 226, 146),
                                (barrel_x - 4, 71 + upper_y, 8, 4))
        pygame.draw.rect(weapon, (25, 34, 45),
                         (cx - 9, 65 + upper_y, 18, 28), border_radius=4)
        pygame.draw.line(weapon, ORANGE,
                         (cx, 69 + upper_y), (cx, 88 + upper_y), 3)
    else:
        # Boca única original del FUSIL DOBLE-T.
        pygame.draw.rect(weapon, (3, 4, 8),
                         (190, 55 + upper_y, 60, 44), border_radius=10)
        pygame.draw.rect(weapon, (82, 100, 114),
                         (190, 55 + upper_y, 60, 44), 3, border_radius=10)
        pygame.draw.rect(weapon, (7, 10, 16),
                         (199, 62 + upper_y, 42, 22), border_radius=7)
        pygame.draw.ellipse(weapon, (1, 2, 5),
                            (204, 64 + upper_y, 32, 18))
        pygame.draw.ellipse(weapon, ORANGE,
                            (211, 69 + upper_y, 18, 8))
        pygame.draw.ellipse(weapon, (255, 215, 125),
                            (216, 71 + upper_y, 8, 4))
    for vent_x in (187, 196, 244, 253):
        pygame.draw.line(weapon, (7, 11, 18),
                         (vent_x, 119 + upper_y), (vent_x + 3, 139 + upper_y), 4)
    for bolt_x in (184, 256):
        pygame.draw.circle(weapon, (139, 158, 171),
                           (bolt_x, 151 + upper_y), 3)
        pygame.draw.circle(weapon, (5, 8, 13),
                           (bolt_x, 151 + upper_y), 1)

    # Empuñadura y seguro inferior; completan la lectura de arma funcional.
    pygame.draw.polygon(weapon, (4, 6, 11),
                        ((198, 267), (242, 267), (254, 342), (186, 342)))
    pygame.draw.polygon(weapon, (28, 38, 49),
                        ((204, 272), (236, 272), (244, 335), (196, 335)))
    for grip_y in range(284, 330, 10):
        pygame.draw.line(weapon, (62, 77, 89),
                         (200, grip_y), (240, grip_y + 3), 3)
    pygame.draw.rect(weapon, (4, 7, 12), (206, 153, 28, 14), border_radius=5)
    pygame.draw.rect(weapon, ORANGE, (212, 157, 16, 5), border_radius=2)

    # El retroceso levanta el arma; la marcha balancea todo el conjunto con inercia.
    recoil_tilt = 1.5 if prototype else 0.8
    transformed = pygame.transform.rotate(
        weapon, -walk_tilt - fire_curve * recoil_tilt
    )
    surface_width, surface_height = surface.get_size()
    weapon_bottom = surface_height if full_view else surface_height + 83
    destination = transformed.get_rect(
        midbottom=(surface_width // 2 + int(walk_x),
                   weapon_bottom + int(walk_y) -
                   int((36 if prototype else 20) * fire_curve))
    )
    surface.blit(transformed, destination)


def _load_weapon_sprites():
    """Carga los sprites activos una sola vez, después de crear la pantalla."""
    global WEAPON_SPRITES
    if WEAPON_SPRITES is None:
        WEAPON_SPRITES = {
            name: pygame.image.load(str(path)).convert_alpha()
            for name, path in WEAPON_ASSET_PATHS.items()
        }
    return WEAPON_SPRITES


def _draw_pixel_muzzle_flash(surface, center_x, center_y, strength,
                             double_barrel=False):
    """Fogonazo cálido y recortado, más cercano a un sprite que a un halo."""
    strength = max(0.0, min(1.0, strength))
    radius = max(6, int(52 * strength))
    flash = pygame.Surface((radius * 4, radius * 3), pygame.SRCALPHA)
    center = (flash.get_width() // 2, flash.get_height() // 2)
    pygame.draw.rect(
        flash, (167, 35, 12, int(64 * strength)),
        (center[0] - radius, center[1] - radius // 2,
         radius * 2, radius),
    )
    points = (
        (center[0], center[1] - radius),
        (center[0] + radius // 4, center[1] - radius // 4),
        (center[0] + radius, center[1]),
        (center[0] + radius // 4, center[1] + radius // 4),
        (center[0], center[1] + radius),
        (center[0] - radius // 4, center[1] + radius // 4),
        (center[0] - radius, center[1]),
        (center[0] - radius // 4, center[1] - radius // 4),
    )
    pygame.draw.polygon(flash, (*DOOM_RED, int(238 * strength)), points)
    core_offset = max(4, int(10 * strength))
    core_centers = (
        ((center[0] - core_offset, center[1]),
         (center[0] + core_offset, center[1]))
        if double_barrel else ((center[0], center[1]),)
    )
    for core in core_centers:
        pygame.draw.rect(
            flash, (*DOOM_AMBER, int(255 * strength)),
            (core[0] - max(2, radius // 7),
             core[1] - max(2, radius // 7),
             max(4, radius // 3), max(4, radius // 3)),
        )
        pygame.draw.rect(
            flash, (255, 244, 196, int(255 * strength)),
            (core[0] - 2, core[1] - 2, 5, 5),
        )
    surface.blit(flash, flash.get_rect(center=(center_x, center_y)))


def _draw_doom_weapon(surface, player, recoil, muzzle_flash, style,
                      full_view=False, action_timer=0.0,
                      switch_progress=0.0):
    sprites = _load_weapon_sprites()
    shotgun = style == "doom_shotgun"
    if shotgun:
        elapsed, firing, _, break_amount, fire_curve = _shotgun_action_curves(
            action_timer, recoil
        )
        sprite_key = "doom_shotgun_open" if break_amount >= 0.42 else style
        kick = fire_curve * 52 + break_amount * 7
        muzzle_local_y = 60 if sprite_key == style else 126
    else:
        elapsed = 0.0
        firing = False
        break_amount = 0.0
        fire_curve = math.sin(min(1.0, recoil) * math.pi / 2)
        sprite_key = style
        kick = fire_curve * 27
        muzzle_local_y = 86

    sprite = sprites[sprite_key]
    switch_amount = _weapon_switch_curve(switch_progress)
    switch_side = math.sin(switch_progress * math.pi) * 18
    if switch_progress < 0.5:
        switch_side *= -1
    if switch_amount > 0:
        switch_tilt = (6.0 if switch_progress < 0.5 else -6.0) * switch_amount
        sprite = pygame.transform.rotate(sprite, switch_tilt)
    if player.moving:
        bob_x = math.sin(player.walk_time) * 10
        bob_y = abs(math.cos(player.walk_time)) * 7
    else:
        idle = math.sin(pygame.time.get_ticks() / 1000.0 * 2.0)
        bob_x = idle * 1.2
        bob_y = idle * 1.0

    surface_width, surface_height = surface.get_size()
    weapon_bottom = surface_height + (68 if not full_view else 5)
    destination = sprite.get_rect(
        midbottom=(surface_width // 2 + int(bob_x + switch_side),
                   weapon_bottom + int(bob_y - kick + switch_amount * 290))
    )
    muzzle_x = destination.centerx
    muzzle_y = destination.top + muzzle_local_y

    if muzzle_flash > 0:
        duration = 0.18 if shotgun else 0.10
        _draw_pixel_muzzle_flash(
            surface, muzzle_x, muzzle_y,
            min(1.0, muzzle_flash / duration), shotgun,
        )

    # Humo pixelado determinista durante la apertura. No crea partículas de
    # mundo ni modifica la duración del ciclo de la escopeta.
    if shotgun and firing and 0.25 < elapsed < 1.26:
        smoke_progress = min(1.0, (elapsed - 0.25) / 0.82)
        smoke_color = _mix_color((150, 139, 119), (62, 55, 48), smoke_progress)
        for index in range(5):
            drift = int((smoke_progress * 34 + index * 11) % 47)
            side = -1 if index % 2 == 0 else 1
            size = 3 + index % 3
            pygame.draw.rect(
                surface, smoke_color,
                (muzzle_x + side * (9 + drift // 2),
                 muzzle_y - 8 - drift, size * 2, size),
            )

    surface.blit(sprite, destination)


def draw_weapon(surface, player, recoil, muzzle_flash, style="doom_rifle",
                full_view=False, action_timer=0.0, switch_progress=0.0):
    """Dibuja sólo las dos armas nuevas; las variantes antiguas quedan inactivas."""
    if style not in ACTIVE_WEAPON_STYLES:
        return
    _draw_doom_weapon(
        surface, player, recoil, muzzle_flash, style, full_view, action_timer,
        switch_progress,
    )


def draw_crosshair(surface, spread=0, hit_confirm=0.0):
    cx, cy = surface.get_width() // 2, surface.get_height() // 2
    gap = 6 + int(spread * 14)
    for start, end in (
        ((cx - gap - 6, cy), (cx - gap, cy)), ((cx + gap, cy), (cx + gap + 6, cy)),
        ((cx, cy - gap - 6), (cx, cy - gap)), ((cx, cy + gap), (cx, cy + gap + 6)),
    ):
        pygame.draw.line(surface, DOOM_BLACK, start, end, 5)
        pygame.draw.line(surface, DOOM_BONE, start, end, 2)
    pygame.draw.rect(surface, DOOM_BLACK, (cx - 3, cy - 3, 7, 7))
    pygame.draw.rect(surface, DOOM_RED, (cx - 1, cy - 1, 3, 3))
    if hit_confirm > 0:
        strength = min(1.0, hit_confirm / 0.14)
        reach = 13 + int(3 * strength)
        inner = 7
        color = _mix_color(DOOM_RUST, DOOM_BONE, strength)
        for direction_x, direction_y in (
                (-1, -1), (1, -1), (-1, 1), (1, 1)):
            start = (
                cx + direction_x * inner,
                cy + direction_y * inner,
            )
            end = (
                cx + direction_x * reach,
                cy + direction_y * reach,
            )
            pygame.draw.line(surface, DOOM_BLACK, start, end, 5)
            pygame.draw.line(surface, color, start, end, 2)


def _draw_status_face(surface, player, face_rect, damage_flash):
    """Retrato animado: mira, parpadea y acumula heridas según la salud."""
    health = max(0, player.health)
    damage_level = min(3, (100 - health) // 25)
    ticks = pygame.time.get_ticks()
    gaze_pattern = (0, 2, 0, -2, 0, 1, 0, -1)
    gaze_x = gaze_pattern[(ticks // 720) % len(gaze_pattern)]
    blinking = ticks % 4100 > 3970
    reacting = damage_flash > 0.12

    pygame.draw.rect(surface, (1, 2, 7), face_rect, border_radius=6)
    frame_color = ORANGE if reacting else (86, 100, 116)
    pygame.draw.rect(surface, frame_color, face_rect, 3, border_radius=6)

    # Casco exterior. Las grietas aparecen a medida que baja la vida.
    helmet = (32, 44, 58) if damage_level < 3 else (23, 29, 38)
    pygame.draw.polygon(surface, helmet,
                        ((448, face_rect.bottom - 13), (451, face_rect.top + 21),
                         (469, face_rect.top + 10), (491, face_rect.top + 10),
                         (509, face_rect.top + 21), (512, face_rect.bottom - 13)))
    pygame.draw.line(surface, (86, 105, 122),
                     (456, face_rect.top + 21), (470, face_rect.top + 13), 2)

    skin_by_damage = (
        (139, 88, 70), (126, 76, 65), (107, 67, 65), (80, 55, 60)
    )
    skin = skin_by_damage[damage_level]
    pygame.draw.rect(surface, skin,
                     (459, face_rect.top + 26, 42, 36), border_radius=9)
    pygame.draw.polygon(surface, _scaled_color(skin, 0.72),
                        ((459, face_rect.top + 45), (466, face_rect.top + 62),
                         (494, face_rect.top + 62), (501, face_rect.top + 45)))

    # Cejas y ojos separados permiten animar la mirada con pupilas reales.
    brow_color = (48, 23, 23)
    pygame.draw.line(surface, brow_color,
                     (463, face_rect.top + 36), (476, face_rect.top + 39), 3)
    pygame.draw.line(surface, brow_color,
                     (497, face_rect.top + 36), (484, face_rect.top + 39), 3)
    eye_color = (255, 116, 40) if not reacting else (255, 230, 185)
    left_eye = pygame.Rect(464, face_rect.top + 40, 12, 6)
    right_eye = pygame.Rect(484, face_rect.top + 40, 12, 6)
    if blinking and not reacting:
        pygame.draw.line(surface, brow_color, left_eye.midleft, left_eye.midright, 2)
        pygame.draw.line(surface, brow_color, right_eye.midleft, right_eye.midright, 2)
    else:
        pygame.draw.rect(surface, eye_color, left_eye, border_radius=2)
        pygame.draw.rect(surface, eye_color, right_eye, border_radius=2)
        pupil_y = face_rect.top + 42
        pygame.draw.rect(surface, (7, 5, 8), (469 + gaze_x, pupil_y, 3, 4))
        pygame.draw.rect(surface, (7, 5, 8), (489 + gaze_x, pupil_y, 3, 4))

    # La boca pasa de firme a dolor, y se abre durante el impacto.
    mouth_y = face_rect.top + 55
    if reacting:
        pygame.draw.ellipse(surface, (30, 8, 13), (473, mouth_y - 2, 15, 9))
        pygame.draw.line(surface, (215, 190, 170), (476, mouth_y), (485, mouth_y), 2)
    elif damage_level >= 2:
        pygame.draw.lines(surface, (34, 10, 14), False,
                          ((470, mouth_y + 3), (478, mouth_y),
                           (486, mouth_y + 4), (492, mouth_y + 1)), 3)
    else:
        pygame.draw.line(surface, (31, 12, 16), (470, mouth_y), (490, mouth_y), 3)

    blood = (123, 6, 24)
    dark_blood = (68, 4, 17)
    if damage_level >= 1:
        pygame.draw.line(surface, blood,
                         (493, face_rect.top + 27), (490, face_rect.top + 39), 3)
        pygame.draw.circle(surface, dark_blood, (490, face_rect.top + 41), 2)
        pygame.draw.line(surface, (12, 18, 25),
                         (503, face_rect.top + 18), (496, face_rect.top + 27), 2)
    if damage_level >= 2:
        pygame.draw.polygon(surface, (72, 34, 48),
                            ((462, face_rect.top + 42), (476, face_rect.top + 39),
                             (477, face_rect.top + 48), (464, face_rect.top + 50)))
        pygame.draw.line(surface, blood,
                         (466, face_rect.top + 46), (469, face_rect.top + 60), 3)
        pygame.draw.line(surface, dark_blood,
                         (483, face_rect.top + 47), (487, face_rect.top + 61), 2)
        pygame.draw.lines(surface, (11, 15, 21), False,
                          ((455, face_rect.top + 18), (463, face_rect.top + 25),
                           (458, face_rect.top + 31)), 2)
    if damage_level >= 3:
        pygame.draw.ellipse(surface, (51, 21, 39),
                            (482, face_rect.top + 36, 17, 14))
        pygame.draw.line(surface, blood,
                         (498, face_rect.top + 30), (496, face_rect.top + 59), 4)
        pygame.draw.circle(surface, blood, (496, face_rect.top + 61), 2)
        pygame.draw.lines(surface, (9, 13, 19), False,
                          ((506, face_rect.top + 23), (499, face_rect.top + 29),
                           (504, face_rect.top + 35), (497, face_rect.top + 42)), 2)


def _draw_doom_status_face(surface, player, face_rect, damage_flash):
    """Retrato pixelado relativo al panel, con heridas acumulativas."""
    portrait = pygame.Surface(face_rect.size, pygame.SRCALPHA)
    width, height = face_rect.size
    health = max(0, player.health)
    damage_level = min(3, (100 - health) // 25)
    ticks = pygame.time.get_ticks()
    gaze = (0, 2, 0, -2, 0, 1, 0, -1)[(ticks // 720) % 8]
    blinking = ticks % 4100 > 3970
    reacting = damage_flash > 0.12

    portrait.fill(DOOM_BLACK)
    frame = DOOM_RED if reacting else DOOM_STEEL
    pygame.draw.rect(portrait, frame, portrait.get_rect(), 3)
    pygame.draw.rect(portrait, DOOM_DARK, (5, 5, width - 10, height - 10))

    helmet = (49, 57, 43) if damage_level < 3 else (35, 35, 30)
    pygame.draw.polygon(
        portrait, helmet,
        ((14, height - 8), (16, 24), (28, 9), (width - 28, 9),
         (width - 16, 24), (width - 14, height - 8)),
    )
    pygame.draw.line(portrait, DOOM_STEEL, (28, 11), (width - 28, 11), 3)
    pygame.draw.rect(portrait, DOOM_BLOOD, (width // 2 - 10, 12, 20, 4))

    skin = (164, 105, 72) if damage_level < 2 else (139, 79, 62)
    skin_dark = _scaled_color(skin, 0.63)
    pygame.draw.rect(portrait, skin, (24, 27, width - 48, height - 38))
    pygame.draw.polygon(
        portrait, skin_dark,
        ((24, 27), (35, 22), (width - 35, 22), (width - 24, 27),
         (width - 29, height - 11), (29, height - 11)),
    )
    pygame.draw.rect(portrait, skin, (30, 28, width - 60, height - 42))

    brow_y = 35
    pygame.draw.line(portrait, (49, 25, 19), (31, brow_y), (45, brow_y - 3), 4)
    pygame.draw.line(portrait, (49, 25, 19),
                     (width - 31, brow_y), (width - 45, brow_y - 3), 4)
    if blinking:
        pygame.draw.line(portrait, (35, 21, 18), (32, 42), (45, 42), 3)
        pygame.draw.line(portrait, (35, 21, 18),
                         (width - 45, 42), (width - 32, 42), 3)
    else:
        pygame.draw.rect(portrait, DOOM_BONE, (32, 39, 13, 7))
        pygame.draw.rect(portrait, DOOM_BONE, (width - 45, 39, 13, 7))
        pygame.draw.rect(portrait, DOOM_BLACK, (37 + gaze, 40, 4, 6))
        pygame.draw.rect(portrait, DOOM_BLACK, (width - 41 + gaze, 40, 4, 6))

    mouth_y = height - 22
    if reacting:
        pygame.draw.rect(portrait, (47, 12, 12), (width // 2 - 10, mouth_y - 3, 20, 9))
        pygame.draw.line(portrait, DOOM_BONE,
                         (width // 2 - 7, mouth_y), (width // 2 + 7, mouth_y), 2)
    else:
        pygame.draw.line(portrait, (48, 18, 16),
                         (width // 2 - 11, mouth_y), (width // 2 + 11, mouth_y), 4)

    if damage_level >= 1:
        pygame.draw.line(portrait, DOOM_BLOOD, (31, 46), (27, 61), 3)
        pygame.draw.rect(portrait, (73, 34, 38), (width - 43, 48, 13, 8))
    if damage_level >= 2:
        pygame.draw.polygon(portrait, (72, 32, 34),
                            ((26, 29), (38, 27), (42, 35), (29, 39)))
        pygame.draw.line(portrait, DOOM_BLOOD, (35, 35), (40, height - 13), 3)
        pygame.draw.line(portrait, DOOM_BLACK,
                         (width - 23, 15), (width - 33, 27), 2)
    if damage_level >= 3:
        pygame.draw.rect(portrait, (52, 19, 25), (width - 48, 34, 17, 16))
        pygame.draw.line(portrait, DOOM_BLOOD,
                         (width - 33, 28), (width - 36, height - 12), 4)
        pygame.draw.lines(portrait, DOOM_BLACK, False,
                          ((17, 18), (24, 25), (19, 33), (27, 40)), 2)

    surface.blit(portrait, face_rect)


def draw_hud(surface, player, score, weapon_style, font, small_font,
             damage_flash=0.0):
    """Barra clásica de metal y piedra con datos reales del juego."""
    surface_width, surface_height = surface.get_size()
    hud_height = 96
    hud_y = surface_height - hud_height
    pygame.draw.rect(surface, DOOM_BLACK, (0, hud_y, surface_width, hud_height))
    pygame.draw.rect(surface, (56, 45, 35), (0, hud_y + 5, surface_width, hud_height - 5))
    pygame.draw.line(surface, DOOM_STEEL, (0, hud_y), (surface_width, hud_y), 5)
    pygame.draw.line(surface, DOOM_RUST, (0, hud_y + 5), (surface_width, hud_y + 5), 3)

    # Moteado determinista de piedra para evitar una franja digital plana.
    for index in range(70):
        x = (index * 137 + 29) % surface_width
        y = hud_y + 10 + (index * 47) % (hud_height - 16)
        color = (72, 57, 42) if index % 3 else (39, 32, 27)
        pygame.draw.rect(surface, color, (x, y, 4 + index % 5, 2))

    def panel(rect):
        pygame.draw.rect(surface, (19, 16, 14), rect)
        pygame.draw.line(surface, DOOM_STEEL, rect.topleft, rect.topright, 3)
        pygame.draw.line(surface, (31, 27, 23), rect.bottomleft, rect.bottomright, 3)
        pygame.draw.rect(surface, DOOM_BLACK, rect, 2)

    def text(value, color, position, use_font=small_font):
        surface.blit(use_font.render(value, False, color), position)

    margin, gap = 10, 7
    face_width, arms_width = 100, 55
    flexible_width = surface_width - margin * 2 - gap * 5 - face_width - arms_width
    score_width = int(flexible_width * 0.20)
    health_width = int(flexible_width * 0.20)
    weapon_width = int(flexible_width * 0.24)
    goal_width = flexible_width - score_width - health_width - weapon_width
    cursor_x = margin

    score_rect = pygame.Rect(cursor_x, hud_y + 11, score_width, 76)
    cursor_x = score_rect.right + gap
    health_rect = pygame.Rect(cursor_x, hud_y + 11, health_width, 76)
    cursor_x = health_rect.right + gap
    arms_rect = pygame.Rect(cursor_x, hud_y + 11, arms_width, 76)
    cursor_x = arms_rect.right + gap
    face_rect = pygame.Rect(cursor_x, hud_y + 6, face_width, 84)
    cursor_x = face_rect.right + gap
    weapon_rect = pygame.Rect(cursor_x, hud_y + 11, weapon_width, 76)
    cursor_x = weapon_rect.right + gap
    goal_rect = pygame.Rect(cursor_x, hud_y + 11, goal_width, 76)
    for rect in (score_rect, health_rect, arms_rect, weapon_rect, goal_rect):
        panel(rect)

    text("PUNTOS", DOOM_BONE, (score_rect.x + 10, score_rect.y + 7))
    text(f"{score:04d}", DOOM_RED, (score_rect.x + 10, score_rect.y + 28), font)

    health = max(0, player.health)
    health_color = DOOM_RED if health > 35 else DOOM_AMBER
    text("VIDA", DOOM_BONE, (health_rect.x + 10, health_rect.y + 7))
    text(f"{health:03d}%", health_color,
         (health_rect.x + 10, health_rect.y + 28), font)

    text("1", DOOM_BONE, (arms_rect.x + 8, arms_rect.y + 7))
    text("2", DOOM_BONE, (arms_rect.x + 29, arms_rect.y + 7))
    selected_slot = 1 if weapon_style == "doom_rifle" else 2
    for slot, x in ((1, arms_rect.x + 6), (2, arms_rect.x + 27)):
        color = DOOM_RED if slot == selected_slot else (70, 57, 43)
        pygame.draw.rect(surface, color, (x, arms_rect.y + 29, 18, 31))
        pygame.draw.rect(surface, DOOM_BLACK, (x, arms_rect.y + 29, 18, 31), 2)
        text(str(slot), DOOM_BONE, (x + 5, arms_rect.y + 36))

    _draw_doom_status_face(surface, player, face_rect, damage_flash)

    weapon_name = "RIFLE" if weapon_style == "doom_rifle" else "ESCOPETA"
    text("ARMA", DOOM_BONE, (weapon_rect.x + 10, weapon_rect.y + 7))
    text(weapon_name, DOOM_AMBER, (weapon_rect.x + 10, weapon_rect.y + 31))
    text("MUNICION INFINITA", DOOM_STEEL,
         (weapon_rect.x + 10, weapon_rect.y + 53))

    text("BRECHA", DOOM_BONE, (goal_rect.x + 10, goal_rect.y + 7))
    text(f"{score:04d}/{TARGET_SCORE}", DOOM_RED,
         (goal_rect.x + 10, goal_rect.y + 27), font)
    progress = max(0.0, min(1.0, score / TARGET_SCORE))
    bar = pygame.Rect(goal_rect.x + 11, goal_rect.bottom - 14, goal_rect.width - 22, 7)
    pygame.draw.rect(surface, (45, 31, 25), bar)
    pygame.draw.rect(surface, DOOM_BLOOD,
                     (bar.x, bar.y, int(bar.width * progress), bar.height))
    pygame.draw.rect(surface, DOOM_BLACK, bar, 1)


def draw_minimap(surface, player, enemies):
    """Automapa de fósforo dentro de un monitor militar desgastado."""
    global RADAR_FONT
    if RADAR_FONT is None:
        RADAR_FONT = pygame.font.SysFont("consolas", 11, bold=True)

    scale = 6
    map_width = len(MAP[0]) * scale
    map_height = len(MAP) * scale
    offset_x, offset_y = surface.get_width() - map_width - 17, 31
    frame = pygame.Rect(offset_x - 8, offset_y - 20, map_width + 16, map_height + 28)
    backing = pygame.Surface(frame.size, pygame.SRCALPHA)
    backing.fill((13, 12, 9, 232))
    surface.blit(backing, frame)
    pygame.draw.rect(surface, DOOM_BLACK, frame, 5)
    pygame.draw.rect(surface, DOOM_STEEL, frame, 2)
    pygame.draw.line(surface, DOOM_RUST, (frame.left + 4, frame.top + 3),
                     (frame.right - 4, frame.top + 3), 2)
    surface.blit(RADAR_FONT.render("AUTOMAPA // S01", False, DOOM_BONE),
                 (offset_x, offset_y - 16))

    pygame.draw.rect(surface, (12, 18, 10), (offset_x, offset_y, map_width, map_height))
    for y, row in enumerate(MAP):
        for x, tile in enumerate(row):
            if tile != ".":
                color = MINIMAP_WALL_COLORS.get(tile, CYAN)
                pygame.draw.rect(surface, color,
                                 (offset_x + x * scale, offset_y + y * scale,
                                  scale - 2, scale - 2))
    for enemy in enemies:
        if enemy.alive:
            pygame.draw.circle(surface, DOOM_RED,
                               (offset_x + int(enemy.x * scale), offset_y + int(enemy.y * scale)), 2)
    px, py = offset_x + int(player.x * scale), offset_y + int(player.y * scale)
    pygame.draw.circle(surface, (0, 0, 0), (px, py), 5)
    pygame.draw.circle(surface, DOOM_BONE, (px, py), 3)
    pygame.draw.line(surface, DOOM_PHOSPHOR, (px, py),
                     (px + int(math.cos(player.angle) * 9),
                      py + int(math.sin(player.angle) * 9)), 2)


def draw_particles(surface, particles):
    for particle in particles:
        if particle.life > 0:
            radius = max(1, int(particle.size * min(1, particle.life * 4)))
            pygame.draw.circle(surface, particle.color,
                               (int(particle.x), int(particle.y)), radius)


def draw_damage_vignette(surface, amount):
    """Golpe rojo intenso: fogonazo central y presión oscura en los bordes."""
    level = max(0, min(10, int(amount * 16)))
    if level <= 0:
        return
    key = (surface.get_size(), level)
    overlay = DAMAGE_OVERLAYS.get(key)
    if overlay is None:
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        strength = level / 10
        overlay.fill((*DOOM_RED, int(38 * strength)))
        for band in range(12):
            alpha = int(strength * (86 - band * 6))
            inset = band * 9
            pygame.draw.rect(
                overlay, (*DOOM_BLOOD, alpha),
                (inset, inset, width - inset * 2, height - inset * 2),
                max(4, 18 - band),
            )
        # Dos cortes diagonales breves dan dirección al impacto sin ocultar la mira.
        slash_alpha = int(72 * strength)
        pygame.draw.polygon(
            overlay, (255, 32, 18, slash_alpha),
            ((0, height // 5), (width // 3, 0),
             (width // 3 + 34, 0), (0, height // 5 + 24)),
        )
        pygame.draw.polygon(
            overlay, (125, 0, 0, slash_alpha),
            ((width, height * 3 // 4), (width * 2 // 3, height),
             (width * 2 // 3 - 38, height), (width, height * 3 // 4 - 28)),
        )
        DAMAGE_OVERLAYS[key] = overlay
    surface.blit(overlay, (0, 0))


def draw_scanlines(surface):
    width, height = surface.get_size()
    key = (width, height)
    overlay = SCANLINE_OVERLAYS.get(key)
    if overlay is None:
        overlay = pygame.Surface(key, pygame.SRCALPHA)
        for y in range(0, height, 4):
            pygame.draw.line(overlay, (0, 0, 0, 12),
                             (0, y), (width, y))
        SCANLINE_OVERLAYS[key] = overlay
    surface.blit(overlay, (0, 0))
