"""ETAPA 10 — Radiografía animada del pipeline completo de un fotograma."""

import math
import sys
from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from entities import Player, create_enemy, normalized_angle
from map_data import MAP
from raycasting import cast_all_rays
from renderer import (
    Particle,
    WALL_COLORS,
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
from settings import (
    BLACK,
    CYAN,
    FOV,
    HEIGHT,
    MAGENTA,
    NUM_RAYS,
    ORANGE,
    PROJECTION_DISTANCE,
    RAY_WIDTH,
    WHITE,
    WIDTH,
)

DEMO_WIDTH = 1600
DEMO_HEIGHT = 900
SCENE_POS = (16, 104)
SIDEBAR_RECT = pygame.Rect(1312, 104, 272, 720)
STEP_SECONDS = 5.2
RAY_VISUAL_STRIDE = 8

STEPS = (
    ("RAYOS + BÚFER", "raycasting.py · cast_all_rays"),
    ("TECHO Y SUELO", "renderer.py · draw_background"),
    ("PAREDES", "renderer.py · draw_walls"),
    ("ENEMIGOS + OCLUSIÓN", "renderer.py · draw_enemies"),
    ("NIEBLA + ATMÓSFERA", "renderer.py · draw_world_atmosphere"),
    ("MOVIMIENTO DE CÁMARA", "main.py · frame.scroll"),
    ("FOGONAZO + PARTÍCULAS", "renderer.py · draw_particles"),
    ("ARMA EN PRIMER PLANO", "renderer.py · draw_weapon"),
    ("MIRA + HUD + RADAR", "renderer.py · draw_hud / draw_minimap"),
    ("DAÑO + LÍNEAS RETRO", "renderer.py · draw_scanlines"),
)

EXPLANATIONS = (
    "640 rayos devuelven distancia, pared e impacto. Las 640 distancias forman el depth_buffer.",
    "El horizonte separa techo y piso. Esta capa debe existir antes que las paredes.",
    "Cada distancia se transforma en altura: proyección / distancia. Un rayo produce una columna.",
    "El sprite se divide en franjas. Sólo se copia una franja si está delante de la pared correspondiente.",
    "Se reconstruye el fondo con detalles y se agrega niebla. Todo sigue usando las mismas distancias.",
    "El mundo completo se desplaza unos píxeles. HUD, radar y arma todavía no existen en esta capa.",
    "El fogonazo ilumina el fotograma y las partículas se actualizan como puntos con velocidad y vida.",
    "El arma es una ilustración 2D dibujada sobre el mundo; por eso ninguna pared puede taparla.",
    "La interfaz se ancla a la pantalla, no al mapa. Se dibuja después de la cámara y del arma.",
    "El flash de daño y las scanlines son filtros finales aplicados sobre toda la composición.",
)


def _fit_text(font, text, max_width):
    """Divide texto por palabras para los paneles estrechos de explicación."""
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _draw_header(screen, step, font, small_font, automatic, paused, progress):
    pygame.draw.rect(screen, (3, 5, 13), (0, 0, DEMO_WIDTH, 88))
    pygame.draw.line(screen, CYAN, (0, 86), (DEMO_WIDTH // 2, 86), 2)
    pygame.draw.line(screen, MAGENTA,
                     (DEMO_WIDTH // 2, 86), (DEMO_WIDTH, 86), 2)
    screen.blit(font.render("RADIOGRAFÍA DE UN FOTOGRAMA", True, WHITE), (18, 13))
    screen.blit(small_font.render(
        "No es una animación prerenderizada: cada capa usa las funciones reales de NEON BREACH.",
        True, (145, 174, 191)), (20, 48))
    mode = "AUTOMÁTICO" if automatic else "MANUAL"
    if paused:
        mode += " · PAUSA"
    label = small_font.render(
        f"PASO {step}/10 · {mode}", True, ORANGE if paused else CYAN
    )
    screen.blit(label, label.get_rect(topright=(DEMO_WIDTH - 18, 18)))
    timeline = pygame.Rect(18, 78, DEMO_WIDTH - 36, 4)
    pygame.draw.rect(screen, (31, 44, 58), timeline)
    pygame.draw.rect(screen, ORANGE,
                     (timeline.x, timeline.y,
                      int(timeline.width * max(0.0, min(1.0, progress))),
                      timeline.height))


def _draw_sidebar(screen, step, font, tiny_font, rays, depth_buffer,
                  camera_offset, progress):
    panel = pygame.Surface(SIDEBAR_RECT.size, pygame.SRCALPHA)
    panel.fill((3, 6, 16, 245))
    pygame.draw.rect(panel, (56, 77, 94), panel.get_rect(), 2, border_radius=7)
    screen.blit(panel, SIDEBAR_RECT)

    x = SIDEBAR_RECT.x + 12
    y = SIDEBAR_RECT.y + 12
    screen.blit(font.render("ORDEN DE COMPOSICIÓN", True, WHITE), (x, y))
    y += 34
    for index, (name, _) in enumerate(STEPS, start=1):
        completed = index <= step
        active = index == step
        color = ORANGE if active else (CYAN if completed else (68, 79, 94))
        marker = "▶" if active else ("■" if completed else "□")
        label = f"{marker} {index:02d}  {name}"
        screen.blit(tiny_font.render(label, True, color), (x, y))
        y += 31

    active_name, active_call = STEPS[step - 1]
    info_rect = pygame.Rect(x - 2, SIDEBAR_RECT.bottom - 172,
                            SIDEBAR_RECT.width - 20, 158)
    pygame.draw.rect(screen, (8, 13, 25), info_rect, border_radius=6)
    pygame.draw.rect(screen, ORANGE, info_rect, 1, border_radius=6)
    screen.blit(tiny_font.render(active_name, True, ORANGE),
                (info_rect.x + 9, info_rect.y + 8))
    screen.blit(tiny_font.render(active_call, True, CYAN),
                (info_rect.x + 9, info_rect.y + 28))
    text_y = info_rect.y + 51
    for line in _fit_text(tiny_font, EXPLANATIONS[step - 1], info_rect.width - 18):
        screen.blit(tiny_font.render(line, True, (188, 204, 216)),
                    (info_rect.x + 9, text_y))
        text_y += 17

    finite_depths = [depth for depth in depth_buffer if math.isfinite(depth)]
    min_depth = min(finite_depths, default=0.0)
    max_depth = max(finite_depths, default=0.0)
    diagnostic = (
        f"rayos={len(rays)}  buffer={len(depth_buffer)}  "
        f"z={min_depth:.2f}…{max_depth:.2f}  cámara={camera_offset}"
    )
    screen.blit(tiny_font.render(diagnostic, True, (135, 155, 173)),
                (18, DEMO_HEIGHT - 42))
    screen.blit(tiny_font.render(
        "1–9/0 paso · ←/→ anterior/siguiente · A automático · ESPACIO pausa · R reinicia · ESC sale",
        True, WHITE), (515, DEMO_HEIGHT - 42))
    timeline = pygame.Rect(SIDEBAR_RECT.x, DEMO_HEIGHT - 48,
                           SIDEBAR_RECT.width, 3)
    pygame.draw.rect(screen, (38, 54, 68), timeline)
    pygame.draw.rect(screen, ORANGE,
                     (timeline.x, timeline.y,
                      int(timeline.width * max(0.0, min(1.0, progress))), 3))


def _draw_depth_graph(surface, depth_buffer, rect, font, title=True,
                      reveal_count=None):
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    overlay.fill((2, 5, 14, 232))
    pygame.draw.rect(overlay, CYAN, overlay.get_rect(), 2, border_radius=6)
    surface.blit(overlay, rect)
    if title:
        surface.blit(font.render(
            f"DEPTH_BUFFER[{len(depth_buffer)}] · distancia por columna", True, WHITE),
                     (rect.x + 12, rect.y + 9))
    graph_top = rect.y + (38 if title else 8)
    graph_bottom = rect.bottom - 15
    graph_height = max(1, graph_bottom - graph_top)
    points = []
    visible_depths = depth_buffer if reveal_count is None else depth_buffer[:reveal_count]
    for index, depth in enumerate(visible_depths):
        x = rect.x + int(index / max(1, len(depth_buffer) - 1) * (rect.width - 1))
        normalized = min(1.0, depth / 14.0)
        y = graph_top + int(normalized * graph_height)
        points.append((x, y))
    if len(points) > 1:
        pygame.draw.lines(surface, MAGENTA, False, points, 2)
    pygame.draw.line(surface, (70, 88, 105),
                     (rect.x, graph_top), (rect.right, graph_top), 1)


def _draw_ray_debug(surface, player, rays, depth_buffer, font, tiny_font,
                    progress=1.0):
    surface.fill((4, 6, 15))
    scale = 21
    map_x, map_y = 34, 80
    map_width = len(MAP[0]) * scale
    map_height = len(MAP) * scale

    # La toma empieza en el plano: primero entra el mapa, luego el jugador y
    # finalmente los rayos. El contador deja claro que no es una diapositiva.
    map_progress = _smoothstep(progress / 0.18)
    player_progress = _smoothstep((progress - 0.18) / 0.12)
    ray_progress = _smoothstep((progress - 0.30) / 0.55)
    visual_ray_indices = tuple(range(0, len(rays), RAY_VISUAL_STRIDE))
    visual_count = min(len(visual_ray_indices),
                       int(len(visual_ray_indices) * ray_progress))
    reveal_count = (
        visual_ray_indices[visual_count - 1] + 1 if visual_count else 0
    )
    active_index = visual_ray_indices[visual_count - 1] if visual_count else -1

    right_panel = pygame.Rect(490, 52, 760, 535)
    pygame.draw.rect(surface, (6, 10, 20), right_panel, border_radius=8)
    pygame.draw.rect(surface, (44, 68, 84), right_panel, 2, border_radius=8)

    map_layer = pygame.Surface((map_width + 24, map_height + 24), pygame.SRCALPHA)
    pygame.draw.rect(map_layer, (7, 12, 24, 245), map_layer.get_rect(),
                     border_radius=8)
    for y, row in enumerate(MAP):
        for x, tile in enumerate(row):
            rect = pygame.Rect(12 + x * scale, 12 + y * scale,
                               scale - 1, scale - 1)
            if tile == ".":
                pygame.draw.rect(map_layer, (12, 19, 30, 255), rect)
            else:
                pygame.draw.rect(map_layer, (*WALL_COLORS.get(tile, CYAN), 255), rect)
    map_layer.set_alpha(int(255 * map_progress))
    surface.blit(map_layer, (map_x - 12, map_y - 12))

    player_pos = (map_x + int(player.x * scale), map_y + int(player.y * scale))
    for ray_index in visual_ray_indices[:visual_count]:
        _, _, hit_x, hit_y = rays[ray_index]
        end = (map_x + int(hit_x * scale), map_y + int(hit_y * scale))
        active = ray_index == active_index
        pygame.draw.line(surface, ORANGE if active else (20, 124, 151),
                         player_pos, end, 2 if active else 1)
        pygame.draw.circle(surface, ORANGE if active else (69, 194, 210),
                           end, 4 if active else 2)
    if player_progress > 0:
        pygame.draw.circle(surface, BLACK, player_pos, 8)
        pygame.draw.circle(surface, WHITE, player_pos, 6)
        pygame.draw.line(
            surface, ORANGE, player_pos,
            (player_pos[0] + int(math.cos(player.angle) * 22 * player_progress),
             player_pos[1] + int(math.sin(player.angle) * 22 * player_progress)), 3,
        )

    right_x = 520
    surface.blit(font.render("1. EL MUNDO SIGUE SIENDO 2D", True, WHITE),
                 (right_x, 74))
    explanation = (
        "El plano aparece primero. Después el jugador lanza 640 consultas, una "
        "por columna: cada impacto guarda distancia, pared y coordenadas."
    )
    text_y = 112
    for line in _fit_text(tiny_font, explanation, 680):
        surface.blit(tiny_font.render(line, True, (174, 196, 210)),
                     (right_x, text_y))
        text_y += 20
    surface.blit(tiny_font.render(
        "Cada punto marca el primer impacto: el rayo no atraviesa esa pared.",
        True, (135, 210, 220)), (right_x, text_y))
    text_y += 22

    surface.blit(tiny_font.render(
        f"RAYOS VISUALES: {visual_count:02d}/{len(visual_ray_indices):02d} · "
        f"CÁLCULO REAL: {len(rays)}", True, ORANGE),
        (right_x, text_y))
    text_y += 24
    samples = (0, NUM_RAYS // 4, NUM_RAYS // 2, NUM_RAYS * 3 // 4, NUM_RAYS - 1)
    text_y += 12
    surface.blit(tiny_font.render("MUESTRAS DE LA MATRIZ:", True, ORANGE),
                 (right_x, text_y))
    text_y += 24
    for index in samples:
        if index >= reveal_count:
            continue
        depth, wall, hit_x, hit_y = rays[index]
        line = (
            f"rays[{index:03d}] = z:{depth:5.2f}  pared:'{wall}'  "
            f"hit:({hit_x:4.1f},{hit_y:4.1f})"
        )
        surface.blit(tiny_font.render(line, True, CYAN), (right_x, text_y))
        text_y += 21

    _draw_depth_graph(
        surface, depth_buffer, pygame.Rect(520, 330, 700, 230), tiny_font,
        reveal_count=reveal_count,
    )

    # Banda de lectura inferior: convierte el espacio libre en una conclusión
    # visual de la toma sin volver a amontonar texto sobre el mapa.
    flow_rect = pygame.Rect(34, 610, 1210, 72)
    pygame.draw.rect(surface, (6, 10, 20), flow_rect, border_radius=7)
    pygame.draw.rect(surface, (44, 68, 84), flow_rect, 1, border_radius=7)
    columns = (
        ("ENTRADA", "MAP[y][x] + posición del jugador", CYAN),
        ("PROCESO", f"{visual_count:02d} rayos visuales · stride {RAY_VISUAL_STRIDE}", ORANGE),
        ("SALIDA", "distancia → altura de columna → depth_buffer", MAGENTA),
    )
    column_width = flow_rect.width // len(columns)
    for index, (heading, value, color) in enumerate(columns):
        x = flow_rect.x + index * column_width + 16
        surface.blit(tiny_font.render(heading, True, color), (x, flow_rect.y + 10))
        surface.blit(tiny_font.render(value, True, (188, 204, 216)),
                     (x, flow_rect.y + 35))
        if index < len(columns) - 1:
            pygame.draw.line(surface, (47, 67, 82),
                             (flow_rect.x + (index + 1) * column_width,
                              flow_rect.y + 12),
                             (flow_rect.x + (index + 1) * column_width,
                              flow_rect.bottom - 12), 1)


def _draw_wall_debug(surface, depth_buffer, tiny_font):
    rect = pygame.Rect(18, HEIGHT - 116, WIDTH - 36, 98)
    _draw_depth_graph(surface, depth_buffer, rect, tiny_font, title=False)
    surface.blit(tiny_font.render(
        "La curva magenta es la distancia de cada columna: cerca = pared más alta",
        True, WHITE), (rect.x + 12, rect.y + 9))


def _enemy_projection(player, enemy):
    dx, dy = enemy.x - player.x, enemy.y - player.y
    distance = math.hypot(dx, dy)
    relative = normalized_angle(math.atan2(dy, dx) - player.angle)
    corrected = distance * math.cos(relative)
    size = min(360, int(PROJECTION_DISTANCE / max(0.001, corrected) * 0.72))
    screen_x = WIDTH // 2 + int(relative / FOV * WIDTH)
    rect = pygame.Rect(0, 0, size, size)
    rect.midbottom = (screen_x, HEIGHT // 2 + size // 2)
    return corrected, rect


def _draw_occlusion_debug(surface, player, enemy, depth_buffer, tiny_font,
                          progress=1.0):
    enemy_depth, rect = _enemy_projection(player, enemy)
    pygame.draw.rect(surface, WHITE, rect, 1)
    start = max(0, rect.left)
    end = min(WIDTH, rect.right)
    column_count = int(max(0, end - start) * _smoothstep(progress))
    visible_columns = 0
    hidden_columns = 0
    for column in range(0, column_count, max(1, RAY_WIDTH)):
        screen_x = start + column
        ray_index = max(0, min(NUM_RAYS - 1, screen_x // RAY_WIDTH))
        visible = enemy_depth <= depth_buffer[ray_index] + 0.08
        color = CYAN if visible else MAGENTA
        visible_columns += int(visible)
        hidden_columns += int(not visible)
        pygame.draw.line(surface, color,
                         (screen_x, max(0, rect.top)),
                         (screen_x, min(HEIGHT - 1, rect.bottom)), 1)
    # Mini mapa de control: el demonio está detrás del pilar 2. Las franjas
    # magenta corresponden exactamente al tramo que ese pilar tapa.
    mini = pygame.Rect(18, 18, 250, 250)
    pygame.draw.rect(surface, (3, 7, 15), mini, border_radius=7)
    pygame.draw.rect(surface, CYAN, mini, 2, border_radius=7)
    scale = 11
    origin = (mini.x + 14, mini.y + 14)
    for map_y, row in enumerate(MAP):
        for map_x, tile in enumerate(row):
            tile_rect = pygame.Rect(origin[0] + map_x * scale,
                                    origin[1] + map_y * scale,
                                    scale - 1, scale - 1)
            color = (12, 19, 30) if tile == "." else WALL_COLORS.get(tile, CYAN)
            pygame.draw.rect(surface, color, tile_rect)
    player_pos = (origin[0] + int(player.x * scale),
                  origin[1] + int(player.y * scale))
    enemy_pos = (origin[0] + int(enemy.x * scale),
                 origin[1] + int(enemy.y * scale))
    pygame.draw.line(surface, ORANGE, player_pos, enemy_pos, 2)
    pygame.draw.circle(surface, WHITE, player_pos, 5)
    pygame.draw.circle(surface, MAGENTA, enemy_pos, 6)
    pygame.draw.circle(surface, ORANGE, (origin[0] + 5 * scale + 5,
                                         origin[1] + 5 * scale + 5), 15, 2)
    surface.blit(tiny_font.render("MAPA 2D · RUTA AL DEMONIO", True, WHITE),
                 (mini.x + 10, mini.bottom - 21))

    label_y = max(10, rect.top - 42)
    panel = pygame.Surface((570, 56), pygame.SRCALPHA)
    panel.fill((2, 5, 14, 220))
    surface.blit(panel, (max(8, rect.centerx - 255), label_y))
    surface.blit(tiny_font.render(
        "CIAN: franja visible · MAGENTA: descartada por depth_buffer",
        True, WHITE), (max(15, rect.centerx - 248), label_y + 7))
    surface.blit(tiny_font.render(
        "La pared se dibuja primero y corta el sprite columna a columna.",
        True, (180, 198, 210)), (max(15, rect.centerx - 248), label_y + 28))

    # Diagrama ampliado: la barra hace visible la decisión que en el sprite
    # puede perderse detrás de un único brazo o una esquina.
    diagram = pygame.Rect(300, 18, 430, 82)
    pygame.draw.rect(surface, (3, 7, 15), diagram, border_radius=7)
    pygame.draw.rect(surface, ORANGE, diagram, 1, border_radius=7)
    surface.blit(tiny_font.render("OCLUSIÓN POR COLUMNA", True, ORANGE),
                 (diagram.x + 10, diagram.y + 8))
    total_columns = max(1, (end - start) // max(1, RAY_WIDTH))
    bar = pygame.Rect(diagram.x + 10, diagram.y + 38, diagram.width - 20, 13)
    pygame.draw.rect(surface, (20, 26, 34), bar)
    for segment in range(total_columns):
        x = bar.x + int(segment / total_columns * bar.width)
        ray_index = max(0, min(NUM_RAYS - 1,
                               (start + segment * RAY_WIDTH) // RAY_WIDTH))
        color = (0, 210, 225) if enemy_depth <= depth_buffer[ray_index] + 0.08 else MAGENTA
        pygame.draw.rect(surface, color, (x, bar.y, 2, bar.height))
    surface.blit(tiny_font.render(
        f"CIAN visible: {visible_columns:02d}   MAGENTA pared: {hidden_columns:02d}",
        True, WHITE), (diagram.x + 10, diagram.y + 60))


def _fade_blit(destination, source, amount):
    """Mezcla una capa sin dejar restos entre fotogramas."""
    amount = max(0.0, min(1.0, amount))
    if amount <= 0.0:
        return
    source.set_alpha(int(255 * amount))
    destination.blit(source, (0, 0))
    source.set_alpha(None)


def _center_reveal(destination, source, amount):
    """Revela una capa desde el centro para que cada fase tenga movimiento."""
    amount = max(0.0, min(1.0, amount))
    width = int(source.get_width() * amount)
    if width <= 0:
        return
    left = (source.get_width() - width) // 2
    destination.blit(source, (left, 0), pygame.Rect(left, 0, width, source.get_height()))


def _effect_values(effect_time):
    cycle = effect_time % 2.4
    muzzle_flash = max(0.0, 0.12 - cycle)
    recoil = max(0.0, 1.0 - cycle / 0.38)
    particles = []
    if cycle < 0.58:
        for index in range(22):
            angle = index * math.tau / 22 + 0.19
            speed = 75 + (index % 5) * 21
            age = cycle
            particles.append(Particle(
                WIDTH / 2 + math.cos(angle) * speed * age,
                HEIGHT / 2 - 25 + math.sin(angle) * speed * age + age * age * 38,
                0.0, 0.0, 0.58 - age,
                ORANGE if index % 3 else MAGENTA,
                3 + index % 3,
            ))
    return muzzle_flash, recoil, particles


def _compose_scene(step, player, enemies, rays, depth_buffer, time_value,
                   effect_time, step_progress, hud_font, hud_small_font,
                   tiny_font):
    if step == 1:
        diagnostic = pygame.Surface((WIDTH, HEIGHT))
        _draw_ray_debug(
            diagnostic, player, rays, depth_buffer, hud_small_font, tiny_font,
            step_progress,
        )
        return diagnostic, (0, 0)

    world = pygame.Surface((WIDTH, HEIGHT))
    world.fill(BLACK)

    # Cada capa entra con su propio gesto visual. El orden real de composición
    # se conserva: suelo/techo → paredes → sprites → atmósfera.
    if step >= 2:
        # Hasta atmósfera sólo mostramos el color base. Los detalles se
        # construyen en una segunda capa para que se vea claramente cuándo
        # aparecen y, desde entonces, permanezcan en la composición.
        background = pygame.Surface((WIDTH, HEIGHT))
        draw_background(background, time_value)
        if step >= 5:
            detailed_background = pygame.Surface((WIDTH, HEIGHT))
            draw_background(detailed_background, time_value, player, depth_buffer)
            draw_ceiling_details(detailed_background, player, time_value, depth_buffer)
            detail_amount = (
                1.0 if step > 5
                else _smoothstep((step_progress - 0.08) / 0.52)
            )
            _fade_blit(background, detailed_background, detail_amount)
        _fade_blit(world, background,
                   1.0 if step > 2 else _smoothstep(step_progress / 0.55))
    if step >= 3:
        # La capa de paredes parte del fondo ya visible. Así, al revelarse las
        # columnas no pinta de negro el piso/techo que ya explicó el paso 2.
        walls = background.copy()
        draw_walls(walls, rays, time_value)
        _center_reveal(world, walls,
                       1.0 if step > 3 else _smoothstep((step_progress - 0.12) / 0.48))
    if step >= 4:
        enemies_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_enemies(enemies_layer, enemies, player, depth_buffer, neutral=True)
        _fade_blit(world, enemies_layer,
                   1.0 if step > 4 else _smoothstep((step_progress - 0.18) / 0.38))
    if step >= 5:
        atmosphere = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_world_atmosphere(atmosphere, player, depth_buffer, time_value)
        _fade_blit(world, atmosphere,
                   1.0 if step > 5 else _smoothstep((step_progress - 0.20) / 0.42))

    frame = pygame.Surface((WIDTH, HEIGHT))
    frame.fill(BLACK)
    camera_x = int(math.sin(time_value * 2.5) * 7) if step >= 6 else 0
    camera_y = int(abs(math.cos(time_value * 2.5)) * 5) if step >= 6 else 0
    frame.blit(world, (0, 0))
    if step >= 6:
        frame.scroll(camera_x, camera_y)

    muzzle_flash, recoil, particles = _effect_values(effect_time)
    if step >= 7:
        if muzzle_flash > 0:
            strength = min(1.0, muzzle_flash / 0.10)
            light = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            light.fill((255, 78, 12, int(42 * strength)))
            frame.blit(light, (0, 0))
        draw_particles(frame, particles)
    if step >= 8:
        weapon_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_weapon(weapon_layer, player, recoil, muzzle_flash,
                    style="doom_rifle")
        _fade_blit(frame, weapon_layer,
                   1.0 if step > 8 else _smoothstep((step_progress - 0.10) / 0.45))
    if step >= 9:
        interface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        draw_crosshair(interface, recoil)
        draw_hud(interface, player, 500, "doom_rifle", hud_font, hud_small_font, 0.0)
        draw_minimap(interface, player, enemies)
        _fade_blit(frame, interface,
                   1.0 if step > 9 else _smoothstep((step_progress - 0.12) / 0.48))
    if step >= 10:
        damage = 0.18 + (math.sin(time_value * 2.2) + 1.0) * 0.08
        final_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        final_layer.fill((255, 15, 30, int(damage * 150)))
        draw_scanlines(final_layer)
        _fade_blit(frame, final_layer, _smoothstep(step_progress / 0.48))

    if step == 3:
        _draw_wall_debug(frame, depth_buffer, tiny_font)
    elif step == 4:
        _draw_occlusion_debug(frame, player, enemies[0], depth_buffer, tiny_font,
                              step_progress)

    return frame, (camera_x, camera_y)


def _step_from_key(key):
    if pygame.K_1 <= key <= pygame.K_9:
        return key - pygame.K_0
    if key == pygame.K_0:
        return 10
    return None


def main():
    pygame.init()
    pygame.display.set_caption("Etapa 10 — Pipeline completo por capas")
    desktop_sizes = pygame.display.get_desktop_sizes()
    desktop_size = desktop_sizes[0] if desktop_sizes else (DEMO_WIDTH, DEMO_HEIGHT)
    fullscreen = any(option in sys.argv
                     for option in ("--pantalla-completa", "--fullscreen"))

    def create_display():
        flags = pygame.FULLSCREEN if fullscreen else 0
        size = desktop_size if fullscreen else (DEMO_WIDTH, DEMO_HEIGHT)
        display = pygame.display.set_mode(size, flags)
        display_width, display_height = display.get_size()
        scale = min(display_width / DEMO_WIDTH, display_height / DEMO_HEIGHT)
        present_size = (max(1, int(DEMO_WIDTH * scale)),
                        max(1, int(DEMO_HEIGHT * scale)))
        present_offset = ((display_width - present_size[0]) // 2,
                          (display_height - present_size[1]) // 2)
        return display, present_size, present_offset

    screen, present_size, present_offset = create_display()
    canvas = pygame.Surface((DEMO_WIDTH, DEMO_HEIGHT))
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont("consolas", 26, bold=True)
    panel_font = pygame.font.SysFont("consolas", 16, bold=True)
    tiny_font = pygame.font.SysFont("consolas", 13)
    hud_font = pygame.font.SysFont("consolas", 27, bold=True)
    hud_small_font = pygame.font.SysFont("consolas", 15, bold=True)

    # El primer demonio queda parcialmente detrás del pilar 2 para que la
    # oclusión sea observable tanto en el render como en el mini mapa.
    player = Player(x=3.4, y=2.7, angle=0.45, health=72)
    # Esta posición deja media silueta detrás de la esquina para que el paso 4
    # enseñe simultáneamente franjas visibles y franjas descartadas.
    primary_enemy = create_enemy(7.3, 5.1)
    primary_enemy.health = 5
    primary_enemy.variant = 2
    secondary_enemy = create_enemy(6.0, 3.5)
    secondary_enemy.health = 5
    secondary_enemy.variant = 2
    enemies = [primary_enemy, secondary_enemy]

    step = 1
    step_elapsed = 0.0
    time_value = 0.0
    effect_time = 0.0
    automatic = True
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
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    screen, present_size, present_offset = create_display()
                    continue
                selected = _step_from_key(event.key)
                if selected is not None:
                    step = selected
                    step_elapsed = 0.0
                    effect_time = 0.0
                    automatic = False
                    paused = False
                elif event.key == pygame.K_RIGHT:
                    step = min(10, step + 1)
                    step_elapsed = effect_time = 0.0
                    automatic = False
                elif event.key == pygame.K_LEFT:
                    step = max(1, step - 1)
                    step_elapsed = effect_time = 0.0
                    automatic = False
                elif event.key == pygame.K_a:
                    automatic = not automatic
                    paused = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    step = 1
                    step_elapsed = effect_time = time_value = 0.0
                    automatic = True
                    paused = False

        if not paused:
            time_value += dt
            effect_time += dt
            for enemy in enemies:
                enemy.animation += dt * 4.0
            if automatic:
                step_elapsed += dt
                if step_elapsed >= STEP_SECONDS:
                    step_elapsed = 0.0
                    effect_time = 0.0
                    step = 1 if step >= 10 else step + 1

        rays, depth_buffer = cast_all_rays(player)
        step_progress = max(0.0, min(1.0, step_elapsed / STEP_SECONDS))
        scene, camera_offset = _compose_scene(
            step, player, enemies, rays, depth_buffer, time_value,
            effect_time, step_progress, hud_font, hud_small_font, tiny_font,
        )

        canvas.fill((2, 3, 9))
        _draw_header(
            canvas, step, title_font, panel_font, automatic, paused,
            step_progress,
        )
        canvas.blit(scene, SCENE_POS)
        pygame.draw.rect(canvas, (67, 88, 104),
                         (*SCENE_POS, WIDTH, HEIGHT), 2)
        _draw_sidebar(
            canvas, step, panel_font, tiny_font, rays, depth_buffer,
            camera_offset, step_progress,
        )
        screen.fill((2, 3, 9))
        presented = pygame.transform.smoothscale(canvas, present_size)
        screen.blit(presented, present_offset)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
