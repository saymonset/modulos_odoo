# Odoo 19 Specific — Cambios verificados en este repo

## Vistas XML

- `attrs` ya no existe: usar atributos directos `invisible="..."`/`required="..."`.
- List view: `<list>` en vez de `<tree>`.

## QWeb

- `hasclass('...')` en vez de `contains(@class, ...)`.
- `t-set` no se comparte entre bloques `<xpath>` — inline la búsqueda en cada uso.

## Monedas

- COP no tiene xml_id garantizado: `env.ref('base.COP', raise_if_not_found=False) or env['res.currency'].sudo().search([('name','=','COP')], limit=1)`.
- Campos monetarios con `$` ambiguo (USD/COP): añadir etiqueta explícita `COP`.

## Toggles de res.company

Aplicar la misma puerta `invisible` en **todas** las ocurrencias, no solo en el footer del form.

## Overrides de métodos core

Mantener la firma exacta del padre, sin `*args/**kwargs`. Ejemplo: `_prepare_account_move_line`.
