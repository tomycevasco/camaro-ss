# Investigación · Correcciones de forma del Camaro SS 1968 (Agente 3, 21/10/2026)

**Para quién:** el agente de carrocería (tanda 2), que corrige `blender/carroceria.py` y `blender/exterior.py`.
**Qué hay acá:** qué está mal hoy en el modelo, a qué medida pasa y de dónde sale cada dato. Todo en
metros y con los ejes de los scripts: **X = ancho** (+X = lado izquierdo), **Y = largo** (el frente
mira a **−Y**), **Z = arriba**, origen en el piso y en el medio entre los ejes. Eje delantero
`y = −1,371`, eje trasero `y = +1,371`.

**Cómo leer las marcas:**
- **[AMA]** = planilla oficial de Chevrolet del Camaro 1968 (dato de fábrica, manda).
- **[restauración]** = camaros.org (Camaro Research Group) o catálogos de piezas de restauración.
- **[foto]** = medido o mirado en fotos de autos 68 reales (Wikimedia Commons). Son aproximados
  (perspectiva): ±3 cm. Si una foto choca con un dato [AMA], gana el [AMA].
- **[decisión de Tomás]** = está en `CLAUDE.md`. No se cambia aunque el auto de fábrica sea distinto.

> Tomás dijo (21/10) que iba a pasar fotos de Google del auto. **A este agente no le llegaron**: si
> te llegan a vos, mandan sobre las fotos de Commons de este documento. Lo que marcó clarito: **la
> trompa quedó demasiado cuadrada y no se parece**. Por eso la sección 1 es la trompa.

---

## 0. Lo más importante, en orden

1. **La trompa** (sección 1): hoy el frente es una tapa plana con una punta de 2 cm y un marco de
   10 cm alrededor del hueco. El 68 tiene **trompa en punta (en V vista de arriba), de ~11 cm**, puntas
   de guardabarros redondeadas y un hueco de parrilla que ocupa casi todo el frente.
2. **Paragolpes delantero y trasero ~12 cm y ~5 cm más arriba** de lo que están [AMA].
3. **Parabrisas y luneta más cortos y más parados; techo más largo** (hoy el techo mide 0,65 m de
   largo y la luneta corre 0,80 m: los vidrios reales miden 22″ y 20″) [restauración].
4. **Luces de estacionamiento adentro de la parrilla**, al lado de los faros (no abajo del paragolpes) [restauración + foto].
5. **Parrilla negra** (SS), **luces traseras sin rayas cromadas**, con la mitad de adentro blanca
   (marcha atrás) entera [foto + restauración].
6. Trocha y zócalos según la planilla de fábrica (sección 2).

---

## 1. La trompa y el frente (pedido especial de Tomás)

### 1.1 Por qué hoy se ve cuadrada (en el código)
- `malla_chapa()`: el frente termina en **una cara plana** (`frente = bm.faces.new(filas[0])`) y la
  punta en V es de solo **0,022 m** (`y -= 0.022 * (1 - (x/0.92)**2) * t`). Vista de arriba es casi
  una regla.
- `inset_region(..., thickness=0.10)`: deja un **marco de chapa de 10 cm parejo** alrededor del hueco
  → se ve una caja con un agujero adentro. En el 68 el marco es finito a los costados y arriba, y abajo
  no hay chapa: el hueco se apoya directo sobre el paragolpes.
- Las puntas de los guardabarros (las «esquinas» de la trompa) quedan en ángulo, sin redondeo.

### 1.2 Cómo es de verdad (mirando un 68 SS de 3/4 adelante)
Fotos de referencia: el SS 350 dorado de 3/4 y el SS celeste de frente (fuentes al final).

- **Vista de arriba: una proa en V.** El centro de la parrilla es lo que más sale; de ahí el frente se
  va para atrás en línea casi recta hasta los faros y después dobla redondeado hacia el costado.
  - Centro de la parrilla (y del capot): `y ≈ −2,22` (como hoy).
  - A la altura del centro de los faros (`x = ±0,62`): **~0,11 m más atrás** → `y ≈ −2,11` [foto].
  - Punta del guardabarros (donde el frente dobla al costado, `x ≈ ±0,86`): **~0,16 m atrás** del
    centro → `y ≈ −2,06`, con un **radio de ~0,12 m** de frente a costado (nada de esquina viva) [foto].
  - Propuesta para el script: que el retroceso dependa de `x`, por ejemplo
    `retroceso(x) = 0,11 · (|x| / 0,62) ** 1,4` hasta `|x| = 0,62`, y de ahí al costado un cuarto
    de círculo de radio 0,12. Reemplaza al `0.022 * (1 - (x/0.92)**2)`. El capot, la parrilla y el
    paragolpes siguen esa misma V.
- **Vista de costado: la cara del frente apenas inclinada para atrás hacia abajo** (lo de arriba sale
  más). El borde de arriba (capot + panel de arriba de la parrilla) queda ~4 cm por delante del borde
  de abajo del hueco. El `+0.05` que ya hay está bien de idea; que valga solo de la mitad de la
  parrilla para abajo, no en toda la cara.
- **El hueco de la parrilla es un «lazo» que ocupa casi todo el frente** [foto]:
  - Ancho: de punta a punta, **faros incluidos**: `x` hasta **±0,80**. Los faros van en las
    puntas, adentro del mismo hueco (no en chapa aparte).
  - Alto: de **z ≈ 0,55** (justo arriba del paragolpes, sin chapa en el medio) a **z ≈ 0,79**.
    Coincide con la parrilla de reposición de 10″ de alto [restauración].
  - Marco de chapa: **arriba ~0,03–0,04 m** (el «panel de arriba», color carrocería), **a los
    costados ~0,04 m** (la punta del guardabarros que abraza el faro). **Abajo, nada**: el paragolpes
    cierra el hueco. Hoy son 10 cm en todo el contorno: es lo que más «encaja» la cara.
  - El borde del hueco es **redondeado (radio ~0,02 m)**, como un labio que se mete hacia adentro;
    las esquinas del hueco, alrededor de cada faro, son **redondas (radio ~0,10 m)** siguiendo el aro.
  - Profundidad: la parrilla queda **hundida ~6–8 cm** detrás del labio; los faros, ~3 cm (asoman
    más que la parrilla).
- **El capot de adelante**: el borde delantero también en V (sigue la proa), apenas redondeado hacia
  abajo (radio ~0,03), a **z ≈ 0,80** en el centro. El lomo SS arranca ~0,20 m detrás del borde y
  **termina adelante en punta redondeada**, no cortado en recto.
- **Los guardabarros de adelante**: la parte de arriba es un **hombro redondeado** que baja hacia el
  costado; la línea marcada del costado (`LINEA_Z`) **nace arriba del faro**, a la altura del borde de
  arriba del hueco (z ≈ 0,72–0,75), y corre recta hacia atrás. Visto de 3/4 es lo que le da la
  «ceja» al faro.

### 1.3 Lo que va en el frente (piezas de `exterior.py`)
| Pieza | Cómo es en el 68 SS | Hoy | Fuente |
|---|---|---|---|
| Parrilla | **Negra** (los SS), plástico, barras horizontales finas con nervios verticales, y una **moldura brillante arriba y abajo** del hueco. Los no SS eran plateados (argent). | Negra con filo plateado en cada barra: sacar el filo plateado de las barras; dejar solo las dos molduras | [restauración] AMD/OER/Eckler's, [foto] |
| Faros | Redondos de 7″ (Ø 0,178 m), sellados, en un **marco de aluminio pulido con el interior negro mate**. Centro en `x = ±0,62`, `z ≈ 0,67` | Bien de tamaño; subirlos con el hueco | [restauración] Camaro Central, OER |
| Luces de estacionamiento | **Rectangulares de puntas redondas, adentro de la parrilla**, una a cada lado, **pegadas por dentro de cada faro**. Lente transparente con lamparita ámbar (prendida da ámbar). Medida aprox. 0,13 × 0,05 m, centro `x ≈ ±0,44`, `z ≈ 0,67` (a la altura del centro del faro), con marco cromado | Hoy ovaladas, en el faldón **abajo** del paragolpes (eso es del RS y del 69): **mover a la parrilla** | [restauración] Champion Cooling, SS396.com, Wikipedia; [foto] |
| Emblema SS de la parrilla | Letras «SS» cromadas sobre fondo negro, en el medio de la parrilla | Hoy fondo rojo: pasar a **negro** | [foto] |
| Paragolpes delantero | Ver sección 4 | Muy bajo | [AMA] |
| Faldón de abajo | Chapa color carrocería debajo del paragolpes, de lado a lado, que se mete hacia atrás; **lisa, sin huecos de luces** (los huecos son del RS). Borde de abajo a **z ≥ 0,30** (ángulo de ataque 22° [AMA]) | Bajar el borde no; subir todo con el paragolpes | [AMA], [restauración] |
| Patente | Centrada, debajo del paragolpes, sobre el faldón | — | [foto] |

---

## 2. Medidas oficiales (planilla AMA de Chevrolet, Camaro 1968, emitida 15/10/1967)
Sport Coupe. Las alturas «al piso» son con 2 personas adelante y 3 atrás (auto cargado); el alto
total es a peso de diseño.

| Medida (código AMA) | Pulgadas | Metros | Hoy en el script | Qué hacer |
|---|---|---|---|---|
| Entre ejes (L101) | 108,0 | 2,743 | 2,742 | ok |
| Largo total (L103) | 184,6 | 4,689 | ~4,69 | ok |
| Voladizo delantero (L104), eje → punta del paragolpes | 36,6 | 0,930 | — | punta del paragolpes en `y = −2,301` |
| Voladizo trasero (L105), eje → punta del paragolpes | 40,0 | 1,016 | — | punta del paragolpes en `y = +2,387` |
| Ancho máximo (W103) | 72,3 | 1,836 | 1,841 | cadera `LADO_X` máx. **0,918** (hoy 0,920) |
| **Trocha delantera (W101)** | 59,6 | **1,514** | 1,499 | **cambiar** `TROCHA_DEL = 1.514` |
| **Trocha trasera (W102)** | 59,5 | **1,511** | 1,496 | **cambiar** `TROCHA_TRAS = 1.511` |
| Alto total (H101) | 50,9 | 1,293 | 1,295 | ok |
| Altura del «cowl» (base del parabrisas en el medio) (H114) | 35,3 | 0,897 | ~0,89 | ok |
| **Zócalo al piso, adelante (H112)** | 7,1 | **0,180** | 0,22 | **bajar** |
| **Zócalo al piso, atrás (H111)** | 8,1 | **0,206** | 0,22 | bajar un poco |
| **Paragolpes al piso, adelante (H102)** (punto más bajo) | 17,2 | **0,437** | 0,318 | **subir ~12 cm** |
| **Paragolpes al piso, atrás (H104)** (punto más bajo) | 17,0 | **0,432** | 0,378 | **subir ~5 cm** |
| Altura del borde del baúl (H195, borde de abajo de la boca) | 30,0 | 0,762 | — | ver sección 6 |
| Ángulo de ataque / de salida / panza | 22° / 19° / 13° | — | — | sirve para chequear faldones |
| Llanta (de serie) | 14 × 6, 5 tuercas, círculo 4,75″ | Ø 0,356 | ok | ok |
| Cubierta | F70-14 diagonal, 815 vueltas/milla | radio rodando ≈ 0,314 | 0,33 | ok (0,33 es sin carga) |

**Detalle del zócalo:** de fábrica el 68 va **apenas «de trompa»**: el zócalo está 2,6 cm más bajo
adelante que atrás. Proponer `FONDO_Z` en el tramo de las puertas de **0,185** (adelante, `y ≈ −0,95`)
a **0,205** (atrás, `y ≈ +0,95`). Es la postura típica del auto; queda «plantado».

---

## 3. Techo, parabrisas y luneta (la silueta de costado)

**Datos:** parabrisas del coupé **22″ × 62″** (0,56 × 1,57 m; medido por un dueño: 58½″ abajo y 49½″
arriba de ancho); luneta del coupé **20″ × 48″** (0,51 × 1,22 m) [restauración]. Es un **hardtop**:
sin parante del medio, vidrios de puerta sin marco, y la ventanilla de atrás baja [restauración].
Sin ventilete (es 68) [decisión de Tomás + todas las fuentes].

**Qué pasa hoy:** `CUBRE_Y = −0,60`, `TECHO_Y = (0,05, 0,70)`, `LUNETA_Y = 1,50`. El parabrisas corre
0,65 m en horizontal (≈ 0,73 m de vidrio) y la luneta 0,80 m (≈ 0,85 m de vidrio): **los dos son
~30–60 % más largos que los reales**, y el techo, que en el 68 es largo y casi plano, queda corto.
Por eso la cabina se ve «burbuja».

**Propuesta (centro del auto):**
| | Hoy | Propuesta | Cuenta |
|---|---|---|---|
| Base del parabrisas (`CUBRE_Y`) | −0,60 | **−0,62** | — |
| Techo, adelante (`TECHO_Y[0]`) | 0,05 | **−0,20** | sube 0,34 m en 0,42 m → vidrio ≈ 0,54 m ✔ 22″ |
| Techo, atrás (`TECHO_Y[1]`) | 0,70 | **1,02** | techo de ~1,22 m, casi plano, punto más alto ~0,35 |
| Base de la luneta (`LUNETA_Y`) | 1,50 | **1,50** | baja ~0,29 m en 0,48 m → vidrio ≈ 0,56 m ✔ 20″ + molduras |

En el costado (foto, ±3 cm): la puerta va de **`y ≈ −0,68` a `y ≈ +0,64`** (hoy −0,62 a 0,53: la
puerta real es ~1,3 m, más larga); el borde de atrás de la ventanilla trasera, abajo, en `y ≈ 0,99`
(como hoy). El canto del techo (la canaleta) baja al parante trasero antes que el centro del techo:
por eso en el costado el techo «termina» en `y ≈ 0,89`. El parante trasero es ancho y se estira en
una «aleta» que muere sobre el guardabarros trasero, cerca de la base de la luneta.

Al mover estas constantes cambian los huecos de vidrio, las puertas (`PUERTA_Y`), la bisagra y los
`enganche_*`: `exterior.py` toma las puertas y los vidrios de `carroceria.py`, así que se acomodan
solos si se usan las constantes (no números sueltos).

---

## 4. Paragolpes

**Delantero** [AMA + foto]
- Una **cuchilla cromada finita** de **~0,11 m de alto**: de **z = 0,437** (abajo) a **~0,55** (arriba,
  donde se apoya la parrilla). Hoy su centro está en 0,37 → pasar el centro a **~0,49**.
- Vista de arriba **sigue la V de la trompa**; la punta del medio en **`y = −2,301`**.
- En las puntas **dobla redondeado (radio ~0,12) y vuelve por el costado del guardabarros ~0,25–0,30 m**,
  terminando unos 0,15 m antes del arco de la rueda. De 3/4 se ve el extremo «envolviendo» la esquina.
- Perfil: frente apenas abombado, el borde de arriba enrollado hacia adelante (un labio) y el de abajo
  metido hacia atrás. El perfil de hoy (`PERFIL_PARAGOLPES`, 0,11 de alto) está bien.
- 1968: **sin topes (bumper guards)**; los chicos son del 67 y del 69 [restauración, camaros.org].

**Trasero** [AMA + foto]
- Misma cuchilla, de **z = 0,432** a **~0,53**; centro hoy 0,43 → **~0,485**. Punta en **`y = +2,387`**.
- Recto de lado a lado, justo debajo de las luces traseras, y en las puntas **envuelve hasta el
  costado** (termina ~0,25 m detrás del arco de la rueda trasera).
- Debajo: faldón color carrocería con la **patente en el medio**.

---

## 5. Costados: líneas, luces y emblemas

- **Botella de Coca** (vista de arriba): angosto en la puerta, ancho en la cadera. Con el ancho
  máximo [AMA] de 1,836: cadera **0,918** de medio ancho (hoy 0,920). El resto de `LADO_X` está bien.
- **Línea marcada**: nace arriba del faro (sección 1), va recta y apenas bajando por la puerta, y
  **sube sobre la rueda de atrás** (la cadera). Lo de `LINEA_Z` va bien de forma.
- **Arcos de rueda**: redondos, con un **labio enrollado** (pestaña de ~1,5 cm hacia adentro), **sin
  molduras** (las molduras de arcos eran del paquete opcional Z21 / del RS) [restauración].
- **Luz de posición delantera (costado)**: rectangular, marco cromado, lente **transparente con
  lamparita ámbar** de fábrica [restauración: OER K70 «Front Side Marker Lens; Clear»]. **[decisión
  de Tomás]: ámbar** → lente ámbar clarito (que se note que es transparente-ámbar). Va **baja, justo
  detrás de la punta del paragolpes**, adelante del arco: centro **`y ≈ −1,92`, `z ≈ 0,50`** (hoy
  −2,00 / 0,425: subirla con el paragolpes). Medida ~0,10 × 0,035 m [foto].
- **Luz de posición trasera**: igual, **roja**, detrás de la rueda trasera: centro **`y ≈ +1,95`,
  `z ≈ 0,52`** [restauración: OER K71; foto].
- **Emblemas** [restauración: kit OER R1073 «1968 Camaro SS-350 … without RS»; foto]:
  - **«350»** cromado en cada guardabarros delantero, **adelante de la rueda, arriba de la luz de
    posición** (`y ≈ −1,85`, `z ≈ 0,60`). Hoy está detrás de la rueda, junto al SS: **moverlo**.
  - **«Camaro»** en letra cursiva + **«SS»** abajo, en cada guardabarros delantero, **detrás de la
    rueda, cerca de la puerta** (`y ≈ −0,85`, `z ≈ 0,62` y `0,57`). Hoy falta el «Camaro».
- **Manijas**: de botón, cromadas, en la parte de arriba de la puerta, cerca del borde de atrás [foto].
- **Espejo**: rectangular cromado, en la puerta del conductor (izquierda), adelante y abajo de la
  ventanilla [restauración: camaros.org, pieza 3914753 «68-69 … rectangular»]. El derecho era opcional.

---

## 6. La cola (vista de atrás)
Foto de referencia: SS 350 dorado, de atrás (fuente al final).

- **Panel de atrás pintado negro** entre las luces (en el auto de Tomás todo es negro igual).
- **Luces traseras del 68**: cada lado un **marco cromado rectangular** (~0,52 × 0,14 m, centro
  `x ≈ ±0,55`) partido en **dos ventanas**: la de **afuera roja** y la de **adentro entera blanca**
  (marcha atrás) [foto + restauración: OER 5959939 «Back Up Lens; Except RS»; Champion Cooling]. Cada
  lente queda hundido en un fondo **negro mate** dentro del marco. **Sin rayas cromadas** sobre el
  vidrio. Hoy: la mitad de adentro es roja con una tira blanca abajo y hay 3 rayas cromadas →
  **corregir**.
- Altura: el marco va **apoyado justo arriba del paragolpes**: de **z ≈ 0,54 a 0,69**, centro ~0,615
  (hoy 0,705: bajarlo). Arriba queda el borde del panel y la boca del baúl (**0,762** [AMA]).
- **Tapa de nafta** en el centro del panel: **emblema redondo «SS»** (Ø ~0,105 m, borde cromado,
  letras cromadas sobre fondo negro) [foto]. Hoy es un rectángulo redondeado: **pasarla a círculo**.
  Arriba de la tapa, la **cerradura redonda del baúl** (Ø ~0,025 m) [foto].
- **Tapa del baúl**: corta (~0,62 m de largo, ~1,40 m de ancho) [restauración: caja de la tapa de
  reposición 58″ × 27″] con un **borde de atrás apenas levantado**. Sin alerón (el D80 era opcional).

---

## 7. Capot SS
- [decisión de Tomás]: **lomo central sin rejillas**. Dato de fábrica, por si algún día se quiere: los
  SS 350 desde noviembre de 1967 llevaban **dos rejillas cromadas que imitan 4 trompetas de
  carburador** cada una, atrás del lomo, cerca del parabrisas [camaros.org, hoods]. **No ponerlas.**
- Lomo: ~0,56–0,64 m de ancho y ~2,5 cm de alto (como hoy, `lomo()` y `LOMO_ALTO`), con los costados
  firmes y la punta delantera redondeada (sección 1.2).
- Bisagra atrás, abre desde adelante (ya está así).

---

## 8. Molduras y terminaciones
Un SS 68 sin el paquete opcional Z21 [restauración: camaros.org foro, kits OER]:

| Terminación | ¿Va? | Cómo |
|---|---|---|
| Moldura del parabrisas | **Sí** | acero inoxidable pulido, ~2 cm, todo alrededor |
| Moldura de la luneta | **Sí** | igual, en 5 partes (se puede hacer una sola) |
| Moldura de la canaleta del techo | No (era Z21) | canaleta pintada, marcada como un pliegue fino sobre la puerta |
| Molduras de los arcos de rueda | No (Z21/RS) | — |
| Moldura ancha de la cintura (debajo de los vidrios) | No (Z21) | solo un **burlete negro** fino (el «felpudo» del vidrio) |
| Moldura de arriba de la puerta | No (era opcional en 1968) | — |
| Burletes | **Sí** | negro mate, 6–8 mm, en el contorno de puertas, capot (atrás) y baúl; se ven al abrir |
| Juntas entre paneles | **Sí** | ranura de 4–5 mm (hoy 5 mm), oscura por dentro |
| Franjas (D90 / D91) | **No** [decisión de Tomás] | de fábrica el SS desde enero/68 traía la D90 (se podía pedir sin) |
| Vidrios | **Sí** | tintados de verde claro «Soft-Ray» (si era con tinte); parabrisas con franja sombreada arriba |

---

## 9. Lo que NO hay que tocar
- Las bisagras (orígenes) de capot, puertas y baúl, y los nombres `id` de las piezas (los usa la página).
- Los `enganche_*` (los usan el motor y las otras piezas): si se mueve algo, se mueve el enganche con
  la constante, no a mano.
- Las decisiones de Tomás: negro entero, sin franjas, sin rejillas en el capot, faros a la vista
  (no RS), luces de posición ámbar, llantas Rally.

---

## Fuentes
**Dato de fábrica**
- [Planilla AMA de Chevrolet, Camaro 1968 (emitida 15/10/1967), pág. 1, 2, 18 y 26 (definiciones)](https://over-drive-magazine.com/wp-content/uploads/2024/03/1968-CHEVROLET-Camaro-396-CIDV8-L34-L78-L89-1-28.pdf)

**Restauración**
- [camaros.org · 1968 Model ID](https://www.camaros.org/diffs68.shtml) · [Exterior (franjas, capots)](https://www.camaros.org/exterior.shtml) · [Capots 67-69](https://camaros.org/hoods.shtml) · [Vidrios](https://www.camaros.org/glass.shtml) · [Opciones](https://www.camaros.org/options.shtml)
- [camaros.org foro · Z21 Style Trim (molduras)](https://www.camaros.org/forum/index.php?msg=35304) · [espejo rectangular 68-69](https://www.camaros.org/forum/index.php?msg=15880) · [tapas de llanta 68](https://www.camaros.org/forum/index.php?msg=5079)
- [Champion Cooling · Spotter's guide 1967-1969](https://blog.championcooling.com/2021/02/01/spotters-guide-identifying-the-1967-1969-camaro/) · [Chevy Hardcore · diferencias 67-68-69](https://www.chevyhardcore.com/news/differences-within-a-generation-the-1967-1969-camaro) · [SS396.com · Camaro 1968](https://www.ss396.com/cars/1968-camaro/)
- [OER · luces de costado 1968](https://www.oerparts.com/shop/1968/chevrolet/camaro/parts/lighting/side-markers/) · [OER · lente de marcha atrás 68 (no RS)](https://www.oerparts.com/product/1968/chevrolet/camaro/parts/5959939.html) · [OER · kit de emblemas SS-350 68](https://www.oerparts.com/product/*r1073.html)
- [AMD · parrilla 68 estándar (43″ × 10″)](https://www.autometaldirect.com/grille---68-camaro---standard) · [Camaro Central · marco de faro 68](https://www.camarocentral.com/1968_Camaro_Standard_Grille_Headlight_Bezel_Right_p/gri-46.htm) · [OER · luneta 20″ × 48″](https://www.oerparts.com/product/bg3814c.html) · [Classic Industries · parabrisas coupé 22″ × 62″](https://help.classicindustries.com/en/what-are-the-dimensions-of-dw688y) · [OER · tapa del baúl 67-69](https://www.oerparts.com/product/152681.html)
- [Wikipedia · Camaro primera generación](https://en.wikipedia.org/wiki/Chevrolet_Camaro_(first_generation))

**Fotos (Wikimedia Commons)**
- [SS 350 dorado, 3/4 adelante](https://commons.wikimedia.org/wiki/File:1968_Chevrolet_Camaro_SS_350,_gold,_front_right_side,_Golden_Super_Cruise_2026-08-01.jpg) — la mejor para la trompa
- [SS celeste, frente](https://commons.wikimedia.org/wiki/File:1968_Chevrolet_Camaro_Coup%C3%A9_Front_hellblau.jpg) — parrilla negra, luces en la parrilla, paragolpes
- [SS 350 dorado, atrás](https://commons.wikimedia.org/wiki/File:1968_Chevrolet_Camaro_SS_350,_gold,_rear,_Golden_Super_Cruise_2026-08-01.jpg) — luces traseras, tapa de nafta
- [SS gris, costado izquierdo](https://commons.wikimedia.org/wiki/File:1968_Chevrolet_Camaro_SS,_slate_blue,_left_side,_Golden_Super_Cruise_2026-10-03.jpg) — proporciones (auto rebajado y con llantas no originales: solo largos, no alturas)

---
**Resumen:** la trompa se ve cuadrada porque el frente es una tapa plana con un marco grueso; el 68
tiene proa en V de ~11 cm, puntas redondeadas y un hueco de parrilla de punta a punta apoyado en el
paragolpes. Además, según la planilla de fábrica, los paragolpes van más arriba, la trocha es 1,514 /
1,511 y los zócalos más bajos; el parabrisas y la luneta son más cortos y el techo más largo; las luces
de estacionamiento van en la parrilla y las traseras tienen la mitad de adentro blanca, sin rayas.
