# Camaro SS

**Qué es:** el Camaro SS 1968 coupé negro de un amigo de Tomás, en 3D en el navegador: se gira, se abren capot, puertas y baúl, y cada pieza (carrocería, motor por afuera y por dentro) se toca para ver qué es y qué hace. Se separa en piezas y se arma paso a paso. Con «Motor», el V8 sale a un soporte de taller, se desarma en orden, se prende con sonido y se ve en corte.
**Tipo:** otro · **Creado:** 21/10/2026 · **Para:** Tomás (lee HTML/CSS/JS, no programa) y su amigo

## El auto (decidido en la entrevista; Tomás pasó fotos de referencia: lo más parecido posible al 68 real)
- **1968 SS coupé**, negro entero, sin franjas ni vinilo. Sin ventilete. Luces de posición ámbar al costado, adelante; rojas atrás. Luces de estacionamiento **adentro de la parrilla** (no es RS). Nafta detrás del emblema trasero. Faros redondos a la vista. Capot SS con lomo central **sin rejillas**. Llantas Rally (asumido).
- Motor: V8 350 small block naranja Chevrolet, tapas de válvulas cromadas, carburador de 4 bocas, **filtro de aire redondo cromado**. Por afuera, 28 piezas con ficha; por dentro (`motor_interno.glb`), 9 con ficha.
- Interior negro: butacas sin apoyacabezas, cinturón de cintura, asiento trasero, volante de 3 rayos, palanca al piso. Se ve (y se puede mirar desde adentro), sin fichas.
- No entra: lo de abajo (suspensión, caja, escapes, frenos).
- **Chequeo de la trompa (21/10, vista inicial 3/4 de adelante):** parrilla en punta, faros redondos dentro del hueco, luces de estacionamiento en la parrilla y paragolpes que envuelve: se ve como un 68, no cuadrado. Lo que todavía queda algo recto es el borde de adelante del capot y de los guardabarros arriba de los faros; si Tomás pide más, se toca en `blender/carroceria.py` (sección de la trompa, ver `INVESTIGACION-carroceria-68.md`).

## Decisiones de diseño (aprobado en la muestra: `docs/muestra-diseno.html`)
- Estilo: estudio blanco, el auto negro es el protagonista. Vista inicial 3/4 de adelante. Piso simple hecho en Blender, con el auto **apoyado** (sombra de contacto), nunca flotando.
- Colores: `--fondo: #f3f2ee` · `--superficie: #ffffff` · `--linea: #e3e1db` · `--texto: #16181c` · `--texto-suave: #61666d` · `--acento: #d9600b` (naranja Chevrolet: pieza marcada, detalles) · `--acento-texto: #b34c05` · `--acento-claro: #fdeee2`. Botones principales en negro (`--texto`).
- Letras: Barlow Condensed (títulos, en mayúsculas con aire) y Barlow (texto).
- Pantalla: barra arriba (marca + Explorar/Separar/Paso a paso + **Motor** + **?**), escena 3D, ficha flotante a la derecha (en celular abajo del auto), lista de piezas a la derecha (grupos Motor · Motor por dentro · Carrocería), botones de cámara abajo a la derecha del 3D (− · + · Adentro), controles abajo (Capot, Puertas, Baúl, Vista inicial, barra Separar). En el celular la barra va en dos renglones (modos abajo, a lo ancho).
- Fichas: explicación simple (2–3 frases) + «Dato Camaro» del 67-68 + «Saber más» desplegable, sin ponerse técnico.

## Controles (Tomás usa laptop sin mouse ni rueda: nunca depender de la rueda)
- Girar: arrastrar (touchpad apretado o un dedo) · `Mayús` + flechas.
- Acercar: pellizco (touchpad o pantalla) · botones + / − · teclas `+` `−`.
- Desplazar: `Mayús` + arrastrar · flechas · dos dedos en el celular.
- Ver por adentro: botón «Adentro» / tecla `A` → la cámara va atrás de las butacas, lente de 62° (afuera 32°), giro más lento. Se sale con «Salir», `A`, «Vista inicial» o `0`. Al cambiar de modo o ir a Motor sale sola, de golpe.
- Las teclas andan en toda la página (handler en `document`), salvo en campos, en la lista, en la ficha y en el panel del motor. Se ignoran los eventos reenviados (`isTrusted = false`) que manda la vista Motor.
- Cartel de ayuda (`<dialog id="ayuda">`): sale la primera vez (se recuerda en `localStorage` `camaro-ayuda-vista`), vuelve con «?» (botón o tecla). Esc o tocar afuera lo cierran. En celular (`pointer: coarse`) muestra los textos de dedos. La ayuda corta propia de la vista Motor (`.vm-ayuda`) va escondida: manda este cartel.

## Cómo está armado
- `index.html` + `css/estilos.css` (todo lo visual) + `css/celular.css` (ajustes finos de celular, va última) + `js/app.js` (escena, cámara y controles, lista, ficha, abrir/cerrar, enganche de módulos).
- Módulos (`js/modulos/`, rutas en `manifiesto.json → modulos`; si faltan ahí, `RUTAS_MODULOS` de `app.js`): `separar.js` y `paso-a-paso.js` (usan `movimiento.js`), después `vista-motor.js` (botón «Motor» ya en el HTML con `data-vista-motor`; avisa con el evento `vista-motor`) y `motor-vivo.js` (panel Prender/Acelerar/Por adentro; `app.js` lo muestra solo con el motor en el soporte). Sus CSS están enlazados en el `<head>`.
- `motor_interno.glb` se baja recién con «Por adentro»; `app.js` suma esas piezas con `sumarPiezas()` (alias: `bloque-corte`→bloque, `tapas-cilindros-corte`→tapas-cilindros, `esparragos`→balancines). En el soporte, los toques sobre piezas de adentro los atiende `app.js` en captura (la vista Motor no las conoce) y lo transparente no frena el toque.
- `datos/fichas.json`: 57 fichas (28 motor, 9 motor por dentro con `"adentro": true`, 20 carrocería). Pieza = objeto de Blender con el nombre del `id` (o los de `piezas3d`). Fuentes: `datos/FUENTES.md`.
- Three.js 0.186.1 copiado en `vendor/three/` (importmap en `index.html`). Nada del 3D depende de un CDN.
- `vendor/three/build/` (three.module.js y three.core.js) va en git gracias a `!vendor/three/build/` en el `.gitignore` (que tiene `build/`). No sacar esa línea: sin esos archivos el 3D no arranca.
- Arranque: las pinturas se arman con `renderer.compileAsync` **antes** del primer dibujo (`preparando` frena el bucle). Dibujar antes congela la página varios segundos en Windows. No sacarlo.
- Sin placa de video (SwiftShader, etc.) entra el `modoLiviano`: sin sombras en tiempo real, pintura sin laca, nitidez 1. A los 20 s sin cargar se ofrece «Recargar»; si se pierde el 3D, también.
- Se dibuja solo cuando algo se mueve.

## Modelos 3D y peso
- Salen de `blender/carroceria.py`, `exterior.py`, `motor.py` y `motor_interno.py` (cómo correrlos: `blender/LEEME.md`). Blender 4.5 LTS portátil va en `.taller/tmp/blender/` (fuera de git).
- **Después de regenerar un `.glb` hay que comprimirlo** (comandos en `README.md`). **No usar `optimize`, `quantize`, `meshopt`, `join`, `flatten` ni `prune`**: rompen bisagras y enganches.
- Pesos hoy: carrocería 105 KB · exterior 185 KB · motor 435 KB (≈725 KB al abrir) · motor por dentro 325 KB y sonido 100 KB (solo al usarlos). Decodificador Draco ~250 KB.
- Celular (≤ 820 px): nitidez máx. 1,5, sombra de 1024 px y **las piezas del motor no tiran sombra** (de 407 a 313 dibujos y de 265 mil a 187 mil triángulos por cuadro).

## Cómo se arranca y se prueba
- Ver: abrir `index.html` en la vista previa.
- Probar: girar, acercar con + / −, correr con flechas, «Adentro», tocar piezas, abrir capot/puertas/baúl, separar, paso a paso, Motor → Prender → Por adentro → tocar un pistón; celular (390×844) y compu (1366×800). Para ver el cartel de nuevo: borrar `camaro-ayuda-vista` del `localStorage` o tocar «?».
- Publicar: Netlify con el botón de Taller. No hay build: se sube la carpeta tal cual (con `vendor/three/build/`).

## Reglas de este proyecto
- Textos en español rioplatense.
- Sin frameworks ni build. Three.js para el 3D. Los modelos salen de Blender portátil manejado por scripts de Python.
- Datos de las fichas verificados en fuentes de restauración (camaros.org y similares), nada inventado; lo no verificado lo dice el texto.
