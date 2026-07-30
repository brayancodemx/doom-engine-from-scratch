# Procedencia de recursos visuales

Los recursos visuales de esta carpeta se prepararon específicamente para este
proyecto con herramientas de inteligencia artificial. Cuentan con la licencia
o autorización necesaria para su uso y distribución dentro de este
repositorio. No se usaron imágenes, logos ni sprites de juegos comerciales
como entrada declarada. Los fondos verdes de las armas se eliminaron
localmente; después se redujeron a 640×360 con muestreo por vecino más cercano.

## Archivos

- `menu_background_doom.png`: corredor industrial infernal original, 960×540.
- `weapons/doom_rifle.png`: rifle centrado en primera persona.
- `weapons/doom_shotgun_closed.png`: escopeta doble cerrada.
- `weapons/doom_shotgun_open.png`: la misma escopeta con recámara abierta.
- `enemies/demon_*.png`: secuencia del demonio (reposo, marcha, ataque,
  daño, muerte y cadáver), importada del paquete local entregado por el autor
  del proyecto en `demon_sprites/`.
- `textures/walls/wall_*.png`: seis materiales opacos para los tipos de pared
  `1` a `6` del mapa.
- `textures/floors/floor_*.png`: placas, rejilla y metal sucio para el muestreo
  de piso en coordenadas del mundo.
- `textures/ceilings/ceiling_*.png`: acero, rejilla y óxido para el techo.

Los nueve sprites del demonio se recibieron con un fondo cromático verde. Se
conservó el dibujo original y sólo se generó el canal alfa con
`remove_chroma_key.py`, usando mate suave y eliminación de contaminación verde.
El juego los normaliza a 512×512 al cargarlos para reducir memoria sin mantener
copias redimensionadas por cada enemigo.

Las doce texturas de escenario fueron entregadas por el autor del proyecto como
PNG opacos de 1254×1254 y se conservan intactas. Las seis paredes son los assets
activos: se normalizan a 512×512 y usan impactos DDA exactos con mipmaps. Los PNG
de piso y techo permanecen disponibles como alternativas; la pasada activa se
construye con losas, biseles, fijaciones, rejillas, cables, manchas, paneles,
vigas y luminarias procedurales proyectadas directamente a 720p. El techo se
compone antes que las paredes para que nunca pueda atravesarlas visualmente.

`menu_background_doom.png` es el único fondo de menú incluido en la
publicación. Los sprites del demonio y las texturas del escenario forman parte
del conjunto visual preparado para este proyecto. Las condiciones de uso y
distribución de los recursos se mantienen bajo la licencia o autorización del
autor del proyecto.

## Prompts finales

### Rifle

```text
Arma original para un raycaster 960×540: rifle de asalto brutal y compacto,
visto en primera persona desde la cadera, perfectamente centrado, con manos y
antebrazos enguantados. Pixel art de FPS de principios de los noventa, metal
ennegrecido y gastado, detalles de hueso y un indicador rojo contenido. Fondo
chroma key #00ff00 uniforme; sin fogonazo, humo, texto, logos, marcas de agua,
neón ni elementos copiados de juegos comerciales.
```

### Escopeta cerrada

```text
Arma original para un raycaster 960×540: escopeta de combate de dos cañones,
cerrada y lista para disparar, vista en primera persona desde la cadera,
perfectamente centrada, con manos enguantadas. Pixel art de FPS retro, acero
ennegrecido, óxido, madera oscura y hueso. Fondo chroma key #00ff00 uniforme;
sin fogonazo, humo, cartuchos, texto, logos, neón ni material copiado.
```

### Escopeta abierta

```text
Conservar exactamente el diseño, manos, materiales, paleta, escala y pixel art
de la escopeta cerrada, cambiando únicamente el mecanismo a recámara abierta y
mostrando las dos cámaras vacías. Mantener el encuadre centrado y el fondo
chroma key #00ff00 uniforme; sin cartuchos, humo, texto, logos ni rediseño.
```

### Menú

```text
Fondo original 16:9 para el menú de un FPS retro: corredor simétrico de búnker
industrial infernal, puerta circular sellada al fondo, acero oxidado, remaches,
tuberías, hormigón agrietado, sangre contenida y lámparas ámbar. Pixel art de
paleta marrón, roja, oliva y hueso, con espacio oscuro para el título. Sin
personajes, armas, texto, logos, neón ni símbolos de juegos comerciales.
```
