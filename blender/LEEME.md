# Blender · cómo se vuelve a generar el auto

Los modelos 3D salen de scripts de Python que maneja Blender sin abrir la ventana. Si cambiás una
medida en el script, lo volvés a correr y el `.glb` se rehace solo.

| Script | Genera | Qué tiene |
|---|---|---|
| `carroceria.py` | `modelos/carroceria.glb` | La chapa del SS 68, capot, puertas, baúl, vano del motor, pasaruedas, piso, sombra y puntos de enganche |

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
