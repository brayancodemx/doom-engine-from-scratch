
DOOM… ese videojuego que puede correr literalmente en cualquier parte. Un clásico que marcó un antes y un después.
Hay cientos de videos donde se muestra cómo correrlo en pantallas absurdas: desde calculadoras hasta pruebas de embarazo. Pero nadie nos ha explicado realmente cómo funciona por dentro o cómo construir uno desde cero…
Así que hoy vamos a programar nuestro propio motor paso a paso para ver cómo pasamos de esto… a esto…
\[INTRO\]
Muy bien. Para construir nuestro DOOM… o bueno, en este caso, **DUCK**, no vamos a necesitar Unity, ni **Unreal Engine**, ni siquiera un **motor 3D** convencional. Solo usaremos al todopoderoso Python.
Y aquí viene el primer secreto: DOOM no es realmente un juego en 3D; es un juego **2.5D**.
No es broma. Básicamente es un juego en dos dimensiones que engaña a nuestro cerebro para simular profundidad.
El DOOM original usaba una tecnología muy compleja llamada Sectores y Árboles BSP, desarrollada por John Carmack. Pero antes de eso, Carmack creó *Wolfenstein 3D* utilizando **Raycasting**. Así que, para entender las bases físicas de este estilo, usaremos el enfoque de Wolfenstein. Antes de correr, hay que aprender a gatear.
Para lograrlo, dividiremos el proyecto en los siguientes archivos: **map_data.py**, **entities.py**, **raycasting.py**, **renderer.py** y **audio.py**. También usaremos un archivo **settings.py** para guardar todas las configuraciones globales, y **main.py** como nuestro coordinador general.

## `MAP_DATA.PY`
---
En **map_data.py** es donde viven los planos del mapa. La información se almacena en una tupla de texto donde cada número representa una textura. Piensa en esto como si fueran bloques de Minecraft: si hay un punto, es un pasillo libre; si hay cualquier otro número, es un muro. Aquí también programamos los puntos de aparición de los enemigos para evitar que aparezcan **monstruos** bugeados dentro de una columna… para no imitar a ciertas compañías de videojuegos.
Aunque a nivel de código es una tupla, visualmente la tratamos como una matriz. Para consultar qué hay en el mundo usamos la sintaxis **`MAP[y][x]`** (primero la fila, luego la columna). El jugador se mueve en coordenadas decimales, como $x = 2.7$ y $y = 4.2$, pero para saber sobre qué celda está parado, convertimos esos números a enteros, lo que nos lleva a la casilla $(2, 4)$.
La función **`tile_at`** (map_data.py#L80) devuelve el carácter de la casilla y **`is_wall`** (map_data.py#L88) hace una pregunta aún más simple: ¿este bloque es diferente de un punto? Si la respuesta es sí, hay una pared. Esta validación servirá tanto para evitar que atravieses muros como para guiar a los enemigos.
> **\[Kimi K3 / Kimi Code\]**<br>Para pasar de esta lógica a código usaremos Kimi Code, con su modelo Kimi K3, diseñado para programar. *\[mostrar pantalla escribiendo el prompt\]*.
---
## `ENTITIES.PY`
---
Muy bien, ya tenemos un mapa en dos dimensiones, pero necesitamos que cobre vida. Aquí entra **entities.py**, donde definimos al jugador y a los enemigos.
Para movernos usando el teclado, recurrimos a nuestras viejas amigas de la escuela: el seno y el coseno. El coseno calcula el desplazamiento horizontal en el eje X y el seno el desplazamiento vertical en el eje Y, con esta fórmula:
```python
# Multiplicamos la velocidad por el Delta Time (dt)
speed = PLAYER_SPEED * dt

# Desplazamiento trigonométrico independiente de los FPS
dx = math.cos(self.angle) * forward * speed
dy = math.sin(self.angle) * forward * speed
```
Aquí es importante explicarle a la IA que no se olvide aplicar el *Delta Time* o **`dt`**, que representa el tiempo que pasa entre cada fotograma. Si no lo usáramos, un jugador con una PC de la NASA a 300 FPS se movería cinco veces más rápido que alguien jugando en una PC del gobierno a 60 FPS.
En este archivo también programamos las colisiones deslizantes y la inteligencia artificial para que los enemigos te persigan y rodeen columnas usando un algoritmo de búsqueda de caminos.
> **\[Corte de Edición: Pantalla - Kimi programando el archivo entities.py…\]**
---
## `RAYCASTING.PY`
---
Con nuestras entidades listas, necesitamos transformar nuestro plano 2D en una vista 2.5D. Para eso sirve **raycasting.py**.
Con la función **`cast_one_ray`** (raycasting.py#L9), lanzamos un rayo invisible desde la mirada del jugador. Para hacerlo súper eficiente, usamos un algoritmo llamado **DDA**, que calcula matemáticamente las intersecciones exactas de las celdas en lugar de avanzar píxel por píxel. Para simular una cámara completa, repetimos este proceso 640 veces en **`cast_all_rays`** (raycasting.py#L54), cubriendo nuestro campo de visión.
Aquí a la IA se le pasó corregir el **“ojo de pez”**. Como los rayos laterales recorren más distancia que el central, las paredes rectas se verían curvadas. Al multiplicar el impacto por el coseno de la diferencia angular de la mirada, eliminamos la deformación y logramos pasillos perfectamente rectos. Le pedimos que implemente la corrección del bug.
> **\[Corte de Edición: Pantalla - Kimi corrigiendo el código del ojo de pez…\]**
---
## `RENDERER.PY`
---
Now que sabemos a qué distancia están las paredes, hay que dibujarlas, y el responsable de esto es **renderer.py**.
En la función **`draw_walls`** (renderer.py#L829), tomamos las 640 distancias corregidas y calculamos la altura de cada columna dividiendo una constante de proyección entre esa distancia. Si la distancia es pequeña, la columna es alta; si es lejana, la columna es baja.
Dibujamos estas franjas una al lado de la otra y ¡listo!, nuestro cerebro ve una habitación tridimensional. Pero un mundo plano necesita decoración. Pintamos el suelo, el techo, y colocamos a nuestros enemigos como dibujos 2D que siempre miran a la cámara en **`draw_enemies`** (renderer.py#L1460).
Y aquí hacemos un truco de magia: para que los monstruos no se vean a través de los muros, comparamos la profundidad de cada franja del enemigo contra el **`depth_buffer`** (nuestro mapa de distancias de la pared). Si la pared está más cerca, descartamos esa columna del enemigo; si está más lejos, la dibujamos. Así es como logramos que un demonio plano pueda asomarse correctamente detrás de una esquina.
> **\[Kimi Code - Comando /swarm\]**<br><br>Aquí voy a utilizar `/swarm`, una función de Kimi Code que distribuye varias tareas entre distintos subagentes para que trabajen en paralelo. Por ejemplo, uno puede encargarse del renderizado, otro revisar las entidades y otro preparar el sistema de audio.
	**\[ Kimi usando el comando /swarm…\]**
---
## `AUDIO.PY`
---
Nuestro motor gráfico casero ya está ready, el juego ya es jugable, pero le falta algo importante: el sonido. En **audio.py**, mediante la clase **`Sounds`** (audio.py#L43), cargamos los archivos de audio para los disparos, la recarga de cartuchos y los gritos de los demonios.
Pero como no es lo mismo matar demonios en silencio, agregamos música heavy metal satánica industrial rompe-tímpanos. Así hasta dan ganas de masacrar demonios.
> **\[Kimi creando el archivo audio.py\]**<br>Este pequeño archivo lo creó uno de los subagentes del comando anterior.
---
## `MAIN.PY`
---
Ya tenemos el mapa, el jugador, los enemigos, los efectos de sonido y la música metalera… ¿pero cómo unimos todo esto? Para eso sirve **main.py**.
Este archivo es el cerebro y coordinador general de todo el proyecto. Aquí vive la clase **`Game`** (main.py#L32), que ejecuta el bucle de juego 60 veces por segundo. Su trabajo es separar estrictamente el juego en dos momentos: **`update`** (main.py#L211), que calcula cualquier cambio en la física o en los monstruos, y **`draw`** (main.py#L391), que toma una “fotografía” en tiempo real de esos datos y pinta el fotograma final por capas.
---
Muy bien, ya tenemos todo. Antes de mostrar el resultado final, si te gustan esta clase de explicaciones, ya sabes qué hacer… Te voy a mostrar todo lo que hace internamente nuestro motor en cada fotograma:
Primero, escanea el mapa 2D y mide las distancias. Luego, pinta el cielo y el suelo de fondo. Después, levanta los muros en 3D con sus texturas y coloca a los enemigos, ocultándolos detrás de las esquinas. A continuación, agrega la niebla y las luces para dar atmósfera, y simula el balanceo de la cabeza al caminar. Al mismo tiempo, genera las chispas y el fogonazo si disparamos, dibuja el arma en primer plano con su retroceso, y encima coloca la mira, el minimapa y tu barra de vida. Finalmente, aplica el filtro de daño rojo y el efecto de televisión antigua.
Todo esto lo hace 60 veces por segundo.
Eso significa calcular **más de 38,000 rayos por segundo**, procesar colisiones, mover enemigos y repintar millones de píxeles en menos de 16 milisegundos. Todo sin que te des cuenta y en completo silencio, solo para que tu cerebro acepte la ilusión de que estás dentro de un calabozo y no frente a una simple lista de texto.
> **\[Kimi - Costos y Parámetros\]**<br>Ejecutar todo esto costó \[precio\], si tomamos en cuenta que es un modelo de 2.8T de parámetros y un contexto de 1 millón de tokens. Está bien. En algunos benchmarks está por encima de Fable aunque todavía comete uno que otro error. Pero en relación calidad-precio está bastante bien. Por cierto, si quieren trastear con su API, tienen un bonus de recarga activo hasta el 12 de agosto; y si usan el link que les dejé abajo, les dan un extra de créditos que se acumula con esa promo, por si quieren probarlo sale prácticamente gratis.
Y ahora que ya conocemos el truco de magia… es hora de ver la magia en acción.
Aquí está el resultado final.
Ver cómo funciona DOOM bajo el **capó** es impresionante. Si quieres ver más
proyectos de tecnología y programación, dale **clic** a este video y te veo por
allá.
