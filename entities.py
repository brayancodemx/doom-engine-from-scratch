"""Jugador y enemigos. Solo contienen datos y reglas de movimiento."""

from collections import deque
from dataclasses import dataclass, field
import math
import random
from typing import ClassVar

import pygame

from map_data import PLAYER_START, is_wall
from settings import (
    ENEMY_BASE_SPEED, ENEMY_MAX_HEALTH, ENEMY_MIN_HEALTH, ENEMY_RADIUS,
    ENEMY_VARIANT_SPEED_STEP, PLAYER_RADIUS, PLAYER_ROTATION_SPEED,
    PLAYER_SPEED,
)


def normalized_angle(angle):
    """Convierte cualquier ángulo al intervalo -pi ... +pi."""
    return math.atan2(math.sin(angle), math.cos(angle))


def normalized_move_axes(forward, strafe):
    """Limita la entrada diagonal a la misma magnitud que un eje individual."""
    magnitude = math.hypot(forward, strafe)
    if magnitude > 1.0:
        return forward / magnitude, strafe / magnitude
    return forward, strafe


@dataclass
class Player:
    x: float = PLAYER_START[0]
    y: float = PLAYER_START[1]
    angle: float = 0.10
    health: int = 100
    walk_time: float = 0.0
    moving: bool = False

    def update(self, dt):
        keys = pygame.key.get_pressed()
        forward = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(
            keys[pygame.K_s] or keys[pygame.K_DOWN]
        )
        strafe = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        turn = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        forward, strafe = normalized_move_axes(forward, strafe)

        self.angle += turn * PLAYER_ROTATION_SPEED * dt
        speed = PLAYER_SPEED * dt
        dx = math.cos(self.angle) * forward * speed
        dy = math.sin(self.angle) * forward * speed
        dx += math.cos(self.angle + math.pi / 2) * strafe * speed
        dy += math.sin(self.angle + math.pi / 2) * strafe * speed

        self.moving = bool(forward or strafe)
        if self.moving:
            self.walk_time += dt * 9

        self._move_with_collision(dx, dy)

    def _move_with_collision(self, dx, dy):
        """Prueba X e Y por separado para que el jugador se deslice por paredes."""
        next_x = self.x + dx
        if not self._touches_wall(next_x, self.y):
            self.x = next_x

        next_y = self.y + dy
        if not self._touches_wall(self.x, next_y):
            self.y = next_y

    @staticmethod
    def _touches_wall(x, y):
        r = PLAYER_RADIUS
        return any(
            is_wall(test_x, test_y)
            for test_x, test_y in (
                (x - r, y - r), (x + r, y - r),
                (x - r, y + r), (x + r, y + r),
            )
        )


@dataclass
class Enemy:
    DEATH_ANIMATION_TIME: ClassVar[float] = 1.15
    CORPSE_LINGER_TIME: ClassVar[float] = 1.25
    BASE_SPEED: ClassVar[float] = ENEMY_BASE_SPEED
    VARIANT_SPEED_STEP: ClassVar[float] = ENEMY_VARIANT_SPEED_STEP
    RADIUS: ClassVar[float] = ENEMY_RADIUS

    x: float
    y: float
    health: int = 1
    attack_timer: float = 0.0
    animation: float = 0.0
    hurt_timer: float = 0.0
    hurt_pose_timer: float = 0.0
    variant: int = 0
    death_timer: float = 0.0
    moving: bool = False
    path: deque = field(default_factory=deque, repr=False)
    path_goal: tuple | None = field(default=None, repr=False)
    path_timer: float = field(default=0.0, repr=False)

    @property
    def alive(self):
        return self.health > 0

    @property
    def tier(self):
        """Agrupa la resistencia restante en tres estados visuales."""
        return max(0, min(3, self.health))

    @property
    def death_visible(self):
        """Mantiene la caída y los restos el tiempo suficiente para poder leerlos."""
        return not self.alive and self.death_timer < (
            self.DEATH_ANIMATION_TIME + self.CORPSE_LINGER_TIME
        )

    @property
    def death_finished(self):
        return not self.alive and not self.death_visible

    def distance_to(self, player):
        return math.hypot(self.x - player.x, self.y - player.y)

    def take_damage(self, amount=1, play_hurt_pose=True):
        """Aplica daño; el destello y la pose corporal son independientes."""
        if not self.alive:
            return False
        self.health = max(0, self.health - amount)
        self.hurt_timer = 0.24
        self.hurt_pose_timer = 0.24 if play_hurt_pose else 0.0
        return not self.alive

    def trigger_death(self, delay=0.0):
        """Fuerza una muerte con retraso para secuencias colectivas."""
        if not self.alive:
            return False
        self.health = 0
        self.hurt_timer = 0.24
        self.hurt_pose_timer = 0.24
        self.death_timer = -max(0.0, delay)
        self.moving = False
        self.path.clear()
        return True

    def update(self, player, dt):
        """Persigue al jugador; devuelve True cuando consigue atacarlo."""
        if not self.alive:
            self.moving = False
            self.death_timer += dt
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
            self.hurt_pose_timer = max(0.0, self.hurt_pose_timer - dt)
            return False

        self.animation += dt * 5
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.hurt_pose_timer = max(0.0, self.hurt_pose_timer - dt)
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.path_timer = max(0.0, self.path_timer - dt)
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.hypot(dx, dy)
        self.moving = distance > 1.15

        if self.moving:
            speed = (
                self.BASE_SPEED + self.variant * self.VARIANT_SPEED_STEP
            ) * dt
            move_x = dx / distance * speed
            move_y = dy / distance * speed
            if not self._touches_wall(self.x + move_x, self.y + move_y):
                self.path.clear()
                self._try_displacement(move_x, move_y)
            else:
                self._follow_grid_path(player, speed)
        elif self.attack_timer <= 0:
            self.attack_timer = 0.85
            return True
        return False

    def _try_displacement(self, dx, dy):
        """Desliza por paredes respetando el volumen físico del demonio."""
        moved = False
        if abs(dx) > 1e-9 and not self._touches_wall(self.x + dx, self.y):
            self.x += dx
            moved = True
        if abs(dy) > 1e-9 and not self._touches_wall(self.x, self.y + dy):
            self.y += dy
            moved = True
        return moved

    def _follow_grid_path(self, player, step):
        """Rodea paredes usando centros de celda sólo cuando se bloquea."""
        goal = (int(player.x), int(player.y))
        if goal != self.path_goal or self.path_timer <= 0.0 or not self.path:
            self.path = self._build_grid_path(goal)
            self.path_goal = goal
            self.path_timer = 0.55

        while self.path:
            waypoint_x, waypoint_y = self.path[0]
            dx, dy = waypoint_x - self.x, waypoint_y - self.y
            distance = math.hypot(dx, dy)
            if distance > max(0.08, step * 1.5):
                self._try_displacement(dx / distance * step, dy / distance * step)
                return
            self.path.popleft()

    def _build_grid_path(self, goal):
        """Devuelve centros transitables desde la celda actual hasta la meta."""
        start = (int(self.x), int(self.y))
        if start == goal:
            return []
        pending = deque([start])
        previous = {start: None}
        while pending:
            cell_x, cell_y = pending.popleft()
            for next_cell in (
                (cell_x + 1, cell_y), (cell_x - 1, cell_y),
                (cell_x, cell_y + 1), (cell_x, cell_y - 1),
            ):
                if next_cell in previous:
                    continue
                center = (next_cell[0] + 0.5, next_cell[1] + 0.5)
                if self._touches_wall(*center):
                    continue
                previous[next_cell] = (cell_x, cell_y)
                if next_cell == goal:
                    pending.clear()
                    break
                pending.append(next_cell)

        if goal not in previous:
            return []
        cells = []
        current = goal
        while current != start:
            cells.append((current[0] + 0.5, current[1] + 0.5))
            current = previous[current]
        cells.reverse()
        return deque(cells)

    @classmethod
    def _touches_wall(cls, x, y):
        radius = cls.RADIUS
        return any(
            is_wall(x + offset_x, y + offset_y)
            for offset_x, offset_y in (
                (-radius, -radius), (radius, -radius),
                (-radius, radius), (radius, radius),
                (-radius, 0.0), (radius, 0.0),
                (0.0, -radius), (0.0, radius),
            )
        )


def create_enemy(x, y):
    health = random.randint(ENEMY_MIN_HEALTH, ENEMY_MAX_HEALTH)
    return Enemy(x, y, health=health, variant=health - ENEMY_MIN_HEALTH)
