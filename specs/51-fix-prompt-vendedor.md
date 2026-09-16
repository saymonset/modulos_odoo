# SPEC 51 — Fix vendedor IA: sin fugas, listado intacto y ejemplos universales

> **Status:** Implemented
> **Depends on:** SPEC 50 (vendedor IA carrito), SPEC 47 (cotización teléfono)
> **Date:** 2026-09-16
> **Objective:** Corregir la redacción del vendedor IA tras el E2E WhatsApp: sin fugas de instrucciones internas, sin alterar listados numerados, sin "pizza" ni CTA de pago donde no toca, y mensajes conversacionales que no se malinterpretan como búsqueda.

## Por qué existe esta spec

El E2E WhatsApp real de la SPEC 50 mostró 4 fallos: (1) fuga del texto del router (`flow_name=... equipo_asignado=...`) visible al cliente; (2) la IA reescribía el catálogo paginado sin los números "1."…, imposible seleccionar por número; (3) la bienvenida del buscador seguía citando "ej. pizza" y añadía "¿Quieres pagar ya?" sin carrito; (4) "que haces" caía al BUSCAR por los tokens 'que'/'qué' en vez de FALLBACK y respondía "No encontré productos" tosco.

## Scope

**In:**

1. **Sanitizador de salida IA** (`chatbot_cart/services/redactar.py::redactar`): tras recibir el texto IA se eliminan líneas con `flow_name=`/`equipo_asignado=`, bloques markdown ``` y JSON `{...}`; si queda vacío/caótico → plantilla original.
2. **Prompt del vendedor** (`prompt_carrito.redact_prompt_vendedor`): nueva regla estricta — el listado numerado de productos es sagrado (índices y precios exactos); solo humaniza el texto alrededor; NO añade preguntas/CTAs que la plantilla no traiga; ejemplos abstractos (nunca "pizza").
3. **`_respuesta_buscador`**: plantilla sin "pizza" → ejemplo abstracto ("pan, repuesto, remedio…"); sin pregunta de pago en la bienvenida.
4. **Clasificador**: quitar 'que'/'qué' del gate BUSCAR tokens; textos conversacionales → FALLBACK (IA vendedor); BUSCAR conserva 'buscar', 'busca', 'muéstrame', 'lista', etc.
5. **Tests**: sanitizador, listado intacto con mock, 'que haces' → FALLBACK, bienvenida genérica sin pregunta de pago. E2E HTTP lead de los 4 casos reproducidos.

**Out of scope:**

- Cambios en n8n, SPEC 47 (ya implementada) ni el módulo `chatbot_cotizacion`.
- Rediseño del catálogo paginado (SPEC 40).

## Data model

Sin estructuras nuevas. Cambios de contrato:

- `clasificar_accion_carrito_use_case._clasificar_fallback`: 'que'/'qué' ya no fuerzan BUSCAR.
- `redactar()` devuelto SIEMPRE sanitizado.

## Implementation plan

1. `_sanitizar()` en `redactar.py` + wire en la respuesta.
2. Nueva versión de `redact_prompt_vendedor` (reglas estrictas).
3. Plantilla de `_respuesta_buscador` genérica, sin pizza ni CTA de pago.
4. Clasificador: gate BUSCAR sin 'que'/'qué'.
5. Tests + regresión `chatbot_cart` en verde.
6. E2E HTTP lead: 4 casos del reporte del usuario.

## Acceptance criteria

- [ ] Ninguna respuesta del carrito contiene `flow_name`, `equipo_asignado`, ``` ni JSON crudo (test + E2E).
- [ ] El catálogo paginado mantiene los números "1."…"n." y precios exactos línea por línea (mock de IA que intenta reformar).
- [ ] La bienvenida del buscador no menciona "pizza" ni termina en "¿quieres pagar ya?".
- [ ] `clasificar('que haces')` → FALLBACK; la respuesta es conversacional y amable (IA vendedor), no "No encontré productos".
- [ ] Suite `chatbot_cart` en verde (excepto los 2 FAIL preexistentes `test_recibo_pago`) + E2E HTTP lead de los 4 casos.

## Decisions

- **Sí:** sanitizador central en `redactar()` — un solo punto, cubre todas las redacciones IA del mundo carrito.
- **Sí:** listado numerado intangible por la IA — la selección por número es el contrato de SPEC 38/40.
- **Sí:** quitar 'que'/'qué' del gate BUSCAR — en SPEC 40 se agregó para "qué venden", pero 'catálogo/productos' ya lo cubre; lo conversacional es FALLBACK.
- **No:** cambiar el catálogo paginado ni n8n.

## Risks

| Riesgo | Mitigación |
|---|---|
| Sanitizador elimina texto legítimo | Solo elimina líneas con patrones Router/JSON/markdown; el resto pasa |
| 'qué venden' deja de clasificarse BUSCAR | 'catálogo', 'productos', 'que venden' permanecen en `_PALABRAS_CATALOGO` |

## What is **not** in this spec

- Cambios en n8n, SPEC 47, `chatbot_cotizacion`.
- Rediseño del catálogo o del flujo de pago.
