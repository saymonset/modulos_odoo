# SPEC 20 — "Convertir" visible solo con método de pago y pre-llenado en Bs

> **Status:** Implemented
> **Depends on:** — (módulo `pos_venezuela_dual_currency`)
> **Date:** 2026-09-06
> **Objective:** Que en la pantalla de pago del POS el bloque "Convertir" esté oculto hasta que se seleccione un método de pago, y al aparecer el input venga pre-llenado en Bs con el restante por pagar, para que el usuario entienda su función.

## Scope

**In:**

- Ocultar todo el bloque `CustomPaymentLines` (título, tasa, toggle, input, preview, acciones rápidas) cuando la orden no tiene ningún método de pago seleccionado.
- Al seleccionar método de pago: mostrar el bloque con toggle **Bs** seleccionado por defecto e `inputAmount` pre-llenado con el **restante por pagar en Bs** (la tasa Bs es 1:1 con el due).
- Al cambiar de método de pago: re-pre-llenar con el restante actualizado.
- "Total exacto" / "Limpiar" quedan dentro del bloque (heredan la visibilidad).
- Bump de versión en manifest + test.

**Out of scope (para otras specs):**

- Cambiar la lógica de conversión/preview ni el config de dual currency.
- Comportamiento del bloque en pantallas distintas de la PaymentScreen.
- Copia/etiquetas nuevas de UI.

## Data model

Sin estructuras nuevas. En `custom_payment_lines.js` el estado ya tiene `selectedCurrency: "bs"` por defecto; se añade una reacción a la línea de pago seleccionada para fijar `inputAmount` con el restante por pagar en Bs.

## Implementation plan

1. `custom_payment_lines.js`: computar `remainingInBs` (restante del due de la orden) y método `prefillFromRemaining()`; conectarlo al cambio en `props.paymentLines` (nueva línea de pago = método seleccionado/cambiado).
2. `custom_payment_lines.xml`: envolver el bloque en `t-if` "existe método de pago seleccionado" (reemplaza el hint actual "Selecciona un método de pago").
3. Llamar `prefillFromRemaining()` al aparecer el bloque y en cada cambio de método; toggle forzado a `"bs"` en cada pre-llenado.
4. Bump de manifest + 1 test: sin método → bloque no renderizado; con método → visible, input = restante en Bs; cambio de método → input actualizado.
5. Verificación en `odoo-19-web-leads`: `-u pos_venezuela_dual_currency --test-enable` + prueba manual en la UI de staging.

## Acceptance criteria

- [ ] Sin método de pago seleccionado, el bloque "Convertir" no aparece en la pantalla de pago.
- [ ] Al seleccionar un método, el bloque aparece con toggle Bs activo e input pre-llenado con el restante por pagar en Bs.
- [ ] Cambiar de método re-pre-llena el input con el restante actualizado.
- [ ] "Total exacto" y "Limpiar" siguen funcionando dentro del bloque.
- [ ] Tests del módulo pasan en staging (`--test-enable`).

## Decisions

- **Sí:** pre-llenar con el *restante* (no el total bruto) — es lo que el usuario realmente va a pagar.
- **Sí:** Bs por defecto en cada aparición/cambio — refuerza la función del bloque.
- **No:** recordar la última moneda usada — confundiría al usuario.
- **No:** tocar la lógica de conversión — solo visibilidad + pre-llenado.

## Risks

| Riesgo | Mitigación |
|---|---|
| Órdenes sin dual currency activa | La visibilidad nueva es sobre el bloque existente; si el config lo desactiva, el bloque ya no se monta (sin cambio). |
| Pre-llenado en COP o tras cambiar toggle | El pre-llenado es siempre en Bs; el usuario cambia el toggle solo si quiere. |

## What is **not** in this spec

- Lógica de conversión o tasas (intactas).
- Deep links de pago (`/payment/<uuid>`) — flujo separado.
- Cambios en n8n/chatbot.

Cada uno, si aterriza, va en su propia spec.
