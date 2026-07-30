# Animaciones QHD nativas

Esta carpeta contiene versiones independientes de las animaciones de
`fases/`. Las escenas 01–07 dibujan cada fotograma directamente a
**2560×1440**. La escena 08 conserva el render real de 1280×720 del juego y lo
presenta con un escalado entero 2×, sin interpolación ni desenfoque.

## Vista previa

```powershell
python fases_qhd/01_map_data_matriz_qhd.py
python fases_qhd/03_raycasting_dda_qhd.py --pantalla-completa
```

La vista previa se adapta al monitor. La resolución interna siempre permanece
en 2560×1440.

Controles: `Espacio` pausa, `R` reinicia, flechas izquierda/derecha recorren la
animación y `Esc` cierra.

## Exportar todos los videos

```powershell
python fases_qhd/exportar_todo.py --sufijo v2
```

También se puede abrir:

```powershell
fases_qhd\exportar_todo_v2.bat
```

Los ocho MP4 se guardan en `fases_qhd/videos/` con resolución 2560×1440,
30 FPS, H.264 y alta calidad (`CRF 14`). Los fotogramas se envían directamente
a FFmpeg, por lo que no se acumulan miles de PNG temporales.

El sufijo crea archivos como `01_map_data_matriz_qhd_v2.mp4`. Si un nombre ya
existe, el exportador lo omite: nunca sobrescribe los videos anteriores.

Opciones útiles:

```powershell
# Sólo una escena
python fases_qhd/exportar_todo.py --escena 03 --sufijo v2

# Prueba rápida de un segundo
python fases_qhd/exportar_todo.py --escena 03 --segundos-prueba 1 --sufijo prueba

# Elegir otra carpeta
python fases_qhd/exportar_todo.py --salida E:\Videos\DOOM
```
