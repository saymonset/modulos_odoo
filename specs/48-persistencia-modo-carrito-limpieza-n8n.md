# SPEC 48 — Persistencia del modo carrito y limpieza n8n

> **Status:** Approved
> **Depends on:** SPEC 34, SPEC 40, SPEC 44, SPEC 46
> **Date:** 2026-09-16
> **Objective:** Hacer que el modo carrito persista en la sesión Odoo en la entrada búsqueda-first y que el 2.º turno ("catálogo") rutee directo al carrito, más limpieza quirúrgica de nodos muertos en los workflows ycloud.

## Por qué existe

Tras la SPEC 44 el 1.er turno "carrito" funciona (menú vía subflow), pero la sesión Odoo queda en modo NEGOCIO: `_respuesta_buscador` no llama a `_guardar_carrito`. En el 2.º turno `configuracion_agente` devuelve `modo_carrito=false`, el orquestador cae al LLM/flujos y el usuario ve "No hay un flujo activo". El hardcode `modo: 'CARRITO'` en `_respuesta` (línea 187) es cosmético. Además quedaron nodos muertos en ambos workflows y claves API en texto plano.

## Scope

**In:**

1. **Odoo** — `chatbot_cart/controllers/chatbot_cart_controller.py::_respuesta_buscador`: persistir con `session._guardar_carrito(session_id, carrito)` (conserva items, setea `modo=CARRITO`) antes de responder.
2. **Odoo (defensa)** — `ai_chatbot_1_portal/controllers/chatbot_0_inicio_agendar_procesar_paso_conroller.py:316-333`: en el branch "sin `paso`", si `_esta_en_modo_carrito(session_id)`, devolver la respuesta de `/chatbot_cart/procesar` en vez de "No hay un flujo activo".
3. **Test** — nuevo test en `chatbot_cart/tests` + caso para el 2.º turno en los tests de `ai_chatbot_1_portal`.
4. **n8n orquestador** `ycloud_create_lead_0_con_menu_whatsapp` — borrar nodos huérfanos `Chatbot_cart_procesar` y `Unificar_salida_carrito` (sin conexiones in/out).
5. **n8n subflow** `ycloud_carrito_subflow` — quitar el dead-code `$('Cita_con_Equipo_asignado')` en `Unificar_salida_carrito` (el `try/catch` cae siempre a `$json`).
6. **Seguridad n8n** — los HTTP Request a YCloud del subflow usan **credencial n8n** (header auth) en vez de `X-API-Key` plano.
7. **Exports** — actualizar los 3 JSON en `/home/odoo/lead/odoo19-skeleton/n8n_json/ycloud/` tras los cambios en la nube (SPEC 43). El export del orquestador ya fue re-hecho y verificado (contiene `Call 'ycloud_carrito_subflow (modo)'` y `(flujo)`).
8. **Promoción** — módulo Odoo a prod y JSONs a `/home/odoo/prod/odoo19-skeleton/n8n_json/` solo tras E2E verde en lead.

**Out of scope (para specs futuras):**

- Refactor de la cadena de envío duplicada del subflow (5 nodos → fusión).
- Refactor del flujo Chatwoot.
- Cambios a `Unificar_salida_carrito` más allá del dead-code, ni al clasificador.

## Data model

Esta feature no introduce estructuras nuevas. Reutiliza:

- `chatbot.session.estado['modo']` (`CARRITO`/`NEGOCIO`) — SPEC 34.
- Contrato de `/chatbot_cart/procesar` (`texto_para_usuario`, `botones`, `imagenes`, `lista_categorias`, `finalizado`, `modo`) — SPEC 39/40/46.
- Mapeo de inputs del subflow `ycloud_carrito_subflow` — SPEC 43/44.

## Implementation plan

1. **Respaldo de rollback**: exportar los 2 workflows nube (orquestador + subflow) a `/tmp/opencode/`.
2. **Fix Odoo** en `_respuesta_buscador`: persistir modo. Verificación manual: POST a `/chatbot_cart/procesar` con `valor="carrito"` → `chatbot.session.estado.modo == 'CARRITO'`.
3. **Defensa Odoo** en `procesar_paso` (delegación a carrito). Verificación manual: POST con sesión en modo carrito y sin `paso` → respuesta del carrito, no el texto genérico.
4. **Tests**: `test_XX_buscador_persiste_modo_carrito` (assertTrue `_esta_en_modo_carrito` tras `_respuesta_buscador`) + caso 2.º turno (`configuracion_agente` → `modo_carrito == True`). Suite del módulo en verde.
5. **n8n en vivo (API/UI)**: borrar nodos huérfanos del orquestador; limpiar dead-code del subflow; reemplazar `X-API-Key` plano por credencial header-auth en los HTTP Request de YCloud.
6. **Exports**: actualizar los JSON en `/home/odoo/lead/odoo19-skeleton/n8n_json/ycloud/` — commit en el repo lead.
7. **E2E lead**: WhatsApp real — "carrito" → menú; luego "catálogo" → catálogo directo (sin "No hay un flujo activo"); "ayuda" → menú de ayuda; "🏪 Volver al negocio" → salida; pregunta de negocio tras salir → flujo normal.
8. **Promoción manual a prod**: copiar módulos Odoo afectados (`chatbot_cart`, `ai_chatbot_1_portal`) y JSONs a prod con commit en rama `main` de prod.

## Acceptance criteria

- [ ] Test `buscador persiste modo` en verde tras actualizar `chatbot_cart`.
- [ ] Test 2.º turno (`modo_carrito == True` en `configuracion_agente`) en verde.
- [ ] POST `/chatbot_cart/procesar` con "carrito" deja la sesión en `estado['modo']=='CARRITO'`.
- [ ] `procesar_paso` con sesión en CARRITO y sin `paso` devuelve la respuesta del carrito.
- [ ] E2E lead: "carrito" → menú; "catálogo" → catálogo; "ayuda" → ayuda; "🏪 Volver al negocio" → sale; luego una pregunta de negocio responde el flujo normal.
- [ ] El orquestador en la nube no tiene nodos huérfanos (`Chatbot_cart_procesar`/`Unificar_salida_carrito` ausentes).
- [ ] El subflow no referencia `$('Cita_con_Equipo_asignado')`.
- [ ] Ningún HTTP Request del subflow lleva `X-API-Key` en texto plano (usa credencial n8n).
- [ ] Los 3 JSON de lead reflejan la nube (SPEC 43) y nada se copió a prod sin E2E verde.

## Decisions

- **Sí:** persistir dentro de `_respuesta_buscador` reusando `_guardar_carrito` — un solo punto, sin métodos nuevos (DRY).
- **Sí:** defensa en `procesar_paso` — red de seguridad ante cualquier pérdida futura de estado.
- **Sí:** API key a credencial n8n — toca los mismos nodos, mejora de seguridad sin extra riesgo.
- **No:** fusionar la cadena de envío del subflow — toca lo probado en producción; queda para otra spec.
- **No:** gate determinista por keywords en n8n antes del LLM — con la persistencia arreglada, el gate `¿Modo_carrito?` es suficiente; menos nodos.
- **No:** cambiar el hardcode `modo:'CARRITO'` en `_respuesta` — deja de mentir una vez que se persiste.

## Risks

| Riesgo | Mitigación |
|---|---|
| Workflow nube ≠ export local tras tocar en la nube | Re-export inmediato de los 3 JSON después del paso 5 |
| La defensa en `procesar_paso` secuestra mensajes legítimos | Solo actúa si `_esta_en_modo_carrito`; sesión en NEGOCIO sin `paso` mantiene el texto genérico (test) |
| Borrar la `X-API-Key` plano rompe envíos YCloud | Cambiar nodo por nodo y probar con el trigger manual del subflow; rollback con export del paso 1 |
| Sesiones en curso a mitad del deploy | El fix añade persistencia a futuro; sesiones previas no son retroactivas — el usuario reescribe "carrito" |

## What is **not** in this spec

- Fusión de la cadena de envío duplicada del subflow.
- Refactor del flujo Chatwoot / `yclod-simple_1_subflow`.
- Gate por keywords en n8n.
- Cambios a `_PALABRAS_*` del clasificador ni al texto de "ayuda".

Cada uno de esos, si llega, va en su propia spec.
