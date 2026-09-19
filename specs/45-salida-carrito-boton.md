# SPEC 45 — Botón de salida del carrito visible

> **Status:** Implemented
> **Depends on:** SPEC 34 (acción SALIR del carrito), SPEC 37 (mapeo botón→valor), SPEC 44 (subflow carrito)
> **Date:** 2026-09-15
> **Objective:** Que el usuario pueda salir del carrito y volver a la información del negocio con un botón interactivo siempre visible, sin depender de escribir "salir" en texto.

## Por qué existe esta spec

En vivo (15/9) el mensaje de bienvenida del carrito muestra solo `catálogo / ver carrito / pagar` (n8n `Unificar_salida_carrito` los convierte en reply buttons). La salida de SPEC 34 existe y funciona, pero **solo por texto** ("salir" llega al clasificador), y el prompt que lo sugiere solo se muestra en respuestas de intención no reconocida. Con 3 botones interactivos a la vista el usuario no sabe que puede escribir; queda "atrapado" sin botón de regreso. WhatsApp admite máximo 3 reply buttons, por lo que la lista estática `BOTONES_CARRITO = ['catálogo', 'ver carrito', 'pagar']` (`chatbot_cart_controller.py:29`) debe volverse dinámica.

## Scope

**In:**

1. **`chatbot_cart_controller.py`** — reemplazar el constante `BOTONES_CARRITO` por un helper `_botones_carrito(carrito)` dinámico (≤3, WhatsApp cap) usado en todas las respuestas que hoy usan el constante:
   - Carrito con items: `['ver carrito', 'pagar', '🏪 Volver al negocio']`
   - Carrito vacío: `['catálogo', 'ayuda', '🏪 Volver al negocio']`
2. **`clasificar_accion_carrito_use_case.py`** — añadir `'volver al negocio'` a `_PALABRAS_SALIR` (el match por substring existente caerá en `SALIR` de forma determinista; `_COMANDOS_CLASIFICADOR` hereda el set automáticamente).
3. **Tests** — nuevo label → `SALIR`; helper de botones (vacío vs items, ≤3, botón de salida siempre presente); regresión suites `chatbot_cart`.
4. Bump versión del módulo + upgrade en lead + E2E WhatsApp.

**Out of scope (para specs futuras):**

- Cambios en n8n (el subflow de SPEC 44 pasa `botones` tal cual — `Unificar_salida_carrito` ya filtra a 3).
- Cambios al flujo de salida 1/2/3 (`pendiente_salida`) ya probado de SPEC 34.
- Asignación de categorías del negocio ("0 categorías" es data del negocio, no bug).

## Modelo de datos

Esta feature **no introduce estructuras de datos nuevas**. Reusa la acción `SALIR` y `_salir_carrito()` existentes (SPEC 34): el título del botón llega como `valor` vía webhook (SPEC 37) → clasificador → `_salir_carrito` → sin items sale directo a `modo=NEGOCIO` con re-bienvenida; con items pregunta 1/2/3 (guardar/vaciar/seguir).

## Plan de implementación

1. `_botones_carrito(carrito)` en el controller: construye la lista según hay items o no, siempre con `'🏪 Volver al negocio'`, cap 3.
2. Reemplazar los usos de `self.BOTONES_CARRITO` por el helper (8+ sitios).
3. Añadir `'volver al negocio'` a `_PALABRAS_SALIR` en el clasificador.
4. Tests nuevos + regresión `chatbot_cart`.
5. Bump versión + upgrade módulo en lead (docker odoo web leads) + E2E: botón con carrito vacío → sale directo; con items → pregunta 1/2/3; pregunta de negocio después → flujo normal del negocio.

## Criterios de aceptación

- [ ] El mensaje principal del carrito (vacío) muestra botones `catálogo / ayuda / 🏪 Volver al negocio`.
- [ ] Con items, muestra `ver carrito / pagar / 🏪 Volver al negocio`.
- [ ] Ninguna lista de botones excede 3 elementos.
- [ ] Tocar "🏪 Volver al negocio" con carrito vacío → sale directo, `modo=NEGOCIO`, mensaje de re-bienvenida del negocio.
- [ ] Tocar "🏪 Volver al negocio" con items → pregunta 1/2/3 (guardar/vaciar/seguir) funcional.
- [ ] `'volver al negocio'` clasifica como `SALIR` de forma determinista (sin LLM).
- [ ] En n8n no hay cambios (subflow SPEC 44 intacto).
- [ ] Suites `chatbot_cart` en verde.

## Decisiones tomadas y descartadas

- **Tomado:** botones dinámicos por estado del carrito — el cap de 3 de WhatsApp lo obliga; "pagar" sin items es imposible de todos modos.
- **Tomado:** label `'🏪 Volver al negocio'` + palabra clave en `_PALABRAS_SALIR` — salida determinista (sin depender del LLM).
- **Descartado:** botón 4º inmediato (`salir` sin reordenar) — WhatsApp descarta el 4º botón.
- **Descartado:** cambiar el flujo de salida 1/2/3 — ya probado de SPEC 34; solo se hace visible por botón.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Otros textos de WhatsApp recortan el label (título del botón a 20/24 chars) | SPEC 40 ya normaliza recortes; "🏪 Volver al negocio" cabe; test de recorte |
| Un cliente del bot valida lista exacta `['catálogo','ver carrito','pagar']` | Solo tests internos dependen del constante; se ajustan al helper |

## What is **not** in this spec

- Cambios en n8n / subflow carrito (SPEC 44).
- Categorías del negocio (data).
- Checkout/pagos.

Cada uno de esos, si llega, va en su propia spec.