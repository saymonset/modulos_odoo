# SPEC 27 — Carrito de compra por WhatsApp con IA

> **Status:** Approved
> **Depends on:** módulos `ai_chatbot_1_portal`, `whatsapp_cloud_integration`, `bcv_rate_update_venezuela`
> **Date:** 2026-09-11
> **Objective:** Permitir comprar por WhatsApp: el usuario consulta productos (con imagen), arma un carrito con operaciones fáciles (ver, agregar, quitar, modificar, volver, cancelar) y paga enviando el vaucher, reutilizando los módulos de chatbot, WhatsApp y bcv.

## Scope

**In:**

- Módulo nuevo `shared/extra/19.0/chatbot_cart` (solo WhatsApp en fase 1).
- Estado del carrito como JSON en `chatbot.session.estado` (clave `carrito`).
- Búsqueda de productos vía AI: interpreta texto natural, busca en `product.template` por nombre/default_code, muestra top N.
- Mostrar cada producto con imagen (mensaje de imagen + caption) seguida de lista numerada de texto.
- Operaciones del carrito en lenguaje natural vía AI: ver, agregar, quitar, modificar cantidad, volver, cancelar, ayuda.
- Pago: resumen completo (items, cantidades, subtotales/total VES, USD, COP) + datos bancarios + recepción del vaucher como imagen por WhatsApp.
- Al pagar: materializar `sale.order` desde el carrito JSON, resolver/crear `res.partner` (anónimo hasta pagar), reusar `action_confirm` de bcv (confirmación WhatsApp).
- Visibilidad condicionada de conversiones: COP solo si `res.company.cop_show_fields`; VES y USD siempre; la tasa se menciona solo en el resumen de pago.
- Capa de UX amigable: confirmaciones en operaciones ambiguas, mini-estado tras cada acción, "ayuda" siempre disponible, errores con salida.
- Extender `whatsapp_cloud_integration`: parsear imágenes entrantes (vaucher) y enviar imágenes con caption (productos).
- Controllers REST `/chatbot_cart/*`.

**Out of scope (fase 2):**

- Navegación iterativa tipo carrusel/catálogo (recorrer categorías, "volver a ver más" persistente).
- Plataformas Instagram y Messenger (solo WhatsApp en fase 1).
- Botones/lists interactivos de WhatsApp (se opera por texto natural).
- Descuentos, promociones, cupones, impuestos por ítem.

## Data model

El carrito vive en el JSON `estado` de `chatbot.session`:

```json
{
  "modo": "CARRITO",
  "carrito": {
    "items": [
      {
        "product_id": 42, "name": "Camisa Roja", "default_code": "CAM-R",
        "qty": 2, "price_ves": 25.00, "price_usd": 6.50,
        "image_url": "/web/image/product.product/42/image_128"
      }
    ],
    "ultima_busqueda": [ { "product_id": 43, "name": "Camisa Azul", "price_usd": 7.00, "image_url": "..." } ]
  }
}
```

No se introducen tablas nuevas. Se añaden métodos a `chatbot.session`, `sale.order` y `whatsapp`, más un `chatbot.flujo` `flujo_carrito` (palabras clave: carrito, compra, comprar, pedido, producto, agregar) que activa el modo CARRITO.

## Implementation plan

1. Esqueleto de `chatbot_cart` (manifest, `__init__`, modelos vacíos). Instalable sin error.
2. Extender `chatbot.session`: modo `CARRITO` + helpers `_get_carrito` / `_guardar_carrito`.
3. `services/cart_service.py`: `agregar`, `quitar`, `modificar`, `consultar`, `resumen` (tasas VES/USD/COP vía `_get_bcv_rate`/`_get_cop_rate`, COP condicionado a `cop_show_fields`).
4. `services/product_buscar.py`: búsqueda top N en `product.template` con precios e imagen.
5. Controller `/chatbot_cart/procesar` (POST): texto natural → AI clasifica acción + args → ejecuta → devuelve `texto_para_usuario` + URLs de imagen.
6. Controllers `/chatbot_cart/consultar`, `/chatbot_cart/buscar`, `/chatbot_cart/pagar` (resumen + bancos).
7. `sale.order._materializar_desde_carrito`: crea líneas, resuelve/crea `res.partner` por teléfono, llama `action_confirm`.
8. Extender webhook `whatsapp_cloud_integration`: parsear `type == 'image'`, descargar, adjuntar al `sale.order` (`ir.attachment`, patrón bcv).
9. `whatsapp_message`: método para enviar imagen con caption en la conversación.
10. Prompt: instrucciones de uso del carrito vía `configuracion_agente`.
11. Tests deterministas (cart CRUD, resumen, materialización, webhook imagen, visibilidad COP).
12. Bump versiones de `chatbot_cart` y `whatsapp_cloud_integration`.

## Acceptance criteria

- [ ] `/chatbot_cart/buscar` con "camisa roja" devuelve coincidencias con imagen, precio VES y USD.
- [ ] `/chatbot_cart/procesar` con "agrega 2 camisas rojas" añade el ítem correcto al carrito JSON.
- [ ] "quita la camisa azul" y "cambia la roja a 3" modifican el carrito correctamente.
- [ ] "ver carrito" devuelve items, cantidades y totales VES/USD/COP consistentes.
- [ ] Con `cop_show_fields=False`, ningún mensaje del bot menciona COP; con `True`, se incluyen totales COP.
- [ ] "cancelar" en modo carrito ofrece guardar/volver al menú, vaciar (con confirmación) o seguir comprando; nunca destruye el carrito en silencio.
- [ ] "ayuda" lista las acciones del carrito en cualquier momento del modo CARRITO.
- [ ] Vaciar el carrito ("quita todo") pide confirmación antes de ejecutarse.
- [ ] Producto inexistente devuelve mensaje amigable con salida sin romper la sesión.
- [ ] Después de cada operación, el bot confirma lo hecho y muestra mini-estado ("✅ Agregué 2 camisas rojas. 🛒 3 items — $55.00").
- [ ] `/chatbot_cart/pagar` materializa un `sale.order` con las líneas del carrito y `action_confirm` envía la confirmación WhatsApp.
- [ ] Un vaucher enviado como imagen se descarga y adjunta al `sale.order`.
- [ ] El carrito persiste entre mensajes (JSON en sesión) y expira por inactividad.
- [ ] Tests deterministas en verde.

## Decisions

- **Sí:** carrito JSON en `chatbot.session`; `sale.order` solo al pagar. Simple y coherente; evita drafts huérfanos.
- **No:** `sale.order` draft desde el inicio. Más robusto pero complejiza sin necesidad en fase 1.
- **Sí:** operaciones por texto natural vía AI. Reutilizable en IG/Messenger después.
- **No:** botones/lists interactivos en fase 1. Requiere más desarrollo de webhook; se difiere.
- **Sí:** imagen por mensaje con caption + lista numerada. Único formato posible en WhatsApp.
- **Sí:** vaucher por imagen (extendiendo el webhook). Mejor UX que link web.
- **Sí:** anónimo hasta pagar. El número de WhatsApp identifica; se pide nombre/cédula solo al pagar.
- **Sí:** COP condicionado a `cop_show_fields`; VES/USD siempre. Coherente con el resto del sistema bcv.
- **Sí:** "cancelar" amigable: guardar/volver al menú, vaciar (con confirmación) o seguir. Nunca destruye el trabajo del usuario en silencio.
- **Sí:** módulo nuevo `chatbot_cart` en `shared/extra/19.0`. Separa responsabilidad sin tocar bcv/ai_chatbot.
- **Sí:** solo WhatsApp en fase 1. Interactivos y webhook de imágenes solo existen para WA hoy.

## Risks

| Riesgo | Mitigación |
|---|---|
| La AI clasifica mal una operación | `gpt.service` + fallback determinista por keywords; si es ambiguo, pedir confirmación. |
| Precios USD/COP cambian entre mensajes | Tasa vigente al consultar/pagar; congelar en `sale.order` al confirmar (bcv). |
| Productos sin imagen / duplicados | `product.template` normalizado; orden estable en top N. |
| Entrega de media de Meta requiere token | Reusar el access_token de `waba.account` para descargar la imagen. |

## What is **not** in this spec

- Navegación iterativa con carrusel/catálogo (fase 2).
- Instagram y Messenger (fase 2).
- Botones/lists interactivos de WhatsApp.
- Descuentos, promociones, cupones, impuestos por ítem.
- Carrito/checkout web (ya existe vía website_sale).

Cada uno de esos, si llega, va en su propio spec.
