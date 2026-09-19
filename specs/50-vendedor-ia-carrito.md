# SPEC 50 — Vendedor IA del carrito: redacción humanizada y rama de cotización

> **Status:** Implemented
> **Depends on:** SPEC 34 (prompt aislado carrito), SPEC 39 (imágenes), SPEC 41 (recibo pago), SPEC 45 (botones), SPEC 47 (cotización IA con MCP), SPEC 49 (mundo carrito)
> **Date:** 2026-09-16
> **Objective:** Que el carrito deje de hablar robótico: la IA redacta todos los mensajes como un vendedor humano (productos con foto, total amigable, "¿quieres pagar ya?"), el motor sigue determinista, y si el cliente no paga ahora se le pide el email y se le envía la cotización PDF de SPEC 47.

## Por qué existe esta spec

El carrito (SPEC 27–49) funciona pero sus textos son plantillas fijas: suena a robot. Tras la SPEC 47 existirá el flujo de cotización por IA; esta spec une las dos piezas: el motor determinista del carrito sigue decidiendo QUÉ acción ejecuta (SPEC 49: sin IA libre que dispare flujos), pero el QUÉ SE DICE lo redacta la IA como un vendedor: "qué buscas, te muestro lo que necesitas con foto y decides de manera humana", totales en lenguaje humano y la pregunta de cierre. Sin IA configurada, avisa y sale al negocio.

## Scope

**In:**

1. **Prompt de vendedor** nuevo en `chatbot_cart/services/prompt_carrito.py`: `redact_prompt_vendedor(contexto, accion)` — system prompt especializado: vendedor amigable de WhatsApp, ≤3 líneas + 1 emoji, menciona los productos por nombre con su precio, nunca inventa datos (solo usa el contexto que le pasa el controller), formula el total de forma humana ("Te queda en Bs. X / $Y") y cierra con la pregunta o llamada a acción correspondiente a la acción ejecutada. Los ejemplos del prompt son abstractos y universales: válidos para cualquier tipo de empresa, de una panadería a una clínica/hospital.
2. **Redacción IA de todos los textos del carrito**: nuevo servicio `redactar.py` con `redactar(env, plantilla_texto, contexto)`: llama a gpt.service con el prompt de vendedor + los datos reales de la acción (productos, precios, imagen, totales). Devuelve el texto IA o la plantilla fija actual si la IA no responde/falla. Se aplica en `chatbot_cart_controller._ejecutar`, `_mostrar_catalogo`, `_respuesta_buscador` y `_pagar` (todos los textos fijos del mundo carrito).
3. **Cierre "¿quieres pagar ya?"**: cuando hay items, el resumen (ver carrito) y las confirmaciones de agregar terminan con "¿quieres pagar ya?" y botones `[pagar, cotización, 🏪 Volver al negocio]`. `pagar` sigue funcionando directo (palabra + botón) con el recibo actual de SPEC 41 (sección pago + vaucher), solo que su texto también lo redacta la IA.
4. **Rama cotización en el mundo carrito**: nueva acción `COTIZACION` (palabras `cotización`, `presupuesto`, `cotizar`, botón `cotización`, y "no" en el turno post-total pendiente). El controller la ejecuta **dentro del mundo carrito** invocando los endpoints del módulo `chatbot_cotizacion` de SPEC 47 (`search_products`/`create_quotation`/`send_quotation`, por HTTP interno o servicios Python directamente): pide el email (validación básica), crea el `sale.order` y envía el PDF dual-currency. Sin email válido no se envía: reformula o cancela amable.
5. **Sin token de IA en el mundo carrito**: si `gpt.service` no tiene config/API key (o falla de forma persistente) el modo carrito responde: "En este momento no tengo la IA activa para atenderte como vendedor. Volvemos al negocio: …" y ejecuta la salida de SPEC 49 (`_salir_carrito`, items conservados, `modo=NEGOCIO`). Un solo aviso, sin pregunta.
6. **Tests**: redacción IA con mock (agregar/resumen/pagar), fallback a texto fijo si IA falla, cierre "¿quieres pagar ya?", acción `COTIZACION` (mock de `chatbot_cotizacion`), salida sin IA, clasificador con las palabras nuevas. Actualizar tests que validaban textos fijos.

**Out of scope (para futuras specs):**

- Que la IA decida acciones del carrito o las ejecute (motor determinista intacto, decisión de SPEC 49).
- Cambios al módulo `chatbot_cotizacion` (SPEC 47 puede necesitar ajustes menores en la integración; quedan en esta spec solo como consumo).
- Que la cotización capture la sesión completa del carrito con contexto (a la IA le toca pedir email y armar la lista desde el carrito).
- Cambios al workflow n8n ni exports (todo vía Odoo).

## Data model

```python
# chatbot_cart: sin modelos nuevos ni cambios de esquema.
# Cambios de contrato:
#   - clasificar_accion_carrito_use_case: nueva acción 'COTIZACION'
#     (palabras cotización/presupuesto/cotizar)
#   - carrito (JSON de chatbot.session) nuevo campo:
#     estado['pendiente_cotizacion'] = True después de que respondan "no"
#     a la pregunta de pagar: condiciona que el turno termine en la rama
#     cotización
#   - sale.order de la cotización: reutiliza chatbot.quote.session (SPEC 47)
```

## Implementation plan

1. **`chatbot_cart/services/redactar.py`** con `redactar()` + prompt de vendedor en `prompt_carrito.py` (función nueva, no se toca el original de SPEC 34). Manual: POST en lead ante "carrito".
2. **Gate sin IA**: `_hay_ia(env)`; si no, mensaje de aviso y `_salir_carrito`. Manual: probar sin token IA, ver modo negocio y conservando items.
3. **Wire de redacción IA** en `_ejecutar` / `_mostrar_catalogo` / `_respuesta_buscador` / `_pagar`: pasar plantilla + productos al servicio 2. Fallback: texto actual si IA no responde. Manual: agregar producto y pagar, texto IA y precios correctos.
4. **Cierre y botones**: resumen y AGREGAR con items añaden "¿quieres pagar ya?" + botones `[pagar, cotización, 🏪 Volver al negocio]`; acción PAGAR exitosa como hoy (recibo SPEC 41) pero texto redactado por IA; COTIZACION maneja el "no" del usuario>; el "no" solo cuando hay `pendiente_pago` activo.
5. **Acción COTIZACION** en clasificador + controller: pide email (validación regex), invoca los 3 endpoints de `chatbot_cotizacion` (SPEC 47) con el estado del carrito; PDF dual-currency por correo. `pendiente_cotizacion` en el estado carrito.
6. **Tests** del módulo en verde (mock del servicio).
7. **E2E lead**: `carrito` → vendedor pregunta qué necesita → nombre de un producto del catálogo (ej. abstracto: `<producto>`; da igual la empresa, de una panadería a una clínica) con foto + precio → número agrega → resumen humano con total + "¿quieres pagar ya?" → `no` → email → PDF llega a la bandeja → `cotización` de nuevo crea segunda sesión; `🏪 Volver al negocio` sale limpio.

## Acceptance criteria

- [ ] `carrito` y todas las acciones (buscar, agregar, resumen, pagar) devuelven texto redactado por IA con fallback a la plantilla actual si la IA falla o no responde.
- [ ] Sin token/config IA en el mundo carrito: mensaje de aviso + salida a modo negocio conservando items; escribiendo `carrito` se retoma.
- [ ] Catálogo/búsqueda muestra imágenes con foto (SPEC 39) sin cambios y menciona los productos mostrados.
- [ ] Resumen/AGREGAR con items terminan en "¿quieres pagar ya?" y botones `[pagar, cotización, 🏪 Volver al negocio]`; "no" con `pendiente_pago` pide el email (rama cotización).
- [ ] `pagar` directo sigue funcionando y muestra los datos de pago actuales (sección "Para completar el pago" + vaucher) con recibo fiel (SPEC 41).
- [ ] Rama cotización: con email válido crea `sale.order` con tasa BCV congelada y envía el PDF dual-currency; sin email válido reformula o cancela amable.
- [ ] Suite `chatbot_cart` en verde (excepto los 2 FAIL preexistentes `test_recibo_pago`) + E2E WhatsApp de los 7 pasos en verde.
- [ ] Sin cambios en workflows n8n ni exports.

## Decisions

- **Sí:** IA solo redacta, el motor determinista decide (decisión de SPEC 49 se mantiene: sin acción que la IA pueda "disparar").
- **Sí:** se redactan TODOS los textos del mundo carrito con fallback a los textos actuales (carrito = como está hoy si IA falla).
- **Sí:** sin IA configurada avisa y sale al negocio conservando items (decisión del usuario).
- **Sí:** la rama cotización usa los endpoints/servicios de `chatbot_cotizacion` (SPEC 47) por ser la especificación base; SPEC 50 depende de SPEC 47.
- **Sí:** los textos de pago (recibo + datos de pago) siguen siendo el recibo fiel de SPEC 41; la IA solo redacta la narración alrededor.
- **Sí:** ejemplo universal (de una panadería a una clínica) — la spec no acopla ejemplos a un sector; empresa de cualquier tipo.
- **No:** asociar nada en n8n en esta spec: los textos/imágenes ya viajan por `Preparar_salida_carrito` (SPEC 49), y el formato de la respuesta no cambia.
- **Descartado:** IA que decida acciones del carrito — rompe el aislamiento determinista (SPEC 49) y añade riesgo de dobles ejecuciones.

## Risks

| Riesgo | Mitigación |
|---|---|
| La latencia de IA en cada mensaje del carrito se nota | `max_tokens` bajos, timeout con fallback inmediato a plantilla; tests con mock |
| La IA inventa precios/productos que no existen | El prompt prohíbe inventar; el contexto son los datos reales de la acción ejecutada; nunca se envían precios IA |
| chatbot_cotizacion no está implementado al ejecutar esta spec | El plan marca chatbot_cotizacion como bloqueante; el paso 5 no cierra hasta que SPEC 47 haya modificado el módulo |
| Cambiar los textos rompe tests existentes atados a plantillas | Paso 6: los tests se actualizan juntos; fallback garantiza que las plantillas siguen existiendo |

## What is **not** in this spec

- IA que decida o dispare acciones (el motor del carrito es determinista).
- Cambios al n8n ni a `ai_chatbot_0_core`/`ai_chatbot_1_portal`.
- Pago online (SPEC 20/21) ni ecommerce (SPEC 46).
