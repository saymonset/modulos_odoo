# SPEC 56 — Carrito visual multi-canal: botón Pagar + resumen claro + adaptación por plataforma

> **Estado:** Approved
> **Depende de:** SPEC 45 (botones interactivos), SPEC 54 (➕/➖), SPEC 55 (catálogo visual + bienvenida), SPEC 49 (salida directa)
> **Fecha:** 2026-09-17
> **Objetivo:** Que el carrito muestre un botón "Pagar" siempre visible cuando hay items, con un resumen visual claro tipo "Estimated total", y que los botones se adapten al canal (WhatsApp quick replies, Messenger quick replies, Instagram texto limpio), siguiendo el patrón visual de la foto de referencia.

## Por qué existe esta spec

En vivo el carrito funciona pero la experiencia de pago es poco visible: "pagar" es solo texto en la guía, no un botón. Con items el usuario ve `['➕ Sumar', '➖ Quitar', 'catálogo']` — "catálogo" ya está accesible por texto (el usuario está viendo productos), mientras que "pagar" debería ser la acción prominente. Además los canales no-WhatsApp (Messenger, Instagram) reciben el mismo JSON sin adaptación: Messenger soporta quick replies (hasta 11 botones) pero hoy solo se convierte para WhatsApp, e Instagram recibe texto truncado sin estructura clara.

La foto de referencia muestra el ideal: producto con imagen + cantidad + controles + subtotal, y abajo un resumen con total + botón "Place order". Esta spec implementa lo equivalente en chat: botón Pagar siempre presente, resumen con énfasis visual, y adaptación por canal.

## Scope

**In:**

1. **Botón "Pagar" como 3er botón con items:** `_botones_carrito()` con items → `['➕ Sumar', '➖ Quitar', '💳 Pagar']` (reemplaza "catálogo" que ya está en el pie guía). Sin items: `['catálogo', 'ayuda', '🏪 Volver al negocio']` (sin cambio).
2. **Resumen del carrito con énfasis visual:** `formato_resumen_amigable()` agrega un separador visual y el total en negrita tipo "Σ Total: Bs. X / $Y" + línea "Toca *💳 Pagar* para confirmar tu pedido" antes de la guía.
3. **Adaptación por canal en el JSON de respuesta:** campo nuevo `botones_por_plataforma` que contiene la misma lista pero preparada para la sintaxis de cada canal (WhatsApp `interactive.button`, Messenger `quick_replies`, Instagram texto con hint). El n8n `Unificar_salida_carrito` usa este campo.
4. **Messenger quick replies / Instagram hint:** en `chatbot_utils.py`, función `build_buttons_for_platform()` que devuelve los botones según el canal; para Instagram agrega el hint de texto "Escribe *pagar* o el número con ➕/➖".
5. **Export n8n actualizado:** `ycloud_carrito_subflow.json` lee `botones_por_plataforma[platform]` si existe, fallback a `botones`.
6. **Tests:** botón Pagar presente con items, resumen con total en negrita, `botones_por_plataforma` en el JSON, regresión SPEC 45/54/55.

**Out of scope (para futuras specs):**

- Telegram integration (para otra spec).
- Inline buttons per product image (WhatsApp no lo permite — ya cubierto por SPEC 54 con texto `1 ➕`).
- Cart image per item (ya cubierto por SPEC 55 — imágenes con caption).
- Web chat UI improvements (el widget n8n es texto-only; para otra spec).

## Modelo de datos

Sin modelos nuevos. Cambios de contrato en el JSON de respuesta del endpoint `/chatbot_cart/procesar`:

```python
resp = {
    'texto_para_usuario': '...',
    'imagenes': [...],
    'botones': ['➕ Sumar', '➖ Quitar', '💳 Pagar'],  # existente, sin cambio
    'botones_por_plataforma': {                       # NUEVO
        'whatsapp': ['➕ Sumar', '➖ Quitar', '💳 Pagar'],
        'messenger': ['➕ Sumar', '➖ Quitar', '💳 Pagar'],
        'instagram': ['➕ Sumar', '➖ Quitar', '💳 Pagar'],
    },
    'resumen_carrito': {                              # NUEVO (en CONSULTAR/PAGAR)
        'total_ves': 35807.50,
        'total_usd': 42.30,
        'total_unidades': 5,
        'count': 3,
    },
}
```

## Plan de implementación

1. **Controller `chatbot_cart_controller.py`:**
   - `_botones_carrito()`: con items → `['➕ Sumar', '➖ Quitar', '💳 Pagar']`.
   - `_respuesta()`: agrega `botones_por_plataforma` calculado por `build_buttons_for_platform()`.
   - `_pagar()` y el bloque CONSULTAR: exponen `resumen_carrito` en el extra del JSON.
2. **Platform utils `chatbot_utils.py`:**
   - `build_buttons_for_platform(botones, platform)` — devuelve la lista de botones según el canal (WhatsApp/Messenger idénticos hoy; IG preparado).
   - `hint_acciones_por_plataforma(platform)` — hint de texto para canales sin botones (IG: "Escribe *pagar* para confirmar"); WhatsApp/Messenger lo omite por usar botón.
3. **Cart service `cart_service.py`:**
   - `formato_resumen_amigable()`: agrega separador + total en negrita + línea "Toca *💳 Pagar* para confirmar tu pedido" antes de `GUIA_AJUSTES`.
   - `resumen()` ya tiene todos los campos necesarios; se expone en `resumen_carrito` del JSON.
4. **Tests:** `_botones_carrito` con items incluye Pagar; `formato_resumen_amigable` tiene total en negrita + línea de pagar; JSON incluye `botones_por_plataforma`; regresión suite `chatbot_cart`.
5. **Exports n8n (`odoo19-skeleton/n8n_json/ycloud/`):** `Unificar_salida_carrito` lee `botones_por_plataforma[platform]` si existe, fallback a `botones`. Commit en rama `lead` del skeleton (SPEC 43).
6. **Bump versión** `19.0.1.14.0` + upgrade en lead + E2E WhatsApp: ver carrito → botón Pagar visible → resumen con total destacado.

## Criterios de aceptación

- [ ] `_botones_carrito()` con items devuelve `['➕ Sumar', '➖ Quitar', '💳 Pagar']` (no "catálogo").
- [ ] `_botones_carrito()` sin items devuelve `['catálogo', 'ayuda', '🏪 Volver al negocio']` (sin cambio).
- [ ] `formato_resumen_amigable()` muestra total en negrita + línea "Toca *💳 Pagar* para confirmar tu pedido".
- [ ] JSON de respuesta incluye `botones_por_plataforma` con keys `whatsapp`, `messenger`, `instagram`.
- [ ] n8n `Unificar_salida_carrito` usa `botones_por_plataforma[platform]` cuando existe, fallback a `botones`.
- [ ] "ver carrito" con items muestra botón 💳 Pagar en WhatsApp (E2E).
- [ ] Suite `chatbot_cart` en verde + bump `19.0.1.14.0`.

## Decisiones tomadas y descartadas

- **Tomado:** botón "Pagar" reemplaza "catálogo" como 3er botón con items (el catálogo ya está accesible por texto y el pie guía lo menciona) — **descartado** mantener los 3 botones actuales (la prioridad del usuario es pagar, no volver al catálogo).
- **Tomado:** resumen con total en negrita + línea explícita de pagar (inspirado en "Estimated total" de la foto) — **descartado** solo texto plano (no destaca la acción de conversión).
- **Tomado:** campo `botones_por_plataforma` preparado para adaptación futura — **descartado** adaptación completa de Messenger/IG ahora (los bots ya devuelven `botones`; esta spec prepara la infraestructura).
- **Tomado:** Telegram se deja para otra spec — **descartado** incluirlo aquí (no existe integración hoy, requiere webhook + adaptador completo).
- **Tomado:** inline buttons per product image no son posibles en WhatsApp — **descartado** intentarlo (la API limita a 3 quick replies por mensaje).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Usuario acostumbrado a "catálogo" como botón | El pie guía dice "toca *catálogo* 🛍️" — accesible por texto |
| n8n no lee `botones_por_plataforma` | Fallback a `botones` existente — sin ruptura si el nodo no se actualiza |
| Instagram no tiene botones nativos | El hint de texto "Escribe *pagar*" funciona como fallback |
| `resumen_carrito` expone montos | Solo montos totales que el usuario ya ve en el carrito (sin datos sensibles) |

## What is **not** in this spec

- Telegram integration (otra spec).
- Web chat UI improvements (widget n8n es texto-only).
- Inline quantity controls per product image (WhatsApp no lo permite).
- Adaptación completa de botones de Messenger/IG (esta spec prepara la infraestructura).

Cada uno de esos, si llega, va en su propia spec.
