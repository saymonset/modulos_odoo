Resumen del módulo bcv_rate_update_venezuela

  Es un módulo de localización venezolana para Odoo 19.0 que resuelve el problema de precios duales (VES/USD) en e-commerce y POS, más un flujo completo
  de pago por transferencia bancaria con comprobante + confirmación por WhatsApp.

  ¿Qué hace puntualmente?

  1. Tasa BCV automática — Dos cron jobs diarios: uno obtiene la tasa oficial del BCV, otro recalcula todos los precios en VES desde los precios en USD.
  2. Precios duales VES/USD — Agrega list_price_usd a productos, variantes y atributos. Sincroniza bidireccionalmente VES ↔ USD usando la tasa BCV.
  Cuando la tasa cambia, todo se recalcula automáticamente.
  3. Totales en USD — Las órdenes de venta y líneas guardan price_usd_bcv, price_subtotal_usd_bcv y amount_total_usd. También se arrastra a las facturas.
  4. Flujo de pago por transferencia — Un componente OWL en el checkout permite:
    - Seleccionar banco origen/destino
    - Subir imagen/PDF del comprobante
    - Validar montos
    - El pago queda como payment.transaction en estado pending → done tras confirmar la orden
  5. Confirmación WhatsApp — Al confirmar la orden, envía un mensaje via WhatsApp Cloud API con el template pedido_confirmado_ubicacion (datos del
  pedido, dirección, horario).
  6. Address autofill — En el checkout, oculta todos los campos de dirección y solo muestra email/teléfono. Si encuentra un partner existente,
  autocompleta los datos.
  7. 25 bancos venezolanos precargados como datos semilla.

  Archivos clave (17 archivos Python + 11 vistas + OWL components)

  ┌─────────────────────────┬─────────────────────────────────────────────────────────────────────────────────┐
  │ Propósito               │ Archivo                                                                         │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ Tasa BCV + recálculo    │ models/res_currency_rate.py, models/product_template.py                         │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ USD en órdenes/facturas │ models/sale_order.py, models/sale_order_line.py, models/account_move_line.py    │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ Pago por transferencia  │ controllers/website_sale_attachment.py, controllers/payment_custom_override.py  │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ Componente OWL pago     │ static/src/js/payment_proof_component.js                                        │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ WhatsApp                │ services/whatsapp_service.py, uses_cases/send_whatsapp_confirmation_use_case.py │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ Address autofill        │ controllers/address_autofill.py, static/src/js/address_autofill.js              │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ Cron jobs               │ data/ir_cron_data.xml                                                           │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────┤
  │ Seguridad               │ tests/test_security_payment.py (previene inyección de montos)                   │
  └─────────────────────────┴─────────────────────────────────────────────────────────────────────────────────┘

  En criollo: convierte Odoo en una tienda online venezolana funcional — con precios en USD que se actualizan solos según la tasa BCV, pagos por
  transferencia con comprobante, y confirmación por WhatsApp.