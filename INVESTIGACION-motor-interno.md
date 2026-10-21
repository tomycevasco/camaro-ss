# Investigación · el 350 por dentro y cómo suena

Para la parte 3 del plan (por adentro y en marcha) y para las fichas nuevas. El motor es el
**L48: V8 350 de 295 HP del Camaro SS 1968**. Lo que no se pudo confirmar para el 68 exacto está
marcado como **(general)** o **(sin confirmar)**. Fuentes numeradas al final [n].

## 1. La idea en dos líneas

Ocho pistones suben y bajan adentro del bloque y empujan, con las bielas, un cigüeñal que gira.
Un árbol de levas, que gira a la mitad de velocidad, abre y cierra las 16 válvulas en el momento justo,
y cada cilindro hace sus 4 tiempos: **admisión, compresión, explosión, escape**.

## 2. Medidas del L48 (las que sirven para el modelo)

| Dato | Pulgadas | Métrico | Fuente |
|---|---|---|---|
| Cilindrada | 350 pulg³ (349,8) | 5.733 cm³ (≈717 cm³ por cilindro) | [1] |
| Diámetro del cilindro (= del pistón) | 4,000 | 101,6 mm | [1][2] |
| Carrera (lo que sube y baja el pistón) | 3,48 | 88,4 mm → **radio de manivela 44,2 mm** | [1][2] |
| Largo de la biela (centro a centro) | 5,7 | 144,8 mm | [1][3] |
| Separación entre cilindros | 4,40 | 111,8 mm | [1] |
| Ángulo entre las dos filas | 90° | — | [1][6] |
| Bancadas del cigüeñal (apoyos) | 2,45 | 62,2 mm | [4] |
| Muñones de biela | 2,10 | 53,3 mm | [4] |
| Válvula de admisión | 1,94 | 49,3 mm | [5] |
| Válvula de escape | 1,50 | 38,1 mm | [5] |
| Cámara de combustión | — | ≈63 cm³ | [5] |
| Compresión | 10,25 : 1 | — | [2] |
| Potencia / par | 295 HP a 4.800 rpm · 380 lb-pie a 3.200 rpm | 515 N·m | [2] |

Dato lindo para la ficha: a 4.800 rpm cada pistón sube y baja **80 veces por segundo** y va, en
promedio, a unos **14 m/s** (50 km/h), frenando y arrancando en cada punta.

## 3. Las piezas de adentro

**Pistón** (8). De aluminio **(general)**, Ø 101,6 mm. Arriba lleva **3 aros**: dos de compresión
(sellan) y uno de aceite (limpia la pared) **(general)**. Un bulón (perno) lo une a la biela.
La forma exacta de la cabeza del pistón del L48 del 68 **(sin confirmar)**: para el modelo, cabeza
casi plana con dos rebajes chicos para las válvulas.

**Biela** (8). Acero forjado, 144,8 mm entre centros [3]. Arriba el ojo chico (bulón), abajo el ojo
grande con su tapa abulonada que abraza el muñón. **Dos bielas comparten cada muñón** (una de cada
fila), por eso la fila izquierda está un poquito más adelante que la derecha (en `motor.py`:
`CORRIDA_BANCADA`).

**Cigüeñal**. 1968 fue el primer año de los **«muñones grandes»** en todos los small block
(2,45″ y 2,10″); en 1968-69 el 350 venía **forjado o de hierro nodular** [4]. Tiene 5 bancadas
y 4 muñones **(general)** y es **«en cruz» (crossplane)**: visto de frente, los 4 muñones quedan a 90°
uno del otro, formando una cruz [6][7]. Contrapesos al lado de cada muñón.

**Árbol de levas**. Uno solo, en el medio de la V, arriba del cigüeñal; 16 levas (una por válvula).
Lo mueve una **cadena de distribución** [1] y gira a **la mitad de velocidad del cigüeñal** [8].
También mueve el distribuidor (que gira en sentido horario [9]) y la bomba de aceite **(general)**.

**Botadores, varillas y balancines** (16 de cada uno). Botadores **hidráulicos** [1] apoyados en las
levas; cada uno empuja una varilla larga que sube hasta la tapa de cilindros; ahí un **balancín de
chapa estampada** que bascula sobre una rótula atornillada a un espárrago [1][10] multiplica el
movimiento **1,5 veces** [10] y empuja la válvula hacia abajo. Todo eso queda **debajo de las tapas
de válvulas cromadas**.

**Válvulas y resortes** (16). Dos por cilindro: admisión (la grande, 49,3 mm) y escape (38,1 mm) [5].
El resorte la vuelve a cerrar. Orden en cada tapa, de adelante hacia atrás:
**E-A-A-E-E-A-A-E** (E = escape, A = admisión) **(general)**.

**Bujía** (8). Una por cilindro, del costado de afuera de cada tapa de cilindros.

## 4. El ciclo de 4 tiempos (lo que tiene que mostrar «Prender»)

Cada cilindro hace los 4 tiempos en **2 vueltas del cigüeñal (720°)** [8]:

| Tiempo | Pistón | Válvulas | Vueltas del cigüeñal |
|---|---|---|---|
| 1 · Admisión | baja | admisión abierta: entra aire y nafta | 0°–180° |
| 2 · Compresión | sube | las dos cerradas: aprieta la mezcla | 180°–360° |
| 3 · Explosión | baja empujado | las dos cerradas; salta la chispa arriba | 360°–540° |
| 4 · Escape | sube | escape abierta: salen los gases | 540°–720° |

Simplificación honesta para la animación: válvulas que abren justo en cada tiempo. En el motor
real abren un poco antes y cierran un poco después (y hay un instante con las dos abiertas, el
«cruce») [8]; no hace falta mostrarlo.

## 5. El orden de encendido 1-8-4-3-6-5-7-2 (para animarlo bien)

**Numeración** [9][11]: sentado en el auto, **fila izquierda (la del conductor) 1-3-5-7** y **fila
derecha 2-4-6-8**, de adelante hacia atrás. Visto **de frente** al motor, la fila impar queda a tu
**derecha**. En los ejes de `blender/motor.py` (+X = izquierda del conductor, el frente mira a −Y):
impares en +X, pares en −X, el 1 adelante (`CILINDRO_1_Y`).

**Sentido de giro**: el cigüeñal gira **en sentido horario mirado de frente** **(general)**.
En Blender eso es **positivo alrededor de +Y**. Al exportar a glTF, el +Y de Blender pasa a −Z,
así que en Three.js es **negativo en `rotation.z`** si la pieza no tiene giros propios
(**comprobarlo con una vuelta lenta**).

**Todos los small block de 1ª y 2ª generación** usan 1-8-4-3-6-5-7-2 [1][9]: salta una chispa
**cada 90°** de cigüeñal, 8 por cada 2 vueltas. Tabla lista para usar (θ = giro del cigüeñal; θ = 0
cuando el cilindro 1 está arriba de todo a punto de explotar):

| Cilindro | Fila | Explota en θ = | Muñón compartido |
|---|---|---|---|
| 1 | izq. | 0° | A (con el 2) |
| 8 | der. | 90° | D (con el 7) |
| 4 | der. | 180° | B (con el 3) |
| 3 | izq. | 270° | B |
| 6 | der. | 360° | C (con el 5) |
| 5 | izq. | 450° | C |
| 7 | izq. | 540° | D |
| 2 | der. | 630° | A |

Para cada cilindro: `local = (θ − explota) mod 720` → 0–180 explosión · 180–360 escape ·
360–540 admisión · 540–720 compresión.

**Ángulo de los muñones** (de adelante hacia atrás, girados en sentido horario respecto del A):
**A 0° · B 90° · C 270° · D 180°**. Los de las puntas (A y D) quedan opuestos y los del medio
(B y C) también: la cruz clásica [6][7]. Cuenta hecha: la tabla de arriba sale de estos ángulos con
filas a ±45° de la vertical, y cada cilindro par llega arriba 270° después que su compañero impar.

**Altura del pistón** (para moverlo sin que «patine»): con radio de manivela r = 44,2 mm, biela
l = 144,8 mm y α = ángulo entre el muñón y el eje de esa fila,
`distancia del centro del cigüeñal al bulón = r·cos α + √(l² − r²·sen² α)`.
Arriba de todo da 189 mm y abajo 100,6 mm (la diferencia es la carrera, 88,4 mm).

**Colores de los tiempos** (sugerencia, lo decide quien arma la animación): admisión azul,
compresión amarillo, explosión el naranja del proyecto (`--acento: #d9600b`), escape gris.

## 6. Cómo suena y por qué

- **El «burbujeo» del V8 americano** sale del cigüeñal en cruz: en total explota parejo (cada 90°),
  pero **cada fila por separado** explota a intervalos desparejos (180-90-180-270°). Cada fila
  descarga por su múltiple de escape, y esos golpes desparejos son el «brrrum-brrrum» [6][7].
- **La nota base** es la frecuencia de explosiones: `Hz = rpm × 8 / 120 = rpm / 15`.
  En ralentí (≈700 rpm) son **≈47 golpes por segundo**: un zumbido grave con pulso.
  A 4.800 rpm (máxima potencia) son 320 por segundo: ya es un rugido agudo.
- **Ralentí del 68**: no encontramos la especificación de fábrica del L48 1968. Como referencia, el
  manual del 350 de 1969 (automático) dice 600 rpm en Drive [12]. Para la animación, **700 rpm** en
  ralentí queda bien **(sin confirmar)**.

**Cómo usarlo en la página** (para el Agente 4):
1. El sonido **arranca en silencio** (lo pide el brief) y los navegadores igual no dejan sonar nada
   hasta que la persona toca algo: crear o reanudar el `AudioContext` **dentro del clic** de
   «Prender» [13][14]. Con botón para silenciar.
2. `assets/audio/v8-ralenti.mp3` en bucle (Web Audio, `loop = true`). Para acelerar sin otra
   grabación: subir `playbackRate` de 1 a ≈1,6 y el volumen un poco; más de 1,8 suena a dibujo animado.
3. «Acelerar»: tocar `assets/audio/v8-acelerando.mp3` encima (el acelerón fuerte está entre 2,2 y
   4,0 s) bajando el bucle mientras suena, y que la animación suba de vueltas al mismo tiempo.
4. Detalle de los archivos y licencias: `assets/audio/CREDITOS.md`.

## 7. Datos para las fichas («Dato Camaro»)

- El 350 **apareció por primera vez en el Camaro SS de 1967** (opción L48), antes que en el Corvette [1].
- 1968 es el primer año de los **cigüeñales de muñones grandes** en el small block [4].
- Las tapas de cilindros del L48 del 68 son las **«291»** (número de fundición 3917291), con válvulas
  de 1,94″ y 1,50″; las mismas tapas llevaba el Z/28 del 68, pero con válvulas más grandes [5].
- Bloque del 68: número de fundición 3914678 según un foro de camaros.org [2]; otras fuentes dicen
  otro número, así que **no usarlo como dato** (sin confirmar).

## Fuentes

1. Wikipedia, *Chevrolet small-block engine (first- and second-generation)* — 350 de 4,000×3,480″, biela 5,7″, separación 4,4″, OHV con botadores hidráulicos, balancines con rótula sobre espárrago, cadena, orden 1-8-4-3-6-5-7-2 en todos. https://en.wikipedia.org/wiki/Chevrolet_small-block_engine_(first-_and_second-generation)
2. Over-Drive Magazine, *1968 Chevrolet Camaro Fact Sheet* (295 HP a 4.800, 380 lb-pie a 3.200, 10,25:1) https://over-drive-magazine.com/2024/03/25/1968-chevrolet-camaro-fact-sheet/ · Speedway Motors, *Small block Chevy engine specifications* https://www.speedwaymotors.com/Tech/small-block-chevy-engine-specifications · camaros.org foro (bloque 68) https://www.camaros.org/forum/index.php?msg=31589
3. It Still Runs, *Chevrolet 350 Engine Specs* (bielas de 5,7″, acero forjado) https://itstillruns.com/chevrolet-350-engine-specs-6904407.html
4. Chevellestuff, *Chevrolet V8 Engine Crankshafts* (1968-69: forjado o nodular, 3,48″, muñones 2,10″, bancadas 2,45″) https://www.chevellestuff.net/qd/crank/crank.htm
5. Camaro Research Group, *Cylinder heads* (1967-68 L48: 3917291, 1,94/1,50, 63 cm³) https://camaros.org/cylinderheads.shtml
6. Wikipedia, *V8 engine* (intervalos 180-90-180-270 por fila y el sonido) https://en.wikipedia.org/wiki/V8_engine
7. Wikipedia, *Crossplane* https://en.wikipedia.org/wiki/Crossplane
8. Wikipedia, *Four-stroke engine* (los 4 tiempos, 2 vueltas, levas a media velocidad) https://en.wikipedia.org/wiki/Four-stroke_engine
9. Summit Racing, *Chevy firing order / cylinder numbering* (impares del lado del conductor, de adelante hacia atrás; distribuidor horario) https://help.summitracing.com/knowledgebase/article/HE-04934/en-us
10. JEGS, balancines estampados 1,5 para small block 1955-86 con espárrago de 3/8″ https://www.jegs.com/i/jegs-555-20280-stamped-steel-rocker-arms-for-1955-1986-small-block-chevy-set-of-16 · All Chevy Performance, *What you need to know about rocker arms* https://digital.allchevyperformance.com/previewissue/october-2025/what-you-need-to-know-about-rocker-arms/
11. BluePrint Engines, *What firing order does my engine use* https://knowledgebase.blueprintengines.com/knowledge/new-article-copilot-said-what-firing-order-does-my-blueprint-engine-use
12. NCRS, *Curb idle settings 1969 350/300* https://www.forums.ncrs.org/forum/technical-discussion/62075-curb-idle-settings-1969-350-300?p=649265
13. MDN, *Web Audio API best practices* (crear o reanudar el contexto dentro de un clic) https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices
14. Chrome for Developers, *Web Audio, Autoplay Policy and Games* https://developer.chrome.com/blog/web-audio-autoplay
15. Sonidos: Freesound, CC0 — ver `assets/audio/CREDITOS.md`.
