# SPEC 25 — Congelar tasa BCV en órdenes de venta, compra y facturas

> **Status:** Implemented
> **Depends on:** — (módulo `bcv_rate_update_venezuela` ≥ 19.0)
> **Date:** 2026-09-08
> **Objective:** Que cada orden de venta, compra y factura congele la tasa BCV al momento de su creación/confirmación, de modo que los totales Bs, USD y VES sean consistentes entre sí y no cambien cuando la tasa del BCV se actualiza después.

## Scope

**In:**

- Campo `bcv_rate_frozen` (Float, digits 12,2) en `sale.order`, `purchase.order` y `account.move`, guardado al crear la orden/factura, no recomputable.
- El valor se inicializa con la tasa BCV vigente al momento del `create` o `action_confirm`.
- `_compute_bcv_rate_value` usa la tasa congelada en vez de la tasa actual cuando existe (`bcv_rate_frozen > 0`).
- `amount_total_ves_from_usd` = `amount_total_usd × bcv_rate_frozen` (consistente con el subtotal Bs nativo).
- `_compute_usd_bcv` en líneas usa la tasa congelada de la orden padre cuando existe.
- Script de migración one-shot para órdenes draft existentes: congele su tasa BCV actual.
- Bump `__manifest__.py` a la siguiente versión.

**Out of scope:**

- Modificar la lógica de `cron_update_ves_prices_from_usd` (los precios de catálogo se siguen actualizando diariamente; solo las órdenes congelan la tasa).
- Recalcular órdenes ya confirmadas/cerradas (S00053 queda con su tasa de 814,69; el fix es solo hacia adelante).
- Facturas electrónicas / fe fiscal (el módulo de facturación electrónica venezolana no está en alcance).
- `point_of_sale` (ordenes de PDV tienen su propio módulo, fuera de alcance de este fix).

## Data model

Nuevo campo en 3 modelos (los 3 heredan de módulos del mismo módulo `bcv_rate_update_venezuela`):

| Modelo | Campo | Tipo | Cálculo |
|---|---|---|---|
| `sale.order` | `bcv_rate_frozen` | Float(12,2), stored | Se setea al `create`; si es 0, se setea al `action_confirm` |
| `purchase.order` | `bcv_rate_frozen` | Float(12,2), stored | Idem |
| `account.move` | `bcv_rate_frozen` | Float(12,2), stored | Se setea al `create` (facturas) / `action_post` si es 0 |

No se introducen relaciones nuevas ni tablas nuevas.

## Implementation plan

1. **`sale_order.py`**: añadir `bcv_rate_frozen = fields.Float(...)` con valor default 0. En `create()` heredado, setear `order.bcv_rate_frozen = rate_actual_si_no_es_cero`. Modificar `_compute_bcv_rate_value` para usar `order.bcv_rate_frozen or current_rate` cuando `bcv_rate_frozen > 0`. La tasa se congela definitivamente en `action_confirm` si aún es 0 (captura el valor final antes del commit).

2. **`purchase_order.py`**: aplicar el mismo patrón: campo `bcv_rate_frozen` en `purchase.order`, seteado en `create`, usado en el cálculo de totales de compra.

3. **`account_move.py`** (o donde estén los campos de tasa en facturas): mismo patrón, seteado en `create` o `action_post`.

4. **`sale_order_line.py` / `purchase_order_line.py`**: `_compute_usd_bcv` usa `self.order_id.bcv_rate_frozen or self.env['product.template']._get_bcv_rate(...)` — la tasa congelada prevalece sobre la actual.

5. **Migración one-shot** (`hooks.py` o script de migración): para órdenes en estado `draft` con `bcv_rate_frozen = 0`, setearlo con la tasa actual al momento de la migración (no tocar las confirmadas).

6. **Bump** `__manifest__.py` a la siguiente versión.

## Acceptance criteria

- [ ] Al crear una orden de venta nueva con tasa BCV = X, `bcv_rate_frozen = X` y `amount_total_ves_from_usd = amount_total_usd × X`.
- [ ] Si la tasa BCV cambia después, la orden draft NO se ve afectada (los totales Bs/USD/VES no cambian).
- [ ] Al confirmar la orden, `bcv_rate_frozen` permanece con la tasa al momento de creación (no se actualiza).
- [ ] En purchase.order se aplica la misma congelación.
- [ ] En account.move (facturas) se aplica la misma congelación.
- [ ] Órdenes draft existentes al momento de la migración reciben `bcv_rate_frozen` con su tasa vigente.
- [ ] `sale_order_line._compute_usd_bcv` usa la tasa congelada de la orden padre.
- [ ] Tests: crear orden, cambiar tasa BCV, verificar que los totales no cambian.
- [ ] No se rompe el cálculo de USD para órdenes antiguas sin `bcv_rate_frozen` (fallback a tasa actual).

## Decisions

- **Sí:** tasa congelada en `create` (captura la tasa al momento del pedido, que es lo que importa fiscalmente en Venezuela).
- **Sí:** fallback a tasa actual si `bcv_rate_frozen = 0` (compatibilidad con órdenes antiguas).
- **Sí:** congelación en los 3 modelos (sale/purchase/invoice) para consistencia.
- **Sí:** migración one-shot solo para draft (confirmadas no se tocan).

## Risks

- Si la tasa BCV se actualiza entre la creación y confirmación de una orden draft, el `price_unit` de las líneas podría estar calculado con la tasa nueva (por onchange) pero el subtotal Bs con la vieja. Mitigación: en `action_confirm`, si `bcv_rate_frozen` es 0, recalcular `price_unit` de las líneas con la tasa congelada antes del commit. Riesgo: bajo (la ventana es pequeña y el onchange ya usa la tasa vigente al momento de la línea).
