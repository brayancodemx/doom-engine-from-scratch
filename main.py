"""NEON BREACH: mini shooter raycaster didáctico hecho con Python + Pygame."""

import math
from pathlib import Path
import random
import sys
import traceback

import pygame

from audio import Sounds
from entities import Player, create_enemy, normalized_angle
from map_data import ENEMY_SPAWNS
from raycasting import cast_all_rays, cast_one_ray
from renderer import (
    ACTIVE_WEAPON_STYLES, draw_background, draw_crosshair,
    draw_damage_vignette, draw_enemies, draw_hud, draw_minimap,
    draw_particles, draw_walls, draw_weapon,
    draw_ceiling_details, draw_world_atmosphere, make_particles,
)
from settings import (
    BLACK, DOOM_AMBER, DOOM_BLACK, DOOM_BLOOD, DOOM_BONE, DOOM_RED,
    DOOM_RUST, DOOM_STEEL, END_SCREEN_REVEAL, ENEMY_SPAWN_DELAY, FPS, HEIGHT,
    INITIAL_ENEMY_COUNT, MIN_ACTIVE_ENEMIES, MOUSE_SENSITIVITY,
    POINTS_PER_ENEMY, RIFLE_HURT_REACTION_CHANCE, SHOTGUN_BREAK_START,
    SHOTGUN_CYCLE, TARGET_SCORE, VICTORY_AFTERMATH, WEAPON_SWITCH_TIME, WIDTH,
)

ROOT = Path(__file__).resolve().parent


class Game:
    """Coordina entradas, actualización y dibujo. Es el director del juego."""

    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("DOOM... digo DUCK")
        self.fullscreen = any(
            option in sys.argv for option in ("--pantalla-completa", "--fullscreen")
        )
        desktops = pygame.display.get_desktop_sizes()
        self.desktop_size = desktops[0] if desktops else (WIDTH, HEIGHT)
        self.game_window = None
        self.screen = self._create_display()
        self.frame = pygame.Surface((WIDTH, HEIGHT))
        self.world_frame = pygame.Surface((WIDTH, HEIGHT))
        # Superficie intermedia para el balanceo de cámara. Evita desplazar el
        # mismo frame con Surface.scroll(), que deja bordes stale y mezcla el
        # mundo con overlays cuando se dispara mientras se camina.
        self.camera_frame = pygame.Surface((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 23, bold=True)
        self.big_font = pygame.font.SysFont("impact", 84)
        self.medium_font = pygame.font.SysFont("consolas", 32, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 14, bold=True)
        self.sounds = Sounds()
        self.menu_background = self._load_menu_background()
        self.weapon_style = ACTIVE_WEAPON_STYLES[0]
        self.show_hud = "--sin-hud" not in sys.argv
        self.running = True
        self.state = "menu"
        self.time = 0.0
        self.reset_game()

    def _create_display(self):
        """Crea borde cero y calcula un ajuste completo sin recortar el juego."""
        size = self.desktop_size if self.fullscreen else (WIDTH, HEIGHT)
        flags = pygame.NOFRAME if self.fullscreen else 0
        screen = pygame.display.set_mode(size, flags)
        try:
            from pygame._sdl2 import Window
            window = Window.from_display_module()
            self.game_window = window
            window.position = (
                (0, 0) if self.fullscreen else
                ((self.desktop_size[0] - WIDTH) // 2,
                 (self.desktop_size[1] - HEIGHT) // 2)
            )
            # Al lanzarse desde una terminal integrada, Windows puede dejar el
            # foco en la consola y enviar allí R/Enter. Elevamos explícitamente
            # la ventana de Pygame para que reciba la entrada desde el inicio.
            window.focus()
        except (ImportError, pygame.error, TypeError):
            self.game_window = None
            pass

        display_width, display_height = screen.get_size()
        scale = min(display_width / WIDTH, display_height / HEIGHT)
        present_width = max(1, int(WIDTH * scale))
        present_height = max(1, int(HEIGHT * scale))
        self.presentation_size = (present_width, present_height)
        self.presentation_offset = (
            (display_width - present_width) // 2,
            (display_height - present_height) // 2,
        )
        self.presentation_surface = pygame.Surface(self.presentation_size)
        return screen

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.screen = self._create_display()
        gameplay_visible = self.state in ("playing", "victory_pending")
        pygame.event.set_grab(gameplay_visible)
        pygame.mouse.set_visible(not gameplay_visible)
        pygame.mouse.get_rel()

    def _load_menu_background(self):
        image_path = ROOT / "assets" / "menu_background_doom.png"
        if not image_path.exists():
            return None
        image = pygame.image.load(str(image_path)).convert()
        return pygame.transform.smoothscale(image, (WIDTH, HEIGHT))

    def reset_game(self):
        self.player = Player()
        self.enemies = []
        self.score = 0
        self.shot_cooldown = 0.0
        self.muzzle_flash = 0.0
        self.recoil = 0.0
        self.weapon_action_timer = 0.0
        self.weapon_switch_timer = 0.0
        self.weapon_switch_to = self.weapon_style
        self.screen_shake = 0.0
        self.damage_flash = 0.0
        self.hit_confirm_timer = 0.0
        self.camera_bob_x = 0.0
        self.camera_bob_y = 0.0
        self.particles = []
        self.spawn_delay = 0.0
        self.victory_timer = 0.0
        self.victory_delay = 0.0
        self.end_screen_timer = 0.0
        self._fill_enemy_wave(INITIAL_ENEMY_COUNT)

    def _fill_enemy_wave(self, amount):
        available = list(ENEMY_SPAWNS)
        random.shuffle(available)
        for x, y in available:
            if len(self.enemies_alive()) >= amount:
                break
            if math.hypot(x - self.player.x, y - self.player.y) > 4:
                self.enemies.append(create_enemy(x, y))

    def enemies_alive(self):
        return [enemy for enemy in self.enemies if enemy.alive]

    def run(self):
        try:
            while self.running:
                dt = min(self.clock.tick(FPS) / 1000.0, 0.04)
                self.time += dt
                self.handle_events()
                self.update(dt)
                self.draw()
        except Exception:
            # Si el juego se abre con doble clic, el traceback de Python
            # desaparece junto con la consola. Conservamos el diagnóstico.
            error_path = ROOT / "neon_breach_error.log"
            error_path.write_text(traceback.format_exc(), encoding="utf-8")
            raise
        finally:
            pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_ESCAPE:
                    if self.state == "menu":
                        self.running = False
                    else:
                        self.state = "menu"
                        pygame.event.set_grab(False)
                        pygame.mouse.set_visible(True)
                elif event.key in (pygame.K_RETURN, pygame.K_r):
                    if self.state not in ("playing", "victory_pending"):
                        self.start_game()
                elif event.key == pygame.K_SPACE and self.state == "playing":
                    self.shoot()
                elif event.key == pygame.K_1 and self.state == "playing":
                    self._request_weapon_switch(ACTIVE_WEAPON_STYLES[0])
                elif event.key == pygame.K_2 and self.state == "playing":
                    self._request_weapon_switch(ACTIVE_WEAPON_STYLES[1])

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "menu":
                    self.start_game()
                elif self.state == "playing" and event.button == 1:
                    self.shoot()

            if event.type == pygame.MOUSEMOTION and self.state == "playing":
                self.player.angle += event.rel[0] * MOUSE_SENSITIVITY

    def start_game(self):
        self.reset_game()
        self.state = "playing"
        if self.game_window is not None:
            try:
                self.game_window.focus()
            except pygame.error:
                pass
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        pygame.mouse.get_rel()

    def _request_weapon_switch(self, weapon_style):
        """Baja el arma actual y levanta la nueva antes de permitir disparar."""
        if (weapon_style == self.weapon_style or
                self.weapon_switch_timer > 0 or
                self.weapon_action_timer > 0):
            return
        self.weapon_switch_to = weapon_style
        self.weapon_switch_timer = WEAPON_SWITCH_TIME

    def _weapon_switch_progress(self):
        if self.weapon_switch_timer <= 0:
            return 0.0
        return 1.0 - self.weapon_switch_timer / WEAPON_SWITCH_TIME

    def update(self, dt):
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        self.muzzle_flash = max(0.0, self.muzzle_flash - dt)
        self.recoil = max(0.0, self.recoil - dt * 6)
        previous_weapon_action = self.weapon_action_timer
        self.weapon_action_timer = max(0.0, self.weapon_action_timer - dt)
        if self.weapon_switch_timer > 0:
            self.weapon_switch_timer = max(0.0, self.weapon_switch_timer - dt)
            if self._weapon_switch_progress() >= 0.5:
                self.weapon_style = self.weapon_switch_to
            if self.weapon_switch_timer <= 0:
                self.weapon_style = self.weapon_switch_to
        break_trigger_timer = SHOTGUN_CYCLE - SHOTGUN_BREAK_START
        if (previous_weapon_action > break_trigger_timer >=
                self.weapon_action_timer and
                self.weapon_style == "doom_shotgun" and
                self.state in ("playing", "victory_pending", "won")):
            self.sounds.play(self.sounds.shotgun_followup)
        self.screen_shake = max(0.0, self.screen_shake - dt * 30)
        self.damage_flash = max(0.0, self.damage_flash - dt * 1.45)
        self.hit_confirm_timer = max(0.0, self.hit_confirm_timer - dt)

        for particle in self.particles:
            particle.update(dt)
        self.particles = [particle for particle in self.particles if particle.life > 0]

        # Las muertes siguen animándose durante la secuencia previa a la victoria.
        for enemy in self.enemies:
            if not enemy.alive and self.state != "won":
                enemy.update(self.player, dt)
        if self.state != "won":
            self.enemies = [
                enemy for enemy in self.enemies if not enemy.death_finished
            ]

        if self.state in ("won", "lost"):
            self.end_screen_timer += dt

        # Si R se pulsa justo al abrir la ventana, el KEYDOWN puede ocurrir
        # antes de que Pygame tome el foco. El sondeo evita dejar el menú
        # aparentemente congelado en ese caso.
        if self.state == "menu":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r] or keys[pygame.K_RETURN] or keys[pygame.K_SPACE]:
                self.start_game()
            return

        if self.state == "victory_pending":
            self.victory_timer += dt
            if (self.victory_timer >= self.victory_delay and
                    self.weapon_action_timer <= 0):
                self._finish_victory()
            return

        if self.state != "playing":
            return

        self.player.update(dt)
        # La cámara acompaña los pasos y vuelve suavemente al centro al detenerse.
        if self.player.moving:
            target_bob_x = math.sin(self.player.walk_time) * 4.2
            target_bob_y = math.sin(self.player.walk_time * 2) * 6.2
        else:
            target_bob_x = 0.0
            target_bob_y = 0.0
        smoothing = min(1.0, dt * 13)
        self.camera_bob_x += (target_bob_x - self.camera_bob_x) * smoothing
        self.camera_bob_y += (target_bob_y - self.camera_bob_y) * smoothing

        for enemy in self.enemies_alive():
            if enemy.update(self.player, dt):
                self.player.health -= 8
                self.damage_flash = min(1.0, self.damage_flash + 0.92)
                self.screen_shake = max(self.screen_shake, 15)

        if self.player.health <= 0:
            self.state = "lost"
            self.end_screen_timer = 0.0
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
            return

        self.spawn_delay -= dt
        if len(self.enemies_alive()) < MIN_ACTIVE_ENEMIES and self.spawn_delay <= 0:
            self._spawn_one_enemy()
            self.spawn_delay = ENEMY_SPAWN_DELAY

    def _spawn_one_enemy(self):
        occupied = {
            (int(enemy.x), int(enemy.y)) for enemy in self.enemies_alive()
        }
        choices = [
            spot for spot in ENEMY_SPAWNS
            if (int(spot[0]), int(spot[1])) not in occupied
            and math.hypot(spot[0] - self.player.x, spot[1] - self.player.y) > 5
        ]
        if choices:
            self.enemies.append(create_enemy(*random.choice(choices)))

    def shoot(self):
        if self.shot_cooldown > 0 or self.weapon_switch_timer > 0:
            return
        shotgun_fired = self.weapon_style == "doom_shotgun"
        self.shot_cooldown = SHOTGUN_CYCLE if shotgun_fired else 0.24
        self.weapon_action_timer = SHOTGUN_CYCLE if shotgun_fired else 0.0
        self.muzzle_flash = 0.18 if shotgun_fired else 0.10
        self.recoil = 1.0
        self.screen_shake = 18 if shotgun_fired else 4
        self.sounds.play(
            self.sounds.shotgun if shotgun_fired else self.sounds.shot,
            maxtime=int(SHOTGUN_CYCLE * 1000) if shotgun_fired else 0,
        )
        self.particles += make_particles(
            WIDTH // 2, HEIGHT // 2 + 80, DOOM_AMBER,
            28 if shotgun_fired else 9, 440 if shotgun_fired else 170,
        )
        if shotgun_fired:
            self.particles += make_particles(
                WIDTH // 2, HEIGHT // 2 + 65, DOOM_STEEL, 18, 330
            )

        # La pared central limita el alcance: no se dispara a través de ella.
        wall_distance = cast_one_ray(
            self.player.x, self.player.y, self.player.angle
        )[0]
        target = None
        best_aim = 999.0

        for enemy in self.enemies_alive():
            dx, dy = enemy.x - self.player.x, enemy.y - self.player.y
            distance = math.hypot(dx, dy)
            angle_to_enemy = math.atan2(dy, dx)
            aim_error = abs(normalized_angle(angle_to_enemy - self.player.angle))
            visible_width = math.atan2(0.58 if shotgun_fired else 0.42, distance)
            if distance < wall_distance + 0.25 and aim_error < visible_width:
                if aim_error < best_aim:
                    target, best_aim = enemy, aim_error

        if target:
            play_hurt_pose = (
                shotgun_fired
                or random.random() < RIFLE_HURT_REACTION_CHANCE
            )
            killed = target.take_damage(
                target.health if shotgun_fired else 1,
                play_hurt_pose=play_hurt_pose,
            )
            self.particles += make_particles(
                WIDTH // 2, HEIGHT // 2,
                DOOM_RUST if shotgun_fired else DOOM_BLOOD,
                52 if shotgun_fired else 10,
                520 if shotgun_fired else 190,
            )
            self.screen_shake = max(
                self.screen_shake, 22 if shotgun_fired else 5
            )
            self.hit_confirm_timer = 0.22 if killed else 0.14
            if killed:
                self.sounds.play(self.sounds.enemy_death)
                self.screen_shake = max(
                    self.screen_shake, 16 if shotgun_fired else 8
                )
                self.particles += make_particles(
                    WIDTH // 2, HEIGHT // 2, DOOM_BLOOD, 20, 410
                )
                self.particles += make_particles(
                    WIDTH // 2, HEIGHT // 2, DOOM_BONE, 9, 260
                )
                self.score += POINTS_PER_ENEMY
                if self.score >= TARGET_SCORE:
                    self._begin_victory_sequence(target)
            else:
                self.sounds.play(self.sounds.hit)

    def _begin_victory_sequence(self, final_enemy):
        """Derriba a toda la horda y deja leer la caída antes del triunfo."""
        death_sound_time = (
            self.sounds.enemy_death.get_length()
            if self.sounds.enemy_death is not None else 0.0
        )
        remaining = sorted(
            self.enemies_alive(),
            key=lambda enemy: enemy.distance_to(self.player),
        )
        last_death_delay = 0.0
        for index, enemy in enumerate(remaining):
            death_delay = 0.08 + index * 0.07
            enemy.trigger_death(death_delay)
            last_death_delay = death_delay
        self.victory_timer = 0.0
        self.victory_delay = max(
            final_enemy.DEATH_ANIMATION_TIME + 0.34,
            last_death_delay + final_enemy.DEATH_ANIMATION_TIME + 0.34,
            death_sound_time,
            self.weapon_action_timer,
        ) + VICTORY_AFTERMATH
        self.state = "victory_pending"
        self.screen_shake = max(self.screen_shake, 18)

    def _finish_victory(self):
        self.state = "won"
        self.end_screen_timer = 0.0
        for enemy in self.enemies:
            if not enemy.alive:
                # Todos llegan al fotograma final y quedan como montones
                # visibles bajo el mensaje de victoria.
                enemy.death_timer = enemy.DEATH_ANIMATION_TIME + 0.02
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        self.screen_shake = max(self.screen_shake, 12)
        self.particles += make_particles(
            WIDTH // 2, HEIGHT // 2, DOOM_AMBER, 72, 520
        )
        self.particles += make_particles(
            WIDTH // 2, HEIGHT // 2, DOOM_BONE, 34, 360
        )
        self.sounds.play(self.sounds.win)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state in ("playing", "victory_pending"):
            self.draw_playing()
        elif self.state in ("won", "lost"):
            self.draw_playing()
            self.draw_end_screen()
        shake_x = 0
        shake_y = 0
        if self.state != "menu":
            shake_x = random.randint(-int(self.screen_shake),
                                     int(self.screen_shake))
            shake_y = random.randint(-int(self.screen_shake),
                                     int(self.screen_shake))
        self._present_frame(shake_x, shake_y)
        pygame.display.flip()

    def _present_frame(self, shake_x=0, shake_y=0):
        """Escala el fotograma completo; HUD, arma y radar nunca se separan."""
        self.screen.fill(BLACK)
        if self.presentation_size == (WIDTH, HEIGHT):
            presented = self.frame
        else:
            pygame.transform.smoothscale(
                self.frame, self.presentation_size, self.presentation_surface
            )
            presented = self.presentation_surface
        scale = self.presentation_size[0] / WIDTH
        self.screen.blit(
            presented,
            (self.presentation_offset[0] + int(shake_x * scale),
             self.presentation_offset[1] + int(shake_y * scale)),
        )

    def draw_playing(self):
        # Mundo y HUD se componen por separado: la cámara se mueve, la interfaz no.
        rays, depth_buffer = cast_all_rays(self.player)
        draw_background(
            self.world_frame, self.time, self.player, depth_buffer
        )
        # Los elementos del techo existen detrás de los muros; el orden evita
        # que una lámpara o panel atraviese visualmente una pared cercana.
        draw_ceiling_details(
            self.world_frame, self.player, self.time, depth_buffer
        )
        draw_walls(self.world_frame, rays, self.time)
        draw_enemies(self.world_frame, self.enemies, self.player, depth_buffer)
        draw_world_atmosphere(
            self.world_frame, self.player, depth_buffer, self.time
        )

        self.frame.blit(self.world_frame, (0, 0))
        camera_x = int(self.camera_bob_x)
        camera_y = int(self.camera_bob_y)
        if camera_x or camera_y:
            # Se copia desde una superficie distinta para que los píxeles
            # expuestos en los bordes queden siempre definidos.
            self.camera_frame.fill(BLACK)
            self.camera_frame.blit(self.frame, (camera_x, camera_y))
            self.frame.blit(self.camera_frame, (0, 0))

        # El fogonazo ilumina brevemente todo el mundo, no solamente el cañón.
        if self.muzzle_flash > 0:
            strength = min(1.0, self.muzzle_flash / 0.10)
            flash_light = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_light.fill((*DOOM_AMBER, int(36 * strength)))
            self.frame.blit(flash_light, (0, 0))

        draw_particles(self.frame, self.particles)
        draw_weapon(
            self.frame, self.player, self.recoil, self.muzzle_flash,
            self.weapon_style, full_view=not self.show_hud,
            action_timer=self.weapon_action_timer,
            switch_progress=self._weapon_switch_progress(),
        )
        draw_crosshair(self.frame, self.recoil, self.hit_confirm_timer)
        if self.show_hud:
            draw_hud(
                self.frame, self.player, self.score, self.weapon_style,
                self.font, self.small_font, self.damage_flash,
            )
        draw_minimap(self.frame, self.player, self.enemies)

        draw_damage_vignette(self.frame, self.damage_flash)
        # Sin rejilla CRT sobre el mundo: YouTube conserva mejor el detalle fino.

    def draw_menu(self):
        if self.menu_background:
            self.frame.blit(self.menu_background, (0, 0))
        else:
            self.frame.fill(DOOM_BLACK)

        title = self.big_font.render("DOOM... digo DUCK", False, DOOM_BONE)
        shadow = self.big_font.render("DOOM... digo DUCK", False, DOOM_BLOOD)
        title_rect = title.get_rect(center=(WIDTH // 2, 105))
        self.frame.blit(shadow, title_rect.move(6, 7))
        self.frame.blit(title, title_rect)
        pygame.draw.line(
            self.frame, DOOM_RUST,
            (title_rect.left + 18, title_rect.bottom + 4),
            (title_rect.right - 18, title_rect.bottom + 4), 4,
        )
        subtitle = self.font.render(
            "BY BrayanCode", False, DOOM_AMBER
        )
        self.frame.blit(
            subtitle, subtitle.get_rect(center=(WIDTH // 2, 190))
        )

        prompt = self.medium_font.render(
            "PRESIONE ENTER PARA JUGAR", False, DOOM_BONE
        )
        if int(self.time * 2) % 2 == 0:
            self.frame.blit(
                prompt, prompt.get_rect(center=(WIDTH // 2, 630))
            )

    def draw_end_screen(self):
        reveal = min(1.0, self.end_screen_timer / END_SCREEN_REVEAL)
        reveal = reveal * reveal * (3.0 - 2.0 * reveal)
        alpha = max(1, int(255 * reveal))
        won = self.state == "won"

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((8, 4, 3, int((165 if won else 215) * reveal)))
        self.frame.blit(veil, (0, 0))

        if won:
            flash = max(0.0, 1.0 - self.end_screen_timer / 0.55)
            victory_light = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            victory_light.fill((*DOOM_AMBER, int(72 * flash)))
            self.frame.blit(victory_light, (0, 0))

        heading = "BRECHA SELLADA" if won else "SISTEMA CAÍDO"
        color = DOOM_AMBER if won else DOOM_RED
        text = self.big_font.render(heading, False, color)
        title_scale = 1.0 + (1.0 - reveal) * 0.16
        text = pygame.transform.scale(
            text,
            (max(1, int(text.get_width() * title_scale)),
             max(1, int(text.get_height() * title_scale))),
        )
        text.set_alpha(alpha)
        title_y = int(220 - 34 * (1.0 - reveal))
        shadow = text.copy()
        shadow.fill((20, 0, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        self.frame.blit(
            shadow, shadow.get_rect(center=(WIDTH // 2 + 6, title_y + 7))
        )
        self.frame.blit(
            text, text.get_rect(center=(WIDTH // 2, title_y))
        )

        line_half_width = int(390 * reveal)
        pygame.draw.line(
            self.frame, DOOM_RUST,
            (WIDTH // 2 - line_half_width, 268),
            (WIDTH // 2 + line_half_width, 268), 4,
        )
        outcome = self.font.render(
            "TODOS LOS DEMONIOS HAN CAÍDO"
            if won else "LA BRECHA SIGUE ABIERTA",
            False, DOOM_BONE,
        )
        outcome.set_alpha(alpha)
        self.frame.blit(
            outcome, outcome.get_rect(center=(WIDTH // 2, 300))
        )

        detail = self.font.render(
            f"PUNTUACIÓN FINAL: {self.score}", False, DOOM_BONE
        )
        detail.set_alpha(alpha)
        self.frame.blit(
            detail, detail.get_rect(center=(WIDTH // 2, 334))
        )
        prompt = self.font.render(
            "PULSA R O ENTER PARA REINICIAR · ESC PARA EL MENÚ",
            False, DOOM_STEEL,
        )
        prompt_reveal = max(
            0.0, min(1.0, (self.end_screen_timer - 0.38) / 0.42)
        )
        prompt.set_alpha(int(255 * prompt_reveal))
        self.frame.blit(
            prompt, prompt.get_rect(center=(WIDTH // 2, 390))
        )


if __name__ == "__main__":
    Game().run()
