# SPEC 47 — Cotización asistida por IA con MCP de Odoo

> **Status:** Draft
> **Depends on:** SPEC 15 (OpenAI agente), SPEC 43 (workspace n8n lead), SPEC 44 (subflow carrito independiente), SPEC 25 (tasa BCV congelada en órdenes)
> **Date:** 2026-09-16
> **Objective:** Que el cliente de WhatsApp pida una cotización, la IA le pregunte qué busca, le muestre productos vía MCP de Odoo, arme la cotización con el módulo BCV (dólares/bolívares) y se la envíe en PDF por correo, todo automático sin intervención humana.

## Por qué existe esta spec

Hoy el chatbot vende por catálogo fijo (SPEC 38/39/40) y el carrito arma la orden. Falta el caso "no sé qué comprar / dame una cotización": el cliente describe su necesidad y un agente IA decide qué productos buscar, los presenta, arma la cotización y la envía. La cotización debe usar el esquema dual-currency que ya implementa `bcv_rate_update_venezuela` (precio USD, tasa BCV congelada, totales USD y VES), no uno nuevo.

## Scope

**In:**

1. **Módulo nuevo `chatbot_cotizacion`** (`shared/extra/19.0/`, hermana de `chatbot_cart`) con endpoints HTTP públicos por token (patrón specs 15/27) que el agente IA invoca:
   - `POST /chatbot_cotizacion/search_products` — búsqueda por nombre/categoría, ≤10 items con precio en USD del pricelist. Reutiliza lógica de catálogo de SPEC 38/40.
   - `POST /chatbot_cotizacion/create_quotation` — crea `sale.order` (partner por teléfono o crea; línea de productos con precios). **La tasa BCV se congela sola** vía overrides existentes de `bcv_rate_update_venezuela` (no duplicar cálculo).
   - `POST /chatbot_cotizacion/send_quotation` — genera PDF del reporte de cotización ya existente (dual-currency) y lo envía por email al correo del cliente; marca `state=sent`.
2. **Subworkflow n8n `ycloud_cotizacion_subflow`** (carpeta `ycloud`, proyecto INTEGRAIA; exports a `/home/odoo/lead/odoo19-skeleton/n8n_json/ycloud/`):
   - Entrada por palabra clave / intención: `cotización`, `presupuesto`, `quote` → clasificador enruta al subflow (patrón SPEC 34/44).
   - Agente OpenAI con function-calling (SPEC 15) y tools `search_products`, `create_quotation`, `send_quotation`.
   - Flujo conversacional: qué busca → muestra items → selección/cantidad → pide email validado → crea `sale.order` → PDF + email → botón `🏪 Volver al negocio`.
   - Aislamiento de sesión: una sesión de cotización activa a la vez por número (patrón SPEC 34); `volver al negocio` limpia la sesión.
3. **Email del cliente** — la IA lo pide en el chat y valida formato básico; sin email válido no se envía (se reformula o cancela amablemente).
4. **Moneda** — precios y totales salen del esquema BCV existente (moneda del negocio: USD + VES con tasa congelada). Sin lógica de conversión nueva.
5. **Tests** unitarios de controllers + regresión `chatbot_cart` + suites nuevas `chatbot_cotizacion` + E2E WhatsApp.

**Out of scope (para specs futuras):**

- Convertir la cotización a pedido de pago online (SPEC 20/21).
- Catálogo visual con imágenes (SPEC 39) — la cotización es texto.
- Enlace al ecommerce (SPEC 46).
- Intervención humana / aprobación del vendedor antes del envío.

## Data model

```python
# chatbot_cotizacion
# Modelo ligero de sesión para rastrear estado entre llamadas del agente:
#   chatbot.quote.session
#   - phone             Char  (clave por número)
#   - partner_id        Many2one res.partner
#   - email             Char  (validado en el chat)
#   - sale_order_id     Many2one sale.order
#   - state             Selection: in_progress / sent / cancelled
#
# sale.order se usa tal cual, con los campos de bcv_rate_update_venezuela:
#   tasa_bcv, tasa_bcv_congelada, total USD, total VES
```

## Implementation plan

1. Crear módulo `chatbot_cotizacion`: manifest, modelo `chatbot.quote.session`, controllers con token (401 sin token), upgrade en lead.
2. `search_products`: búsqueda `product.template` por nombre/categoría, ≤10 items (nombre, precio USD, moneda).
3. `create_quotation`: resuelve/crea partner por teléfono, arma líneas, deja que `bcv_rate_update_venezuela` congele la tasa. No duplicar cálculo.
4. `send_quotation`: render PDF del reporte existente, adjuntar, enviar email al cliente, `state=sent`.
5. Tests unitarios de los 3 endpoints + regresión `chatbot_cart`.
6. Subworkflow n8n `ycloud_cotizacion_subflow` en vivo + exports en `n8n_json/ycloud/`.
7. E2E WhatsApp real: `cotización` → conversación → email → PDF.

## Acceptance criteria

- [ ] Escribir `cotización`, `presupuesto` o `quote` entra al subflow de cotización (y `volver al negocio` sale limpio).
- [ ] La IA pregunta qué busca y muestra ≤10 productos con precio USD.
- [ ] La cotización se crea como `sale.order` con la tasa BCV congelada (módulo `bcv_rate_update_venezuela`), totales USD y VES correctos.
- [ ] El PDF dual-currency se envía por email al correo validado del cliente y `state=sent`.
- [ ] Sin email válido, no se envía; la IA reformula o cancela amable.
- [ ] Solicitar cambios tras enviar crea una nueva sesión; la anterior queda en `sent`/borrador sin duplicar.
- [ ] Suites `chatbot_cotizacion` + regresión `chatbot_cart` verdes en lead + E2E WhatsApp aprobado.

## Decisions

- **Yes:** módulo nuevo `chatbot_cotizacion` — se mantiene la convención de nombres `chatbot_*` y el carrito no se mezcla con cotización.
- **Yes:** agente OpenAI con function-calling + endpoints HTTP en el módulo — coherente con SPEC 15/43/44.
- **Yes:** reutilizar `bcv_rate_update_venezuela` para la moneda (USD/VES con tasa congelada) — no reinventar cálculo; SPEC 22/25 quedan intactos.
- **Yes:** auto al confirmar el cliente, sin aprobación humana (decisión del usuario).
- **Yes:** email pedido por la IA en el chat, validado con formato básico.
- **No:** catálogo visual de SPEC 39 — mantener la cotización en texto ligero.
- **No:** nodo `AI Agent` de n8n — se usa el agente OpenAI ya estabilizado (SPEC 15).

## Risks

| Riesgo | Mitigación |
| --- | --- |
| MCP de Odoo inalcanzable desde n8n | Endpoints HTTP propios del módulo (protocolo estándar); el MCP es la capa de consulta. Fallback a error amable. |
| Cliente pide cambios tras enviar | Nueva invocación de `cotización` = nueva sesión; la anterior queda como `sent`, sin duplicados. |
| Búsqueda sin resultados | La IA reformula; máx 2 reintentos antes de derivar a asesor (SPEC 06). |
| Tasa BCV no disponible al crear | `bcv_rate_update_venezuela` ya congela la última tasa disponible; si falta, error claro del endpoint y la IA informa. |

## What is **not** in this spec

- Pago online de la cotización (SPEC 20/21).
- Catálogo visual con imágenes (SPEC 39).
- Enlace al ecommerce (SPEC 46).
- Aprobación humana del vendedor antes del envío.