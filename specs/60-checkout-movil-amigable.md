# SPEC 60 — Checkout móvil amigable: pago por transferencia con pasos claros y contraste

> **Estado:** Implemented
> **Depende de:** SPEC 42 (checkout teléfono primero)
> **Fecha:** 2026-09-19
> **Objetivo:** Hacer las pantallas de Detalles (teléfono) y Pago (transferencia/pago móvil) del checkout web claras y usables en móvil, reordenando el formulario, dando contraste real a fondo/inputs y agregando botón Continuar e instrucción visible, sin tocar ninguna funcionalidad.

## Por qué existe esta spec

Usuarios reales se pierden en el checkout de IntegraIA: (1) la burbuja flotante del chatbot n8n (`.chat-window-toggle`, 64px, `position:fixed`, z-index 9999) tapa el botón de pago en móvil; (2) la tarjeta "Instrucciones de pago" aparece ARRIBA de los selects de banco (`payment_proof_component.xml:11-36`), así que el texto "Seleccione un banco destino…" queda lejos de donde el usuario elige; (3) `payment_proof_component.css` está **vacío**, todo depende del tema blanco del sitio — no se distingue dónde escribir; (4) en Detalles, el banner solo aparece tras buscar (`address_autofill.xml:4`, condición `status !== 'idle'`) y el disparo es solo Enter/blur — el usuario móvil no sabe que debe introducir el teléfono ni cómo activar la validación.

## Scope

**In:**

1. **Reorden del formulario de pago con pasos numerados** (`static/src/xml/payment_proof_component.xml`): 1) Fecha + Forma de pago + Banco origen + Banco destino → 2) tarjeta de datos del banco destino (aparece DEBAJO al seleccionar) → 3) Referencia + montos (Bs/BCV/USD/COP) → 4) Comprobante. Mismos IDs, mismos bindings `t-on-*`/`data-field`, misma lógica.
2. **CSS de contraste y móvil** (`static/src/css/payment_proof_component.css`, hoy vacío): tarjeta fondo `#f5f7fa`, labels `#2a3a4b`, inputs blancos con borde visible y foco azul `#4a90e2`, alto mínimo 44px y `font-size:16px` en inputs (evita zoom de iOS), pasos con encabezados numerados.
3. **Ocultar burbuja del chatbot en checkout móvil** (CSS global ya cargado por `web.assets_frontend`): en pantallas <992px, ocultar `.chat-window-wrapper` cuando existe `#payment_proof_form_container` (Pago) o `form[name="address_form"]` (Dirección/Detalles). En desktop sigue visible.
4. **Pantalla Detalles: instrucción + botón Continuar** (`static/src/xml/address_autofill.xml` + `static/src/js/address_autofill.js`): tarjeta siempre visible en estado `idle` ("Escribe tu teléfono y presiona Continuar"), input Teléfono resaltado (CSS), y botón Continuar a ancho completo inyectado bajo el input (en `#div_phone` vía DOM en `onMounted`, mismo patrón que los listeners actuales) que llama `_searchByPhone`. Enter y blur se mantienen intactos.
5. **Bump** `bcv_rate_update_venezuela` a `19.0.1.4.0` + upgrade en lead.

**Out of scope (para futuras specs):**

- Rediseñar los campos estándar del checkout que se revelan cuando el teléfono no existe (Odoo nativo).
- Cambios en el widget de chat n8n (solo se oculta en checkout móvil; no se toca su JS).
- Cambios en POS (`pos_venezuela_dual_currency`) ni en backend/controllers/rutas.
- Tests automatizados nuevos (cambio presentacional; verificación manual + suites existentes).

## Modelo de datos

Sin estructuras nuevas. Sin campos, rutas ni IDs nuevos. Solo cambian templates OWL, CSS y un botón inyectado por DOM. Reusa el modelo de SPEC 42.

## Plan de implementación

1. `static/src/css/payment_proof_component.css`: tarjeta `#f5f7fa`, labels `#2a3a4b`, inputs borde visible + foco `#4a90e2`, reglas móvil (44px alto, 16px font, full-width). Manual: recargar Pago en 375px y ver el formulario destacado.
2. `static/src/xml/payment_proof_component.xml`: reordenar a los 4 pasos numerados; mover la tarjeta de datos del banco a después de la fila de bancos. Manual: seleccionar Banco destino → datos aparecen debajo del select.
3. CSS de checkout: ocultar `.chat-window-wrapper` en <992px cuando exista `#payment_proof_form_container` o `form[name="address_form"]`. Manual: en móvil la burbuja desaparece en Detalles y Pago; en desktop sigue.
4. `static/src/xml/address_autofill.xml`: rama `idle` con tarjeta de instrucción. `static/src/js/address_autofill.js`: inyectar botón Continuar dentro de `#div_phone` (ancho completo) que llame `_searchByPhone`. `static/src/css/address_autofill.css`: resaltar input `#o_phone` (borde azul, tamaño móvil). Manual: cargar Detalles en móvil, escribir teléfono, presionar Continuar → mismo banner found/not_found que con Enter.
5. Bump `19.0.1.4.0` en `__manifest__.py`, upgrade del módulo en lead, E2E manual móvil completo (carrito → Detalles → Pago → comprobante) + suites existentes en verde.

## Criterios de aceptación

- [ ] En móvil (<992px) la burbuja del chatbot no se ve en Detalles ni en Pago; en desktop (≥992px) sí se ve.
- [ ] En Pago el orden visible es: 1 fecha/forma/bancos → 2 datos del banco → 3 referencia/montos → 4 comprobante, con encabezados numerados.
- [ ] La tarjeta de datos del banco aparece debajo del select Banco destino al seleccionarlo (no arriba).
- [ ] El formulario de pago tiene fondo de tarjeta distinguible del fondo blanco de la página; los labels son oscuros y legibles sobre su fondo.
- [ ] Todos los inputs/selects tienen borde visible, foco azul y en móvil ≥44px de alto con font-size 16px.
- [ ] En Detalles, al cargar (estado `idle`) se ve la tarjeta de instrucción, el campo Teléfono resaltado y el botón Continuar a ancho completo.
- [ ] Presionar Continuar dispara la misma búsqueda que Enter/blur hoy (banner "Hola {nombre}…" o "No encontramos tu teléfono…").
- [ ] Validación intacta: monto ≥ total habilita el botón de pago; el comprobante sigue siendo obligatorio; la subida funciona igual.
- [ ] El diff no toca controllers, rutas, campos de modelo ni IDs de inputs (`payment_date`, `bank_origin`, `bank_destination`, `reference`, `amount_vef`, `amount_usd`, `payment_proof_file`, `o_phone`, etc.).
- [ ] Suites de `bcv_rate_update_venezuela` en verde y bump `19.0.1.4.0` aplicado en lead.

## Decisiones tomadas y descartadas

- **Tomado:** ocultar el toggle del chat solo en checkout móvil vía CSS `:has()` — **descartado** tocar el JS del widget n8n o moverlo de posición (menor riesgo, reversible, cero dependencia del CDN).
- **Tomado:** reorden XML puro con pasos numerados — **descartado** reescribir el componente o dividirlo en sub-pantallas (la funcionalidad ya probada no se toca).
- **Tomado:** paleta gris claro `#f5f7fa` + azul `#4a90e2` — **descartado** azul suave o blanco reforzado (coherencia con el azul del chatbot y contraste verificado sobre tema blanco).
- **Tomado:** botón Continuar inyectado por DOM junto al input (el componente OWL se monta fuera del form nativo) — **descartado** renderizarlo en el template (quedaría lejos del campo).
- **Tomado:** verificación manual móvil + suites existentes — **descartado** test OWL automatizado (cambio presentacional, sin lógica nueva).
- **Tomado:** Enter y blur siguen funcionando además del botón.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| El icono estorbante sea un botón del tema y no el toggle n8n | Paso 3 verifica en DevTools la clase real en lead; si difiere, se extiende el selector CSS |
| `:has()` no soportado en navegadores viejos | Degradación aceptable: el toggle queda visible, nada se rompe |
| El tema del sitio pisa los estilos nuevos | CSS con selectores por ID (`#payment_proof_form_container`) y `!important` puntual |
| `address_form` aparece también al editar dirección desde el portal | Comportamiento deseado: misma ayuda en cualquier edición de dirección |

## What is **not** in this spec

- Rediseño de los campos estándar revelados del checkout Odoo.
- Cambios al widget de chat n8n o al flujo del chatbot.
- Cambios en POS, controllers, rutas o modelos.
- Tests automatizados del frontend.

Cada uno, si llega, va en su propia spec.