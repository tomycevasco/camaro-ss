# Camaro SS

**Qué es:** el Camaro SS 1968 coupé negro de un amigo de Tomás, en 3D en el navegador: se gira, se abren capot, puertas y baúl, y cada pieza (carrocería y motor) se toca para ver qué es y qué hace. También se puede separar en piezas y armar paso a paso.
**Tipo:** otro · **Creado:** 21/10/2026 · **Para:** Tomás (lee HTML/CSS/JS, no programa) y su amigo

## El auto (decidido en la entrevista, sin fotos)
- **1968 SS coupé**, negro entero, sin franjas ni vinilo. Sin ventilete. Luces de posición ámbar chicas abajo, adelante, al costado. Nafta detrás del emblema trasero. Faros redondos a la vista (no es RS). Capot SS con lomo central **sin rejillas**. Llantas Rally (asumido).
- Motor: V8 350 small block naranja Chevrolet, tapas de válvulas cromadas, carburador de 4 bocas, **filtro de aire redondo cromado** (la «turbina»). Solo piezas de afuera del motor, nada interno.
- Interior negro: butacas sin apoyacabezas, cinturón solo de cintura, asiento trasero, volante de 3 rayos, palanca al piso. Se ve, pero sin fichas.
- No entra: lo de abajo (suspensión, caja, escapes, frenos).

## Decisiones de diseño (aprobado en la muestra: `docs/muestra-diseno.html`)
- Estilo: estudio blanco, el auto negro es el protagonista. Vista inicial 3/4 de adelante. Piso simple hecho en Blender, con el auto **apoyado** (sombra de contacto), nunca flotando.
- Colores: `--fondo: #f3f2ee` · `--superficie: #ffffff` · `--linea: #e3e1db` · `--texto: #16181c` · `--texto-suave: #61666d` · `--acento: #d9600b` (naranja Chevrolet: pieza marcada, detalles) · `--acento-texto: #b34c05` · `--acento-claro: #fdeee2`. Botones principales en negro (`--texto`).
- Letras: Barlow Condensed (títulos, en mayúsculas con aire) y Barlow (texto).
- Pantalla: barra arriba (marca + Explorar/Separar/Paso a paso), escena 3D, ficha flotante a la derecha (en celular abajo del auto), lista de piezas a la derecha, controles abajo (Capot, Puertas, Baúl, Vista inicial, barra Separar).
- Fichas: explicación simple (2–3 frases) + «Dato Camaro» del 67-68 + «Saber más» desplegable, un poco más a fondo pero sin ponerse técnico ni aburrido.

## Cómo está armado
- `index.html` + `css/estilos.css` (todo lo visual) + `css/celular.css` (solo ajustes finos de celular) + `js/app.js` (la escena, la lista, la ficha, abrir/cerrar). Separar y Paso a paso viven en `js/modulos/separar.js` y `js/modulos/paso-a-paso.js` (los dos usan `js/modulos/movimiento.js`: hacia dónde va cada pieza y cómo vuelve; se cargan según `modulos` del manifiesto); si faltan, `app.js` usa una versión simple propia.
- `modelos/manifiesto.json` dice qué `.glb` se cargan y cómo abre cada cosa (eje y grados). Una pieza se reconoce porque el nombre del objeto en Blender = `id` de su ficha en `datos/fichas.json` (33 fichas: 18 del motor, 15 de carrocería). Fuentes de las fichas: `datos/FUENTES.md`.
- Three.js 0.186.1 desde jsDelivr (importmap en `index.html`; la ruta del decodificador Draco en `app.js` tiene que ser la misma versión).
- Se dibuja solo cuando algo se mueve, y en celular la nitidez y las sombras van más bajas (en `app.js`).

## Modelos 3D y peso
- Salen de `blender/carroceria.py`, `blender/exterior.py` y `blender/motor.py` (cómo correrlos: `blender/LEEME.md`). Blender 4.5 LTS portátil va en `.taller/tmp/blender/` (fuera de git).
- **Después de regenerar un `.glb` hay que comprimirlo** (Blender lo exporta sin comprimir, ~3-5 veces más pesado). Comandos en `README.md`. Draco solo achica la geometría: nombres, bisagras y orígenes quedan igual. **No usar `optimize`, `quantize`, `meshopt`, `join`, `flatten` ni `prune`**: mueven los orígenes (rompen las bisagras), juntan piezas o borran los `enganche_*`.
- Pesos hoy (comprimidos con Draco, sombra en WebP): carrocería 102 KB · exterior 142 KB · motor 89 KB = **≈340 KB** (antes 1,7 MB). El decodificador Draco (~100 KB) baja de jsDelivr.

## Cómo se arranca y se prueba
- Ver: abrir `index.html` en la vista previa.
- Probar: girar, tocar piezas, abrir capot/puertas/baúl, separar, paso a paso; celular (390×844) y compu (1366×800).
- Publicar: Netlify con el botón de Taller. No hay build: se sube la carpeta tal cual.

## Reglas de este proyecto
- Textos en español rioplatense.
- Sin frameworks ni build. Three.js para el 3D. El modelo sale de Blender portátil manejado por scripts de Python.
- Datos de las fichas verificados en fuentes de restauración (camaros.org y similares), nada inventado.
