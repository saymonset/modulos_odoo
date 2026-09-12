# SPEC 35 — Fix de routing: valor del usuario perdido en la activación del carrito

> **Status:** Approved
> **Depends on:** SPEC 33 (fix de routing, pendiente), SPEC 34 (aislamiento de modos, implementado)
> **Date:** 2026-09-12
> **Objective:** Que "carrito"/"ver carrito" desde modo negocio lleguen a `/chatbot_cart/procesar` con el texto real del usuario (hoy llega vacío y responde el mensaje genérico), activando el modo CARRITO en la instancia lead.

## Por qué existe esta spec

Transcript real del 12/9 (bot Karla Campoverde, lead.integraia.lat): la usuaria escribió
"carrito" y "ver carrito" y recibió dos veces *"Escribe ver carrito, ayuda o el nombre de
un producto para comenzar."* — el texto exacto de la rama `valor` vacío en
`chatbot_cart_controller.py:101`. Verificado en el export n8n: el nodo `Chatbot_cart_procesar`
envía `"valor": "{{ $json.text }}"`, pero en la rama `¿Flujo_carrito?` el item proviene de
`Separar_variables_en_json`, cuyo resultado normal (`{...datosParseados, output, tipoPregunta}`)
NO incluye el `text` del usuario → `valor` llega vacío → nunca se procesa el carrito, nunca se
setea `estado['modo']='CARRITO'` y el bypass `¿Modo_carrito?` (SPEC 34) jamás opera. El módulo
chatbot_cart 1.5.0 funciona; el problema es 100% de mapeo en el workflow n8n.

## Scope

**In:**

1. **Fix en n8n VIVO (no solo el export):** `Chatbot_cart_procesar` lee `valor`, `session_id`,
   `conversation_id` y `account_id` de `$('Obtener_configuracion_agente').item.json.*` (el
   endpoint ecoa el request completo) usando el patrón `JSON.stringify(...)` — el mismo de
   `Obtener_configuracion_agente` — para no romper el JSON con comillas/saltos de línea.
2. **Verificación BD lead** (odoo-db19-leads, NO prod): `flujo_carrito_compra` existe y está
   activo (evidencia del transcript: el anuncio aparece → `carrito_disponible` = true). Solo
   verificar; no crear.
3. **Higiene de staging:** upgrade `-u chatbot_cart,ai_chatbot_1_portal` en `odoo-19-web-leads`
   + suites de tests en verde. Sin cambios Python (1.5.0 ya trae CATALOGO/SALIR/botones).
4. **Export del workflow** actualizado a `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/`
   (única fuente de verdad), sin copias en el repo.

**Out of scope:**

- Respuestas de RAG ante tipos de inmueble inexistentes ("fincas"/"terrenos") — decisión: correcto, no tocar.
- Despliegue a prod Odoo (prod no corre el bot; ahí solo viven los JSON n8n).
- Nueva UX del carrito (catálogo visual, paginación) — ya implementado en SPEC 33/34.

## Modelo de datos

Sin estructuras nuevas. Se reusa `chatbot.session.estado['modo']` (valores `'CARRITO'`/`'NEGOCIO'`).

## Plan de implementación

1. Editar el workflow en la instancia n8n en vivo: jsonBody de `Chatbot_cart_procesar` con
   `JSON.stringify($('Obtener_configuracion_agente').item.json...)` para `valor` e ids.
2. Verificar en BD lead el flujo activo; `docker exec odoo-19-web-leads odoo -d odoo-db19-leads
   -u chatbot_cart,ai_chatbot_1_portal --stop-after-init` + restart + tests.
3. Exportar el workflow a la ruta prod de JSONs.
4. E2E WhatsApp staging replicando el transcript: "carrito" → entra al carrito (no genérico);
   "catálogo" → tarjetas; "salir" → vuelve al negocio.

## Criterios de aceptación

- [ ] "carrito"/"ver carrito" desde modo negocio NUNCA responden el mensaje genérico de valor vacío.
- [ ] Tras "carrito", `estado['modo']='CARRITO'` y los mensajes siguientes van por el bypass `¿Modo_carrito?` (sin LLM de negocio).
- [ ] Texto del usuario con comillas o saltos de línea no rompe el jsonBody (JSON.stringify).
- [ ] `flujo_carrito_compra` verificado activo en BD lead.
- [ ] Suites `chatbot_cart` + `ai_chatbot_1_portal` en verde en staging.
- [ ] Export n8n actualizado solo en `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/`.

## Decisiones tomadas y descartadas

- **Tomado:** fix en el workflow n8n en vivo; el JSON exportado es registro, no el cambio.
- **Tomado:** leer `valor`/ids de `$('Obtener_configuracion_agente')` (eco del request, presente en ambas ramas) — **descartado** reparar `text` en `Separar_variables_en_json` (toque más invasivo en código compartido por otras ramas).
- **Tomado:** verificar el flujo en la BD lead — **descartado** crearlo/activarlo (la consulta previa que motivó "no existe" fue contra la BD prod; el anuncio en el transcript prueba que en lead ya está activo).
- **Tomado:** sin cambios Python ni bumps — chatbot_cart 1.5.0 ya contiene todo lo necesario.
- **Descartado:** tocar respuestas de RAG para "fincas/terrenos" (decisión del usuario: correcto así).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| El LLM no activa el flujo ante "carrito" (desobedece el prompt) | El bloque del carrito ya dice "INMEDIATAMENTE, PRIORIDAD" y el transcript muestra que el routing sí se activó; criterio E2E lo cubre |
| Referencia `$('Obtener_configuracion_agente')` si el nodo falla (timeout) | El flujo ya depende de ese nodo para todo; si falla, degrada igual que hoy |
| Editar n8n vivo sin export posterior | Paso 3 explícito del plan (export = fuente de verdad) |

## What is **not** in this spec

- Respuestas de RAG para tipos de inmueble inexistentes (fincas/terrenos).
- Despliegue a prod Odoo (solo el JSON n8n vive en prod).
- Nueva UX del carrito (ya cubierta por SPEC 33/34).

Cada uno de esos, si llega, va en su propia spec.