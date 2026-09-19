# SPEC 36 — Recuperación del texto plano de la IA: fin del 400 de YCloud en el camino de error

> **Status:** Implemented
> **Depends on:** — (toca el mismo workflow que SPEC 35 pero no depende de él)
> **Date:** 2026-09-12
> **Objective:** Que cuando la IA incumpla el formato JSON, el usuario reciba igualmente respuesta por WhatsApp (el texto plano de la IA o el fallback) en vez del 400 `PARAM_MISSING` actual, reinyectando los campos de ruteo desde `Obtener_configuracion_agente` en los items de recuperación.

## Por qué existe esta spec

Incidente real del 12/9 (bot Karla Campoverde, `flujo_agendamiento_default`): la IA respondió
prosa válida sin JSON → `Separar_variables_en_json` emitió el item `JSON_PARSE_ERROR` cuyo
spread `...item.json` solo hereda `{output}` (la salida del agente n8n es un solo campo) → el
item pierde `account_id`, `session_id` y `platform` → `Enviar_mensaje_de_IA1` arma
`from: undefined` y `to: undefined` → `JSON.stringify` descarta las claves → YCloud responde
400 `PARAM_MISSING target "from"` → **el usuario no recibe nada**: ni la buena respuesta de la
IA ni el fallback. Defecto de diseño: el ruteo (`session_id`, `conversation_id`, `account_id`,
`platform`) viaja dentro del eco JSON que hace la propia IA, así que la red de seguridad
hereda datos del único item que no los tiene. El agente no tiene output parser — el formato
JSON depende solo del prompt, por lo que el texto plano ocurrirá siempre de vez en cuando.

## Scope

**In:**

1. **`Separar_variables_en_json` (workflow vivo ycloud):** en las tres salidas de error
   (`JSON_PARSE_ERROR`, `INVALID_OUTPUT_TYPE` y el `catch`), inyectar `session_id`,
   `conversation_id`, `account_id` y `platform` desde
   `$('Obtener_configuracion_agente').item.json` (eco del request, upstream garantizado de la
   rama), con try/catch y sin sobrescribir claves existentes.
2. **Contenido de recuperación:** para `JSON_PARSE_ERROR` y `catch` (cuando
   `item.json.output` es string no vacío), enviar **el propio texto de la IA** como
   `output`/`text`/`content` si no parece JSON roto; si está vacío o parece fragmento JSON
   (empieza con `{`/`[` o contiene patrón `"clave":`), usar `fallbackTexto` (fallback_message
   de Odoo). `INVALID_OUTPUT_TYPE` → siempre `fallbackTexto`.
3. **Ruteo del item de error sin cambios:** se mantiene `tipoPregunta='FALLBACK'`,
   `flow_name='flujo_agendamiento_default'` y **sin** `esPreguntaSiNo` → el item siempre sale
   por `Enviar_mensaje_de_IA1` como texto plano (sin botones interactivos).
4. **Export** del workflow a `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/` (única fuente
   de verdad), sin copias en el repo.

**Out of scope:**

- Output parser estructurado en `Agente_Informacion_basica` (reducir la frecuencia del texto
  plano; propia spec si llega).
- Variante chatwoot del workflow (el incidente es YCloud; el sender es otro).
- `Enviar_mensaje_de_IA2` y demás nodos de envío (su ruteo viene de
  `Cita_con_Equipo_asignado`/`tomar_parametros`, no del parseo).
- Cambios Python/Odoo: ninguno.

## Modelo de datos

Sin estructuras nuevas. El item de recuperación gana las claves `session_id`,
`conversation_id`, `account_id`, `platform` (mismos nombres que el camino normal) y conserva
`error`, `message`, `original`, `_raw_extracted` para debugging.

## Plan de implementación

1. Editar el jsCode de `Separar_variables_en_json` en la instancia n8n en vivo: helper
   `routingFields` (lectura try/catch de `$('Obtener_configuracion_agente')`) + helper
   `textoRecuperacion(raw)` (prosa válida vs `fallbackTexto`); aplicar a las tres salidas de
   error.
2. Prueba determinista en n8n: ejecutar el code node con el item del incidente fijado como
   entrada (`{output: "<prosa de la IA>"}`) y verificar que el item de salida trae
   `account_id`/`session_id`/`platform` no vacíos y `output` = la prosa.
3. Smoke E2E WhatsApp en staging: mensaje normal → respuesta normal sin cambios (regresión
   del camino parseado).
4. Exportar el workflow a `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/`.

## Criterios de aceptación

- [ ] Con el item del incidente como entrada, la salida del code node contiene `account_id`,
      `session_id`, `conversation_id` y `platform` no vacíos.
- [ ] En ese caso `output`/`text`/`content` = la prosa de la IA (no el fallback genérico).
- [ ] Con `output` vacío o fragmento JSON (empieza con `{`/`[` o contiene `"clave":`),
      `output` = `fallbackTexto`.
- [ ] `Enviar_mensaje_de_IA1` arma el body con `from` y `to` resueltos → YCloud responde 200
      (sin `PARAM_MISSING`).
- [ ] El camino normal (JSON válido de la IA) queda intacto: ningún campo del item parseado
      es sobrescrito por la inyección.
- [ ] Export n8n actualizado solo en `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/`.

## Decisiones tomadas y descartadas

- **Tomado:** inyectar el ruteo en el code node — **descartado** endurecer solo el jsonBody de
  `Enviar_mensaje_de_IA1` (duplica lógica y deja rotos los checks de `platform` de los IFs
  intermedios) — **descartado** ambos (defensa en profundidad innecesaria: un solo punto de
  inyección arregla toda la cadena downstream).
- **Tomado:** enviar la prosa de la IA como recuperación — **descartado** fallback genérico
  siempre (descarta respuestas buenas; en el incidente la respuesta era correcta).
- **Tomado:** heurística "parece JSON roto" → fallback — protege al usuario de recibir
  fragmentos JSON.
- **Tomado:** item de error siempre texto plano por `Enviar_mensaje_de_IA1` — **descartado**
  recomputar `esPreguntaSiNo`/menús en el item de error (menos riesgo de rama de botones).
- **Descartado:** output parser estructurado (fuera de scope; cambia comportamiento del agente).
- **Descartado:** tocar la variante chatwoot o `Enviar_mensaje_de_IA2` (rutas con otra fuente
  de ruteo).
- **Corrección (lección del 12/9):** n8n 2.x usa modelo **draft/versión/publish** — editar
  `workflow_entity` directo NO llega al runtime (el editor lee la última `workflow_history`
  y el webhook ejecuta la versión publicada en `workflow_publish_history`). Los cambios
  quedaron aplicados actualizando la versión publicada `07f87bba` (+ borrar
  `n8n:cache:collaboration` del workflow en Redis + restart). Mecanismo futuro: editar en
  el editor y **Publish**, o cirugía sobre la versión publicada.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| `$('Obtener_configuracion_agente')` inaccesible en el code node (ej. ejecución manual) | try/catch: degrada al comportamiento actual (fallback; el 400 solo en esa doble falla) |
| Heurística demasiado laxa → el usuario recibe un fragmento JSON | Regex conservadora (empieza con `{`/`[` o patrón `"clave":`) + caso del incidente cubierto en la prueba determinista |
| Prosa que contiene patrón `"clave":` (raro) | Cae al fallback genérico: falla segura |

## What is **not** in this spec

- Output parser estructurado para el agente.
- Variante chatwoot del workflow.
- `Enviar_mensaje_de_IA2` y otros nodos de envío.
- Cambios Python/Odoo.

Cada uno de esos, si llega, va en su propia spec.