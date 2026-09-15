# SPEC 44 — Subflow de carrito independiente (ycloud)

> **Status:** Implemented
> **Depends on:** SPEC 34 (aislamiento modo carrito), SPEC 39 (catálogo imágenes), SPEC 40 (categorías)
> **Date:** 2026-09-15
> **Objective:** Extraer la lógica de carrito del workflow principal `ycloud_create_lead_0_con_menu_whatsapp` a un subflow autocontenido `ycloud_carrito_subflow`, dejando dos gates que lo llaman y terminan la rama, de modo que carrito y flujo principal puedan vivir y activarse por separado.

## Por qué existe esta spec

Hoy la lógica de carrito está incrustada en el workflow principal: `¿Modo_carrito?` → `Chatbot_cart_procesar` → `Unificar_salida_carrito` → `¿Enviar menú interactivo?1` (compartido con el flujo normal vía `Unificar_salida`). Eso impide desplegar/activar el carrito independientemente del flujo de negocio, y hace que tocar uno rompa el otro. La intención es que el carrito "el día del amanecer" pueda vivir sin el flujo principal y viceversa.

## Scope

**In:**

1. **Subflow nuevo `ycloud_carrito_subflow`** (folder `ycloud`, proyecto INTEGRAIA, id proyecto `8nX7JPpIR54QE71D`):
   - Trigger `executeWorkflowTrigger` con inputs **iguales al mapeo del Call existente** de `yclod-simple_1_subflow`: `text, session_id, account_id, conversation_id, platform, channel, user_number, phone_number, user_name, image_url, message_type, content, file_type, agente_desactivado` + `phone_number_formatted` (para el envío).
   - Trigger `When clicking 'Execute workflow'` para pruebas manuales (patrón del subflow actual).
   - Nodos: `Chatbot_cart_procesar` (HTTP POST a `https://lead.integraia.lat/chatbot_cart/procesar`, adaptado para leer `session_id/conversation_id/account_id/text` del input del trigger, no de `Obtener_configuracion_agente`) → `Unificar_salida_carrito` (código SPEC 39/40 intacto; el `try/catch` de `Cita_con_Equipo_asignado` cae a `$json`) → **cadena de envío duplicada**: `¿Enviar menú interactivo?1` + `Construir_botones_WhatsApp` + `Enviar texto despues del menu` + `Enviar_mensaje_de_IA1` + `Fin menú WhatsApp1` (copias idénticas con credencial YCloud).
   - **Independiente total:** el subflow no devuelve control al flujo principal.

2. **Flujo principal `ycloud_create_lead_0_con_menu_whatsapp`:**
   - Conserva `¿Modo_carrito?` (tras `Obtener_configuracion_agente`): true → `Call 'ycloud_carrito_subflow (modo)'` (nodo executeWorkflow separado), **fin de rama**; false → `Agente_Informacion_basica`.
   - Conserva `¿Flujo_carrito?` (tras `Cita_con_Equipo_asignado`): true → `Call 'ycloud_carrito_subflow (flujo)'` (nodo executeWorkflow separado), **fin de rama**; false → `paso_0_inicio_agendar`.
   - **Elimina:** `Chatbot_cart_procesar`, `Unificar_salida_carrito`, y la conexión `Unificar_salida_carrito → ¿Enviar menú interactivo?1`.
   - `¿Enviar menú interactivo?1` queda conectado **solo** a `Unificar_salida` (flujo normal).

**Out of scope (para specs futuras):**

- Actualizar exports en `/home/odoo/lead/odoo19-skeleton/n8n_json/` (decisión: solo n8n en vivo).
- Refactor del flujo Chatwoot (`chatbot_create_lead_0_con_menu_whatsapp`) — no tiene carrito.
- Cambios en `Unificar_salida_carrito` (SPEC 39/40) ni en el endpoint `/chatbot_cart/procesar`.

## Modelo de datos

Esta feature **no introduce estructuras de datos nuevas**. Reusa:
- `chatbot.session.estado['modo']` y `modo_carrito` (SPEC 34).
- La respuesta de `/chatbot_cart/procesar` (`texto_para_usuario`, `botones`, `imagenes`, `lista_categorias`, `modo_carrito`, `finalizado`) — SPEC 39/40.
- El contrato de inputs/outputs del subflow existente `yclod-simple_1_subflow` (mismo mapeo).

## Plan de implementación

1. **Respaldar estado actual** en la instancia: `docker exec n8n-container n8n export:workflow --id=L2r9IMI9lGrERuZq` (flujo principal) a `/tmp/opencode/` (rollback).
2. **Crear subflow** `ycloud_carrito_subflow` en el proyecto INTEGRAIA (folder `ycloud`) vía API REST (API key) o `n8n import:workflow --projectId=8nX7JPpIR54QE71D`, con triggers `executeWorkflowTrigger` (input mapeado) + manual.
3. **Copiar al subflow**: `Chatbot_cart_procesar` (reapuntando a `$json.*` del input), `Unificar_salida_carrito` (sin cambios), y la cadena de envío duplicada (`¿Enviar menú interactivo?1` → `Construir_botones_WhatsApp` → `Enviar texto despues del menu` → `Fin menú WhatsApp1`, rama false → `Enviar_mensaje_de_IA1`).
4. **Flujo principal — gates:** en `¿Modo_carrito?` rama true conectar `Call 'ycloud_carrito_subflow (modo)'` (executeWorkflow, mapeo de inputs desde `$json`, sin salida → fin de rama); ídem en `¿Flujo_carrito?` rama true con `Call 'ycloud_carrito_subflow (flujo)'`.
5. **Flujo principal — limpieza:** eliminar `Chatbot_cart_procesar`, `Unificar_salida_carrito`, la conexión `Unificar_salida_carrito → ¿Enviar menú interactivo?1`; verificar que `¿Enviar menú interactivo?1` recibe solo de `Unificar_salida`.
6. **Activar** ambos workflows (active=true) y verificar que no hay nodos huérfanos ni conexiones rotas en la UI.

## Criterios de aceptación

- [ ] `ycloud_carrito_subflow` existe en folder `ycloud` con triggers `executeWorkflowTrigger` + manual.
- [ ] En el subflow, `Chatbot_cart_procesar` lee `session_id/conversation_id/account_id/text` del input del trigger (sin referencia a `Obtener_configuracion_agente`).
- [ ] El subflow contiene la cadena de envío completa (`¿Enviar menú interactivo?1`, `Construir_botones_WhatsApp`, `Enviar texto despues del menu`, `Enviar_mensaje_de_IA1`, `Fin menú WhatsApp1`) y es funcional al ejecutarse manualmente con el trigger de prueba.
- [ ] El flujo principal ya no contiene `Chatbot_cart_procesar` ni `Unificar_salida_carrito`.
- [ ] `¿Modo_carrito?` true → `Call 'ycloud_carrito_subflow (modo)'` (sin salida posterior); false → `Agente_Informacion_basica`.
- [ ] `¿Flujo_carrito?` true → `Call 'ycloud_carrito_subflow (flujo)'` (sin salida posterior); false → `paso_0_inicio_agendar`.
- [ ] `¿Enviar menú interactivo?1` recibe conexión únicamente de `Unificar_salida`.
- [ ] E2E WhatsApp: escribir "carrito" → responde el subflow (catálogo/categorías/imágenes); escribir pregunta de negocio → responde el flujo normal (sin tocar carrito).
- [ ] Ningún export en `/home/odoo/lead/odoo19-skeleton/n8n_json/` fue modificado.

## Decisiones tomadas y descartadas

- **Tomado:** subflow 100% autocontenido con cadena de envío **duplicada** — independencia real; el flujo principal no sabe cómo se envía el carrito.
- **Tomado:** conservar los 2 gates en el flujo principal (¿Modo_carrito?, ¿Flujo_carrito?) → cada uno con su nodo `Call` propio — mínima invasión, se mantiene el ruteo por modo ya probado (SPEC 34).
- **Tomado:** 2 nodos Call separados (uno por gate) — cada rama mapea sus inputs desde su propio `$json`.
- **Tomado:** mismo mapeo de inputs que `yclod-simple_1_subflow` — patrón conocido, evita campos faltantes en el envío.
- **Tomado:** implementación solo en el n8n en vivo (sin exports a lead) — decisión del usuario; el registro versionado queda fuera de esta spec.
- **Descartado:** que el subflow devuelva el control al principal — rompe el aislamiento (objetivo de la spec).
- **Descartado:** un solo nodo Call compartido — mezcla inputs de dos gates distintos.
- **Descartado:** aplicar también al flujo Chatwoot — no tiene lógica de carrito.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Credenciales YCloud duplicadas en la cadena de envío del subflow | Copiar exactas del nodo actual (`X-API-Key` `9332...`) y verificar con el trigger manual |
| Referencia rota en `Unificar_salida_carrito` (usa `$('Cita_con_Equipo_asignado')`) | El `try/catch` ya degrada a `$json`; probar manualmente en el subflow |
| Import del subflow sin folder `ycloud` | Mover vía API REST (PATCH con `parentFolderId`) tras el import |
| Rollback en vivo | Export de respaldo previo (paso 1) de ambos workflows |

## What is **not** in this spec

- Exports en `/home/odoo/lead/odoo19-skeleton/n8n_json/` (SPEC 43).
- Refactor del flujo Chatwoot.
- Cambios al endpoint `/chatbot_cart/procesar` ni a `Unificar_salida_carrito` (SPEC 39/40).
/
Cada uno de esos, si llega, va en su propia spec.
