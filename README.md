# Camaro SS 1968 · en 3D, pieza por pieza

El Camaro SS 68 coupé negro de un amigo, en 3D en el navegador: se gira, se abren capot, puertas y
baúl, se separa en piezas y cada pieza tiene su ficha con qué es, qué hace, un dato del Camaro 67-68
y un «Saber más». Con el botón **Motor**, el V8 350 sale del auto a un soporte de taller: ahí se
separa en orden, se arma paso a paso, se prende (con sonido) y se ve por adentro, en corte.

Se usa sin mouse: touchpad, teclado o dedos (ver «Controles» abajo).

## Cómo se abre

Es una página estática: no hay que instalar nada ni armar nada.

- En Taller: la vista previa abre `index.html`.
- En la compu, fuera de Taller: hace falta un servidor local cualquiera (abrir el archivo con doble
  clic no anda, porque el navegador no deja cargar los modelos desde `file://`).
- Publicado: Netlify con el botón de Taller, subiendo la carpeta tal cual.

Three.js 0.186.1 y el decodificador de los modelos van copiados en `vendor/three/` (licencia MIT en
`vendor/three/LICENSE`). Lo único que baja de internet son las letras (Barlow, de Google Fonts); sin
internet se ven con la letra del sistema.

> **Ojo:** `vendor/three/build/` (el corazón de Three.js) tiene que estar en la carpeta. El
> `.gitignore` ignora toda carpeta `build/`, pero tiene la excepción `!vendor/three/build/`: no
> la saques, o esa carpeta deja de viajar a las copias y a GitHub.

## Controles

| Qué | Touchpad / teclado | Celular |
|---|---|---|
| Girar | Apretar y arrastrar · `Mayús` + flechas | Un dedo |
| Acercar / alejar | Pellizcar · botones + / − · teclas `+` `−` | Pellizcar · botones + / − |
| Correrse a un costado | `Mayús` + arrastrar · flechas | Dos dedos |
| Ver por adentro (cabina) | Botón «Adentro» · tecla `A` | Botón «Adentro» |
| Volver | «Vista inicial» · tecla `0` | «Vista inicial» |
| Ayuda | Botón `?` · tecla `?` | Botón `?` |

## Qué hay en cada carpeta

| Carpeta / archivo | Qué es |
|---|---|
| `index.html` | La pantalla (con el cartel de ayuda) |
| `css/estilos.css` · `css/celular.css` | El diseño · ajustes finos para el celular |
| `css/vista-motor.css` · `css/motor-vivo.css` | La vista Motor · el panel de Prender / Acelerar |
| `js/app.js` | La escena 3D, la cámara y sus controles, la lista, la ficha, abrir y cerrar, y el enganche de los módulos |
| `js/modulos/` | Separar, Paso a paso, la vista Motor y el motor en marcha |
| `datos/fichas.json` · `datos/FUENTES.md` | Las 57 fichas · de dónde salió cada dato |
| `modelos/*.glb` · `modelos/manifiesto.json` | El auto y el motor en 3D (comprimidos) · qué se carga, cómo abre cada cosa y el orden de desarme |
| `assets/audio/` | El sonido del V8 (CC0, créditos en `CREDITOS.md`) |
| `vendor/three/` | Copia de Three.js (solo los archivos que se usan) |
| `blender/` | Los scripts que generan los modelos (cómo se corren: `blender/LEEME.md`) |
| `docs/muestra-diseno.html` | La muestra de diseño aprobada |

## Peso

Al abrir se bajan carrocería (105 KB), exterior (185 KB) y motor (435 KB): unos 725 KB, más el
decodificador (~250 KB). El motor por dentro (`motor_interno.glb`, 325 KB) y el sonido (100 KB) se
bajan recién al usarlos.

## Volver a generar y comprimir un modelo

1. Generar el `.glb` con Blender como dice `blender/LEEME.md`.
2. Comprimirlo (sale ~4 veces más liviano, se ve igual). Con Node instalado, desde la carpeta del
   proyecto (`@gltf-transform/cli`, se baja solo con `npx`):

   ```sh
   npx @gltf-transform/cli webp  modelos/carroceria.glb modelos/carroceria.glb --quality 85
   npx @gltf-transform/cli draco modelos/carroceria.glb modelos/carroceria.glb --method edgebreaker
   ```

   (`webp` hace falta en los modelos que traen imágenes: la sombra de la carrocería y las texturas
   del motor.)

No usar `optimize`, `meshopt`, `quantize`, `join`, `flatten` ni `prune`: corren las bisagras de
lugar, juntan piezas o borran los puntos de enganche.
