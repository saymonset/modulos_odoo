# SPEC 24 — Formulario alta producto PDV con USD/COP

> **Status:** Approved
> **Depends on:** — (módulos `pos_venezuela_dual_currency` ≥ 19.0.1.5.0, `bcv_rate_update_venezuela`)
> **Date:** 2026-09-08
> **Objective:** Que el formulario de alta de producto desde el PDV (`point_of_sale.product_template_view_form_normalized_pos`) muestre precio en USD (y COP si `cop_show_fields`), igual que el formulario de Ventas, implementado por herencia en `pos_venezuela_dual_currency`.

## Scope

**In:**

- Vista de herencia del form normalizado POS con `list_price_usd` y `list_price_cop` junto a `list_price`.
- Campos técnicos `cop_show_fields`, `currency_usd_id`, `currency_cop_id` invisibles para los `invisible` de Odoo 19.

**Out of scope:**

- Costo (`standard_price`): no aparece en ese formulario.
- Lógica de conversión Python (inverse compute existente, intacto).
- Vistas core de Odoo (sin tocar `point_of_sale`).
- Formulario de edición de producto desde PDV (usa la vista estándar, ya heredada).

## Data model

Ninguno. Solo vistas; reutiliza campos existentes de `bcv_rate_update_venezuela`.

## Implementation plan

1. Crear `views/product_template_pos_views.xml` en `pos_venezuela_dual_currency`: vista `product_template_form_normalized_pos_usd`, `inherit_id` = `point_of_sale.product_template_view_form_normalized_pos`, inserta tras el `list_price` el patrón ya usado en `bcv_rate_update_venezuela/views/product_views.xml` (span "o", `list_price_usd` monetary USD, "o" + `list_price_cop` monetary COP invisible si `not cop_show_fields`, hint "COP").
2. Registrar el archivo en `'data'` del `__manifest__.py`.
3. Bump `19.0.1.5.0` → `19.0.1.6.0`.

## Acceptance criteria

- [ ] Al crear producto desde el PDV se ven `Bs o $` (y `o … COP` si COP habilitado).
- [ ] Ingresar precio en USD guarda el `list_price` en Bs correctamente (inverse compute).
- [ ] Con COP deshabilitado, el campo COP y su "o" no se muestran.
- [ ] El formulario de Ventas sigue funcionando sin cambios.
- [ ] Verificado manualmente en staging.

## Decisions

- **Sí:** vista en `pos_venezuela_dual_currency` (no en módulo BCV base, evita agregar `point_of_sale` a sus depends).
- **Sí:** solo precio de venta; costo fuera de alcance.
- **Sí:** guardar automáticamente el equivalente en Bs (comportamiento existente).
- **Sí:** verificación manual en staging, sin test automatizado de vista.

## Risks

- Si Odoo cambia el arch de `product_template_view_form_normalized_pos` en un futuro upgrade, el xpath puede romper (riesgo bajo, vista estable en 19.0).
