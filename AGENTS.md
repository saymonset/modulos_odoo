# AGENTS.md — Odoo Modules monorepo

This repo contains Odoo 19.0 custom modules under `shared/extra/19.0/`. Each module is an independent Odoo addon.

## Module: `bcv_rate_update_venezuela` (`shared/extra/19.0/bcv_rate_update_venezuela`)

### Quick start
- Python deps: `uv pip install requests beautifulsoup4`
- No JS build step, no npm, no codegen — OWL components are plain ES modules

### Key dependencies (from manifest)
- `currency_rate_update_base` + `currency_rate_update_venezuela` (BCV rate fetching)
- `whatsapp_cloud_integration` (WhatsApp confirmations)
- `website_sale`, `payment`, `point_of_sale`, `sale_management`, `account`, `stock`, `contacts`

You MUST have these Odoo addons available in the addons path for the module to work.

### Architecture notes
- **`models/`**: Standard Odoo model inheritance. `sale.order.line` computes USD prices at BCV rate. `account.move.line` copies those values on create.
- **`controllers/`**: Public JSON/HTTP routes for payment proof upload, address autofill, payment validation.
- **`services/`**: `whatsapp.service` (AbstractModel) — delegates to a use case.
- **`uses_cases/`**: Plain Python classes (not Odoo models) that receive `env` in constructor. The `SendWhatsappConfirmationUseCase` sends via `whatsapp_cloud_integration` template `pedido_confirmado_ubicacion`.
- **`static/src/`**: OWL components (`PaymentProofComponent`, `AddressAutofill`) registered in `public_components` registry. No build step — they use `owl` from Odoo's bundled version.
- **`tests/test_security_payment.py`**: Only test file. Extends `TransactionCase`. Run with standard Odoo test runner: `odoo -u bcv_rate_update_venezuela --test-enable --stop-after-init`.
- **`hooks.py`**: `post_init_hook` + `uninstall_hook` both delete specific named views to avoid orphans.

### Gotchas
- `views/website_sale_templates.xml` and `views/invoice_report_templates.xml` are **NOT loaded** (commented out in `__manifest__.py` `data` key). Do not add them back without understanding why they were disabled.
- The `assets` entry uses `bcv_rate_update_venezuela/static/src/**/*` for `point_of_sale.assets` and `web.assets_backend` (glob), but lists files individually for `web.assets_frontend`. Keep this consistent.
- Payment proof upload uses **`fetch`/`FormData`** (not JSON RPC) to `/shop/upload_payment_proof`.
- Address autofill hides checkout address fields via **`display: none !important`** in CSS — a fragile selector approach.
- Only 2 access rules defined (in `security/ir.model.access.csv`), both for internal users (`base.group_user`).
- Menu items are placed under `account.menu_finance` > `Tasas de Cambio` > `Actualización Multi-País`.
- The module auto-install is `False` and it is not an application.
