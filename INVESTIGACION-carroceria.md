# Investigación · Carrocería del Camaro SS 68 (Agente 1, 21/10/2026)

**Mi parte:** la chapa del SS 68 coupé negro, hecha en Blender por script, apoyada en el piso con
sombra de contacto, exportada a `modelos/carroceria.glb` con capot, puertas y baúl separados y con su
bisagra.

## Lo que ya hay
- Nada de Blender ni modelos todavía (solo la muestra de diseño y los documentos).
- Blender no está instalado en la PC. Hay que bajarlo (ya aprobado en el plan).

## Medidas reales del 68 coupé (para no dibujar «a ojo»)
| Medida | Valor |
|---|---|
| Distancia entre ejes | 2742 mm (108″) |
| Largo total | 4691 mm |
| Ancho | 1841 mm |
| Alto | 1295 mm |
| Trocha (distancia entre ruedas de un mismo eje) | 1499 adelante · 1496 atrás |

Rasgos que hacen que «sea un Camaro»: capot largo y baúl corto, techo semi-fastback, la cadera
marcada sobre la rueda de atrás («botella de Coca»), línea de carácter a lo largo del costado, frente
con la parrilla hundida, costados que se meten hacia arriba (los vidrios inclinados), sin ventilete.
El capot del 1er Camaro **se abre desde adelante** (bisagra atrás, junto al parabrisas).

## Cómo modelarlo por script: opciones
| Opción | A favor | En contra |
|---|---|---|
| **Cortes transversales + subdivisión (elegida)** | Defino ~20 «rebanadas» del auto a lo largo, con las medidas de arriba; el script las une en una malla y la suaviza. Simétrica, prolija, liviana y fácil de ajustar si Tomás pide «más bajo el capot» | Hay que afinar bien las rebanadas para la cadera y el techo |
| Cajas + modificadores (biselado, subdivisión) | Rápido | Queda «de juguete», no llega a la forma del Camaro |
| Superficies por curvas (Coons patch) | Muy suave | Lo bueno es un add-on pago; más difícil de manejar por script |

Después de armar la malla entera, **recorto los paneles** (capot, puertas, baúl) por zonas, con una
ranura fina entre panel y carrocería, así no queda un agujero al abrir (se ve un interior negro mate).

## Bisagras y nombres (para que los demás se enganchen)
- Cada pieza es un objeto con nombre: `carroceria`, `capot`, `puerta_izq`, `puerta_der`, `baul`.
- **El punto de origen de cada objeto es su bisagra**: girar el objeto ya lo abre bien. Le dejo
  anotado en sus datos extra (el glTF los lleva como `extras` y Three.js los pone en `userData`) el eje
  y el ángulo máximo: ej. `capot` → eje X, hasta 55°; puertas → eje vertical, hasta 65°; `baul` → eje X.
- **Puntos de enganche vacíos** (objetos sin forma, solo una posición) para la tanda 2: dónde va el
  motor, el centro de cada rueda, los paragolpes, faros y vidrios. Así el Agente 4 y el 5 ubican sus
  piezas sin adivinar.
- Ejes: Blender usa Z para arriba; el exportador lo pasa a Y para arriba (lo que usa Three.js). Metros,
  piso en 0, el centro entre los ejes en el origen, el frente mirando hacia +Z en Three.js.

## Pintura y piso
- Negro con brillo de laca: material estándar (metálico 0, rugosidad baja) + **capa de barniz**
  (clearcoat, que glTF y Three.js entienden). Ranuras e interior en negro mate.
- **Sombra de contacto horneada**: en Blender calculo la sombra suave debajo del auto y la guardo en una
  imagen chica (512 px) sobre un plano `piso_sombra`. Es lo más liviano y se ve más «apoyado» que la
  sombra automática de Three.js. Límite: la sombra es la del auto cerrado (al abrir o separar no
  cambia; en Separar conviene que la pantalla la atenúe).
- El piso del estudio (un disco claro `piso`) va en el mismo .glb.

## Que pese poco
- Meta: carrocería **≤ 1 MB** y ~30–40 mil triángulos (suficiente con normales suaves).
- **Sin compresión Draco por ahora**: obliga a la pantalla a cargar un decodificador; la compresión
  final (Draco o meshopt con gltf-transform) la hace el Agente 7 en el cierre.
- Exportar con los modificadores aplicados (la subdivisión queda «congelada»), sin animaciones ni
  cámaras.

## Blender
- **Blender 4.5.14 LTS**, .zip oficial de blender.org (~400 MB, soporte hasta 2027). Se descomprime y
  anda sin instalar; se maneja sin ventana: `blender -b -P blender/carroceria.py`.
- **Dónde va:** en mi copia, en `.taller/tmp/blender/` (no se guarda ni va a git). El `.gitignore` del
  proyecto no tiene una carpeta para Blender y no es mío; si se quiere dejar fijo en el proyecto, hay
  que sumar `herramientas/` al `.gitignore`. En `blender/LEEME.md` explico dónde ponerlo y cómo
  regenerar.
- Para revisar la forma, Blender saca fotos de frente, costado y 3/4 (en `.taller/tmp/`) y además lo
  miro en la vista previa con un visor de prueba.

## Fuentes
- [Medidas Camaro 1968 coupé (Carsales / Redbook)](https://www.carsales.com.au/research/chevrolet/camaro/1968/ss/)
- [Diferencias 1967-69 (Street Muscle)](https://www.streetmusclemag.com/features/car-features/at-a-glance-how-to-spot-differences-in-first-gen-camaro-1967-69/) · [Capots (camaros.org)](https://camaros.org/hoods.shtml)
- [Versiones de Blender 4.5 LTS (download.blender.org)](https://download.blender.org/release/Blender4.5/) · [Blender Portable LTS (PortableApps)](https://portableapps.com/apps/graphics_pictures/blender-portable-lts)
- [Exportador glTF de Blender: compresión Draco (commit oficial)](https://developer.blender.org/rBA0a26f6cce99ce064c48a75c2df7533b2b3156d42) · [Blender a glTF por consola (Khronos)](https://github.khronos.org/glTF-Tutorials/BlenderGltfConverter/)
- [Sombra horneada en un plano (foro Three.js)](https://discourse.threejs.org/t/how-can-i-bake-a-shadow-onto-a-planegeometry/40887) · [ContactShadows vs. horneado](https://discourse.threejs.org/t/shadow-contact-threejs/29505)
- [Modelado de autos: forma base + paneles (Foolproof Car Modelling)](https://superhivemarket.com/products/foolproof-car-modelling-in-blender)

---
**Resumen:** armo la chapa del 68 por script con «rebanadas» a medida real (108″ entre ejes, 4,69 m de
largo) que Blender suaviza, y recorto capot, puertas y baúl con su bisagra como punto de giro.
Sale un .glb liviano (≤ 1 MB, sin Draco) con piso, sombra horneada y puntos de enganche para la tanda 2.
