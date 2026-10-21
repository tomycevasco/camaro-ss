# Créditos de los sonidos

Los dos sonidos son grabaciones reales bajadas de [Freesound](https://freesound.org) con licencia
**CC0 (dominio público)**: se pueden usar, cambiar y publicar gratis, sin pedir permiso ni poner
crédito. Igual lo ponemos, por respeto a quien grabó.

| Archivo | Qué es | Grabación original | Autor | Licencia |
|---|---|---|---|---|
| `v8-ralenti.mp3` | V8 de muscle car en ralentí, 2,2 s, armado para repetirse sin corte | [Muscle_Idle.ogg](https://freesound.org/people/FreeCarSoundsGaming/sounds/535038/) | FreeCarSoundsGaming | [CC0 1.0](http://creativecommons.org/publicdomain/zero/1.0/) |
| `v8-acelerando.mp3` | V8 «gargarero» que acelera fuerte y vuelve al ralentí, 8,5 s | [v8 engine rev.wav](https://freesound.org/people/overmedium/sounds/651534/) | overmedium | [CC0 1.0](http://creativecommons.org/publicdomain/zero/1.0/) |

Licencias verificadas en la página de cada sonido el 21/10/2026.

## Qué se les hizo
- Se bajó la vista previa de alta calidad de Freesound (la descarga original pide cuenta).
- Pasados a **mono, 44,1 kHz, MP3 VBR** (`ffmpeg -q:a 5`) para que pesen poco: 36 KB + 64 KB = **≈100 KB**.
- Volumen parejo: el ralentí quedó en −20 LUFS y el acelerando en −16 LUFS (el acelerón suena más fuerte, como en la realidad). Al acelerando se le puso un desvanecido en el último medio segundo.

## Cómo es cada uno (para el que lo engancha)
- **`v8-ralenti.mp3`**: volumen constante de punta a punta, pensado para sonar en bucle.
  Conviene cargarlo con Web Audio (`decodeAudioData` + `AudioBufferSourceNode` con `loop = true`):
  con `<audio loop>` el MP3 deja un microcorte al volver a empezar. Si se escucha un «clic» en la
  vuelta, recortar con `loopStart ≈ 0.03` y `loopEnd ≈ duración − 0.03`.
- **`v8-acelerando.mp3`**: 0–2,2 s ralentí y un par de golpes de acelerador · **2,2–4,0 s el acelerón
  fuerte** (lo más alto) · 4,0–8,5 s baja de vueltas y queda en ralentí. Se puede tocar entero una
  vez al apretar «Acelerar» y volver al bucle del ralentí.

Detalle de cómo se relaciona el sonido con las vueltas del motor: `INVESTIGACION-motor-interno.md`, sección 6.
