# Investigación · Detalle a lo loco + vista «Motor» que se separa y anda (21/10/2026, segunda vuelta)

**En una línea:** el salto de calidad gratis sale de **modelar mejor en Blender** (bordes redondeados,
formas reales de cada pieza, tornillos, nervaduras, mangueras con abrazaderas) + **texturas libres
CC0** (hierro fundido, aluminio, goma, pintura con desgaste) + una **vista Motor aparte** que carga el
motor pesado solo cuando lo pedís. «Prenderlo» se puede de dos maneras: solo lo de afuera (poleas,
correas, ventilador, vibración, chispas) o **en corte**, viendo pistones, bielas, cigüeñal y válvulas
moviéndose de verdad, en sincronía.

## Qué tiene hoy (lo miré de cerca)
- Las piezas del motor son cajas y cilindros con aristas vivas, sin tornillos, sin texturas, sin
  nervaduras ni letras. Por eso se ven «cuadradas».
- La carrocería tiene la forma general pero le faltan terminaciones: bordes suaves, juntas entre
  paneles, molduras, burletes, detalle en llantas y cubiertas.
- Blender portátil **no está** en la carpeta (quedó en la copia del multi-agente): hay que volver a
  bajarlo (~400 MB, gratis).

## Proyectos parecidos
- Los demos de «V8 interactivo con vista explotada» y «motor a reacción explotado» hechos con Claude +
  Three.js tienen: botón Explotar, etiquetas, descripción al pasar el mouse, y el motor **andando**
  (pistones y cigüeñal sincronizados). Están hechos con geometría generada por código: el detalle sale
  de muchas piezas chicas bien formadas, no de un modelo descargado.
- El avión de referencia: el detalle impresiona por **cantidad de piezas reales** (remaches, paneles,
  tornillos) + materiales bien hechos + animación de armado.

## Cómo se hace hoy el detalle «hard surface» (piezas mecánicas)
- **Bisel** (bevel) en todas las aristas + **normales ponderadas** (weighted normal): es lo que más
  saca el aspecto de «caja de plástico». Se hace por script.
- **Subdivisión** solo en piezas fundidas y redondeadas (múltiples, carter, tapas).
- **Tornillos y bulones repetidos** sobre bordes (como hacen BoltGen o Procedural Bolts), por script.
- **Curvas** para mangueras, cables de bujías con sus capuchones y abrazaderas.
- **Texturas PBR CC0** (Poly Haven, ambientCG): libres y gratis, sin pedir crédito. Hierro fundido
  áspero, aluminio, cromo, goma, pintura naranja con un poco de desgaste.

## Opciones para el motor detallado
| Opción | A favor | En contra |
|---|---|---|
| **A. Lo modelo yo, pieza por pieza, mucho más fino (recomendada)** | Gratis; queda fiel a un 350 del 68 (no a uno moderno); cada pieza sale separada, con nombre y lista para animar; misma onda que el auto | Mucho trabajo (lo hacemos de a tandas, varios agentes) |
| B. Partir de un SBC 350 gratis de Sketchfab (116.000 triángulos, muy detallado) | Mucho detalle de entrada | Licencia **no comercial** con crédito obligatorio; trae piezas de **otros años** (distribuidor HEI de 1974+, headers largos, caja TH400); no se sabe si viene separado; mezcla estilos |
| C. Generarlo con IA (Hunyuan3D, gratis) | Rápido para formas orgánicas | Necesita placa NVIDIA (tu PC tiene AMD); en piezas mecánicas queda blando y deforme; sale de un bloque, no se separa. **Descartada** |

## «Prender el motor»: lo posible
- **Por afuera (simple):** vibración en ralentí, poleas y correas girando, ventilador, chispazos en
  los cables, un tacómetro, botón «Acelerar».
- **En corte (lo más impresionante):** el bloque se vuelve transparente o se corta a la mitad y se ve
  adentro: cigüeñal, 8 bielas y pistones, árbol de levas, botadores, balancines y válvulas, todo en
  sincronía (orden de encendido real del small block: 1-8-4-3-6-5-7-2), con colores para los 4 tiempos.
  Esto suma piezas internas, que antes habíamos dejado afuera.
- **Sonido:** se puede sintetizar en el navegador (sin archivos ni licencias) o usar una grabación
  libre. El sintetizado suena «a juego», no a grabación real.

## Lo que NO es posible (o no conviene)
- Calidad de película (render fotográfico) **en tiempo real en el celular**: la vista se puede
  acercar mucho, pero un render de Blender de varios minutos por cuadro no se puede girar en vivo.
- Simular la física del motor de verdad: es una **animación fiel**, no un simulador.
- Que sea **el** motor de tu amigo sin fotos: será un 350 del 68 bien hecho.

## Peso y velocidad
- Más detalle = más peso. Solución: la vista del auto sigue liviana y el **motor detallado se baja
  recién cuando tocás «Motor»** (Draco para la forma; texturas chicas en WebP/KTX2). Meta: abrir la
  vista Motor en 2–4 s en el celular.

## Qué necesita Tomás
- Permiso para volver a bajar Blender portátil (~400 MB, gratis).
- Nada pago. Las texturas CC0 no piden cuenta.

## Fuentes
- [SBC V8 Engine en Sketchfab (licencia CC BY-NC, 116k triángulos)](https://sketchfab.com/3d-models/sbc-v8-engine-9bdb8ebcdfaa4a5e9708bc77e3c78709)
- [Prompt «V8 interactivo con vista explotada» (Claude + Three.js)](https://www.tripo3d.ai/3d-prompts/v8-car-engine-interactive-3d-exploded-view) · [Motor a reacción explotado](https://www.tripo3d.ai/3d-prompts/jet-engine-interactive-3d-exploded-view)
- [Visor de avión generado con un script de Blender + Three.js](https://github.com/Danhayasen/ccc/pull/1)
- [Bevel y normales en Python: bug y cuidados (Blender)](https://developer.blender.org/T58113) · [Normales ponderadas](https://superhivemarket.com/products/weighted-normals-node) · [BoltGen](https://superhivemarket.com/products/geometry-nodes-rivetbolt-generator)
- [Texturas y HDRIs gratis 2026: Poly Haven y ambientCG son CC0](https://app.cinevva.com/guides/free-textures-hdris-materials)
- [Hunyuan3D 2.1 local: requisitos y límites](https://www.tspi.at/2026/05/01/opensource3dassets.html)
- [Small block Chevrolet, primera generación (Wikipedia)](https://en.wikipedia.org/wiki/Chevrolet_small-block_engine_(first-_and_second-generation))

---

# Investigación · Camaro SS en 3D, pieza por pieza (21/10/2026)

**En una línea:** un visor 3D en el navegador (Three.js) donde el Camaro se gira, se abre el capot y
cada pieza se toca para ver qué es y qué hace; la carrocería conviene armarla en **Blender** (gratis,
sin prueba: es libre) con scripts, o partir de un modelo comprado, y el motor modelarlo nosotros pieza
por pieza.

## Proyectos parecidos
- El "avión que se arma" que nombra Tomás es del tipo **vista explotada**: cada pieza es un objeto con
  nombre, guarda su lugar armado y una dirección para "separarse"; un control las lleva y las trae, y al
  tocar una (raycasting = detectar qué pieza está bajo el dedo) se resalta y muestra su ficha.
- *PC Anatomy* (foro de Three.js): explorador 3D de una PC que separa componentes con movimientos de
  cámara. Mismo concepto, buen modelo de interfaz.
- Visores con modo "armar paso a paso" (anterior/siguiente) además de "separar todo".

## Cómo identificar el modelo exacto (1967, 1968 o 1969)
| Señal | 1967 | 1968 | 1969 |
|---|---|---|---|
| Ventilete (vidrio triangular adelante de la puerta) | **Sí** | No | No |
| Luces de posición en los costados | No | Grandes, bajas adelante | Finas, más altas |
| "Branquias" falsas atrás de la puerta trasera y líneas marcadas desde las ruedas | No | No | **Sí** |
| Tapa de nafta | Panel trasero, entre las luces | Panel trasero, entre las luces | **Abajo del paragolpes, detrás de la patente** |
| Luces traseras (no RS) | 2 por lado | 2 por lado | 3 secciones por lado |
| Parrilla | Toda negra | Con molduras plateadas | Con punta en el centro |
| Emblema SS | Parrilla + guardabarros delantero | Parrilla + guardabarros trasero | Parrilla + guardabarros trasero |
| Franja SS | "Bumblebee" cruzando el frente | Bumblebee | "Hockey stick" en el costado (no cruza el frente) |
| Apoyacabezas | Opcional (rarísimo) | Opcional (rarísimo) | **De serie** desde 1/1/1969 |
| Cinturones | Solo de cintura (los de hombro eran opcionales) | Solo cintura hasta dic/1967; de hombro obligatorios en coupés desde 1/1/1968 | Cintura + hombro |
| Capot SS | Con 2 "rejillas" decorativas | Rejillas fundidas (cromadas) | Igual que 68 |

Lo que contó Tomás (sin apoyacabezas, cinturón solo de cintura) apunta a un **1967 o un 1968 temprano**,
pero el interior está tocado, así que lo que más define es la carrocería: **ventilete, luces laterales y
tapa de nafta**. Con 4 fotos (frente, costado, atrás, motor) se cierra seguro. Si tiene la chapa de VIN
(en el parante de la puerta en 67-68, en el tablero en 69), mejor.

La "turbina adentro del motor" puede ser: un **compresor (blower) arriba del motor** que sale por el capot,
un **turbo**, o el **filtro de aire redondo cromado** que muchos confunden con una turbina. Cambia
mucho el modelo: hay que preguntarlo (o verlo en una foto).

## Cómo se hace hoy
- **Visor:** Three.js (librería 3D para la web, gratis) con un archivo `.glb` (el formato estándar de
  modelos 3D para la web). Controles para girar/zoom, piezas con nombre, fichas al tocar, capot y
  puertas que se abren con animación.
- **Modelado:** Blender es **gratis y libre** (no hay prueba, es para siempre). Se puede manejar por
  scripts de Python sin abrir la ventana (`blender -b -P script.py`) y exportar `.glb`. Hay versión
  "portable" (un .zip) que se puede dejar dentro de la carpeta del proyecto, así no se instala nada en
  la PC.
- **Modelos ya hechos:** hay Camaro 1967-69 en CGTrader, TurboSquid y 3DCADBrowser (≈ USD 20–80, con
  licencia para usar). La mayoría trae la carrocería muy bien hecha pero el motor apenas insinuado o en
  un solo bloque.

## Opciones para la carrocería
| Opción | A favor | En contra |
|---|---|---|
| **Blender por scripts, modelado por mí (recomendada si no querés gastar)** | Gratis; todo con nombre y separable desde el arranque; lo adaptamos 100 % al auto de tu amigo | La forma de la chapa es lo más difícil: va a quedar muy parecida, pero no idéntica a un escaneo |
| Comprar un modelo bueno (≈ USD 20–80) y adaptarlo | La carrocería queda casi perfecta | Cuesta plata; hay que revisar la licencia; casi nunca trae el motor por piezas (ese lo hago igual) |
| Todo a mano en código Three.js, sin Blender | Nada para bajar | Menos suave y menos realista que Blender: no llega al "perfecto" que pedís |

El **motor** se modela pieza por pieza en las tres opciones (block, tapas de válvulas, múltiples,
carburador, compresor/filtro, alternador, bomba de agua, radiador, distribuidor y cables, etc.).

## Limitaciones y seguridad
- "Perfecto" sin escanear el auto real tiene un límite: se logra con **fotos de referencia del auto de
  tu amigo** + las medidas reales del Camaro (planos de la época). Cuantas más fotos, más fiel.
- Un modelo con mucho detalle pesa: hay que comprimirlo (Draco/meshopt) para que abra rápido en el celular.
- Todo es local, sin cuentas ni claves. Nada sensible.

## Errores comunes (y cómo los evitamos)
- Modelo en un solo bloque que no se puede separar → cada pieza es un objeto con nombre desde el principio.
- Fichas técnicas inventadas → los textos de cada pieza salen de fuentes de restauración (camaros.org).
- Mezclar años (luces del 69 en un 67) → primero cerramos el año con fotos.

## Qué necesita Tomás (va en la ronda 1)
- **Fotos del auto de tu amigo** (frente, costado, atrás, motor con el capot abierto, interior, y si se
  puede la chapa del VIN). Es lo que más define el "ese mismo auto".
- **Permiso para bajar Blender portable** (≈ 350 MB, gratis) dentro de la carpeta del proyecto.
- Si se elige comprar la carrocería: una cuenta en la tienda y pagar el modelo (≈ USD 20–80).

## Fuentes
- [At A Glance: diferencias Camaro 1967-69 (Street Muscle)](https://www.streetmusclemag.com/features/car-features/at-a-glance-how-to-spot-differences-in-first-gen-camaro-1967-69/)
- [Chevrolet Camaro primera generación (Wikipedia)](https://en.wikipedia.org/wiki/Chevrolet_Camaro_(first_generation))
- [Camaro Research Group: cinturones](https://camaros.org/seatbelt.shtml) · [apoyacabezas](https://camaros.org/headrest.shtml) · [capots](https://camaros.org/hoods.shtml) · [modelos](https://camaros.org/model.shtml)
- [Blender a glTF por línea de comando (Khronos)](https://github.khronos.org/glTF-Tutorials/BlenderGltfConverter/) · [Exportar a GLB desde la consola](https://til.jakelazaroff.com/blender/export-a-blender-file-to-glb-from-the-command-line/)
- [PC Anatomy, explorador 3D en Three.js](https://discourse.threejs.org/t/pc-anatomy-interactive-3d-pc-hardware-explorer-built-with-three-js/94612.md)
- [Modelo 1969 Camaro SS en CGTrader (referencia de precio)](https://www.cgtrader.com/3d-models/car/luxury-car/chevrolet-camaro-ss-1969-8346fe38-a1e4-410a-b2de-9300f9d29c7a)
