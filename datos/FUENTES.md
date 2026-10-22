# Fuentes de las fichas

De acá salen los datos de `fichas.json` (revisado el 21/10/2026). Cada ficha trae sus fuentes y una
marca `verificado`: **true** = está en una fuente documentada; **false** = lo dicen restauradores en
foros, una sola fuente general, o no se encontró el dato del Camaro (la ficha lo dice).

## Fuentes documentadas (confianza alta)
| Fuente | Qué se sacó |
|---|---|
| [CRG · Diferencias del modelo 1968](https://camaros.org/diffs68.shtml) | Emblema «SS 350», franja D91/D90, carburador Quadrajet en el L48, radiador 21" 2 filas, ventilador fijo, poleas comunes, aislante del capot SS, sin topes chicos de paragolpes |
| [CRG · Motores](https://camaros.org/engine.shtml) | 350/295 HP, 12.496 hechos en 1968, distribuidor de aluminio con platinos (1111264 manual / 1111168 automática), bobina 1115293 «293» Delco-Remy, burro 1108338 con corona de 14" |
| [CRG · Carburadores](https://camaros.org/carb.shtml) | Rochester Quadrajet 4MV de 750 CFM; bocas chicas y grandes; Rochester y Carter intercambiables |
| [CRG · Refrigeración](https://camaros.org/coolingsystems.shtml) | Radiador 21" 2 filas (23" 3 filas con aire), ventilador fijo de 4 palas 3839282, bomba corta 67-68 |
| [CRG · Bombas de agua](https://camaros.org/waterpumps.shtml) | Bomba corta en 67-68, ~1" entre bomba y bloque, fundición 3782608 para 327/350 |
| [CRG · Tapas de cilindros](https://camaros.org/cylinderheads.shtml) | Tapas «462» y «291», válvulas 1,94"/1,50", símbolo de doble joroba |
| [CRG · Vano motor y baterías](https://camaros.org/underhood.shtml) | Batería de 61 Ah para motores de 327 o más; resortes del capot SS distintos |
| [CRG · Capots 1967-69](https://camaros.org/hoods.shtml) | Capot SS 68 (3919102), tomas «trompetas» cromadas con desagüe |
| [CRG · Exterior](https://camaros.org/exterior.shtml) | Paragolpes 67 vs 68, franjas, alerón 68 y emblema del baúl corrido 3,27" |
| [CRG · Cross-ram](https://camaros.org/crossram.shtml) | Ningún Z/28 salió de fábrica con cross-ram |
| [CRG · Vidrios](https://camaros.org/glass.shtml) | LOF como proveedor, «Soft-Ray», códigos de fecha, logo Astro en la puerta hasta nov/dic 67 |

## Fuentes generales (confianza media-alta)
| Fuente | Qué se sacó |
|---|---|
| [Wikipedia · Camaro 1.ª generación](https://en.wikipedia.org/wiki/Chevrolet_Camaro_(first_generation)) | 235.147 hechos en 1968, Norwood y Van Nuys, semi-monocasco, medidas, sin ventilete por la ventilación Astro, luces de posición, luces traseras divididas, parrilla en punta, faros escondidos del RS, insignias del SS, llantas de 14", espejo (sin confirmar) |
| [Wikipedia · Small block de Chevrolet](https://en.wikipedia.org/wiki/Chevrolet_small-block_engine_(first-_and_second-generation)) | El 350 debutó en el Camaro 67, medidas del cilindro, más de 100 millones hechos |
| [Street Muscle · Diferencias 1967-69](https://www.streetmusclemag.com/features/car-features/at-a-glance-how-to-spot-differences-in-first-gen-camaro-1967-69/) | Tapa de nafta entre las luces (67-68), luces de posición del 68, parrilla del 67 negra y del 68 con rayas plateadas, ventilete |

## Foros de restauradores (marcado «sin verificar»)
| Fuente | Qué se sacó |
|---|---|
| [Foro CRG · filtro del SS 350](https://www.camaros.org/forum/index.php?msg=13857) | Tapa cromada, unas 16" de diámetro (del 67) |
| [Foro CRG · tapas de válvulas L48](https://www.camaros.org/forum/index.php?msg=7252) | De fábrica, tapas de chapa pintadas; las cromadas son de los dueños |
| [Foro CRG · llantas Rally](https://www.camaros.org/forum/index.php?msg=159338) | Tapas centrales 68-69 y versiones para disco/tambor |
| [Foro CamaroZ28 · alternador](https://www.camaroz28.com/forums/fuel-ignition-74/alternator-question-887144) | Alternadores opcionales de 42 y 61 A en 1968 (citando el «White Book») |
| [Foros NCRS · naranja Chevrolet](https://www.forums.ncrs.org/forum/technical-discussion-archives/30051-chevy-orange-paint) | Naranja en los small block desde fines de 1956; el tono variaba |

## Lo que no se pudo verificar (las fichas lo dicen)
- **Cárter, múltiples de escape y cables de bujías**: no encontramos datos propios del Camaro 67-68. El orden de encendido 1-8-4-3-6-5-7-2 es el de todos los small block, sin fuente leída en esta tanda.
- **Espejo**: solo Wikipedia dice que en el 68 pasó de redondo a cuadrado.
- **Faros de 7"**: sale de catálogos de repuestos.
- **Lo propio del auto del amigo** (motor naranja, tapas cromadas, capot sin tomas, sin franja, llantas Rally) va en `notaAuto`, separado de lo de fábrica.

## Fichas nuevas (21/10/2026, segunda vuelta: 24 piezas más)
10 piezas nuevas del motor por afuera, 9 del motor por dentro (grupo «Motor por dentro», se ven con
«Por adentro» en la vista Motor) y 5 terminaciones de la carrocería. También se corrigieron `correas`
(ahora es solo la correa: las poleas tienen ficha propia), `parrilla` y `luces-posicion` (las luces de
estacionamiento del 68 van adentro de la parrilla) y `emblemas-ss` (suma «Camaro» y «350»).
Las investigaciones completas: `INVESTIGACION-motor-detalle.md`, `INVESTIGACION-motor-interno.md` y
`INVESTIGACION-carroceria-68.md`.

| Fuente | Qué se sacó |
|---|---|
| [Wikipedia · Small block de Chevrolet](https://en.wikipedia.org/wiki/Chevrolet_small-block_engine_(first-_and_second-generation)) | Cadena de distribución desde 1955, biela de 5,7″, botadores hidráulicos, balancines con rótula sobre espárrago, medidas del cilindro |
| [Chevellestuff · cigüeñales](https://www.chevellestuff.net/qd/crank/crank.htm) | 1968, primer año de muñones grandes; forjado o nodular en 68-69 |
| [CRG · Tapas de cilindros](https://camaros.org/cylinderheads.shtml) | Tapas «291» del L48 68, válvulas de 1,94″ y 1,50″ |
| [Over-Drive · ficha del Camaro 68](https://over-drive-magazine.com/2024/03/25/1968-chevrolet-camaro-fact-sheet/) | 295 HP a 4.800 rpm (de ahí las 80 subidas por segundo del pistón) |
| [Wikipedia · Motor de 4 tiempos](https://en.wikipedia.org/wiki/Four-stroke_engine) · [V8](https://en.wikipedia.org/wiki/V8_engine) · [Crossplane](https://en.wikipedia.org/wiki/Crossplane) | Árbol de levas a media velocidad, cigüeñal en cruz y el sonido del V8 |
| [JEGS · balancines 1955-86](https://www.jegs.com/i/jegs-555-20280-stamped-steel-rocker-arms-for-1955-1986-small-block-chevy-set-of-16) | Balancines estampados de relación 1,5 |
| [JEGS · cárter con varilla del lado del conductor 57-79](https://www.jegs.com/i/oer-691-t5100-t5100-1957-79-chevrolet-small-block-4-quart-oil-pan-driver-side-dipstick-location) | Lado de la varilla y cárter de 4 cuartos |
| [CRG · Bombas de agua](https://www.camaros.org/waterpumps.shtml) · [CRG · Refrigeración](https://camaros.org/coolingsystems.shtml) | Bomba corta 67-68 (correa) · radiador con y sin aire (termostato) |
| [Planilla AMA de Chevrolet, Camaro 1968](https://over-drive-magazine.com/wp-content/uploads/2024/03/1968-CHEVROLET-Camaro-396-CIDV8-L34-L78-L89-1-28.pdf) | Ángulos de ataque y de salida (faldones) |
| [NHTSA · interpretación de la FMVSS 108 (1968)](https://www.nhtsa.gov/interpretations/nht68-340) | Luces de posición laterales exigidas desde el 1/1/1969 |
| [OER · luces de costado 1968](https://www.oerparts.com/shop/1968/chevrolet/camaro/parts/lighting/side-markers/) | Luces de posición traseras rojas |

**Marcado «sin verificar» (lo dice el texto de la ficha):**
- Bujías AC R44 de fábrica: [foro NCRS](https://www.forums.ncrs.org/forum/technical-discussion/83548-what-spark-plug-for-a-65-327ci-350-hp).
- Filtro enroscable desde 1968: [foro NCRS](https://www.forums.ncrs.org/forum/technical-discussion-archives/42426-oil-filter-adapters?p=466550) y [Ecklers](https://ecklers.com/56-67-v8-oil-filter-conversion-tech-guide.html) (no encontramos documento de fábrica).
- Limpiaparabrisas a la vista en 68-69 y escondidos desde 1970: deducido de catálogos de repuestos ([Classic Industries](https://web2.classicindustries.com/shop/all-years/chevrolet/camaro/parts/body-components/wiper-components/wiper-linkages), [kit de ocultos](https://www.classicindustries.com/product/162821.html)).
- Termostato: **no encontramos** la temperatura de fábrica del 68; la ficha lo dice y da el dato del radiador.
- Cerradura del baúl y bomba de nafta: ubicación sacada de fotos y de restauradores.
- Balanceador y mangueras: datos generales de los small block, no propios del Camaro (la ficha lo dice).

## Lo que no se usó
- Avisos de venta de autos: muestran piezas cambiadas, no lo de fábrica.
- Páginas que dicen que el naranja Chevrolet arrancó «a principios de los 50» o con un código de pintura: no coinciden con los foros de restauradores y no tienen respaldo.
