# SPEC 34 — Aislamiento total de modos: carrito vs. negocio

> **Status:** Implemented
> **Depends on:** SPEC 29 (exclusión auto-detección), SPEC 31 (gate carrito), SPEC 32 (JSON plano), SPEC 33 (catálogo amigable)
> **Date:** 2026-09-12
> **Objective:** Que el modo carrito y el modo negocio estén 100% aislados: en carrito el usuario solo ve lógica de compra (sin LLM de negocio ni RAG), con salida explícita ("salir/cancelar") que regresa al negocio, y sin que el agente de negocio confunda preguntas de compra con preguntas del negocio.

## Por qué existe esta spec

Verificado en código (12/9): `configuracion_agente` (chatbot_0_inicio_agendar_procesar_paso_conroller.py:406-413) entrega al LLM el prompt del negocio **con el bloque del carrito prepended** → el LLM ve ambos contextos y los mezcla (confusión reportada). `chatbot.session.estado['modo']='CARRITO'` ya se escribe (chatbot_session.py:38) pero `_esta_en_modo_carrito` nunca se lee. El flujo `CANCELAR` del carrito (chatbot_cart_controller.py:212-220) pregunta "1/2/3" sin handler para esas respuestas → la salida nunca se completa ("no funcionó").

## Scope

**In:**

1. **`ai_chatbot_1_portal` — `configuracion_agente`:** leer `estado['modo']` de `chatbot.session` (via import suave de `chatbot_cart`). Si `modo == 'CARRITO'` → `system_prompt` = solo instrucciones mínimas de carrito (sin negocio, sin RAG) + campo nuevo `modo_carrito: true`. Si negocio → prompt actual + anuncio (comportamiento hoy, sin bloque de instrucciones de operación del carrito — el disparo "carrito" se mantiene).
2. **n8n — ruteo por modo:** nuevo IF tras `Obtener_configuracion_agente`: si `modo_carrito=true` → ruta directa a `Chatbot_cart_procesar` (texto crudo del usuario), **sin pasar por Agente_Informacion_basica ni Simple Memory**. Export actualizado en `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/`.
3. **`chatbot_cart` — salida del carrito:** nueva acción `SALIR` en el clasificador (fallback determinista: "salir", "cancelar", "menú principal", "volver", "dejar carrito"). Con items → pregunta única "¿1️⃣ guardo y salgo / 2️⃣ vacío y salgo?" con handler para `1`/`2`; carrito vacío → sale directo. Al salir: `estado['modo']='NEGOCIO'` + mensaje de re-bienvenida del negocio.
4. **`chatbot_cart` — respuesta determinista a preguntas de negocio en carrito:** acción no reconocida como carrito → "🛒 Estás de compras. Para preguntas del negocio escribe *salir*." (sin RAG, sin LLM de negocio).
5. **Re-entrada:** "carrito" en modo negocio → marca `modo='CARRITO'` (ya ocurre al procesar; confirmar) y restaura carrito guardado.
6. Bump `chatbot_cart` → `1.2.0` (o siguiente) y `ai_chatbot_1_portal` → siguiente patch. Tests nuevos + regresión.

**Out of scope:**
- Checkout/pagos (ya materializa sale.order; solo se toca el flujo de salida).
- Memoria n8n compartida entre modos (la memoria del negocio simplemente no se consulta en modo carrito; no se borra nada).
- Menú determinista, RAG, datos de otros clientes.

## Modelo de datos

Sin campos nuevos: se usa `chatbot.session.estado['modo']` existente (valores `'CARRITO'` / `'NEGOCIO'`). `estado['modo']='NEGOCIO'` se escribe al salir del carrito (crea el registro si no existe, mismo patrón de `_guardar_carrito`).

## Plan de implementación

1. `chatbot_cart/models/chatbot_session.py`: `_salir_modo_carrito(session_id)` → modo `NEGOCIO` + conserva/limpia items según parámetro.
2. `chatbot_cart/uses_cases/clasificar_accion_carrito_use_case.py`: acción `SALIR` en fallback + prompt IA; handler de `1`/`2` post-CANCELAR (estado pendiente en `carrito['pendiente_salida']`).
3. `chatbot_cart/controllers/chatbot_cart_controller.py`: `_ejecutar` maneja `SALIR` y las respuestas 1/2; mensaje determinista para intención no reconocida; respuestas de salida con `finalizado` según corresponda.
4. `ai_chatbot_1_portal/controllers/chatbot_0_inicio_agendar_procesar_paso_conroller.py`: en `configuracion_agente`, branch por `modo` (import suave, degrada a comportamiento actual si `chatbot_cart` no está instalado).
5. n8n: IF `modo_carrito` → bypass del agente → `Chatbot_cart_procesar` → `Unificar_salida_carrito` → envío (reusa cadena existente). Export JSON a `n8n_json/ycloud/`.
6. Tests: salida con/vacío items, handler 1/2, pregunta de negocio en carrito, `configuracion_agente` en ambos modos, regresión suites `chatbot_cart` + `ai_chatbot_1_portal`.

## Criterios de aceptación

- [ ] En modo CARRITO, `configuracion_agente` devuelve `modo_carrito=true` y prompt sin contenido de negocio ni bloque del menú.
- [ ] En modo CARRITO, ningún mensaje pasa por el LLM de negocio ni por la memoria del negocio (ruta n8n directa).
- [ ] Pregunta de negocio en carrito → respuesta determinista que sugiere `salir` (sin RAG).
- [ ] "salir"/"cancelar" con items → pregunta 1/2; responder 1 guarda y sale; 2 vacía y sale; ambos ponen `modo='NEGOCIO'`.
- [ ] "salir" con carrito vacío → sale directo a NEGOCIO con re-bienvenida.
- [ ] En modo NEGOCIO, "carrito" entra al carrito y restaura items previos guardados.
- [ ] Suites `chatbot_cart` y `ai_chatbot_1_portal` en verde.
- [ ] Export n8n actualizado solo en `/home/odoo/prod/odoo19-skeleton/n8n_json/ycloud/` (sin copias en el repo).

## Decisiones tomadas y descartadas

- **Tomado:** modo carrito 100% determinista (sin LLM) — aislamiento real, latencia menor, costo cero por mensaje de compra.
- **Tomado:** salida con items pregunta guardar/vaciar (una sola vez, con handler).
- **Tomado:** editar el workflow n8n en esta spec (necesario para el bypass; SPEC 31 lo tenía excluido).
- **Descartado:** LLM con prompt solo-carrito (sigue probabilístico y más lento).
- **Descartado:** salida automática ante pregunta de negocio (rompe la compra a mitad; el usuario debe decidir salir).
- **Descartado:** borrar memoria del negocio al entrar al carrito (la memoria no se consulta en modo carrito; preservarla evita perder contexto de citas en curso).

## Riesgos identificados

- Si `modo` queda en `CARRITO` huérfano (crash a mitad), el usuario queda atrapado: mitigación — el mensaje determinista de intención no reconocida siempre menciona `salir`, y `SALIR` con carrito vacío sale directo.
- El IF de n8n depende de que `configuracion_agente` responda antes del agente; si el endpoint falla, degrada al comportamiento actual (sin `modo_carrito` → ruta LLM).