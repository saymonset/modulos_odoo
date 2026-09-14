# SPEC 42 — Checkout "teléfono primero": autocompletado de datos por teléfono

> **Status:** Approved
> **Depends on:** —
> **Date:** 2026-09-14
> **Objective:** En el paso Detalles/Dirección del checkout web, pedir solo el teléfono; si existe en BD autocompletar los datos del usuario (campos ocultos) para evitar duplicados, y si no existe mostrar todos los campos para llenar.

## Por qué existe esta spec

La base está medio construida en `bcv_rate_update_venezuela`: el CSS de `address_autofill.css` ya oculta los campos del checkout y existe el componente OWL `AddressAutofill`, pero **el template de montaje (`views/website_sale_templates.xml`) está comentado en el manifest** (`__manifest__.py:46`), así que el componente nunca se monta — hoy solo actúa el CSS (oculta todo menos email/teléfono) y no hay autocompletado real. Además la búsqueda existente (`/shop/search_partner_by_email_or_phone`) usa `ilike` de email/teléfono sin normalizar dígitos, débil para formatos venezolanos. El patrón robusto ya existe en `ai_chatbot_1_portal` (`ChatBotUtils.find_partner_by_phone`, chatbot_utils.py:158) con 4 estrategias de matching por dígitos.

## Scope

**In:**

1. **Montaje real del componente** — habilitar `views/website_sale_templates.xml` en el manifest y montar con `<owl-component name="bcv_rate_update_venezuela.AddressAutofill"/>` (patrón de `payment_attachment_templates.xml`) en un inherit de `website_sale.address` (pantalla Detalles), antes del formulario `address_form`.
2. **Ruta `/shop/find_partner_by_phone`** (`type='json'`, `auth='public'`, `website=True`, `csrf=False`) con matching robusto por dígitos (mín. 7 dígitos; estrategias: sufijo 10, `ilike` completo, sufijo 8, comparación manual) copiado de `ChatBotUtils.find_partner_by_phone`. Respuesta `{found, partner:{name, phone, email, company_name, street, street2, city, zip, vat, country_id, state_id}}`. Se reemplaza la ruta antigua (muerta, el componente nunca se montó).
3. **OWL `AddressAutofill`** — estado inicial solo teléfono visible; disparo en Enter + blur; si existe → rellena campos ocultos + banner "Hola {nombre}, tus datos están cargados" con enlace "¿No eres tú? Completa tus datos"; si no existe → revela todos los campos + banner "No encontramos tu teléfono. Completa tus datos".
4. **CSS** — ocultar por defecto todos los campos del checkout excepto teléfono (incluye `company_name` y sus labels).
5. **Tests** — helper de matching en `TransactionCase`: formatos distintos encuentran al mismo partner; sin match; `<7` dígitos no busca.
6. **Bump** `bcv_rate_update_venezuela` a `19.0.1.3.0` + upgrade en leads + E2E manual.

**Out of scope:**

- Ligar la orden al partner encontrado en el submit (dedup se delega al pre-relleno + dedup de Odoo por vat/email).
- Búsqueda por email (solo teléfono).
- Auto-búsqueda con debounce mientras escribe.
- Dependencia de `ai_chatbot_1_portal` (la lógica se copia).
- Campos readonly/bloqueados cuando el usuario existe.

## Modelo de datos

Sin estructuras nuevas. Reusa `res.partner`. Solo la nueva ruta JSON.

## Plan de implementación

1. `controllers/address_autofill.py`: helper `find_partner_by_phone_digits(env, phone)` (copia de estrategias) + ruta nueva `/shop/find_partner_by_phone`; eliminar la ruta antigua. Verificar los ids/names reales del template `website_sale.checkout` en leads antes de seguir.
2. `__manifest__.py`: descomentar `views/website_sale_templates.xml`; reemplazar el montaje manual del script por `<owl-component>` en inherit de `website_sale.address`; bump a `19.0.1.3.0`.
3. `static/src/css/address_autofill.css`: ocultar todo menos teléfono (base + labels).
4. `static/src/js/address_autofill.js` + `static/src/xml/address_autofill.xml`: estado phone-only, bind Enter+blur, banners found/not-found, reveal y fill.
5. Tests `tests/test_address_autofill.py` (helper de matching) en verde.
6. Upgrade en leads + E2E manual (teléfono existente y teléfono nuevo).

## Criterios de aceptación

- [ ] Al cargar el paso Detalles solo se ve el campo Teléfono (sin nombre/email/dirección/vat/etc.).
- [ ] Teléfono existente + Enter (o blur) → banner "Hola {nombre}, tus datos están cargados" sin rellenar visualmente los campos.
- [ ] Al continuar con ese teléfono, el pedido usa los datos del partner encontrado y no crea un partner duplicado.
- [ ] Teléfono inexistente → se muestran todos los campos del checkout para llenar.
- [ ] Teléfono con <7 dígitos al presionar Enter → revela los campos sin llamada al servidor.
- [ ] "0414-123.45.67", "+584141234567" y "04141234567" encuentran al mismo partner.
- [ ] `/shop/find_partner_by_phone` sin match → `{found: False}`.
- [ ] Suites de `bcv_rate_update_venezuela` en verde + bump aplicado en leads.

## Decisiones tomadas y descartadas

- **Tomado:** solo teléfono visible al inicio (pedido del usuario).
- **Tomado:** disparo Enter + blur — **descartado** solo Enter y debounce automático.
- **Tomado:** campos ocultos + banner cuando existe — **descartado** readonly.
- **Tomado:** pre-rellenar + dedup de Odoo (vat/email) — **descartado** ligar el partner en el submit (más invasivo).
- **Tomado:** copiar la lógica de búsqueda a `bcv_rate_update_venezuela` — **descartado** depender de `ai_chatbot_1_portal` (arrastra dependencias pesadas).
- **Tomado:** revelar checkout estándar completo si no existe — **descartado** subconjunto mínimo.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| DOM del checkout (ids/names) distinto a lo asumido | Paso 1 verifica el template real en leads antes de codificar |
| Flash de campos visibles antes del montaje | CSS por defecto oculta (phone-only); el JS solo revela |
| Duplicado residual si el partner no tiene vat/email | Documentado; ligado server-side queda fuera de scope |
| `company_name` no exista en este checkout | Verificar en paso 1; si no existe, se omite de la lista |

## What is **not** in this spec

- Ligar la orden al partner existente en el submit.
- Búsqueda por email o debounce automático.
- Dependencia del módulo chatbot.
- Campos readonly cuando el usuario existe.

Cada uno de esos, si llega, va en su propia spec.