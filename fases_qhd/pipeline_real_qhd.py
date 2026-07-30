"""Vista QHD del pipeline real de ``etapas/10_pipeline_completo.py``."""

import importlib.util
from pathlib import Path

import pygame


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "etapas" / "10_pipeline_completo.py"
_module = None
_state = None


def _load_module():
    global _module
    if _module is None:
        spec = importlib.util.spec_from_file_location(
            "pipeline_completo_original", SOURCE
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"No se pudo cargar {SOURCE}")
        _module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_module)
    return _module


def _initialize_state():
    global _state
    if _state is not None:
        return _state

    module = _load_module()
    player = module.Player(x=3.4, y=2.7, angle=0.45, health=72)
    primary_enemy = module.create_enemy(7.3, 5.1)
    primary_enemy.health = 5
    primary_enemy.variant = 2
    secondary_enemy = module.create_enemy(6.0, 3.5)
    secondary_enemy.health = 5
    secondary_enemy.variant = 2
    _state = {
        "player": player,
        "enemies": [primary_enemy, secondary_enemy],
        "hud_font": pygame.font.SysFont("consolas", 27, bold=True),
        "hud_small_font": pygame.font.SysFont("consolas", 15, bold=True),
        "tiny_font": pygame.font.SysFont("consolas", 13),
    }
    return _state


def draw_pipeline_real(canvas, time_value):
    """Compone el mismo fotograma del original y lo presenta a 2× exacto."""
    module = _load_module()
    state = _initialize_state()
    total_steps = len(module.STEPS)
    step_index = min(
        total_steps - 1, int(time_value / module.STEP_SECONDS)
    )
    step = step_index + 1
    step_elapsed = time_value - step_index * module.STEP_SECONDS
    step_progress = max(
        0.0, min(1.0, step_elapsed / module.STEP_SECONDS)
    )

    for enemy in state["enemies"]:
        enemy.animation = time_value * 4.0

    rays, depth_buffer = module.cast_all_rays(state["player"])
    scene, _camera_offset = module._compose_scene(
        step,
        state["player"],
        state["enemies"],
        rays,
        depth_buffer,
        time_value,
        step_elapsed,
        step_progress,
        state["hud_font"],
        state["hud_small_font"],
        state["tiny_font"],
    )

    # El original genera 1280×720. Un escalado entero 2× conserva los píxeles
    # nítidos y llena el lienzo QHD sin interpolación ni estiramiento borroso.
    canvas.surface.blit(
        pygame.transform.scale(scene, canvas.surface.get_size()), (0, 0)
    )
