# SPEC 37 — Botones interactivos de WhatsApp: el título del botón fluye como texto del usuario

> **Status:** Implemented
> **Depends on:** — (mismo workflow que SPEC 36; su export pendiente queda cubierto por el paso de export de esta spec)
> **Date:** 2026-09-12
> **Objective:** Que presionar un botón interactivo del catálogo ("catálogo", "ver carrito", "pagar") responda igual que escribir su texto, mapeando `interactive.button_reply.title` en `Obtener_Info_basica` para que no llegue vacío al subflow.

## Por qué existe esta spec

Incidente real del 12/9 (bot Karla, sesión Teresa +58 414 389 8602): el transcript muestra respuesta a
"carrito" (4:35) y "3" (4:35), pero **silencio absoluto** ante los botones "catálogo" (4:36:49),
"ver carrito" (4:37:14) y "pagar" (4:38). Verificado en las ejecuciones guardadas de `db_n8n`
(decodificadas, execs 43217/43219): YCloud entrega la presión del botón como
`type: "interactive"` con `interactive.button_reply: {id, title}` — el título **no** está en
`text.body`. `Obtener_Info_basica` mapea `text`/`content` solo desde `text?.body` y captions de
image/video/document → llegan `""` al subflow. El switch `Texto_o_Audio?` del subflow solo tiene
ramas para content no vacío, `audio` e `image` → el interactivo **no matchea ninguna rama** →
`Call 'yclod-simple_1_subflow'` devuelve 0 items → el workflow termina "success" sin responder
(muerte silenciosa). El clasificador de `chatbot_cart` ya reconoce los tres títulos
(CATALOGO/CONSULTAR/PAGAR, tests en verde en `test_clasificador.py`), así que con el mapeo
restaurado el botón se comporta como texto tecleado.

## Scope

**In:**

1. **`Obtener_Info_basica` (workflow vivo ycloud):** extender las asignaciones `text` y
   `content` con `interactive?.button_reply?.title || interactive?.button_reply?.id ||
   interactive?.list_reply?.title || interactive?.list_reply?.id` (encadenado tras
   `text.body`/captions, antes del `|| ''` final).
2. **Edición en vivo** (patrón SPEC 36: validación determinista pre-aplicación + `UPDATE` en
   `db_n8n` con backup previo + `docker restart n8n-container` + verificación en BD).
3. **Export** del workflow a `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/` (única fuente
   de verdad; arrastra también el jsCode de SPEC 36 aún no exportado).

**Out of scope:**

- Subflow `yclod-simple_1_subflow` (intacto: con content no vacío la rama texto matchea tal cual).
- Catch-all del subflow para tipos desconocidos (location/sticker/contact mueren en silencio
  como hoy; propia spec si duele).
- Variante chatwoot del workflow (otro sender, otro mapeo de botones).
- Cambios Python/Odoo: ninguno (chatbot_cart ya reconoce los títulos).

## Modelo de datos

Sin estructuras nuevas. Para mensajes `type=interactive` el item entrante gana contenido en
`text`/`content` (el título del botón); `file_type` sigue siendo `"interactive"`.

## Plan de implementación

1. Construir las expresiones nuevas de `text`/`content` y validarlas determinísticamente en
   Node contra el payload real decodificado de la exec 43217 (button_reply "catálogo") y el de
   la 43213 (texto "carrito" — regresión).
2. `UPDATE` del nodo `Obtener_Info_basica` en `db_n8n` (backup previo) +
   `docker restart n8n-container` + verificación byte a byte en BD.
3. E2E WhatsApp presionando "catálogo", "ver carrito" y "pagar" → cada uno responde igual que
   escribir el texto.
4. Export del workflow a la ruta prod.

## Criterios de aceptación

- [ ] Presionar "catálogo" → llega el catálogo (igual que escribirlo).
- [ ] Presionar "ver carrito" → resumen del carrito (igual que escribirlo).
- [ ] Presionar "pagar" → flujo de pago (igual que escribirlo).
- [ ] La expresión evalúa contra el payload real de la exec 43217: `text`/`content` = "catálogo".
- [ ] Mensajes de texto normales mapean igual que antes (regresión con el payload de la 43213).
- [ ] El subflow queda byte-idéntico (sin cambios).
- [ ] Export n8n actualizado solo en `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/`.

## Decisiones tomadas y descartadas

- **Tomado:** mapear en `Obtener_Info_basica` — **descartado** tocar el switch del subflow (con
  content no vacío la rama texto matchea; punto único de cambio).
- **Tomado:** extracción `title || id` — **descartado** solo `title` (YCloud podría enviar solo
  id en otros formatos; id=title en nuestros botones).
- **Tomado:** solo workflow ycloud — **descartado** la variante chatwoot (el incidente es YCloud).
- **Descartado:** catch-all del subflow para tipos desconocidos (scope mínimo; propia spec si llega).
- **Corrección (lección del 12/9):** n8n 2.x usa modelo **draft/versión/publish** — editar
  `workflow_entity` directo NO llega al runtime (el editor lee la última `workflow_history`
  y el webhook ejecuta la versión publicada en `workflow_publish_history`). Los cambios
  quedaron aplicados actualizando la versión publicada `07f87bba` (+ borrar
  `n8n:cache:collaboration` del workflow en Redis + restart). Mecanismo futuro: editar en
  el editor y **Publish**, o cirugía sobre la versión publicada.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Restart de n8n (~20-30 s de webhook caído) | Ventana corta, patrón ya usado en SPEC 36 |
| Variante de interactive sin title ni id | Optional chaining: cae al `\|\| ''` actual → comportamiento de hoy, sin regresión |
| Expresión larga mal escapada en el UPDATE | Validación determinista pre-aplicación + diff byte a byte del nodo en BD |

## What is **not** in this spec

- Catch-all del subflow para tipos desconocidos.
- Variante chatwoot.
- Cambios Python/Odoo.

Cada uno de esos, si llega, va en su propia spec.