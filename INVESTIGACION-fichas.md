# Investigación · Fichas de las piezas (Agente 2 · 21/10/2026)

**En una línea:** las fichas salen de camaros.org (el Camaro Research Group, la referencia de los
restauradores) más Wikipedia para lo general; cada dato lleva su fuente y una marca de «verificado» o
«sin verificar», y van en un solo `datos/fichas.json` con ids fijos que usan el motor 3D y la pantalla.

## Qué hay en la carpeta
- La muestra (`docs/muestra-diseno.html`) ya fija la forma de la ficha: **grupo** («Motor · Admisión de
  aire»), **nombre**, **explicación** (2–3 frases), **Dato Camaro** (una línea) y **Saber más** (1–2
  párrafos). La lista agrupa: Motor (18), Carrocería (14), Interior (6, sin fichas).
- Todavía no existe `datos/`: la creo yo. Nadie más escribe ahí.

## Fuentes y qué tan confiables son
| Fuente | Sirve para | Confianza |
|---|---|---|
| camaros.org (CRG): páginas de modelo 1968, motor, carburadores, refrigeración, capots, vano motor | Datos de fábrica del 68: motor, carburador, radiador, ventilador, batería, capot, emblemas | **Alta** (es investigación documentada) |
| Foro de camaros.org | Detalles finos (tapa cromada del filtro, toma de aire) | **Media**: son recuerdos de dueños; se marca «sin verificar» |
| Wikipedia (Camaro 1.ª generación) | Contexto: lanzamiento, producción total, cambios del 68 | Media-alta, solo para lo general |
| Sitios de fichas técnicas (auto-data, etc.) | Confirmar potencia y torque | Media; solo como segunda fuente |
| Avisos de venta | Nada | **No se usan**: muestran piezas cambiadas, no de fábrica |

## Datos ya verificados (ejemplos que van a las fichas)
- Motor del SS 350 del 68: **350 pulgadas cúbicas (5,7 L), 295 HP**, con carburador de 4 bocas; en
  1968 se hicieron **12.496** (camaros.org/engine). Torque ≈ 380 lb-pie (sitios de fichas, no CRG).
- Carburador: **Rochester Quadrajet 4MV, 750 CFM**; las 2 bocas chicas cuidan la nafta en el andar
  normal y las 2 grandes se abren cuando pisás a fondo (camaros.org/carb).
- Radiador del SS 350 de serie: **21" y 2 filas**; con aire acondicionado, 23" y 3 filas. Ventilador
  **fijo de 4 palas** (el de 5 palas con embrague era con aire). Bomba de agua «corta» en 67-68
  (camaros.org/coolingsystems).
- Batería: la de **61 Ah** para motores de 327 en adelante (camaros.org/underhood).
- Capot SS 68: tenía tomas falsas cromadas tipo «trompetas» que en el 68 llevaron agujeros de desagüe
  (camaros.org/hoods). **El auto del amigo no las tiene**: la ficha lo cuenta como cambio del dueño.
- 1968: sin ventilete por la ventilación «Astro», luces de posición nuevas en los guardabarros,
  235.147 Camaros hechos, armados en Norwood (Ohio) y Van Nuys (California) (Wikipedia).
- Emblema «SS 350» en el SS con motor 350; la franja «bumblebee» venía en el SS (camaros.org/diffs68,
  exterior). **El auto del amigo no la tiene** (negro entero): se aclara igual que el capot.

## Lo que no se pudo verificar todavía (se marca así en la ficha)
- **Filtro de aire con tapa cromada** en el SS 350 del 68: lo dicen varios en el foro del CRG, no un
  documento. Va como «según restauradores».
- **Tapas de válvulas cromadas** y el **naranja** del motor: son del auto del amigo; el CRG no dice el
  color de fábrica en lo que leí. Lo busco en la construcción; si no aparece, va marcado.
- Alternador, bobina, motor de arranque, bomba de nafta, mangueras: falta buscar el dato del 68 (el CRG
  tiene páginas de distribuidores, bobinas, arranque y bombas de agua que todavía no leí).

## Cómo conviene armar `datos/fichas.json`
Un solo archivo, simple de leer y de corregir a mano:
```json
{
  "version": 1,
  "piezas": [
    {
      "id": "filtro-aire",
      "nombre": "Filtro de aire",
      "grupo": "motor",
      "subgrupo": "Admisión de aire",
      "explicacion": "2–3 frases: qué es y qué hace.",
      "dato": { "texto": "Dato Camaro 67-68", "fuente": "https://camaros.org/...", "verificado": true },
      "saberMas": ["párrafo 1", "párrafo 2"],
      "fuentes": ["https://camaros.org/carb.shtml"],
      "notaAuto": "Opcional: en qué se diferencia el auto del amigo del de fábrica"
    }
  ]
}
```
- **id** en minúsculas con guiones: es el **nombre del objeto en Blender**, así el motor (Agente 5) y
  la carrocería (Agente 4) solo tienen que llamar igual a sus piezas, y la pantalla (Agente 3 y 6) busca
  la ficha por ese nombre. Las piezas que van de a pares (puertas, tapas de válvulas, múltiples de
  escape) comparten una ficha: los objetos se llaman `tapa-valvulas-izq` / `-der` y el JSON trae un
  campo `piezas3d` con esos nombres.
- **orden**: un número para el «Paso a paso» (Agente 6), de lo primero que se arma a lo último.
- `verificado: false` cuando el dato sale del foro o no se encontró: la pantalla puede mostrar
  «según restauradores».
- Además `datos/FUENTES.md`: la lista de fuentes con qué se sacó de cada una (para Tomás y su amigo).

## Piezas (ids finales, los que quedaron en `datos/fichas.json`)
**Motor (18):** `bloque`, `tapas-cilindros`, `carter`, `multiple-admision`, `tapas-valvulas`,
`multiples-escape`, `bomba-agua`, `motor-arranque`, `distribuidor`, `bobina`, `cables-bujias`,
`alternador`, `correas`, `ventilador`, `carburador`, `filtro-aire`, `radiador`, `bateria`.
(Cambió respecto de la propuesta: `culatas` → `tapas-cilindros`, como se dice acá; `mangueras` →
`motor-arranque`, porque del burro sí hay datos del 68 y las mangueras van con el radiador.)
**Carrocería (15):** `carroceria`, `capot`, `puertas`, `tapa-baul`, `paragolpes-delantero`,
`paragolpes-trasero`, `parrilla`, `faros`, `luces-posicion`, `luces-traseras`, `emblemas-ss`,
`tapa-nafta`, `llantas-rally`, `vidrios`, `espejo`.
Los nombres de los objetos 3D de las piezas dobles están en el campo `piezas3d` de cada ficha.

## Tono
Como la muestra: frases cortas, comparaciones de todos los días («respira», «se ahoga»), cifras
redondas en km y litros además de las de la época, nada de números de pieza en la ficha (esos quedan
solo en FUENTES.md).

## Fuentes
- [CRG · Diferencias del modelo 1968](https://camaros.org/diffs68.shtml)
- [CRG · Motores](https://camaros.org/engine.shtml) · [Carburadores](https://camaros.org/carb.shtml) · [Refrigeración](https://camaros.org/coolingsystems.shtml) · [Vano motor y baterías](https://camaros.org/underhood.shtml)
- [CRG · Capots 1967-69](https://camaros.org/hoods.shtml) · [Exterior](https://camaros.org/exterior.shtml)
- [Foro CRG · filtro de aire del SS](https://www.camaros.org/forum/index.php?msg=13857)
- [Wikipedia · Camaro primera generación](https://en.wikipedia.org/wiki/Chevrolet_Camaro_(first_generation))
- [auto-data · Camaro SS 350 295 HP](https://www.auto-data.net/en/chevrolet-camaro-i-ss-350-v8-turbo-fire-295hp-40113)

---
**Resumen:** los datos salen de camaros.org (lo más confiable para un 67-68) y cada uno lleva su
fuente y si está verificado o es «según restauradores»; ya hay base firme para motor, carburador,
radiador, batería y capot.
Las fichas van en un solo `datos/fichas.json` con ids = nombres de las piezas en Blender, para que el
motor, la carrocería y la pantalla se enganchen sin tocar mis archivos.
