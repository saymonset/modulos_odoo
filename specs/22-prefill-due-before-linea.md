# SPEC 22 — Pre-llenado con el restante capturado antes de agregar la línea

> **Status:** Approved
> **Depends on:** SPEC 21
> **Date:** 2026-09-08
> **Objective:** Que el pre-llenado del bloque "Convertir" muestre el restante real **antes** de que el core agregue la nueva línea de pago, eliminando la regresión introducida por SPEC 21.

## Contexto

SPEC 21 eliminó el fallback a la última línea de pago en `remainingInBs()` por causar re-inyección de la deuda completa. Eso causó una regresión: al seleccionar un método de pago, el core auto-llena la línea nueva con el restante → `remainingDue` pasa a 0 → el pre-llenado queda vacío.

**Solución:** capturar `remainingDue` **antes** de que `addPaymentline()` cree la línea. El patch de `payment_screen.js` ya calcula `dueBefore` justo antes de `super.addNewPaymentLine()`. Almacenarlo como valor transitorio en `posState` y consumirlo en `prefillFromRemaining()`.

## Scope

**In:**

- Almacenar `pendingPrefillDue` en `posState` antes de agregar la línea.
- Consumir y resetear ese valor en `prefillFromRemaining()`.
- Nuevos tests de regresión.
- Bump de manifest.

**Out of scope:**

- Lógica de conversión/tasas.
- `applyExactRemaining()` (ya usa `remainingDue` directamente, correcto).
- UI/etiquetas.

## Implementation plan

1. `shared_state.js`: añadir campo `pendingPrefillDue: null`.
2. `payment_screen.js`: antes de `super.addNewPaymentLine(...)`, asignar `posState.pendingPrefillDue = dueBefore`.
3. `custom_payment_lines.js`: modificar `prefillFromRemaining()` para consumir `posState.pendingPrefillDue` si no es `null`, y resetearlo a `null` después.
4. Tests: validar que `pendingPrefillDue` exista en shared_state, que `prefillFromRemaining` lo consuma, y que los tests previos sigan pasando.
5. Bump `19.0.1.3.0` → `19.0.1.4.0`.

## Acceptance criteria

- [ ] Seleccionar método de pago con deuda pendiente → input pre-llenado con el restante.
- [ ] Deuda cubierta + agregar método B → input vacío (restante 0).
- [ ] Pago parcial → input con el restante real.
- [ ] `pendingPrefillDue` se resetea a `null` después de consumirse.
- [ ] Tests del módulo pasan en staging.

## Decisions

- **Sí:** SPEC 22 nueva (trazabilidad, SPEC 21 marcada con nota del fix).
- **Sí:** valor transitorio en `posState` (ya tiene `is_igtf` y `paymentMethodName` como valores transitorios del mismo patch).
- **No:** tocar `applyExactRemaining()` (usa `remainingDue` directamente, correcto para "Total exacto").
