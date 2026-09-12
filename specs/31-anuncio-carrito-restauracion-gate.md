# SPEC 31 — Restauración del gate del carrito y anuncio de compra vía prompt

> **Status:** Approved
> **Depends on:** SPEC 29 (exclusión de auto-detección), SPEC 30 (botón "Activar carrito")
> **Date:** 2026-09-12
> **Objective:** Que el anuncio 💡 "Escribe «carrito»…" y el disparo del flujo del carrito vuelvan a funcionar restaurando la cadena del gate (flujo recreado + sync que preserva la marca manual), sin tocar n8n ni el mecanismo del RAG.

## Por qué existe esta spec

Verificados en BD/logs (12/9): `flujo_carrito_compra` quedó con **0 registros** tras el churn de flujos; el gate `_carrito_disponible` da False y por tanto el bloque del carrito ya no viaja en el system prompt — el LLM no recibe la instrucción del anuncio ni del disparo (las pruebas de WhatsApp post-fix eran sobre una feature "apagada", no una característica defectuosa). Además, `action_recargar_todo_desde_rag` pierde la marca manual del carrito en cada sync (orden de escritura en `(6,0)`), causa raíz de la exposición a borrado/desmarcado. La sync del RAG, las intenciones y el LLM funcionan correctamente.

## Scope

**In:**

1. **Fix de orden en `ai_chatbot_1_portal/models/chatbot_config.py` (`action_recargar_todo_desde_rag`):** mover la lectura de `marcados_manuales = self.flujo_ids` **antes** del `self.write({'flujo_ids': [(6, 0, flujos_detectados.ids)]})` y re-añadirlos con `(4, id)` después (una sola escritura combinada de preferencia). Es la única alteración a la lógica de la sync.
2. **Recreación de `flujo_carrito_compra`** vía `chatbot.config.action_activar_carrito` (SPEC 30, ya implementado) en la config activa de staging — sin código nuevo.
3. **Prueba de la cadena completa en vivo:** `POST /ai_chatbot_1_portal/configuracion_agente` debe devolver el prompt empezando con `=== CARRITO DE COMPRA ===` (ya implementado en 1.3.2, solo dependía del gate).
4. Tests deterministas nuevos (sin llamadas de RAG reales): sync preserva la marca manual.
5. Bump `ai_chatbot_1_portal` → `1.0.38` (único módulo tocado; `chatbot_cart` no cambia).

**Out of scope:**
- Todo cambio en n8n (el anexo determinista queda como plan B condicionado, ver "Decisions").
- Auto-reparación del flujo en cada sync (el botón es el mecanismo).
- Menú, tipo de pregunta, prompts del RAG, datos de Karla.

## Modelo de datos

No introduce nuevas estructuras ni campos. Solo el orden de lectura/escritura respecto a `flujo_ids` en la sync.

## Plan de implementación

1. Editar `chatbot_config.py`: `marcados_manuales` capturado antes del `(6,0)`; re-añadido después. No cambiar nada más del método.
2. Añadir test en `ai_chatbot_1_portal/tests/` (suite existente de sync/detección): con `flujo_carrito_compra` inactivo y marcado en `config.flujo_ids`, tras `action_recargar_todo_desde_rag` (con RAG mockeado/`_refrescar_desde_rag` parcheado a resultado OK) → flujo sigue en `flujo_ids`, sigue inactivo, no archivado. Y un test inverso: flujo no marcado y no autodetectado no se agrega.
3. Suite `-u ai_chatbot_1_portal --test-enable` verde + `chatbot_cart` (regresión) verde.
4. Ejecutar `action_activar_carrito` en la config Karla (staging), restart del contenedor.
5. Verificación en vivo: `configuracion_agente` → prompt empieza con el bloque y trae el anuncio; BD → flujo activo y marcado; correr una sync desde la ficha → la marca sobrevive.

## Criterios de aceptación

- [ ] `action_recargar_todo_desde_rag` no pierde la marca manual de `flujo_carrito_compra` (test booleano nuevo verde).
- [ ] Tras la sync, el flujo del carrito sigue inactivo/activo según su estado previo (sin archivado involuntario).
- [ ] `POST /ai_chatbot_1_portal/configuracion_agente` devuelve `system_prompt.startswith('=== CARRITO DE COMPRA ===')`.
- [ ] WhatsApp "hola" → respuesta termina con `💡 Escribe «carrito» para ver nuestro catálogo y comprar por WhatsApp.`
- [ ] WhatsApp "carrito" → n8n recibe `equipo_asignado=flujo_carrito_compra` → `/chatbot_cart/procesar` responde con el menú del carrito (verificable en log en vivo).
- [ ] Suites `ai_chatbot_1_portal` y `chatbot_cart` en verde.
- [ ] Sin cambios en `n8n_json/`, sin cambios en el mecanismo de intents/RAG, sin tocar datos de otros clientes.

## Decisiones tomadas y descartadas

- **Tomado:** prompt como único mecanismo del anuncio para esta spec; separarse de n8n hasta medir con la cadena del gate restaurada. Anexo determinista en n8n = plan B si la prueba real falla (requerirá permiso explícito).
- **Tomado:** reactivación del flujo solo por el botón SPEC 30 (predecible, ya probado); auto-reparación descartada (lógica con conflicto latente).
- **Tomado:** distinguir la causa base: el diagnóstico "Sin intenciones" del 12/9 fue un estado transitorio por diseño de `_refrescar_desde_rag` (borra y recrea); no implicaba un problema de la sync.
- **Descartado (2026-09-12):** duplicar el endpoint `/configuracion_agente` en `chatbot_cart` (Werkzeug resuelve primero en orden de registro: el override nunca tuvo efecto desde SPEC 29) — consolidado en el controlador de `ai_chatbot_1_portal` con la importación suave (commit 79330c7).
- **Descartado (2026-09-12):** instrucciones relativas a ramos/productos del negocio dentro del bloque del carrito — el disparo depende solo de la palabra "carrito", neutro para cualquier cliente (inmobiliaria/metalúrgica/clínica).

## Riesgos identificados

- El anuncio permanece basado en el LLM (probabilístico) — aceptado por el usuario; el criterio (ii) es la activación funcional.
- El borrado manual del flujo en la UI vuelve a dejar el carrito silencioso con gate False (sin auto-reparación por decisión) — mitigación: el botón "Activar carrito" lo reconstruye al momento; documentar en la guía 27.