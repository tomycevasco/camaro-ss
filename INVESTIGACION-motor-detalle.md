# Investigación · Motor por afuera, con detalle (Agente 1, 21/10/2026)

**En una línea:** rehacer `blender/motor.py` con un juego de herramientas propias (bisel + normales
ponderadas, tornillos, nervaduras, mangueras con abrazaderas, letras en relieve) y texturas de
«fundición» **generadas por el mismo script**, sumar las piezas que faltan respetando dónde van en un
350 del 68, y dejar en el manifiesto todo lo que la vista Motor necesita para engancharse.

## Lo que hay hoy (lo leí entero)
- `motor.py` (755 líneas) arma 18 piezas con cajas, cilindros y tubos; bisel solo en algunas, sin
  tornillos, sin texturas, sin coordenadas de textura (`export_texcoords=False`).
- La base sirve y se mantiene: medidas reales (V a 90°, 4,4″ entre cilindros, 9,025″ de deck),
  `Malla` con número de material, origen en el centro de cada pieza, pares agrupados en un vacío
  (`tapas-valvulas` → `tapa-valvulas-izq/der`), todo colgado de `motor`, y el control que avisa si
  algo toca el capot o se sale del vano.
- `app.js` reconoce piezas por nombre = `id` de ficha (o por `piezas3d`). **Lo que no tiene ficha se
  ve pero no se toca**: las piezas nuevas quedan así hasta que el Agente 7 escriba sus fichas.
- Blender **no está** en ninguna copia: hay que bajar otra vez el portátil 4.5.14 LTS a
  `.taller/tmp/blender/` (~400 MB, ya aprobado en el plan).

## Datos del 350 del 68 que hay que respetar
| Pieza | Dónde va | Fuente |
|---|---|---|
| Bomba de agua **corta** + alternador **del lado del conductor** (+X), soporte a la bomba y al múltiple | 67-68; en el 69 pasa al otro lado con bomba larga | camaros.org, Rick's, Yenko |
| Alternador Delcotron 42 A (61 A con aire), **regulador aparte** (va en la carrocería: no lo modelo) | — | camaroz28 (White Book), Yenko |
| Bomba de nafta mecánica | Lado **acompañante**, adelante y abajo, delante del soporte del motor | camaroz28, NCRS |
| Varilla del aceite | Lado **conductor**, en el bloque (hasta el 79) | JEGS / OER |
| Filtro de aceite (cartucho enroscado) | Lado conductor, atrás y abajo (de memoria: el Agente 7 lo confirma en la ficha) | — |
| Motor de arranque | Lado acompañante, atrás (ya está bien) | — |
| Múltiples de escape | Hierro fundido, salida hacia abajo; el izquierdo tiene donde atornillar el soporte del alternador | NCRS (3932461) |
| Carburador | Quadrajet de 4 bocas: chicas adelante, grandes atrás (ya está así) | — |

## Herramientas de detalle (cómo se hace bien hoy)
- **Bisel + normales ponderadas** en todo lo duro: es lo que más saca la cara de «caja de plástico».
  En Blender 4.5 el orden importa: bisel → «Smooth by Angle» → **Weighted Normal** al final, y se
  aplican antes de exportar (el `.glb` lleva las normales tal cual y Three.js las usa así).
- **Subdivisión suave** solo en lo fundido y redondo (cárter, múltiples, tapas de cilindros).
- **Tornillos hexagonales** con una función `tornillos(fila)` que los pone sobre un borde (tapas de
  válvulas, cárter, bomba, tapa de distribución). Van **dentro de la malla de su pieza**: así no se
  suman objetos (menos trabajo para el celular) y se separan con ella.
- **Nervaduras, bridas y letras en relieve** (texto de Blender pasado a malla). Letras solo donde
  esté confirmado lo que decía de fábrica; si no, sin letras.
- **Mangueras y cables** como curvas con abrazaderas y capuchones; los cables de bujías ya existen.

## Texturas: las tres opciones
| Opción | A favor | En contra |
|---|---|---|
| **A. Generarlas en el script (ruido con Python), recomendada** | Reproducible, sin descargar nada, sin licencias, tamaño justo; el mismo script las rehace | Hay que escribir el generador (corto) |
| B. Hornear nodos procedurales de Blender con Cycles | Mucho control | El glTF **no** exporta nodos procedurales: hay que hornear sí o sí; lento y frágil en modo sin ventana |
| C. Bajar de Poly Haven / ambientCG (CC0) | Calidad fotográfica | Archivos grandes, hay que achicarlos; quedan más «genéricas» |

- Plan: mapas de **relieve (normal) y rugosidad** de 512 px que se repiten (hierro fundido granulado,
  aluminio fundido, goma), **compartidos por material**. El color va liso para no ensuciar el naranja
  Chevrolet. El cromo, sin textura (brilla por el reflejo del estudio).
- Coordenadas de textura por **proyección de caja** hecha en el script (Three.js no tiene
  proyección triplanar sin código propio).
- Se pasan a **WebP** al comprimir (como la sombra de la carrocería).

## Peso (para que el celular no sufra)
- Meta: **≤ 450 KB** comprimido (hoy 89 KB) y unos 60–90 mil triángulos. Un objeto por pieza, menos de
  10 materiales.
- Comprimir igual que hoy: `webp` y después `draco --method edgebreaker`. Draco solo achica la forma:
  nombres y `extras` (userData) quedan afuera de lo comprimido. Igual, después de comprimir lo
  **verifico con un script** (nombres, `enganche_*`, orígenes) y miro que el bisel no se vea
  «escalonado» por la cuantización de normales.

## Piezas nuevas (ids propuestos; las fichas son del Agente 7)
`bomba-nafta`, `filtro-aceite`, `varilla-aceite`, `termostato` (toma de agua), `mangueras`
(calefacción y nafta), `bujias` (8, en `piezas3d`), `poleas` y `balanceador` (hoy viven dentro de
`correas`: las separo y `correas` queda solo la correa), `soportes-motor`, `tapa-distribucion`.
Los 18 ids que ya tienen ficha **no cambian**.

## Enganche para la vista Motor (lo que dejo en `manifiesto.json`)
- Un bloque `"vista_motor"` con: archivo y raíz (`motor`), **qué se queda en el auto** (`radiador`,
  `bateria`), el **orden de desarme** real (filtro de aire → carburador → cables → distribuidor →
  bobina → ventilador → correa → poleas → alternador → bomba de nafta → termostato → múltiple de
  admisión → tapas de válvulas → múltiples de escape → bujías → tapas de cilindros → bomba de agua →
  balanceador → arranque → filtro y varilla → cárter → bloque), hacia dónde sale cada una, y dónde
  va el interno (`motor_interno.glb`, del Agente 4).
- **El soporte de taller**: se atornilla a la cara de atrás del bloque. Dejo un vacío
  `enganche_soporte` en el `.glb` (punto y orientación) y sus medidas en el manifiesto. El soporte en
  sí lo arma el Agente 6: si lo pongo yo en `motor.glb`, aparecería metido en el auto hasta que la
  tanda 3 lo esconda.
- Para el Agente 4: `motor.py` queda **importable** (como `carroceria.py`): medidas, `Malla`,
  materiales y texturas, así `motor_interno.py` arma pistones y bielas encima sin copiar código. El
  `bloque` sigue entero; el corte vive en `motor_interno.glb`.

## Fuentes
- [CRG · bombas de agua de los Camaro 67-69](https://www.camaros.org/waterpumps.shtml) · [Soporte alternador 67-68 (Rick's)](https://www.rickscamaros.com/camaro-alternator-bracket-small-block-upper-1967-1968-33-185170-1.html) · [Yenko: lado del alternador en 1969](https://www.yenko.net/forum/showthread.php?p=989196)
- [camaroz28: alternadores del 68 (White Book)](https://www.camaroz28.com/forums/fuel-ignition-74/alternator-question-887144) · [Yenko: regulador externo](https://www.yenko.net/forum/archive/index.php/t-90285.html)
- [Bomba de nafta, lado acompañante (camaroz28)](https://camaroz28.com/forums/3rd-gen-l98-engine-tech-20/alright-help-me-out-lame-instalation-163815) · [NCRS: bomba de nafta del 327](https://www.forums.ncrs.org/forum/technical-discussion/69327-help-fuel-pump-install?p=731164)
- [Varilla del lado del conductor 57-79 (JEGS)](https://www.jegs.com/i/oer-691-t5100-t5100-1957-79-chevrolet-small-block-4-quart-oil-pan-driver-side-dipstick-location)
- [NCRS: múltiple 3932461](https://www.forums.ncrs.org/forum/technical-discussion/60773-3932461-exhaust-manifold-casting)
- [glTF de Blender: qué materiales exporta](https://docs.blender.org/manual/pt/2.90/addons/import_export/scene_gltf2.html) · [Weighted Normal (manual)](https://docs.blender.org/manual/en/3.5/modeling/modifiers/modify/weighted_normal.html) · [Orden de modificadores en 4.1+](https://projects.blender.org/blender/blender/issues/121620) · [Weighted Normal y glTF](https://projects.blender.org/blender/blender-addons/issues/64979)
- [gltf-transform: draco](https://gltf-transform.dev/modules/functions/functions/draco) · [KHR_draco_mesh_compression](https://github.com/KhronosGroup/glTF/blob/master/extensions/2.0/Khronos/KHR_draco_mesh_compression/README.md)

**Resumen:** el motor se rehace en el mismo script, con bisel, tornillos y texturas de fundición generadas por él, y suma 9 piezas puestas donde van en un 350 del 68 (alternador del lado del conductor, bomba de nafta del otro).
El manifiesto va a tener el orden real de desarme y el punto donde se atornilla el soporte, para que la vista Motor y el interior se enganchen sin tocar mis archivos.
