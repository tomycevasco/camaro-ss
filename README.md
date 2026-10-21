# Camaro SS 1968 · en 3D, pieza por pieza

El Camaro SS 68 coupé negro de un amigo, en 3D en el navegador: se gira, se abren capot, puertas y
baúl, se separa en piezas y cada pieza (carrocería y motor V8 350) tiene su ficha con qué es, qué
hace, un dato del Camaro 67-68 y un «Saber más».

## Cómo se abre

Es una página estática: no hay que instalar nada ni armar nada.

- En Taller: la vista previa abre `index.html`.
- En la compu, fuera de Taller: hace falta un servidor local cualquiera (abrir el archivo con doble
  clic no anda, porque el navegador no deja cargar los modelos desde `file://`).
- Publicado: Netlify con el botón de Taller, subiendo la carpeta tal cual.

Three.js 0.186.1 y el decodificador de los modelos van copiados en `vendor/three/` (licencia MIT en
`vendor/three/LICENSE`). Lo único que baja de internet son las letras (Barlow, de Google Fonts); sin
internet se ven con la letra del sistema.

## Qué hay en cada carpeta

| Carpeta / archivo | Qué es |
|---|---|
| `index.html` | La pantalla |
| `css/estilos.css` · `css/celular.css` | El diseño · ajustes finos para el celular |
| `js/app.js` | La escena 3D, la lista, la ficha, abrir y cerrar |
| `js/modulos/` | Separar piezas y Paso a paso |
| `datos/fichas.json` · `datos/FUENTES.md` | Las 33 fichas · de dónde salió cada dato |
| `modelos/*.glb` · `modelos/manifiesto.json` | El auto en 3D (comprimido) · qué se carga y cómo abre cada cosa |
| `vendor/three/` | Copia de Three.js (solo los archivos que se usan) |
| `blender/` | Los scripts que generan los modelos (cómo se corren: `blender/LEEME.md`) |
| `docs/muestra-diseno.html` | La muestra de diseño aprobada |

## Volver a generar y comprimir un modelo

1. Generar el `.glb` con Blender como dice `blender/LEEME.md`.
2. Comprimirlo (sale ~4 veces más liviano, se ve igual). Con Node instalado, desde la carpeta del
   proyecto (`@gltf-transform/cli`, se baja solo con `npx`):

   ```sh
   npx @gltf-transform/cli webp  modelos/carroceria.glb modelos/carroceria.glb --quality 85
   npx @gltf-transform/cli draco modelos/carroceria.glb modelos/carroceria.glb --method edgebreaker
   ```

   (`webp` solo hace falta en `carroceria.glb`, que es el único con imagen: la sombra del piso.)

No usar `optimize`, `meshopt`, `quantize`, `join`, `flatten` ni `prune`: corren las bisagras de
lugar, juntan piezas o borran los puntos de enganche.
