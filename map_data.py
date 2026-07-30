"""Arena industrial abierta: grandes líneas de visión y pilares aislados."""

import math

# Cada cadena representa una fila; los caracteres son las casillas del mapa.
# 1 = pared exterior, . = suelo libre, 2-6 = pilares numerados.
MAP = (
    "11111111111111111111",
    "1..................1",
    "1..................1",
    "1..................1",
    "1..................1",
    "1....22......33....1",
    "1....22......33....1",
    "1..................1",
    "1..................1",
    "1........44........1",
    "1........44........1",
    "1..................1",
    "1..................1",
    "1....55......66....1",
    "1....55......66....1",
    "1..................1",
    "1..................1",
    "1..................1",
    "1..................1",
    "11111111111111111111",
)

MAP_WIDTH = len(MAP[0])
MAP_HEIGHT = len(MAP)

PLAYER_START = (2.5, 2.5)


def _build_enemy_spawns(amount=24):
    """Selecciona celdas libres alejadas del inicio y repartidas por el mapa."""
    candidates = []
    for grid_y, row in enumerate(MAP):
        for grid_x, tile in enumerate(row):
            if tile != ".":
                continue
            position = (grid_x + 0.5, grid_y + 0.5)
            distance = math.hypot(position[0] - PLAYER_START[0],
                                  position[1] - PLAYER_START[1])
            if distance >= 4.0:
                candidates.append((distance, grid_x, grid_y, position))

    # Muestreo de máxima distancia: cada nuevo punto busca el sector menos
    # representado, evitando concentrar toda la oleada en un mismo borde.
    candidates.sort(key=lambda item: (-item[0], item[2], item[1]))
    selected = [candidates[0][3]]
    remaining = candidates[1:]
    while remaining and len(selected) < amount:
        best_index = max(
            range(len(remaining)),
            key=lambda index: (
                min(math.hypot(remaining[index][3][0] - other[0],
                                remaining[index][3][1] - other[1])
                    for other in selected),
                remaining[index][0],
                -remaining[index][2],
                -remaining[index][1],
            ),
        )
        candidate = remaining.pop(best_index)
        if min(math.hypot(candidate[3][0] - other[0], candidate[3][1] - other[1])
               for other in selected) >= 2.0:
            selected.append(candidate[3])

    if len(selected) < amount:
        raise ValueError("No hay suficientes celdas libres para los spawns")
    return tuple(selected)


# Nunca se crean enemigos dentro de una pared; la lista se adapta al sector actual.
ENEMY_SPAWNS = _build_enemy_spawns()


def tile_at(x, y):
    """Devuelve el carácter de la casilla (x, y); fuera del mapa es pared."""
    grid_x, grid_y = int(x), int(y)
    if 0 <= grid_x < MAP_WIDTH and 0 <= grid_y < MAP_HEIGHT:
        return MAP[grid_y][grid_x]
    return "1"


def is_wall(x, y):
    """True cuando la posición está ocupada por una pared."""
    return tile_at(x, y) != "."
