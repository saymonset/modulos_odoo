# SPEC 21 — "Convertir" pre-llenado siempre con el restante real

> **Status:** Approved
> **Depends on:** SPEC 20
> **Date:** 2026-09-08
> **Objective:** Que el pre-llenado del bloque "Convertir" refleje siempre `order.remainingDue` (el restante por pagar), nunca el monto de una línea de pago previa, incluso cuando el restante es 0.

## Contexto / bug reportado

Tras SPEC 20, el usuario reporta: al pagar un método de pago completo (deuda cubierta) y luego agregar otro método (queda en 0, correcto), el bloque "Convertir" se pre-llena en Bs con **la deuda completa** en vez del restante (0).

**Raíz:** en `custom_payment_lines.js` el getter `remainingInBs()` tiene un fallback: si `remainingDue` es 0 (no `> 0`), devuelve el monto de la última línea de pago. `remainingDue` del core Odoo 19 (`pos_order_accounting.js:70`) ya devuelve 0 correctamente al cubrir la deuda, por lo que el fallback es innecesario y reinyecta la deuda completa.

## Scope

**In:**

- Corregir `remainingInBs()`: devolver siempre `order.remainingDue` acotado a `>= 0`, eliminando el fallback a la última línea de pago.
- Con restante 0 el input queda vacío (`_formatInput(0)` ya devuelve `""`).
- Test de regresión + bump de manifest.

**Out of scope:**

- Lógica de conversión/tasas y preview (intactas).
- `applyExactRemaining()` ("Total exacto") — su `return` silencioso con restante 0 ya es correcto.
- UI/etiquetas del bloque.

## Data model

Sin estructuras nuevas. Solo cambia la fuente del valor en `remainingInBs`.

## Implementation plan

1. `custom_payment_lines.js`: reemplazar el getter completo por:
   ```js
   get remainingInBs() {
       const order = this.pos.getOrder();
       return order ? Math.max(order.remainingDue, 0) : 0;
   }
   ```
   `Math.max(..., 0)` evita pre-llenar con negativos (caso IGTF/cambio).
2. `tests/test_convertir_visibility.py`: nuevo test que verifique que el getter ya no contiene el fallback a la última línea (`getAmount`/`get_amount`) y sí usa `Math.max(order.remainingDue, 0)`.
3. Bump de versión en `__manifest__.py`.
4. Verificación en `odoo-19-web-leads`: `-u pos_venezuela_dual_currency --test-enable` + prueba manual (método A completo → método B → "Convertir" vacío).

## Acceptance criteria

- [ ] Con deuda cubierta (método A completo + método B en 0), el input de "Convertir" queda vacío, no con la deuda completa.
- [ ] El pre-llenado usa siempre `order.remainingDue` con piso en 0.
- [ ] "Total exacto" y "Limpiar" siguen funcionando sin cambios.
- [ ] Tests del módulo pasan en staging (`--test-enable`).

## Decisions

- **Sí:** SPEC 21 nueva (la 20 quedó Implemented; el bug es de la fuente del valor, no de su alcance).
- **Sí:** input vacío con restante 0 (coherente con `_formatInput`; un `0` invitaría a aplicar un pago de 0).
- **No:** tocar `applyExactRemaining()` — comportamiento actual correcto.
- **No:** eliminar el fallback "por si acaso" parcialmente — se elimina por completo; el getter del core es confiable.

## Risks

| Riesgo | Mitigación |
|---|---|
| `remainingDue` indefinido en órdenes edge | Se acota con `order ? ... : 0` (ya existente). |
| Escenarios IGTF con montos negativos | `Math.max(..., 0)` garantiza pre-llenado nunca negativo. |
