# DOOM... digo DUCK

Un proyecto didáctico para entender cómo los videojuegos de los años 90
creaban la ilusión de un mundo tridimensional usando matemáticas, mapas 2D y
un renderizador mucho más sencillo que un motor 3D moderno.

![Gameplay](assets/previews/gameplay_documental.png)

## Requisitos

- Python 3.10 o posterior
- Pygame 2.6.1
- NumPy 2.x

Instala las dependencias con:

```powershell
python -m pip install -r requirements.txt
```

## Cómo ejecutar

Desde la carpeta del proyecto, inicia el juego con:

```powershell
python main.py
```

Opcionalmente, puedes abrirlo a pantalla completa:

```powershell
python main.py --pantalla-completa
```

Controles principales: `WASD` para moverte, ratón o flechas para girar,
clic izquierdo o `Espacio` para disparar, `1` y `2` para cambiar de arma,
`R` o `Enter` para iniciar o reiniciar, `F11` para pantalla completa y `Esc`
para volver al menú.

## Objetivo

La meta no es reconstruir el código original de DOOM, sino estudiar las ideas
que hicieron posibles los shooters clásicos: cómo un mapa plano puede
convertirse en una vista en primera persona, cómo se proyectan las paredes y
cómo se dibujan enemigos y armas con recursos bidimensionales.

## Qué se explora

- **Mapas 2D y coordenadas:** el mundo se representa como una matriz de
  celdas, donde cada valor identifica un tipo de pared o un espacio libre.
- **Raycasting y DDA:** se lanzan rayos desde la cámara y se calcula la celda
  exacta que alcanza cada uno sin recorrer píxeles innecesarios.
- **Corrección del efecto de ojo de pez:** las distancias laterales se corrigen
  para que las paredes rectas sigan viéndose rectas.
- **Proyección en perspectiva:** la distancia al impacto determina la altura
  de cada columna vertical que forma la escena.
- **Suelo, techo y materiales:** se combinan texturas, geometría procedural,
  luces, sombras y atmósfera para dar profundidad al mapa.
- **Sprites y billboards:** los enemigos y las armas son imágenes 2D que se
  escalan y orientan para parecer parte del mundo.
- **Oclusión por profundidad:** un `depth_buffer` evita que los enemigos
  aparezcan a través de las paredes.
- **Movimiento y colisiones:** el jugador usa trigonometría, desplazamiento
  independiente de los FPS y colisiones deslizantes.
- **Enemigos:** se incluyen estados de reposo, marcha, ataque, daño y muerte,
  además de navegación para rodear obstáculos.
- **Bucle de juego:** la actualización de la lógica y el dibujo se separan
  para mantener un comportamiento estable en cada fotograma.

El raycasting de este proyecto es una aproximación educativa relacionada con
los primeros shooters en primera persona. El DOOM original utilizaba un
renderizador basado en sectores y árboles BSP; aquí se usa un raycaster para
que el proceso sea más fácil de observar y explicar desde cero.

## Organización del proyecto

- `main.py`: coordina el bucle del juego, los estados, la entrada y la escena.
- `map_data.py`: contiene el mapa, sus materiales y los puntos de aparición.
- `raycasting.py`: calcula los impactos de los rayos mediante DDA.
- `entities.py`: contiene al jugador, los enemigos, el movimiento y las
  colisiones.
- `renderer.py`: dibuja paredes, suelo, techo, enemigos, armas, efectos y HUD.
- `settings.py`: reúne las constantes de cámara, física y renderizado.
- `audio.py`: carga efectos opcionales y conserva un respaldo procedural.
- `etapas/`: recorrido progresivo desde el mapa 2D hasta el pipeline completo.
- `fases/`: escenas y demostraciones visuales de conceptos concretos del
  desarrollo.
- `fases_qhd/`: versiones de mayor resolución de algunas escenas del proceso.

## Enfoque del proyecto

Cada sistema está separado para que pueda estudiarse por partes: primero el
mapa, después los rayos, la proyección, las entidades y finalmente la
composición del fotograma. La intención es mostrar la tecnología que había
detrás de los juegos de los 90 con ejemplos visuales y código legible, no
ocultar el proceso detrás de un motor externo.

Los recursos visuales incluidos fueron creados específicamente para este
proyecto con herramientas de inteligencia artificial y cuentan con la licencia
o autorización necesaria para su uso y distribución dentro del repositorio.
