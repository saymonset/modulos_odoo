# SPEC 23 — Formato es-VE + deudor al cambiar moneda + mostrar 0

> **Status:** Approved (implementado, 16 tests 0.10s)
> **Depends on:** SPEC 22
> **Date:** 2026-09-08
> **Objective:** Que el input del "Convertir" use formato es-VE (puntos de miles, coma decimal), que al cambiar de moneda se pre-llene con el deudor convertido, y que restante 0 muestre `0`.

## Scope

**In:**

- Input formato en vivo es-VE (solo cuando usuario escribe decimales).
- `selectCurrency()` pre-llena el input con el deudor en la moneda seleccionada (no lo borra).
- Restante ≤ 0 muestra `0` en vez de vacío.
- `applyToPaymentLine()` y `convertedBs` parsean formato es-VE correctamente.

**Out of scope:**

- Lógica de conversión/tasas (intacta).
- `applyExactRemaining()` (usa `remainingDue` directamente).
- UI/etiquetas.

## Implementation plan

1. `custom_payment_lines.js`: helpers `_parseEsVE(raw)` y `_formatDisplay(value, {decimals})`.
2. Modificar `onInputChange`, `prefillFromRemaining`, `selectCurrency`, `clearInput`, `applyToPaymentLine`, `convertedBs`.
3. Guardar `state.remainingAtSelection` durante pre-llenado para reutilizar en cambio de moneda.
4. Tests de parsing ida/vuelta, cambio de moneda, y restante 0.
5. Bump manifest `19.0.1.4.0` → `19.0.1.5.0`.

## Acceptance criteria

- [ ] Input muestra `1.234,50` para montos ≥ 1000.
- [ ] Cambiar a USD/COP pre-llena el input con el deudor en esa moneda.
- [ ] Restante 0 muestra `0` en el input.
- [ ] "Limpiar" deja el input en `0`.
- [ ] Tests pasan en staging.

## Decisions

- **Sí:** decimales solo cuando el usuario los escribe (menos ruido).
- **Sí:** "Limpiar" → `0`.
- **Sí:** cambio de pestaña → input = deudor en la moneda de esa pestaña.
