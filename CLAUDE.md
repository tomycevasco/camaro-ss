# Camaro SS

<!-- Plantilla de Taller. El núcleo reemplaza Camaro SS, otro, (sin descripción) y 21/10/2026
     al crear el proyecto. El constructor la mantiene al día: corta, solo lo que evita errores. -->

**Qué es:** (sin descripción)
**Tipo:** otro · **Creado:** 21/10/2026 · **Para:** Tomás (lee HTML/CSS/JS, no programa)

## Decisiones de diseño
- Estilo: _(a definir: en una línea, la idea y el porqué)_
- Colores: _(nombre y hex de cada variable, ej. `--color-acento: #2457d6` botones y links)_
- Letras: _(familias y para qué se usa cada una)_
- Otras: _(esquinas, íconos, modo oscuro sí/no…)_

## Cómo se arranca y se prueba
- Ver: _(ej. «abrir index.html en la vista previa» · «npm run dev → http://127.0.0.1:5173»)_
- Probar: _(ej. «npx playwright test» · «probar el formulario vacío y completo»)_
- Publicar: _(ej. «Netlify, carpeta . » · «primero Publicar → Subir a Supabase, después Netlify» · todavía no)_

## Reglas de este proyecto
- Textos en español rioplatense.
- Sin frameworks ni build salvo que se decida acá abajo.
- _(lo que pida Tomás, ej. «los precios siempre con punto de miles: $12.500»)_

## Servicios y datos
- _(servicios externos, dónde van las claves (.env), datos reales que faltan)_
- _(si usa algo de afuera: variables que necesita (nombres, no valores), dónde está cargada cada clave,
  qué se paga aparte, y qué hace Tomás a mano cuando cambia la base o se publica)_
- _(si usa Supabase: todo en `supabase/` — `config.toml`, `migrations/` (una migración nueva por
  cambio; nunca se edita una ya subida), `functions/<nombre>/index.ts` y `taller.json` (nombres de las
  claves secretas). Lo sube Tomás con Publicar → Subir a Supabase; los `.sql` sueltos de antes, si
  quedan, ya no se usan)_
