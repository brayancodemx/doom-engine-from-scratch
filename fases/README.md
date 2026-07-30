# Animaciones del guion

Las escenas siguen únicamente las explicaciones incluidas en `guion.md`.
No intentan documentar todas las funciones reales del proyecto.

```powershell
python fases/01_map_data_matriz.py
python fases/02_entities_movimiento.py
python fases/03_raycasting_dda.py
python fases/04_renderer_proyeccion.py
python fases/05_audio_carga.py
python fases/06_main_bucle.py
python fases/07_pipeline_fotograma.py
python fases/delta_time_gameplay.py --self-test
python fases/delta_time_gameplay.py
python fases/rendimiento_38k_rayos.py
python fases/rendimiento_38k_rayos_documental.py
python fases/demonio_atorado_pared.py
python fases/demonio_billboard_semivuelta.py
```

Controles comunes: `Espacio` pausa, `R` reinicia, flechas izquierda/derecha
recorren la animación y `Esc` cierra.

Para guardar un fotograma:

```powershell
python fases/03_raycasting_dda.py --captura captura.png --tiempo 6.5
```

La escena de delta time exporta dos clips de 7 segundos en
`videos/delta_time/`: `delta_time_con_dt.mp4` y `delta_time_sin_dt.mp4`.
También puede abrirse una vista interactiva con `--vista con_dt` o
`--vista sin_dt`.

`rendimiento_38k_rayos.py` crea la animación cinematográfica de 11 segundos
en `videos/rendimiento_38k_rayos.mp4`.

`rendimiento_38k_rayos_documental.py` crea la versión documental de 18
segundos usando `assets/previews/gameplay_documental.png` como cierre y como
base visual del pintado por sectores.

`demonio_atorado_pared.py` crea una toma de gameplay de 4 segundos sin textos
extra en `videos/demonio_atorado_pared.mp4`.

`demonio_billboard_semivuelta.py` crea una toma de gameplay de 8 segundos
rodeando 180 grados a un demonio 2D inmóvil.
