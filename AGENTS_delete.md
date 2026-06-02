# AGENTS.md — Odoo Modules monorepo

This repo contains Odoo 19.0 custom modules under `shared/extra/19.0/`. Each module is an independent Odoo addon.

## Module: `bcv_rate_update_venezuela` (`shared/extra/19.0/bcv_rate_update_venezuela`)

### Quick start
- Python deps: `uv pip install requests beautifulsoup4`
- No JS build step, no npm, no codegen — OWL components are plain ES mcd   odules.

### Key dependencies (from [__manifest__.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/__manifest__.py))
- `currency_rate_update_base` + `currency_rate_update_venezuela` (BCV rate fetching)
- `whatsapp_cloud_integration` (WhatsApp confirmations)
- `website_sale`, `payment`, `point_of_sale`, `sale_management`, `account`, `stock`, `contacts`

You MUST have these Odoo addons available in the addons path for the module to work.

### Architecture notes
- **`models/`**: Standard Odoo model inheritance.
  * [sale_order_line.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order_line.py): The [SaleOrderLine](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order_line.py#L3) computes USD prices (`price_usd_bcv`, `price_subtotal_usd_bcv`) at the active BCV rate on the fly.
  * [sale_order.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order.py): The [SaleOrder](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/sale_order.py#L9) contains binary payment proof (`payment_proof`) fields, and hooks into `action_confirm` to persist payment data and trigger post-confirmation hooks.
  * [account_move_line.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/account_move_line.py): The [AccountMoveLine](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/models/account_move_line.py#L3) copies those computed values to invoice lines on create.
- **`controllers/`**: Public JSON/HTTP routes.
  * [website_sale_attachment.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/website_sale_attachment.py): Route `/shop/upload_payment_proof` processes proof upload via multipart `fetch`/`FormData`.
  * [address_autofill.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/address_autofill.py): Routes `/shop/get_company_address_data` and `/shop/search_partner_by_email_or_phone` handle checkout address autofill.
  * [payment_validation.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_validation.py): Route `/payment/validate_and_save` performs backend check of payment reference, banks, and amounts.
  * [payment_custom_override.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/controllers/payment_custom_override.py): Overrides `/payment/custom/process` to process standard wire transfer confirmations.
- **`services/`**: [whatsapp_service.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services/whatsapp_service.py) - abstract [WhatsappService](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/services/whatsapp_service.py#L14) model delegating to a use case.
- **`uses_cases/`**: [send_whatsapp_confirmation_use_case.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/uses_cases/send_whatsapp_confirmation_use_case.py) - plain Python class [SendWhatsappConfirmationUseCase](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/uses_cases/send_whatsapp_confirmation_use_case.py#L7) executing message dispatches with the template `pedido_confirmado_ubicacion`.
- **`static/src/`**: OWL frontend components for [PaymentProofComponent](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/static/src/js/payment_proof_component.js) and [AddressAutofill](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/static/src/js/address_autofill.js) registered in Odoo's frontend assets registry.
- **`tests/`**: [test_security_payment.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/tests/test_security_payment.py) - contains [TestSecurityPayment](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/tests/test_security_payment.py#L6) verifying that manipulating frontend parameters (amount, exchange rates, etc.) does NOT alter the actual `amount_total` of the order or invoice. Run with:
  ```bash
  odoo -u bcv_rate_update_venezuela --test-enable --stop-after-init
  ```
- **`hooks.py`**: [hooks.py](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/hooks.py) - `post_init_hook` (`_clean_orphan_views`) and `uninstall_hook` (`_uninstall_cleanup`) to prevent duplicate/orphaned views.

### Gotchas
- `views/website_sale_templates.xml` and `views/invoice_report_templates.xml` are **NOT loaded** (commented out in the manifest `data` key). Do not add them back without understanding why they were disabled.
- The `assets` entry in manifest uses wildcards (`bcv_rate_update_venezuela/static/src/**/*`) for backend and POS assets, but lists files individually for `web.assets_frontend`. Keep this consistent.
- Payment proof upload uses `fetch`/`FormData` (not JSON RPC) to `/shop/upload_payment_proof`.
- Address autofill hides checkout address fields via CSS `display: none !important;` (fragile selector approach).
- Only 2 access rules defined in [ir.model.access.csv](file:///home/odoo/develop/modulos_odoo/shared/extra/19.0/bcv_rate_update_venezuela/security/ir.model.access.csv), both for internal users (`base.group_user`).
- Menu items are placed under `account.menu_finance` > `Tasas de Cambio` > `Actualización Multi-País`.
- The module auto-install is `False` and it is not an application.
