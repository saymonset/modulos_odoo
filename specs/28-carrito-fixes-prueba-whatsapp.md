# SPEC 28 — Fixes del carrito y prueba end-to-end por WhatsApp

> **Status:** Implemented
> **Depends on:** SPEC 27 (chatbot-carrito-whatsapp)
> **Date:** 2026-09-11
> **Objective:** Corregir los dos defectos conocidos de `chatbot_cart` y habilitar la prueba end-to-end del carrito por WhatsApp real en staging, con guía actualizada.

## Scope

**In:**

- Fix 1 — `controllers/chatbot_cart_controller.py`: la acción `BUSCAR` guarda los resultados en `carrito['ultima_busqueda']` (vía `session._guardar_carrito`) para que "responde el número" resuelva el producto.
- Fix 1b — `services/product_buscar.py`: devuelve el id de la variante (`tmpl.product_variant_id.id`) en vez del id del template, para que la referencia numérica y la búsqueda por nombre agreguen el producto correcto (el carrito opera sobre `product.product`).
- Fix 2 — `models/sale_order.py`: `_resolver_partner(session_id, phone=None, conversation_id=None)` recibe `conversation_id`; si no hay teléfono, lo recupera del `estado` de la sesión (`datos_paciente.phone/solicitar_phone/telefono`); se elimina el lookup global de `whatsapp.history` (tomaba el último mensaje entrante de cualquier conversación). Sin teléfono en ningún lado → partner genérico "Cliente Chatbot {session_id}".
- Tests nuevos para ambos fixes; los 46 existentes siguen en verde.
- Bump `__manifest__.py` de `chatbot_cart` a `19.0.1.1.0`.
- Actualizar `docs/27-chatbot-carrito-como-probar.md`: quitar las limitaciones ya arregladas y añadir la sección "Prueba end-to-end por WhatsApp (staging)": redirigir n8n a staging (mismo número, `waba` "whatsapp 0412"), activación del flujo por el agente, operaciones del carrito, pago y envío del vaucher.

**Out of scope (para futuras specs):**

- Deploy de `chatbot_cart` a producción.
- Instagram/Messenger, botones interactivos, carrusel (fase 2 del SPEC 27).
- Cambios al webhook de imágenes de `whatsapp_cloud_integration` (ya parsea vaucher y lo adjunta).
- Cambios en n8n más allá de la redirección temporal a staging.

## Data model

Esta feature no introduce estructuras nuevas. Reutiliza:

- Clave `carrito.ultima_busqueda` del JSON `chatbot.session.estado` (ya existía, solo pasa a poblarse).
- `ir.attachment` para el vaucher (patrón existente de `whatsapp_cloud_integration`).
- `sale.order` con `client_order_ref = session_id` para la prueba.

## Implementation plan

1. Guardar `ultima_busqueda` en la rama `BUSCAR` de `_ejecutar`. Test manual: `buscar "pizza"` → `consultar` muestra la lista en `ultima_busqueda`.
2. Hacer `_resolver_partner` conversation-aware y eliminar el lookup global. Test manual: `pagar` sin teléfono crea "Cliente Chatbot {session_id}", nunca el partner de otra conversación.
3. Añadir tests deterministas de ambos fixes; correr la suite completa (`--test-enable`) en verde.
4. Bump de versión a `19.0.1.1.0`.
5. Actualizar la guía en `docs/`: sección WhatsApp con los pasos de redirección de n8n, criterio de éxito por fase (carrito → pago → vaucher) y cómo revertir la redirección.

## Acceptance criteria

- [ ] Tras `buscar`, `consultar` devuelve `ultima_busqueda` con los productos mostrados.
- [ ] `procesar` con "agrega 1" (refiriéndose al resultado de la búsqueda) agrega el producto correcto.
- [ ] `pagar` sin teléfono no usa nunca el `whatsapp.history` global; crea partner genérico o por teléfono de la sesión.
- [ ] Si la sesión tiene teléfono capturado, el `sale.order` queda con ese partner.
- [ ] Suite completa de `chatbot_cart` en verde con los tests nuevos incluidos.
- [ ] Versión en manifest = `19.0.1.1.0`.
- [ ] La guía incluye la sección WhatsApp con redirección de n8n, fases de prueba y rollback.
- [ ] En staging con WhatsApp real: el agente activa `flujo_carrito`, el carrito opera por texto y "pagar" crea una orden `state=sale` con partner resuelto por teléfono.
- [ ] Enviar el vaucher como imagen lo adjunta como `ir.attachment` a esa orden.

## Decisions

- **Sí:** arreglar solo los 2 defectos conocidos; el resto del módulo ya pasa 46 tests.
- **Sí:** `product_buscar` devuelve `product.product` (variante por defecto) y no el id del template: el carrito y `agregar` operan sobre `product.product`, así la referencia numérica y la búsqueda por nombre agregan el producto correcto.
- **Sí:** resolver el partner por la sesión (`estado`) antes que crear genérico; elimina el bug del partner aleatorio global.
- **Sí:** eliminar el lookup de `whatsapp.history` en vez de filtrarlo: el modelo no tiene `conversation_id`, así que no hay forma correcta de filtrar.
- **Sí:** probar WhatsApp en staging con el mismo número redirigiendo n8n; prod no tiene `chatbot_cart` aún.
- **Sí:** la guía vive en `docs/27-chatbot-carrito-como-probar.md` (se actualiza, no se duplica).
- **No:** deploy a prod en esta spec (otra spec o el pipeline normal tras aprobar).
- **No:** tocar el webhook de imágenes; ya cumple (descarga vía `waba.account.download_media` y adjunta a la orden).

## Risks

| Riesgo | Mitigación |
|---|---|
| Redirigir n8n a staging desvía tráfico real de prod | Ventana de prueba corta + revert documentado en la guía (apuntar n8n de vuelta a prod) |
| Clasificación IA inestable al probar por WhatsApp | Fallback determinista por keywords ya cubre los comandos base |
| El agente no activa `flujo_carrito` con frases ambiguas | La política de inicio es `confirmation`; la guía lista frases de activación probadas |

## What is **not** in this spec

- Deploy a producción y pruebas del WhatsApp real del negocio en prod.
- Nuevas plataformas, botones interactivos o carrusel.
- Ajustes de precios, impuestos o formato de mensajes no relacionados con los fixes.