# SPEC 49 — Mundo carrito: ruteo unificado, catálogo clásico y IA solo-carrito

> **Status:** Approved
> **Depends on:** SPEC 34, SPEC 40, SPEC 44, SPEC 45, SPEC 48
> **Date:** 2026-09-16
> **Objective:** Convertir el modo carrito en un mundo separado y completo: gate único por `modo_carrito` en el orquestador (sin callejones del subflow simple), "catálogo" que muestra la lista paginada, IA aislada para mensajes que el clasificador no entiende y salida directa al negocio.

## Por qué existe

Tras la SPEC 48 el estado persiste, pero el ruteo sigue roto: en `yclod-simple_1_subflow` la cadena `Agrupar_texto → Borrar_mensajes_buffer → Preparar_Input_AI → Consultar_estado_Odoo` termina sin salida (`Consultar_estado_Odoo` llama a `/procesar_paso` y muere ahí); `Combinar_entrada_session_odoo → Recuperar_paso` están desconectados. Resultado: estando en modo CARRITO, el 2.º mensaje queda sin respuesta. Además `catálogo` dispara buscador-first siempre (163 productos, 0 categorías → prompt vacío) y `salir` tiene un intermedio 1/2/3. El usuario no debe pasar por la IA del negocio ni por nodos muertos: cuando está en carrito, el mensaje vive en el mundo carrito.

## Scope

**In:**

1. **Odoo — clasificador:** nueva acción `FALLBACK` en `clasificar_accion_carrito_use_case.py` cuando NO matchea ninguna palabra (hoy devuelve `CONSULTAR` por defecto, líneas 72/172/182); `CONSULTAR` queda solo para las palabras de carrito explícitas.
2. **Odoo — IA solo-carrito:** en `_ejecutar` (controller), acción `FALLBACK` → responde con IA usando `render_prompt_carrito_solo()` (SPEC 34) vía `gpt.service`; el prompt ya obliga a hablar solo en términos del carrito y sugerir `salir`. Si la IA falla → mensaje genérico actual.
3. **Odoo — salida directa:** `SALIR` (`salir` / `🏪 Volver al negocio`) sale inmediatamente a modo negocio conservando items, sin la pregunta 1/2/3; mensaje: "¡Listo! Volvemos al negocio. Tu carrito queda guardado, escribe *carrito* para retomarlo." `_resolver_salida_pendiente` queda para sesiones legacy con `pendiente_salida`.
4. **Odoo — catálogo clásico:** acción `CATALOGO` (offset 0) muestra SIEMPRE la lista paginada clásica de productos (números, "responde el número"). El buscador-first (SPEC 40) queda solo para la activación ("carrito"), con el prompt de búsqueda aunque no haya categorías.
5. **n8n — orquestador:** mover el gate: `Call 'yclod-simple_1_subflow'` → **`Obtener_configuracion_agente` → `¿Modo_carrito?`** ANTES de `Consulta_o_agendar_cita`; true → `Call 'ycloud_carrito_subflow (modo)'` (fin de rama); false → `Consulta_o_agendar_cita` (flujo de negocio/IA normal, intacto).
6. **n8n — limpieza subflow simple:** borrar `Consultar_estado_Odoo`, `Preparar_Input_AI`, `Combinar_entrada_session_odoo`, `Recuperar_paso` y reconectar `Borrar_mensajes_buffer` directamente al final del subflow (el dato regresa al orquestador).
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
5. **n8n orquestador por API:** mover `Obtener_configuracion_agente`+`¿Modo_carrito?` antes de `Consulta_o_agendar_cita`; reconectar rama false al switch. Validar grafo sin nodos sueltos.
6. **n8n simple subflow por API:** borrar los 4 nodos muertos y reconectar. Validar grafo.
7. **Exports** de ambos workflows al repo lead + commit.
8. **E2E lead:** carrito → "catálogo" (lista clásica) → número agrega → texto fuera del carrito → IA carrito responde en términos del carrito; "🏪 Volver al negocio" → sale directo y una pregunta de negocio la atiende el flujo normal.

## Acceptance criteria

- [ ] `clasificar('¿dime el precio de una reparación?')` en carrito → `accion='FALLBACK'`.
- [ ] FALLBACK con IA disponible responde texto del prompt carrito-solo (test con mock).
- [ ] FALLBACK sin IA disponible responde el mensaje genérico actual (sin error).
- [ ] `salir` con items: modo→NEGOCIO, items conservados, sin pregunta 1/2/3.
- [ ] `catálogo` en carrito: `texto_para_usuario` contiene el listado numerado y el buscador solo aparece en la activación.
- [ ] Orquestador: `¿Modo_carrito?` true alcanza `Call carrito (modo)` sin pasar por `Consulta_o_agendar_cita`; false sigue el flujo normal.
- [ ] Simple subflow sin los 4 nodos muertos; sin llamadas sin salida.
- [ ] Suite `chatbot_cart` en verde (excepto los 2 FAIL preexistentes `test_recibo_pago`).
- [ ] E2E lead pasa en los 8 pasos de WhatsApp del plan.
- [ ] Exports actualizados en lead y commits hechos.

## Decisions

- **Sí:** gate único en el orquestador — un solo punto de decisión de ruta; el subflow carrito gana independencia real.
- **Sí:** FALLBACK como acción nueva del clasificador — punto de anclaje determinista para la IA sin tocar el negocio.
- **Sí:** IA con `render_prompt_carrito_solo` reusado — SPEC 34 ya define el prompt aislado; DRY.
- **Sí:** salida directa — la pregunta 1/2/3 añade fricción; items se conservan por defecto (seguro).
- **No:** mover el gate al subflow simple — duplicaría la decisión y su mantenimiento.
- **No:** IA libre que dispare flujos del negocio desde el carrito — el mundo carrito solo sale vía `salir`.
- **Descartado:** que el clasificador devuelva CONSULTAR por defecto — causa el prompt "163 productos" ante texto inesperado.

## Risks

| Riesgo | Mitigación |
|---|---|
| IA en carrito deriva al negocio por error | El prompt carrito_solo ya prohíbe rutas (SPEC 34); test de aislamiento con mock |
| El switch `Consulta_o_agendar_cita` deja de reconocer formas nuevas tras mover el gate | El gate actúa ANTES del switch; el switch solo ve mensajes modo NEGOCIO, como hoy |
| Cambio de salida rompe sesiones con `pendiente_salida` | `_resolver_salida_pendiente` se conserva para sesiones legacy |
| Borrar nodos del subflow simple rompe el agrupado de mensajes | Reconexión explícita `Borrar_mensajes_buffer`→salida del subflow; prueba con trigger |

## What is **not** in this spec

- Configurar categorías de producto del negocio (dato maestro).
- Fusión de la cadena de envío del carrito subflow.
- Promoción a prod (SPEC 48 + 49 junto, tras E2E).
- Cambios al flujo Chatwoot.
