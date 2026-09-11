# SPEC 29 — Carrito automático universal con gate de productos

> **Status:** Implemented
> **Depends on:** SPEC 28 (fixes carrito + prueba WhatsApp), SPEC 17, SPEC 18
> **Date:** 2026-09-11
> **Objective:** Que el flujo `flujo_carrito` se active automáticamente para todo cliente en cada sincronización desde RAG — sin pasos manuales — con gate bloqueante: si el módulo no está instalado o el negocio no tiene productos vendibles con precio, nunca se activa ni se inyecta en el prompt.

## Por qué existe esta spec

Caso real (2026-09-11, bot Karla Campoverde): el usuario preguntó "tienes pizza" y el bot desvió a "no ofrecemos pizzas…". `flujo_carrito` existe y está activo en la BD, pero no está en `flujo_ids` de la `chatbot.config` del cliente, así que ni el prompt del agente ni el `flow_map` lo incluyen tras la sync. El onboarding deja un paso manual (marcar flujos por cliente). El carrito es una **capacidad universal** (como `flujo_agendamiento_default`), no un flujo de negocio, y debe encenderse solo: siempre que haya productos; nunca si no los hay o el módulo no está.

## Scope

**In:**

- **Universal con gate (en `ai_chatbot_1_portal`):** `aplicar_deteccion_automatica`, `_aplicar_deteccion_desde_config` y `action_recargar_todo_desde_rag` incluyen `flujo_carrito` en el set de flujos activos del cliente SIEMPRE que el gate pase, aunque la detección por keywords/IA no lo mencione. Es una capacidad, no depende del texto del negocio.
- **Gate de disponibilidad (en `chatbot_cart`):** helper `CartService.disponible(env)` → `∃ product.template` con `sale_ok=True` **y** `list_price > 0`. Lo llaman ambos módulos. Si `chatbot_cart` no está instalado, el gate devuelve `False` y la inclusión se omite limpiamente (guard, sin romper el sync).
- **Gate de prompt:** `configuracion_agente` (chatbot_cart) solo inyecta el bloque `=== CARRITO DE COMPRAS ===` si `disponible(env)` es `True`. Sin productos vendibles o sin módulo, el agente no menciona el carrito.
- **Carrito sin pasos genéricos:** en `data/chatbot_flujo_carrito_data.xml`, `flujo_carrito` nace con `generar_pasos_automatico = False`; la migración elimina los 13 pasos genéricos ya creados (`paso_ids`). El carrito lo gestiona `/chatbot_cart/procesar`, no la captura clásica (`inicioagendar`).
- **Resumen de sync visible:** el mensaje del botón "Sincronizar todo desde RAG" registra el estado del carrito: `"Carrito: activado"` / `"Carrito: omitido (sin productos vendibles)"` / `"Carrito: omitido (módulo chatbot_cart no disponible)"`.
- Bump de versiones (`chatbot_cart` → `19.0.1.2.0`, `ai_chatbot_1_portal` → `19.0.1.0.36`) + tests deterministas.

**Out of scope (para futuras specs):**

- Cambios en n8n (el Switch del carrito del SPEC 28 queda intacto; el `flow_map` ya entrega `flujo_carrito` si el flujo queda activo).
- Deploy a producción.
- Alta/baja automática del catálogo (una vez registrados los productos, entran al gate).
- Carrito para Instagram/Messenger.

## Data model

Sin campos nuevos. Cambios de comportamiento sobre datos existentes:

```
chatbot.flujo 'flujo_carrito':
  generar_pasos_automatico: True → False
  paso_ids: se eliminan los 13 genéricos actuales (migración)

'Sincronizar todo desde RAG' / activaciones por config:
  flujo_ids: incluye flujo_carrito cuando el gate pasa (universal)
```

## Implementation plan

1. `chatbot_cart`: `CartService.disponible(env)` (gate) y su uso en `configuracion_agente_controller` (no inyectar el bloque sin gate). Test manual: prompt sin productos → sin bloque CARRITO; con productos → lo incluye.
2. `chatbot_cart`: `data/chatbot_flujo_carrito_data.xml` con `generar_pasos_automatico=False` + migración que borre `paso_ids` de `flujo_carrito`. Test: el flujo no tiene pasos tras upgrade.
3. `ai_chatbot_1_portal`: universal con gate en `_aplicar_deteccion_desde_config` y `aplicar_deteccion_automatica`. Test manual: `flujo_carrito` activo con config que no lo marca, si hay productos.
4. `ai_chatbot_1_portal`: en `action_recargar_todo_desde_rag`, mezclar `flujo_carrito` (gated) en `flujos_detectados` antes del `write flujo_ids` y añadir la línea de resumen del carrito. Test manual: sync en bot Karla → mensaje dice "Carrito: activado".
5. Tests deterministas (sync con/sin productos, prompt con/sin gate, flujo sin pasos) + bump de versiones + suite completa en verde.

## Acceptance criteria

- [ ] Tras "Sincronizar todo desde RAG" en cliente con productos vendibles (sale_ok y precio > 0), `chatbot.config.flujo_ids` incluye `flujo_carrito` — sin marcarlo a mano.
- [ ] Tras sync en cliente sin productos vendibles, `flujo_carrito` queda desactivado y fuera de `flujo_ids`, y el resumen dice `"Carrito: omitido (sin productos vendibles)"`.
- [ ] Si `chatbot_cart` no está instalado, el sync funciona igual y el resumen lo indica, sin error.
- [ ] Tras cada activación por config (sync o botón "Activar solo los flujos marcados"), `flujo_carrito` queda activo si el gate pasa.
- [ ] El `system_prompt` del agente incluye el bloque CARRITO solo cuando el gate pasa; con un negocio sin productos, el prompt no lo menciona.
- [ ] `flujo_carrito` tiene `paso_ids` vacío tras el upgrade y `generar_pasos_automatico=False`.
- [ ] Con `flujo_carrito` activo: las operaciones del carrito ("agrega", "ver carrito", "pagar") pasan por `/chatbot_cart/procesar`; las consultas de producto siguen por `Base_Conocimiento_RAG` (regla 13).
- [ ] Suites deterministas en verde para `chatbot_cart` (55) y `ai_chatbot_1_portal` (incluyendo los tests nuevos).

## Decisions

- **Sí:** carrito como capacidad universal con gate, no como flujo detectado por keywords/IA: la sync de una inmobiliaria nunca menciona "pizza", pero el cliente con catálogo debe poder comprar.
- **Sí:** gate = `∃ product.template` con `sale_ok=True` **y** `list_price > 0`. Evita activarlo por productos residuales de precio 0 (Tips/Anticipo) que son solo de pago en PDV.
- **Sí:** el gate se evalúa en cada sync/activación — al quitarse los productos, el carrito se desactiva solo en la próxima sync (comportamiento reversible, sin estado extra).
- **Sí:** `flujo_carrito` sin pasos: n8n delega directo a `/chatbot_cart/procesar`; la captura clásica (`inicioagendar`) no aplica.
- **Sí:** prompt de agente y flujo con el mismo gate (coherencia: nunca prometer algo que el endpoint no puede ofrecer).
- **No:** flag por cliente ("habilitar carrito") — el gate por productos ya decide; un flag añadiría una configuración más que olvidar.
- **No:** desactivar el bloque n8n del carrito — SPEC 28 sigue siendo la rama funcional.

## Risks

| Riesgo | Mitigación |
|---|---|
| Productos placeholder con precio ≠ 0 (Tips, Anticipo) activan el carrito en un cliente sin catálogo real | El gate exige venta con precio; el resumen de sync lo hace visible y, si hace falta, un criterio más estricto (stock/imagen) va en otra spec |
| El agente multicliente insiste en los CTAs del negocio (ej. inmobiliaria) en vez de activar el carrito | El bloque CARRITO se inyecta al final del prompt (tras el rol del cliente) y se valida post-sync; la regla de activación es "usuario confirma que quiere comprar" |
| `chatbot_cart` desinstalado a mitad de vida | Odoo elimina el flujo con la desinstalación; el sync con guard no rompe; el prompt deja de inyectarlo |
| Doble escritura de `flujo_ids` (sync + activación por config) | El write está centralizado en `action_recargar_todo_desde_rag` y la inclusión universal en `_aplicar_deteccion_desde_config`; se testea el set resultante |

## What is **not** in this spec

- Deploy a producción (rama/pipeline normal).
- Nuevos nodos o workflows de n8n.
- Otros canales (Instagram/Messenger), carrusel o catálogo iterativo.
- Gestión del catálogo en sí (carga/import de productos) — los productos ya viven en `product.template`.