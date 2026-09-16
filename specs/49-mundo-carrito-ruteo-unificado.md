# SPEC 49 — Mundo carrito: ruteo unificado, catálogo clásico y IA solo-carrito

> **Status:** Approved
> **Depends on:** SPEC 34, SPEC 40, SPEC 44, SPEC 45, SPEC 48
> **Date:** 2026-09-16
> **Objective:** Convertir el modo carrito en un mundo separado y completo: gate único por `modo_carrito` en el orquestador (sin callejones del subflow simple), "catálogo" que muestra la lista paginada, IA aislada para mensajes que el clasificador no entiende y salida directa al negocio.

## Por qué existe

Tras la SPEC 48 el estado persiste, pero el ruteo sigue roto: el nodo terminal del subflow simple, `Consultar_estado_Odoo` (= `/procesar_paso`), al devolver `modo: CARRITO` (gracias a la defensa de SPEC 48) no matchea ninguna regla del switch `Consulta_o_agendar_cita` del orquestador (solo `MENU_PRINCIPAL/FLUJO/COMPLETADO`) → el mensaje muere y WhatsApp queda sin contestar. `Combinar_entrada_session_odoo`/`Recuperar_paso` están desconectados (dead code real). Además `catálogo` dispara buscador-first siempre (163 productos, 0 categorías → prompt vacío) y `salir` tiene un intermedio 1/2/3. Corrección de implementación: durante el paso 5 se descubrió que `Consultar_estado_Odoo` NO es un callejón sin salida sino el terminal que devuelve el estado/ruteo al orquestador (también es el enrrutador de los flujos de captura); por eso el diseño del ruteo se ajustó al enfoque (A): rama `CARRITO` en el switch del orquestador + envío directo, en vez de borrar el nodo y mover el gate.

## Scope

**In:**

1. **Odoo — clasificador:** nueva acción `FALLBACK` en `clasificar_accion_carrito_use_case.py` cuando NO matchea ninguna palabra (hoy devuelve `CONSULTAR` por defecto, líneas 72/172/182); `CONSULTAR` queda solo para las palabras de carrito explícitas.
2. **Odoo — IA solo-carrito:** en `_ejecutar` (controller), acción `FALLBACK` → responde con IA usando `render_prompt_carrito_solo()` (SPEC 34) vía `gpt.service`; el prompt ya obliga a hablar solo en términos del carrito y sugerir `salir`. Si la IA falla → mensaje genérico actual.
3. **Odoo — salida directa:** `SALIR` (`salir` / `🏪 Volver al negocio`) sale inmediatamente a modo negocio conservando items, sin la pregunta 1/2/3; mensaje: "¡Listo! Volvemos al negocio. Tu carrito queda guardado, escribe *carrito* para retomarlo." `_resolver_salida_pendiente` queda para sesiones legacy con `pendiente_salida`.
4. **Odoo — catálogo clásico:** acción `CATALOGO` (offset 0) muestra SIEMPRE la lista paginada clásica de productos (números, "responde el número"). El buscador-first (SPEC 40) queda solo para la activación ("carrito"), con el prompt de búsqueda aunque no haya categorías.
5. **n8n — orquestador:** el switch `Consulta_o_agendar_cita` gana una regla **primera** `CARRITO` (`$json.modo == 'CARRITO'`) → nuevo Code `Preparar_salida_carrito` (clon del formateador del carrito subflow: botones/lista/imágenes → `whatsappPayload`) → nuevo HTTP `Enviar_salida_carrito` (YCloud con credencial `YCloud API (SPEC48)`). La respuesta carrito ya fue generada por `procesar_paso` (SPEC 48) — **no se llama de nuevo a `/chatbot_cart/procesar`** (evita doble ejecución). Gate `¿Modo_carrito?` existente queda intacto para la activación ("carrito", turno 1).
6. **n8n — limpieza subflow simple:** borrar los nodos muertos `Combinar_entrada_session_odoo` y `Recuperar_paso`. **Se conserva** `Consultar_estado_Odoo` (terminal que devuelve el estado y enrrutador de flujos de captura) y la cadena `Agrupar → Borrar → Preparar_Input_AI → Consultar_estado_Odoo`.
7. **Exports:** actualizar `ycloud_create_lead_0_con_menu_whatsapp.json` y `yclod-simple_1_subflow.json` en `/home/odoo/lead/odoo19-skeleton/n8n_json/ycloud/` (SPEC 43).
8. **Tests** en `chatbot_cart`: FALLBACK clasifica sin palabras; IA solo-carrito (con mock de `gpt.service`); salida directa conserva items; `catálogo` clásico con >10 productos. Actualizar tests que dependían de salida 1/2/3 y de `CONSULTAR` por defecto.
9. **Sin promoción a prod** en esta spec (queda pendiente de E2E + decisión del usuario, al igual que SPEC 48).

**Out of scope (para futuras specs):**

- Fusionar la cadena de envío duplicada del carrito subflow.
- Configurar categorías de producto en lead (dato maestro del negocio).
- Cambiar el texto del menú de ayuda ni las `_PALABRAS_*` existentes.
- Promoción a prod de SPEC 48 + 49 (una sola, cuando el E2E esté completo).

## Data model

Sin estructuras nuevas. Cambios de contrato:

- `clasificar_accion_carrito_use_case.execute()` puede devolver `accion='FALLBACK'` en vez de `CONSULTAR` cuando no hay match.
- Respuesta de `/chatbot_cart/procesar` con FALLBACK: misma forma (`texto_para_usuario` + botones), texto generado por IA solo-carrito.
- Sesión: `estado['modo']='NEGOCIO'` tras SALIR directa, con `estado['carrito']` preservado.

## Implementation plan

1. **Respaldo n8n** de los 2 workflows por API a `/tmp/opencode/spec49-rollback/`.
2. **Clasificador:** agregar acción `FALLBACK` (sin match) y explicitar las palabras de `CONSULTAR`.
3. **Controller:** FALLBACK → IA solo-carrito (mockable); SALIR directa; `CATALOGO` siempre lista clásica; buscador-first solo en activación. Manual check: POST "catálogo" en carrito → lista con números.
4. **Tests** del módulo en verde (incluye los ajustes a tests afectados).
5. **n8n orquestador por API:** regla `CARRITO` primera en el switch → `Preparar_salida_carrito` → `Enviar_salida_carrito` (credencial). Validar grafo sin nodos sueltos.
6. **n8n simple subflow por API:** borrar los 2 nodos muertos (`Combinar_entrada_session_odoo`, `Recuperar_paso`). Validar grafo.
7. **Exports** de ambos workflows al repo lead + commit.
8. **E2E lead:** carrito → "catálogo" (lista clásica) → número agrega → texto fuera del carrito → IA carrito responde en términos del carrito; "🏪 Volver al negocio" → sale directo y una pregunta de negocio la atiende el flujo normal.

## Acceptance criteria

- [ ] `clasificar('¿dime el precio de una reparación?')` en carrito → `accion='FALLBACK'`.
- [ ] FALLBACK con IA disponible responde texto del prompt carrito-solo (test con mock).
- [ ] FALLBACK sin IA disponible responde el mensaje genérico actual (sin error).
- [ ] `salir` con items: modo→NEGOCIO, items conservados, sin pregunta 1/2/3.
- [ ] `catálogo` en carrito: `texto_para_usuario` contiene el listado numerado y el buscador solo aparece en la activación.
- [ ] Orquestador: la regla `CARRITO` del switch (primera) alcanza `Preparar_salida_carrito` → `Enviar_salida_carrito` sin pasar por IA del negocio; MENU/FLUJO/COMPLETADO siguen su ruteo original (flujos de captura intactos).
- [ ] Simple subflow sin `Combinar_entrada_session_odoo`/`Recuperar_paso`; `Consultar_estado_Odoo` conservado.
- [ ] Suite `chatbot_cart` en verde (excepto los 2 FAIL preexistentes `test_recibo_pago`).
- [ ] E2E lead pasa en los 8 pasos de WhatsApp del plan.
- [ ] Exports actualizados en lead y commits hechos.

## Decisions

- **Sí:** gate único en el orquestador — el mensaje del mundo carrito se atiende y se envía SIN pasar por la IA del negocio (defensa de `procesar_paso` + rama `CARRITO` del switch).
- **Sí (ajuste durante implementación):** el ruteo del carrito en vivo usa la rama `CARRITO` del switch + envío preprocesado en lugar de borrar `Consultar_estado_Odoo`/mover el gate — el nodo resultó ser el enrrutador real de flujos de captura; borrarlo rompería los flujos. Decisión aprobada por el usuario (diseño A).
- **Sí:** FALLBACK como acción nueva del clasificador — punto de anclaje determinista para la IA sin tocar el negocio.
- **Sí:** IA con variante de respuesta del prompt aislado (SPEC 34) — DRY; el original es de ruteo JSON y no sirve para redactar texto.
- **Sí:** salida directa — la pregunta 1/2/3 añade fricción; items se conservan por defecto (seguro).
- **No:** llamar a `/chatbot_cart/procesar` por segunda vez para respuestas ya generadas por `procesar_paso` — ejecutaría la acción dos veces (ej. "2" agregaría doble).
- **No:** IA libre que dispare flujos del negocio desde el carrito — el mundo carrito solo sale vía `salir`.
- **Descartado:** que el clasificador devuelva CONSULTAR por defecto — causa el prompt "163 productos" ante texto inesperado.

## Risks

| Riesgo | Mitigación |
|---|---|
| IA en carrito deriva al negocio por error | El prompt carrito_solo ya prohíbe rutas (SPEC 34); test de aislamiento con mock |
| La rama `CARRITO` aparece ante respuestas que ya se ejecutaron (procesar_paso) | La rama NUNCA llama de nuevo a `/chatbot_cart/procesar`; solo envía (`Preparar_salida_carrito`→`Enviar_salida_carrito`) |
| Cambio de salida rompe sesiones con `pendiente_salida` | `_resolver_salida_pendiente` se conserva para sesiones legacy |
| Borrar nodos del subflow simple rompe el agrupado de mensajes | Solo se borraron los 2 nodos aislados; la cadena del agrupador queda intacta; prueba con trigger |

## What is **not** in this spec

- Configurar categorías de producto del negocio (dato maestro).
- Fusión de la cadena de envío del carrito subflow.
- Promoción a prod (SPEC 48 + 49 junto, tras E2E).
- Cambios al flujo Chatwoot.
