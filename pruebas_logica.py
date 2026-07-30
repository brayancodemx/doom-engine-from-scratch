"""Pruebas rápidas sin abrir una ventana. Útiles antes de grabar."""

import math
from collections import deque

import pygame

from entities import (
    Enemy, Player, create_enemy, normalized_angle, normalized_move_axes,
)
from map_data import ENEMY_SPAWNS, MAP, MAP_HEIGHT, MAP_WIDTH, PLAYER_START, is_wall, tile_at
from raycasting import cast_all_rays, cast_one_ray
from renderer import (
    ACTIVE_WEAPON_STYLES, CEILING_TEXTURE_ASSET_PATHS, ENEMY_ASSET_PATHS,
    ENVIRONMENT_TEXTURE_SIZE, FLOOR_TEXTURE_ASSET_PATHS,
    LEGACY_WEAPON_STYLES, WALL_COLORS, WALL_TEXTURE_ASSET_PATHS,
    WEAPON_ASSET_PATHS, _create_wall_texture, _doom_enemy_canvas,
    _enemy_frame_name, _enemy_ground_screen_y, _enemy_ground_screen_y_clamped,
    _enemy_projected_size, _load_ceiling_textures, _load_floor_textures,
    _load_wall_textures, _project_world_point, _shotgun_action_curves,
    _sprite_visible_spans, _weapon_switch_curve, draw_background,
    draw_ceiling_details, draw_walls,
)
from settings import (
    ENEMY_MAX_HEALTH, ENEMY_MAX_RENDER_SIZE, ENEMY_MIN_HEALTH, HEIGHT,
    INITIAL_ENEMY_COUNT, MIN_ACTIVE_ENEMIES, NUM_RAYS, PROJECTION_DISTANCE,
    RIFLE_HURT_REACTION_CHANCE, SHOTGUN_CYCLE, WIDTH,
)


def run_tests():
    forward, strafe = normalized_move_axes(1, 1)
    assert math.isclose(math.hypot(forward, strafe), 1.0)
    assert normalized_move_axes(1, 0) == (1, 0)
    assert normalized_move_axes(0, -1) == (0, -1)

    assert len(MAP) == 20
    assert all(len(row) == 20 for row in MAP)
    assert MAP_WIDTH == 20 and MAP_HEIGHT == 20
    assert is_wall(0, 0)
    assert not is_wall(*PLAYER_START)
    assert tile_at(-1, 3) == "1"
    assert sum(row.count(".") for row in MAP) > MAP_WIDTH * MAP_HEIGHT * 0.70

    # Los spawns se generan sólo en suelo libre, alejados del inicio y sin duplicados.
    assert len(ENEMY_SPAWNS) == 24
    assert len(set(ENEMY_SPAWNS)) == len(ENEMY_SPAWNS)
    assert all(not is_wall(x, y) for x, y in ENEMY_SPAWNS)
    assert all(math.hypot(x - PLAYER_START[0], y - PLAYER_START[1]) >= 4.0
               for x, y in ENEMY_SPAWNS)

    # Todos los sectores libres deben pertenecer a la misma red transitable.
    start_cell = (int(PLAYER_START[0]), int(PLAYER_START[1]))
    reachable = {start_cell}
    pending = deque([start_cell])
    while pending:
        grid_x, grid_y = pending.popleft()
        for offset_x, offset_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            next_x, next_y = grid_x + offset_x, grid_y + offset_y
            if not (0 <= next_x < MAP_WIDTH and 0 <= next_y < MAP_HEIGHT):
                continue
            if MAP[next_y][next_x] == "." and (next_x, next_y) not in reachable:
                reachable.add((next_x, next_y))
                pending.append((next_x, next_y))
    assert len(reachable) == sum(row.count(".") for row in MAP)

    player = Player()
    distance, wall, _, _, _ = cast_one_ray(player.x, player.y, player.angle)
    assert distance > 0
    assert wall != "."
    assert -math.pi <= normalized_angle(10) <= math.pi
    exact_distance, _, hit_x, _, _ = cast_one_ray(2.5, 2.5, 0.0)
    assert math.isclose(exact_distance, 16.5)
    assert math.isclose(hit_x, 19.0)

    # Piso y techo comparten proyección y permanecen anclados al mundo al girar.
    floor_point = _project_world_point(player, player.x + 2, player.y, 0.0)
    ceiling_point = _project_world_point(player, player.x + 2, player.y, 1.0)
    assert floor_point and floor_point[1] > HEIGHT // 2
    assert ceiling_point and ceiling_point[1] < HEIGHT // 2
    assert _project_world_point(player, player.x - 2, player.y, 0.0) is None

    # Las superficies de material son deterministas y no cambian entre cuadros.
    texture_a = _create_wall_texture("1", WALL_COLORS["1"])
    texture_b = _create_wall_texture("1", WALL_COLORS["1"])
    assert pygame.image.tostring(texture_a, "RGB") == pygame.image.tostring(texture_b, "RGB")

    # Las seis paredes, tres pisos y tres techos se cargan desde PNG opacos.
    assert set(WALL_TEXTURE_ASSET_PATHS) == set("123456")
    assert set(FLOOR_TEXTURE_ASSET_PATHS) == {"steel", "grate", "dirty"}
    assert set(CEILING_TEXTURE_ASSET_PATHS) == {"steel", "grate", "rust"}
    for asset_path in (
        *WALL_TEXTURE_ASSET_PATHS.values(),
        *FLOOR_TEXTURE_ASSET_PATHS.values(),
        *CEILING_TEXTURE_ASSET_PATHS.values(),
    ):
        assert asset_path.exists(), asset_path
        texture = pygame.image.load(str(asset_path))
        assert texture.get_width() == texture.get_height()
        assert texture.get_width() >= 1024
        assert texture.get_masks()[3] == 0
    assert all(texture.get_size() == (ENVIRONMENT_TEXTURE_SIZE,) * 2
               for texture in _load_wall_textures().values())
    assert all(texture.get_size() == (ENVIRONMENT_TEXTURE_SIZE,) * 2
               for texture in _load_floor_textures().values())
    assert all(texture.get_size() == (ENVIRONMENT_TEXTURE_SIZE,) * 2
               for texture in _load_ceiling_textures().values())
    floor_a = pygame.Surface((WIDTH, HEIGHT))
    floor_b = pygame.Surface((WIDTH, HEIGHT))
    rays, depths = cast_all_rays(player)
    draw_background(floor_a, 1.0, player, depths)
    draw_background(floor_b, 1.0, player, depths)
    assert pygame.image.tostring(floor_a, "RGB") == pygame.image.tostring(
        floor_b, "RGB"
    )

    # El techo se compone antes de los muros: puede verse en cielo abierto,
    # pero nunca modifica los píxeles que pertenecen a una pared cercana.
    with_ceiling = floor_a.copy()
    without_ceiling = floor_b.copy()
    draw_ceiling_details(with_ceiling, player, 1.0, depths)
    draw_walls(with_ceiling, rays, 1.0)
    draw_walls(without_ceiling, rays, 1.0)
    assert pygame.image.tostring(with_ceiling, "RGB") != pygame.image.tostring(
        without_ceiling, "RGB"
    )
    center_ray = NUM_RAYS // 2
    wall_depth = rays[center_ray][0]
    wall_height = min(int(PROJECTION_DISTANCE / wall_depth), HEIGHT * 2)
    projected_top = HEIGHT // 2 - wall_height // 2
    wall_top = max(0, projected_top)
    wall_bottom = min(HEIGHT, projected_top + wall_height)
    wall_rect = pygame.Rect(
        center_ray * (WIDTH // NUM_RAYS), wall_top,
        WIDTH // NUM_RAYS, wall_bottom - wall_top,
    )
    assert pygame.image.tostring(
        with_ceiling.subsurface(wall_rect), "RGB"
    ) == pygame.image.tostring(without_ceiling.subsurface(wall_rect), "RGB")

    # Una marca del mundo cambia de proyección al girar; no queda pegada a pantalla.
    rotated = Player(angle=player.angle + 0.65)
    world_mark_a = _project_world_point(player, 8.5, 7.5, 0.0)
    world_mark_b = _project_world_point(rotated, 8.5, 7.5, 0.0)
    assert world_mark_a and world_mark_b
    assert world_mark_a[:2] != world_mark_b[:2]

    # Un muro puede ocultar el centro o un lateral sin hacer desaparecer el resto.
    depths = [10.0] * NUM_RAYS
    depths[50] = 2.0
    depths[52] = 2.0
    spans = _sprite_visible_spans(100, 12, 5.0, depths)
    assert all(destination not in (100, 104) for _, destination, _ in spans)
    assert sum(width for _, _, width in spans) == 8

    # Un enemigo muerto deja de atacar, completa su caída y luego puede retirarse.
    corpse = Enemy(4.5, 3.5, health=0, animation=2.0)
    corpse_position = (corpse.x, corpse.y)
    assert corpse.death_visible
    assert not corpse.update(player, 0.5)
    assert math.isclose(corpse.death_timer, 0.5)
    assert (corpse.x, corpse.y) == corpse_position
    assert math.isclose(corpse.animation, 2.0)
    corpse.update(player, corpse.DEATH_ANIMATION_TIME + corpse.CORPSE_LINGER_TIME)
    assert corpse.death_finished

    # Los pies y los restos comparten exactamente la base proyectada del muro.
    ground_depth = 5.0
    expected_wall_height = min(
        int(PROJECTION_DISTANCE / ground_depth), HEIGHT * 2
    )
    assert _enemy_ground_screen_y(ground_depth) == (
        HEIGHT // 2 + expected_wall_height // 2
    )
    assert _enemy_projected_size(0.9) > _enemy_projected_size(1.4)
    assert _enemy_projected_size(1.4) > _enemy_projected_size(2.0)
    assert _enemy_projected_size(0.9) > 360
    assert _enemy_projected_size(0.1) == ENEMY_MAX_RENDER_SIZE
    close_size = _enemy_projected_size(0.1)
    assert _enemy_ground_screen_y_clamped(0.1, close_size) <= (
        HEIGHT + int(close_size * 0.08)
    )
    assert _enemy_ground_screen_y_clamped(0.1, close_size) < (
        _enemy_ground_screen_y(0.1)
    )

    # Los colores representan tres impactos y descienden un nivel por disparo.
    armored = Enemy(5.0, 5.0, health=3, variant=2)
    assert armored.tier == 3
    assert not armored.take_damage()
    assert armored.health == 2 and armored.tier == 2
    assert math.isclose(armored.hurt_timer, 0.24)
    assert math.isclose(armored.hurt_pose_timer, 0.24)
    assert not armored.take_damage()
    assert armored.health == 1 and armored.tier == 1
    assert armored.take_damage()
    assert armored.health == 0 and not armored.alive

    armored = Enemy(5.0, 5.0, health=3, variant=2)
    assert armored.take_damage(armored.health)
    assert armored.health == 0
    assert math.isclose(SHOTGUN_CYCLE, 1.5)
    assert math.isclose(RIFLE_HURT_REACTION_CHANCE, 0.40)
    assert INITIAL_ENEMY_COUNT == 8 and MIN_ACTIVE_ENEMIES == 7

    # El destello rojo permanece aunque el impacto no active la pose corporal.
    steady = Enemy(5.0, 5.0, health=5)
    steady.take_damage(play_hurt_pose=False)
    assert steady.hurt_timer > 0 and steady.hurt_pose_timer == 0
    assert _enemy_frame_name(steady) == "idle"
    steady_flash = pygame.image.tostring(_doom_enemy_canvas(steady, 160), "RGBA")
    calm_sprite = pygame.image.tostring(
        _doom_enemy_canvas(Enemy(5.0, 5.0, health=5), 160), "RGBA"
    )
    assert steady_flash != calm_sprite

    # La persecución mantiene presión sin cruzar el mapa a una velocidad que
    # haga ilegible la animación de marcha.
    walker = Enemy(5.0, 1.5, health=3, variant=2)
    assert not walker.update(Player(2.0, 1.5), 1.0)
    assert math.isclose(walker.x, 4.54)

    # El pilar central obliga a rodear; nunca se invade su volumen.
    navigator = Enemy(8.5, 9.5, health=5, variant=2)
    navigation_target = Player(11.5, 9.5)
    for _ in range(240):
        navigator.update(navigation_target, 0.05)
        assert not navigator._touches_wall(navigator.x, navigator.y)
    assert navigator.x > 10.5

    # Sólo las dos armas nuevas son seleccionables; las anteriores permanecen
    # documentadas en código, sin compartir identificadores activos.
    assert ACTIVE_WEAPON_STYLES == ("doom_rifle", "doom_shotgun")
    assert not set(ACTIVE_WEAPON_STYLES) & set(LEGACY_WEAPON_STYLES)
    assert set(WEAPON_ASSET_PATHS) == {
        "doom_rifle", "doom_shotgun", "doom_shotgun_open"
    }
    for asset_path in WEAPON_ASSET_PATHS.values():
        assert asset_path.exists(), asset_path
        sprite = pygame.image.load(str(asset_path))
        assert sprite.get_masks()[3] != 0
        assert all(sprite.get_at(corner).a == 0 for corner in (
            (0, 0), (sprite.get_width() - 1, 0),
            (0, sprite.get_height() - 1),
            (sprite.get_width() - 1, sprite.get_height() - 1),
        ))
        visible = sprite.get_bounding_rect(min_alpha=8)
        assert visible.width > sprite.get_width() * 0.45
        assert visible.height > sprite.get_height() * 0.60

    # La secuencia completa del demonio usa PNG transparentes y encuadres
    # aprovechables, sin conservar el verde de producción en las esquinas.
    assert set(ENEMY_ASSET_PATHS) == {
        "idle", "walk_a", "walk_b", "attack_prepare", "attack_strike",
        "hurt", "death_impact", "death_fall", "corpse",
    }
    for asset_path in ENEMY_ASSET_PATHS.values():
        assert asset_path.exists(), asset_path
        sprite = pygame.image.load(str(asset_path))
        assert sprite.get_masks()[3] != 0
        assert all(sprite.get_at(corner).a == 0 for corner in (
            (0, 0), (sprite.get_width() - 1, 0),
            (0, sprite.get_height() - 1),
            (sprite.get_width() - 1, sprite.get_height() - 1),
        ))
        visible = sprite.get_bounding_rect(min_alpha=8)
        assert visible.width > sprite.get_width() * 0.55
        assert visible.height > sprite.get_height() * 0.60

    # La recámara sólo se abre después del fogonazo y vuelve a cerrarse al
    # terminar el ciclo de 1.5 segundos.
    _, firing, _, opening, _ = _shotgun_action_curves(SHOTGUN_CYCLE, 1.0)
    assert firing and math.isclose(opening, 0.0)
    _, firing, _, opening, _ = _shotgun_action_curves(0.80, 0.0)
    assert firing and opening > 0.95
    _, firing, _, opening, _ = _shotgun_action_curves(0.0, 0.0)
    assert not firing and math.isclose(opening, 0.0)

    # Los tres niveles del demonio usan dibujos cromáticamente distintos.
    demon_tiers = [
        pygame.image.tostring(
            _doom_enemy_canvas(Enemy(5.0, 5.0, health=tier), 120), "RGBA"
        )
        for tier in (1, 2, 3)
    ]
    assert len(set(demon_tiers)) == 3

    animated = Enemy(5.0, 5.0, health=3)
    assert _enemy_frame_name(animated) == "idle"
    animated.moving = True
    animated.animation = 0.0
    assert _enemy_frame_name(animated) == "walk_a"
    animated.animation = 1.25
    assert _enemy_frame_name(animated) == "walk_a"
    animated.animation = 2.50
    assert _enemy_frame_name(animated) == "walk_b"
    animated.animation = 4.50
    assert _enemy_frame_name(animated) == "walk_a"
    animated.attack_timer = 0.85
    assert _enemy_frame_name(animated) == "attack_strike"
    animated.hurt_pose_timer = 0.24
    assert _enemy_frame_name(animated) == "hurt"
    animated.health = 0
    assert _enemy_frame_name(animated) == "death_impact"
    animated.death_timer = animated.DEATH_ANIMATION_TIME
    assert _enemy_frame_name(animated) == "corpse"

    delayed = Enemy(5.0, 5.0, health=3)
    assert delayed.trigger_death(0.30)
    assert delayed.health == 0 and math.isclose(delayed.death_timer, -0.30)
    assert _enemy_frame_name(delayed) == "hurt"
    delayed.update(player, 0.31)
    assert _enemy_frame_name(delayed) == "death_impact"

    live_sprite = _doom_enemy_canvas(Enemy(5.0, 5.0, health=3), 240)
    attack_sprite = _doom_enemy_canvas(
        Enemy(5.0, 5.0, health=3, attack_timer=0.85), 240
    )
    assert attack_sprite.get_height() == live_sprite.get_height()
    corpse_sprite = _doom_enemy_canvas(animated, 240)
    assert corpse_sprite.get_width() < live_sprite.get_width() * 0.80
    assert corpse_sprite.get_height() < live_sprite.get_height() * 0.50

    for _ in range(20):
        spawned = create_enemy(6.0, 6.0)
        assert ENEMY_MIN_HEALTH <= spawned.health <= ENEMY_MAX_HEALTH
        assert spawned.variant == spawned.health - ENEMY_MIN_HEALTH

    # El rifle resta un punto por impacto: cada demonio exige de 2 a 3 tiros.
    assert (ENEMY_MIN_HEALTH, ENEMY_MAX_HEALTH) == (2, 3)
    for health in range(ENEMY_MIN_HEALTH, ENEMY_MAX_HEALTH + 1):
        target = Enemy(6.0, 6.0, health=health)
        for _ in range(health - 1):
            assert not target.take_damage()
        assert target.take_damage()

    # El cambio baja por completo el arma vieja y levanta la nueva suavemente.
    assert math.isclose(_weapon_switch_curve(0.0), 0.0)
    assert math.isclose(_weapon_switch_curve(0.5), 1.0)
    assert math.isclose(_weapon_switch_curve(1.0), 0.0)
    assert _weapon_switch_curve(0.25) > 0
    assert _weapon_switch_curve(0.75) > 0

    print(
        "OK: arena, DDA, texturas, oclusión, armas, demonios y muertes funcionan."
    )


if __name__ == "__main__":
    run_tests()
