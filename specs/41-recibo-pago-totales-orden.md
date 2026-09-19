# SPEC 41 — Recibo de pago real: totales desde la orden + datos de depósito configurables

> **Status:** Implemented
> **Depends on:** SPEC 38 (selección por número — validada por este mismo incidente: S00242 tiene la pizza)
> **Date:** 2026-09-12
> **Objective:** Que "pagar" entregue un recibo fiel del pedido (items y totales reales de la orden) con los datos de depósito del negocio, en vez del actual "0 item(s) — Bs. 0.00 / $0.00" con instrucciones que prometen datos bancarios que nunca llegan.

## Por qué existe esta spec

E2E del 12/9 18:24 (post-SPEC 38): la pizza se agregó bien — S00242 quedó con 1 línea, Bs.
20.212,96 — pero el recibo mintió: `_materializar_desde_carrito` (sale_order.py:49) confirma
la orden y **vacía el carrito**, y `_pagar` (chatbot_cart_controller.py) calcula el resumen
**después** → "🛒 0 item(s) — Total: Bs. 0.00 / $0.00". Además dice "Realiza la transferencia
a los datos bancarios que te indicamos" pero **no existe ninguna fuente de datos bancarios**
en la config. El usuario no supo dónde depositar ni qué compró.

## Scope

**In:**

1. **Recibo desde la orden** — `_pagar` (controller): el desglose sale del resumen capturado
   **antes** de materializar (el carrito tal cual se pagó) o desde `order.order_line`
   (qty × price_unit) con total Bs + USD (tasas del CartService) + COP si aplica. Wording:
   "✅ *Pedido S00242 recibido!*" (se mantiene `action_confirm` → estado 'sale'; el vaucher
   se verifica después a mano).
2. **`payment_instructions` en `chatbot.config`** (herencia de chatbot_cart en
   `models/chatbot_config.py` + campo en `views/chatbot_config_views.xml`): Text con los
   datos de depósito del negocio (banco, cuenta, Pago Móvil, alias...). `_pagar` lo inyecta
   en el paso "1. Realiza la transferencia a: <datos>". Si está vacío → "Te escribiremos
   aquí mismo para coordinar el pago." (fallback genérico; nunca prometer datos que no
   llegan).
3. **Cierre del recibo**: tras pagar el usuario sigue en CARRITO (decisión) — recibo +
   "¿Quieres algo más? Escribe *catálogo*." + botones de navegación.
4. **Bump `chatbot_cart`** a `19.0.1.7.0` (si SPEC 40 no aterrizó antes; si sí, el siguiente
   patch) + tests + upgrade en leads + E2E.

**Out of scope:**

- Wiring del voucher: la foto del comprobante adjuntada al pedido (propia spec).
- Crear el pedido en borrador hasta verificar el voucher (decisión: mantener 'sale').
- Salir a modo NEGOCIO tras pagar (decisión: quedarse en CARRITO).
- Imágenes del catálogo (SPEC 39) y escalabilidad (SPEC 40).

## Modelo de datos

Campo nuevo `chatbot.config.payment_instructions` (Text, heredado vía chatbot_cart). Sin
más estructuras.

## Plan de implementación

1. `models/chatbot_config.py` (chatbot_cart): campo `payment_instructions` + vista en
   `chatbot_config_views.xml`; upgrade para aplicarlo.
2. `_pagar`: capturar resumen antes de `_materializar_desde_carrito`; recibo con items,
   totales reales, N.º de pedido, wording "recibido", datos de depósito (config o fallback)
   y cierre CARRITO.
3. Tests: pagar con items → recibo con items/totales reales (nunca "0 items");
   `payment_instructions` presente/vacío; carrito vacío → sin orden y mensaje (regresión);
   sesión sigue en CARRITO tras pagar.
4. Bump + upgrade en leads (`docker exec odoo-19-web-leads python3 /opt/odoo/odoo-core/odoo-bin
   -d dbodoo19 -u chatbot_cart --test-enable --stop-after-init --no-http --log-level=test`)
   + E2E.

## Criterios de aceptación

- [ ] "pagar" con carrito con items → recibo con items y totales REALES (ej. "1 item —
      Bs. 20.212,96 / $12.00"); jamás "0 item(s)".
- [ ] Orden queda en estado 'sale' y el wording dice "Pedido S00242 recibido!".
- [ ] Con `payment_instructions` configurado → el recibo incluye los datos de depósito.
- [ ] Sin `payment_instructions` → fallback "te escribiremos aquí mismo para coordinar el
      pago" (sin prometer datos).
- [ ] "pagar" con carrito vacío → "Tu carrito está vacío..." y NO se crea orden.
- [ ] Tras pagar la sesión sigue en CARRITO con oferta de seguir comprando.
- [ ] Suites `chatbot_cart` en verde + bump aplicado.

## Decisiones tomadas y descartadas

- **Tomado:** resumen capturado antes de materializar (o desde la orden) — **descartado**
  mantener el resumen post-limpieza (es exactamente el bug).
- **Tomado:** `payment_instructions` como Text en `chatbot.config` (per-negocio, fuente
  única SPEC 03) — **descartado** `ir.config_parameter` (nivel instancia, no negocio) y
  `res.partner.bank` (poco flexible para Pago Móvil/alias/Bs).
- **Tomado:** mantener `action_confirm` ('sale') + wording "recibido" — **descartado**
  borrador-hasta-voucher (requiere wiring del voucher, otra spec).
- **Tomado:** quedarse en CARRITO tras pagar — **descartado** salir a NEGOCIO.
- **Descartado:** wiring del voucher (foto → attachment del pedido): propia spec.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Orden de operaciones en `_pagar` (leer tras limpiar) | Test específico: recibo con items nunca "0 items" |
| Clientes existentes sin `payment_instructions` | Fallback genérico (nunca prometer datos) |
| Recibo largo recortado por plataforma | Mantener el recibo conciso (items + total + datos) |

## What is **not** in this spec

- Wiring del voucher (foto del comprobante → pedido).
- Pedido en borrador hasta verificación.
- Salir del carrito tras pagar.

Cada uno de esos, si llega, va en su propia spec.