# Blender · cómo se vuelve a generar el auto

Los modelos 3D salen de scripts de Python que maneja Blender sin abrir la ventana. Si cambiás una
medida en el script, lo volvés a correr y el `.glb` se rehace solo.

| Script | Genera | Qué tiene |
|---|---|---|
| `carroceria.py` | `modelos/carroceria.glb` | La chapa del SS 68, capot, puertas, baúl, vano del motor, pasaruedas, piso, sombra y puntos de enganche |
| `exterior.py` | `modelos/exterior.glb` | Paragolpes, luces, llantas, vidrios, manijas, espejo e interior |
| `motor.py` | `modelos/motor.glb` | El V8 350 por afuera, con detalle (28 piezas, tornillos, textura de fundición) y los enganches de la vista Motor (ver sección 6) |

## 1. Tener Blender (una sola vez)

- Versión: **Blender 4.5.14 LTS**, el `.zip` oficial para Windows (~400 MB, no se instala):
  <https://download.blender.org/release/Blender4.5/blender-4.5.14-windows-x64.zip>
- Se descomprime adentro del proyecto, en **`.taller/tmp/blender/`** (esa carpeta no se guarda en
  los pasos ni va a GitHub). Queda así:
  `.taller/tmp/blender/blender-4.5.14-windows-x64/blender.exe`
- Si algún día se quiere dejar fijo en otra carpeta del proyecto (por ejemplo `herramientas/`), hay
  que sumarla antes al `.gitignore`: Blender pesa demasiado para GitHub.

## 2. Generar

Desde la carpeta del proyecto, en la terminal (Git Bash):

```sh
./.taller/tmp/blender/blender-4.5.14-windows-x64/blender.exe -b -P blender/carroceria.py
```

Tarda unos 10 segundos (la mayor parte es la sombra) y termina con
`Listo: ...\modelos\carroceria.glb (≈460 KB)`. Para guardarlo en otro lado:
`... -P blender/carroceria.py -- otra/ruta.glb`.

## 3. Qué hay adentro de `carroceria.glb`

Ejes como los usa Three.js: **arriba = +Y**, **el frente mira a +Z**, el lado izquierdo del auto
(el del conductor) es +X. Metros. El origen está en el piso, en el medio entre los dos ejes.

| Objeto | Qué es | Para abrirlo (`userData`) |
|---|---|---|
| `carroceria` | La chapa fija (guardabarros, techo, parantes, zócalos, frente y cola) | — |
| `capot` | Capot SS con el lomo central, sin rejillas | eje `x`, `-55`° |
| `puerta_izq` / `puerta_der` | Puertas (sin vidrio: lo pone el Agente 4) | eje `y`, `-62`° / `62`° |
| `baul` | Tapa del baúl | eje `x`, `58`° |
| `vano_motor` | Torpedo, paredes internas y soporte del radiador (negro mate) | — |
| `pasaruedas` | Los huecos de adentro de las ruedas (negro mate) | — |
| `piso` | El disco claro del estudio (`#f3f2ee`) | — |
| `piso_sombra` | La sombra de contacto horneada (imagen negra con transparencia) | — |
| `enganche_*` | Puntos vacíos: dónde va cada cosa de las tandas que siguen | — |

- **Cada pieza que se abre tiene el origen en su bisagra**: para abrirla alcanza con
  `objeto.rotation[userData.eje] = THREE.MathUtils.degToRad(userData.abierto_grados)`.
  Las puertas giran sobre su borde de adelante; el capot, sobre el borde del parabrisas (se abre
  desde adelante, como el original); el baúl, sobre el borde de la luneta.
- Las piezas de chapa traen `userData.pieza` con su nombre (el mismo id de la ficha).
- Materiales: `pintura_negra` (negro con barniz: en Three.js sale como `MeshPhysicalMaterial` con
  clearcoat, conviene un `scene.environment` para que brille), `negro_mate` (adentro de los paneles,
  vano y pasaruedas), `piso_estudio` y `sombra_contacto`.
- Sin compresión Draco (no hace falta decodificador). Pesa ≈460 KB y ~15 mil triángulos.

### Puntos de enganche (para la tanda 2)

`enganche_motor`, `enganche_radiador`, `enganche_bateria`, `enganche_paragolpes_del`,
`enganche_paragolpes_tras`, `enganche_parrilla`, `enganche_faro_izq/der`,
`enganche_luz_posicion_izq/der`, `enganche_luces_traseras_izq/der`, `enganche_tapa_nafta`,
`enganche_parabrisas`, `enganche_luneta`, `enganche_interior` y
`enganche_rueda_del_izq/der`, `enganche_rueda_tras_izq/der` (centro de cada rueda, a 0,33 m del piso).

- **El hueco de la parrilla**: el frente tiene un marco de chapa y adentro un hueco de 8,5 cm de
  fondo, a lo ancho; ahí van la parrilla y los faros redondos (68 no RS: faros a la vista).
- **La cola** tiene un panel apenas hundido para las luces traseras y la tapa de nafta.
- **Los vidrios** son huecos: parabrisas, luneta y ventanillas (sin parante del medio, como el coupé).
- La sombra se calculó con cubiertas de mentira en los `enganche_rueda_*` (radio 0,33 m, ancho
  0,21 m): las ruedas de verdad tienen que ir ahí para que coincidan con la sombra.

## 4. Si sos otro script (Agente 4, Agente 5)

Para armar encima de la carrocería sin copiar código:

```python
import importlib.util
spec = importlib.util.spec_from_file_location("carroceria", "blender/carroceria.py")
car = importlib.util.module_from_spec(spec)
spec.loader.exec_module(car)
car.limpiar_escena()
objetos = car.construir(sombra=False)    # {nombre: objeto de Blender}
# las medidas están en el módulo: car.EJE_DEL_Y, car.TROCHA_DEL, car.RADIO_RUEDA, car.perfil(y)...
```

Ojo: adentro de Blender los ejes son otros (Z arriba, el frente mira a -Y, +X = izquierda).

## 5. Qué se puede tocar fácil en `carroceria.py`

- Medidas generales arriba de todo (`ENTRE_EJES`, `FRENTE_Y`, `COLA_Y`, bordes de capot, puertas y baúl).
- La forma: las curvas `LADO_X`, `LINEA_Z` (la línea marcada del costado), `HOMBRO_Z`,
  `CRESTA_Z`, `LOMO_ALTO` (el lomo del capot), `TECHO_*`. Cada una es una lista de
  `(posición a lo largo, valor)` en metros.
- La sombra: `hornear_sombra()` (qué tan oscura y hasta dónde llega).

## 6. El motor (`motor.py`)

```sh
./.taller/tmp/blender/blender-4.5.14-windows-x64/blender.exe -b -P blender/motor.py
```

Tarda unos 15 segundos. Primero escribe el **control de lugar** (cuánto le queda a cada pieza hasta
el capot cerrado y hasta los costados del vano; si algo toca, dice `¡TOCA EL CAPOT!`) y termina con
`Listo: ...\modelos\motor.glb (≈3 MB, ≈80 mil triángulos)`. Sale **sin comprimir**: después va sí o
sí este paso (queda en ≈450 KB):

```sh
npx @gltf-transform/cli webp  modelos/motor.glb modelos/motor.glb --quality 85
npx @gltf-transform/cli draco modelos/motor.glb modelos/motor.glb --method edgebreaker --quantize-position 12 --quantize-texcoord 10
```

(`--quantize-position 12` alcanza: Draco mide cada pieza por separado, así que en el bloque es
~0,15 mm de precisión. Ahorra ~10 % sin que se note.)

### Cómo se logra el detalle (las herramientas de `Malla`)

| Herramienta | Qué hace |
|---|---|
| `caja`, `cilindro`, `torno`, `placa`, `prisma` | Las formas. `torno` gira un perfil (poleas, filtros, tapas, bujías); `placa` estira un contorno (tapa de distribución, palas, soportes). Todas aceptan `bisel=`: redondea los cantos de verdad, al crear la forma |
| `tubo`, `anillo` | Mangueras, cables y caños por puntos; aros (manija de la varilla) |
| `tornillo`, `tornillos`, `abrazadera` | Cabeza hexagonal con arandela; fleje de manguera con su tornillito. Van **dentro** de la malla de su pieza |
| `objeto(...)` | Cierra la pieza: coordenadas de textura (proyección de caja), suavizado, **normales ponderadas** y origen en el centro |

- **La textura** (`imagen_relieve`) es un relieve de fundición en arena hecho con ruido por el mismo
  script (256 px, se repite sin costura cada `TEXTURA_METROS` = 16 cm). No se baja nada. Va en el
  naranja (suave), el hierro de los múltiples (fuerte), el aluminio y el zinc. El cromo, la goma y el
  negro van lisos. Cuánto se nota: `fuerza=` en `materiales()`.
- **El peso**: `DETALLE_REDONDOS` (0,75) le saca lados a lo redondo grande. Subirlo a 1 da más
  redondez y ~25 % más peso.
- **Los lados**: «izq» = conductor (+X en Blender), «der» = acompañante (-X). Lo del 67-68: bomba de
  agua corta con el alternador del lado del conductor; bomba de nafta del lado del acompañante;
  varilla del lado del conductor (fuentes en `INVESTIGACION-motor-detalle.md`).

### Qué hay adentro de `motor.glb`

Todo cuelga del vacío `motor`. Cada pieza se llama como el `id` de su ficha y trae
`userData = { id, grupo: "motor" }`. Las que van de a varias son un vacío con las partes adentro:
`tapas-cilindros`, `tapas-valvulas`, `multiples-escape` (`-izq` / `-der`), `soportes-motor`
(`soporte-motor-izq/der`) y `bujias` (`bujia-1` … `bujia-8`, con la numeración de Chevrolet:
izquierda 1-3-5-7, derecha 2-4-6-8).

Piezas: bloque, tapa-distribucion, tapas-cilindros, carter, soportes-motor, multiple-admision,
termostato, tapas-valvulas, multiples-escape, bujias, bomba-agua, balanceador, poleas, motor-arranque,
bomba-nafta, filtro-aceite, varilla-aceite, distribuidor, bobina, cables-bujias, alternador, correas,
ventilador, carburador, filtro-aire, mangueras, radiador, bateria.

Enganches (vacíos, adentro de `motor`):

| Enganche | Dónde | Para qué |
|---|---|---|
| `enganche_soporte` | Centro de la brida de atrás del bloque, a la altura del cigüeñal | Donde abraza el soporte de taller en la vista Motor |
| `enganche_ciguenal` | Medio del eje del cigüeñal | Eje para girar el motor en el soporte; referencia del interno |
| `enganche_gancho` | Arriba del filtro de aire | De donde lo levanta la grúa al sacarlo del vano |

El orden de desarme, hacia dónde sale cada pieza y qué se queda en el auto están en
`modelos/manifiesto.json` → `vista_motor`.

### Si sos `motor_interno.py` (pistones, bielas, cigüeñal, válvulas)

```python
import importlib.util
spec = importlib.util.spec_from_file_location("motor", "blender/motor.py")
mot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mot)
mot.limpiar_escena()
mats = mot.materiales()                     # los mismos materiales y la misma textura
m = mot.Malla(["acero", "hierro"])          # las mismas herramientas (torno, tornillo, bisel…)
# medidas: mot.CIG_Z, mot.DECK, mot.DIAMETRO, mot.CARRERA, mot.ENTRE_CILINDROS,
#          mot.cilindros_y(lado), mot.a_lo_largo(lado, d, t), mot.en_banco(…), mot.eje_banco(lado),
#          mot.numero_cilindro(lado, k)
```

Se arma en las **mismas coordenadas** que `motor.glb` (el cigüeñal en `enganche_ciguenal`), así el
interno se pone adentro sin mover nada. `motor.py` deja el bloque entero: el corte va en el interno.
