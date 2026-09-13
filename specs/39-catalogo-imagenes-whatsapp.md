# SPEC 39 — Miniaturas de producto en WhatsApp: imágenes del catálogo y búsqueda

> **Status:** Implemented
> **Depends on:** SPEC 37 (botones ya en vivo), SPEC 38 (número→AGREGAR ya en vivo). Se implementa ANTES que SPEC 40 (decisión del usuario).
> **Date:** 2026-09-12
> **Objective:** Que el catálogo y la búsqueda del carrito envíen una imagen por producto como media-message de WhatsApp con caption (nombre + precio), usando URLs públicas absolutas — hoy Odoo las devuelve pero n8n nunca las envía.

## Por qué existe esta spec

Reporte reiterado del usuario (12/9): "las imágenes nunca se ven" en el catálogo. Diagnóstico
verificado: `product_buscar._producto_dict` devuelve `image_url` **relativa**
(`/web/image/product.product/{id}/image_128`) y el controller expone `imagenes` en
catálogo/búsqueda, pero `Enviar_mensaje_de_IA1` (n8n) solo envía el payload de texto → las
imágenes jamás se envían. Verificado además: Pizza y Refresco tienen imagen (los otros 3
productos no), `/web/image/...` es **público** (200, image/webp, sin auth) y
`web.base.url` = `https://lead.integraia.lat` — disponible para construir la URL absoluta
que YCloud/Meta necesita para descargar el medio.

## Scope

**In:**

1. **`chatbot_cart` (Odoo):**
   - `product_buscar.py`: `image_url` **absoluta**: `{web.base.url}/web/image/product.product/{id}/image_128` (desde `ir.config_parameter`).
   - Controller `_imagenes_de_productos`: devolver objetos `{link, caption}` (caption: "Nombre — Bs. X / $Y") solo de productos con `has_image`.
2. **n8n — `Unificar_salida_carrito`:** tras el item de texto (que conserva botones), emitir
   un item extra por imagen con `whatsappPayload = {from, to, type: 'image', image: {link,
   caption}}`. `Enviar_mensaje_de_IA1` ya prefiere `whatsappPayload` → envía un
   media-message por item **sin cambios en el nodo de envío**.
3. Orden de llegada: primero el texto del catálogo (índice + botones), luego las imágenes.
4. **Bump `chatbot_cart` → `19.0.1.8.0`** + tests + upgrade leads + aplicar n8n vía
   **Publish** (lección 36/37) + export a la ruta prod.
5. E2E: "carrito" → catálogo + imágenes de Pizza y Refresco; búsqueda "pizza" → lista + imagen.

**Out of scope:**

- Imagen al agregar ("✅ Agregué" con ficha) — decisión: solo catálogo/búsqueda.
- Imágenes en "ver carrito" (resumen).
- Video/documentos como medios.
- SPEC 40 (escalabilidad; se implementa después: orden 39→40).

## Modelo de datos

Sin modelos nuevos. En la respuesta de `/chatbot_cart/procesar` (catálogo/búsqueda),
`imagenes` pasa de `[string]` a `[{link, caption}]`.

## Plan de implementación

1. Odoo: URL absoluta con `web.base.url` + captions en `_imagenes_de_productos`; tests
   (URL absoluta, caption con precio, exclusión de productos sin imagen).
2. n8n: harness determinista del jsCode nuevo de `Unificar_salida_carrito` (items de
   imagen) → aplicar al workflow (editor → **Publish**, o cirugía de versión publicada) →
   export a la ruta prod.
3. E2E real por WhatsApp: catálogo + búsqueda con imágenes; verificar envíos en ejecuciones.

## Criterios de aceptación

- [ ] Tras el texto del catálogo llegan media-messages con la imagen de cada producto que
      la tenga (hoy: Pizza y Refresco) y caption "Nombre — Bs. X / $Y".
- [ ] Productos sin imagen no generan mensajes (solo quedan en el texto).
- [ ] La búsqueda ("pizza") también envía la imagen del resultado.
- [ ] El texto del catálogo llega primero con sus botones intactos.
- [ ] Las URLs son absolutas y públicas (curl sin auth → 200).
- [ ] Suites `chatbot_cart` en verde + bump `19.0.1.8.0`.
- [ ] n8n publicado (Publish) y export actualizado en la ruta prod.

## Decisiones tomadas y descartadas

- **Tomado:** imágenes en catálogo + búsqueda — **descartado** también al agregar (menos
  mensajes; el catálogo es el punto de decisión de compra).
- **Tomado:** un media-message por producto (WhatsApp no tiene imágenes inline en texto).
- **Tomado:** URL absoluta con `web.base.url` (estándar por instancia) — **descartado**
  hardcode o `cta_url` de la config.
- **Tomado:** reusar el mecanismo `whatsappPayload` (items múltiples = envíos múltiples) —
  **descartado** tocar `Enviar_mensaje_de_IA1` (no hace falta).
- **Tomado:** aplicar n8n vía Publish (lección del modelo draft/versión/publish).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| `web.base.url` mal configurado en un deploy (localhost) → Meta no descarga la imagen | Verificación manual del parámetro + test de URL pública por curl |
| 5 imágenes seguidas por página de catálogo (spam visual) | Aceptable en catálogos chicos; SPEC 40 reduce páginas en catálogos grandes |
| Orden/latencia de llegada de las imágenes | Aceptable (async natural de WhatsApp) |

## What is **not** in this spec

- Imagen al agregar producto.
- Imágenes en el resumen del carrito.
- Video/documentos.
- Escalabilidad del catálogo (SPEC 40, va después).

Cada uno de esos, si llega, va en su propia spec.