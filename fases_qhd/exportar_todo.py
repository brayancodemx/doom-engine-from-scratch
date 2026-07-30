"""Exporta las animaciones QHD a videos MP4 de 30 FPS mediante FFmpeg."""

import argparse
import math
from pathlib import Path
import shutil
import subprocess
import sys

import pygame

from escenas_qhd import SCENES
from motor_qhd import EXPORT_FPS, HEIGHT, WIDTH, draw_frame, initialize_hidden


def export_scene(
    scene, output_dir, ffmpeg_path, crf, preset, suffix="",
    max_seconds=None,
):
    duration = (
        min(scene.duration, max_seconds)
        if max_seconds is not None else scene.duration
    )
    frame_count = int(math.ceil(duration * EXPORT_FPS))
    output_path = output_dir / f"{scene.filename}{suffix}.mp4"
    if output_path.exists():
        print(f"{scene.key}/{len(SCENES):02d}  Omitido: {output_path.name}")
        return None
    command = [
        ffmpeg_path,
        "-n",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pixel_format", "rgb24",
        "-video_size", f"{WIDTH}x{HEIGHT}",
        "-framerate", str(EXPORT_FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    surface = pygame.Surface((WIDTH, HEIGHT))

    try:
        for frame_index in range(frame_count):
            time_value = frame_index / EXPORT_FPS
            draw_frame(surface, scene, time_value)
            process.stdin.write(pygame.image.tobytes(surface, "RGB"))
            if frame_index % EXPORT_FPS == 0 or frame_index + 1 == frame_count:
                percentage = (frame_index + 1) / frame_count * 100
                print(
                    f"\r{scene.key}/{len(SCENES):02d}  {output_path.stem}: "
                    f"{percentage:5.1f}%",
                    end="",
                    flush=True,
                )
        process.stdin.close()
        return_code = process.wait()
    except (BrokenPipeError, KeyboardInterrupt):
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.terminate()
        process.wait()
        raise

    print()
    if return_code != 0:
        raise RuntimeError(
            f"FFmpeg terminó con código {return_code}: {output_path.name}"
        )
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Exporta las ocho escenas QHD a MP4 de 30 FPS."
    )
    parser.add_argument(
        "--salida", type=Path,
        default=Path(__file__).resolve().parent / "videos",
    )
    parser.add_argument(
        "--escena", choices=tuple(SCENES), action="append",
        help="Exporta sólo una escena. Puede repetirse.",
    )
    parser.add_argument("--crf", type=int, default=14)
    parser.add_argument(
        "--sufijo", default="",
        help="Añade una versión al nombre, por ejemplo: v2.",
    )
    parser.add_argument(
        "--preset",
        choices=("ultrafast", "fast", "medium", "slow"),
        default="medium",
    )
    parser.add_argument(
        "--segundos-prueba", type=float,
        help="Limita cada video; útil para verificar FFmpeg rápidamente.",
    )
    args = parser.parse_args()

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise SystemExit(
            "No se encontró FFmpeg en PATH. Instálalo antes de exportar."
        )
    if args.segundos_prueba is not None and args.segundos_prueba <= 0:
        raise SystemExit("--segundos-prueba debe ser mayor que cero.")
    suffix = args.sufijo.strip()
    if suffix and not suffix.startswith("_"):
        suffix = f"_{suffix}"

    selected = args.escena or tuple(SCENES)
    args.salida.mkdir(parents=True, exist_ok=True)
    initialize_hidden()
    outputs = []
    try:
        for key in selected:
            output = export_scene(
                SCENES[key], args.salida, ffmpeg_path,
                args.crf, args.preset, suffix, args.segundos_prueba,
            )
            if output is not None:
                outputs.append(output)
    except KeyboardInterrupt:
        print("\nExportación cancelada.", file=sys.stderr)
        raise SystemExit(130)
    finally:
        pygame.quit()

    if outputs:
        print("\nVideos creados:")
        for output in outputs:
            print(f"  {output}")
    else:
        print("\nNo se creó ningún video nuevo.")


if __name__ == "__main__":
    main()
