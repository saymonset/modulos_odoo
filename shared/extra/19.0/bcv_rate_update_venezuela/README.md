# Resumen del módulo bcv_rate_update_venezuela

Es un módulo de localización venezolana para Odoo 19.0 que resuelve el problema de precios duales (VES/USD) en e-commerce y POS, más un flujo completo de pago por transferencia bancaria con comprobante + confirmación por WhatsApp.

## ¿Qué hace puntualmente?

1.  **Tasa BCV automática** — Dos cron jobs diarios: uno obtiene la tasa oficial del BCV, otro recalcula todos los precios en VES desde los precios en USD.
2.  **Precios duales VES/USD** — Agrega `list_price_usd` a productos, variantes y atributos. Sincroniza bidireccionalmente VES ↔ USD usando la tasa BCV. Cuando la tasa cambia, todo se recalcula automáticamente.
3.  **Totales en USD** — Las órdenes de venta, facturas y líneas correspondientes guardan `price_usd_bcv`, `price_subtotal_usd_bcv` y `amount_total_usd`. También cuenta con soporte para el flujo de compras (`purchase.order`).
4.  **Flujo de pago por transferencia** — Un componente OWL en el checkout permite:
    *   Seleccionar banco origen/destino
    *   Subir imagen/PDF del comprobante
    *   Validar montos y referencias bancarias
    *   El pago queda como `payment.transaction` en estado *pending* y se aprueba tras confirmar la orden
5.  **Confirmación WhatsApp** — Al confirmar la orden, envía un mensaje via WhatsApp Cloud API con el template `pedido_confirmado_ubicacion` (datos del pedido, dirección, horario).
6.  **Address autofill** — En el checkout, oculta todos los campos de dirección y solo muestra email/teléfono. Si encuentra un partner existente, autocompleta los datos.
7.  **25 bancos venezolanos** precargados como datos semilla.

## Archivos clave (22 archivos Python + 17 archivos XML + OWL components)

| Propósito | Archivo |
| :--- | :--- |
| **Tasa BCV + recálculo** | [res_currency_rate.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/res_currency_rate.py), [product_template.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/product_template.py), [res_company.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/res_company.py) |
| **USD en ventas, facturas y compras** | [sale_order.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order.py), [sale_order_line.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order_line.py), [account_move_line.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/account_move_line.py), [account_move.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/account_move.py), [purchase_order.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/purchase_order.py), [purchase_order_line.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/purchase_order_line.py), [website_cart_usd.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/website_cart_usd.py) |
| **Inventario y Costos USD** | [stock_quant.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/stock_quant.py) |
| **Pago por transferencia** | [website_sale_attachment.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/website_sale_attachment.py), [payment_custom_override.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_custom_override.py), [payment_validation.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_validation.py), [payment_provider.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/payment_provider.py) |
| **Componente OWL pago** | [payment_proof_component.js](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/static/src/js/payment_proof_component.js) |
| **WhatsApp** | [whatsapp_service.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services/whatsapp_service.py), [send_whatsapp_confirmation_use_case.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/uses_cases/send_whatsapp_confirmation_use_case.py), [whatsapp_history_extension.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/whatsapp_history_extension.py) |
| **Address autofill** | [address_autofill.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/address_autofill.py), [address_autofill.js](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/static/src/js/address_autofill.js) |
| **Cron jobs y Datos Semilla** | [ir_cron_data.xml](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/data/ir_cron_data.xml), [res_bank_data.xml](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/data/res_bank_data.xml) |
| **Seguridad** | [test_security_payment.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/tests/test_security_payment.py) (previene inyección de montos) |
| **Migración y Hooks** | [post-migrate.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/migrations/19.0.1.0.1/post-migrate.py), [hooks.py](file:///home/odoo/lead/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/hooks.py) |

En resumen: convierte Odoo en una tienda online venezolana funcional — con precios en USD que se actualizan solos según la tasa BCV, pagos por transferencia con comprobante, y confirmación automática por WhatsApp.

---

## 📱 Plantillas de Copy para Instagram (Publicidad & Marketing)

Aquí tienes varias opciones de publicaciones listas para usar, adaptadas para el mercado venezolano y enfocadas en distintas necesidades comerciales:

### 🌟 Opción 1: Enfoque Integral (El poder de Odoo 19 en Venezuela)

**¿Cansado de actualizar precios a mano todos los días según la tasa del BCV?** 😩💸

Lleva tu negocio al siguiente nivel con Odoo 19 y nuestro módulo de localización venezolana. Olvídate del trabajo manual y automatiza las ventas de tu e-commerce y punto de venta (POS) en tiempo récord. 🚀

**¿Qué logras con esta solución?**
1️⃣ **Tasa BCV Automática:** Conexión directa y diaria para actualizar la tasa oficial sin mover un dedo.
2️⃣ **Precios Duales Reales:** Muestra tus precios en USD y VES de forma simultánea y transparente. ¡La conversión se calcula sola!
3️⃣ **Pagos Sencillos:** Módulo de pago para transferencias bancarias y pago móvil con subida de capture en el checkout.
4️⃣ **Notificaciones al instante:** Confirmación de pedidos automática enviada por WhatsApp con mapa y horarios.

---
💼 **Módulo de Contabilidad**
Incluido en Odoo Community. Cubre libros contables, facturación e informes financieros. No cumple al 100% con los requisitos del SENIAT, pero al ser Community el código es completamente tuyo. Si decides homologarlo, te ayudo gratis con toda la parte técnica y desarrollo necesario.
---

¡Es hora de digitalizar y optimizar tus ventas en Venezuela! 🇻🇪
🔗 Escríbenos al DM o al link en bio para una demostración en vivo.

`#OdooVenezuela #LocalizationVenezuela #TasaBCV #Odoo19 #EcommerceVenezuela #EmprendimientoVenezuela`

---

### ⚡ Opción 2: Enfoque Técnico y de Control (Tu Código, Tus Reglas)

**¡El código es tuyo! Configura Odoo Community a tu medida en Venezuela** 💻🔥

Si estás buscando una plataforma de gestión para tu negocio que te dé libertad total sin licencias costosas ni mensualidades ocultas, Odoo Community es la respuesta.

Nuestro módulo añade las piezas clave que todo comercio en Venezuela necesita:
*   Sincronización automática de tasa de cambio oficial BCV.
*   Gestión de costos y precios duales (VES/USD) en inventario, ventas y facturas.
*   Validación de comprobantes de pago bancarios por el propio cliente en la web.
*   Envíos automáticos de confirmaciones de compras por WhatsApp.

---
💡 **Módulo de Contabilidad**
Incluido en Odoo Community. Cubre libros contables, facturación e informes financieros. No cumple al 100% con los requisitos del SENIAT, pero al ser Community el código es completamente tuyo. Si decides homologarlo, te ayudo gratis con toda la parte técnica y desarrollo necesario.
---

Toma el control absoluto de tu software empresarial. 🛠️
📩 Déjanos un mensaje y te asesoramos sin costo sobre cómo empezar.

`#OdooCommunity #SoftwareLibre #PythonOdoo #PymesVenezuela #TecnologiaVenezuela #OdooDev`

---

### 💬 Opción 3: Enfoque de Experiencia de Cliente (E-commerce + WhatsApp + Pagos)

**Dale a tus clientes la experiencia de compra que se merecen en Venezuela** 🛒🇻🇪

Comprar online en el país a veces puede ser complicado: calcular la tasa, enviar el pago, mandar el comprobante por una vía y la dirección por otra... ¡Es hora de simplificar el flujo!

Con esta solución integrada en Odoo 19:
✅ Tu cliente ve precios duales exactos basados en la tasa oficial BCV.
✅ Paga por transferencia o Pago Móvil y sube su comprobante directamente en la web.
✅ Recibe de inmediato un mensaje de WhatsApp confirmando su pedido, detalles del envío y horarios de atención.

---
🛡️ **Módulo de Contabilidad**
Incluido en Odoo Community. Cubre libros contables, facturación e informes financieros. No cumple al 100% con los requisitos del SENIAT, pero al ser Community el código es completamente tuyo. Si decides homologarlo, te ayudo gratis con toda la parte técnica y desarrollo necesario.
---

¡Haz que comprar en tu tienda sea fácil, rápido y profesional!
👉 Haz clic en el enlace de nuestro perfil y agenda tu demo hoy mismo.

`#LocalizacionVenezuela #MarketingDigitalVenezuela #OdooSales #PosVenezuela #NegociosCaracas #WhatsAppBusiness`