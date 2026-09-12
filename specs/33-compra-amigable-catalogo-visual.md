# SPEC 33 — Compra amigable: catálogo visual, navegación guiada y fix de routing

> **Status:** Approved
> **Depends on:** SPEC 29/30 (flujo carrito + botón), SPEC 31 (gate del carrito), SPEC 32 (anuncio determinista, JSON plano)
> **Date:** 2026-09-12
> **Objective:** Que comprar por WhatsApp sea fácil para cualquier negocio: el usuario nunca se pierde, ve productos como tarjetas amigables (imagen + precio + descripción), y "carrito"/"ver carrito" siempre muestran el catálogo en vez del mensaje genérico.

## Por qué existe esta spec

Transcript real del 12/9 (bot Karla Campoverde): la usuaria escribió "carrito" y "ver carrito" y recibió el mensaje genérico *"Escribe ver carrito, ayuda o el nombre de un producto para comenzar."* — exactamente el texto de la rama `valor` vacío en `chatbot_cart_controller.py:97`. Es decir, el mensaje llegó al endpoint sin `valor` (o el flujo no activó y cayó ahí), y la usuaria quedó estancada: nunca vio productos ni catálogo. Además, aunque funcionara, la UX actual solo muestra texto numerado y la usuaria no sabía qué escribir. La feature debe (a) arreglar la causa raíz del bloqueo y (b) rediseñar la experiencia de compra con el estándar del mercado: tarjetas imagen+precio+descripción, comando catálogo con paginación y guía persistente, sin que el usuario se pierda.

## Scope

**In:**

1. **Fix de routing (diagnóstico primero).** El mensaje genérico de `valor` vacío no debe aparecer cuando el usuario escribe "carrito"/"ver carrito". Diagnóstico en staging: logs de n8n (qué payload envía el flujo a `/chatbot_cart/procesar`) y de Odoo (qué `valor` recibe). Fix según causa raíz (mapeo de `valor` en `Unificar_salida_carrito` o activación del flujo). Además: en `procesar`, cuando el carrito está vacío, la acción `CONSULTAR` muestra el **catálogo** en vez de solo "está vacío".
2. **Comando catálogo (universal).** Palabras "catálogo/catalogo", "productos", "qué tienen/qué tienen", "catálogo" (clasificación IA + fallback determinista) → acción nueva `CATALOGO`. Muestra hasta 5 productos (`sale_ok=True`) ordenados por nombre, con paginación "más" (offset guardado en `carrito.pagina_catalogo`). El prompt del bloque carrito anuncia el comando.
3. **Tarjetas de producto.** Cada producto se envía como imagen con caption (`send_image_with_caption`, ya existe en `whatsapp_cloud_integration/models/whatsapp_message.py:36`): imagen + nombre + precio (VES/USD/COP según `cop_show_fields`) + descripción desde `description_sale` (vacío → solo nombre/precio). Lista numerada en texto como respaldo; el array `imagenes` de la respuesta REST alimenta el envío en n8n.
4. **Anti-pérdida (guía persistente).** Toda respuesta del carrito termina con mini-guía: `Responde el número para agregar • catálogo • ver carrito • pagar • cancelar`. Después de cada AGREGAR/QUITAR/MODIFICAR se muestra el estado del carrito (ya existe) + esa guía.
5. **Botones interactivos (mejora, con fallback).** El flujo n8n de salida del carrito envía el texto con **interactive reply buttons** (Cloud API `interactive.type=button`, hasta 3: `Catálogo`, `Ver carrito`, `Pagar`) cuando la respuesta lo marque (`extra['botones']`); si falla el envío interactivo → texto plano (fallback, sin romper nada).
6. **Bumps:** `chatbot_cart` → `19.0.1.4.0`; JSON n8n actualizado y exportado.

**Out of scope:** catálogo nativo de Meta Commerce Manager / carrusel nativo; Instagram/Messenger; cupones/descuentos; deploy a producción.

## Modelo de datos

Sin estructuras nuevas. Nueva clave en el JSON `chatbot.session.estado` → `carrito.pagina_catalogo` (int, offset de paginación del catálogo).

## Plan de implementación

1. **S1 — Diagnóstico:** logs de n8n y Odoo en staging para el caso "carrito"/"ver carrito"; identificar causa raíz antes de tocar código.
2. **S2 — Clasificador + catálogo:** acción `CATALOGO` (fallback determinista + IA), servicio de catálogo con paginación y descripción `description_sale`, formato con mini-guía persistente.
3. **S3 — Controlador:** `procesar` maneja `CATALOGO`; `CONSULTAR` con carrito vacío redirige al catálogo; respuesta marca `extra['botones']` para el envío interactivo.
4. **S4 — n8n:** `Unificar_salida_carrito` envía interactive buttons con fallback a texto plano; export del workflow.
5. **S5 — Tests:** catálogo, paginación, descripción vacía, guía presente, clasificación, consulta vacía → catálogo; suites `chatbot_cart` + `ai_chatbot_1_portal` en verde.
6. **S6 — E2E WhatsApp staging:** hola → anuncio; "catálogo" → tarjetas; número → agrega; "ver carrito" → resumen; "pagar" → orden. Bump + commit.

## Criterios de aceptación

- [ ] "carrito" o "ver carrito" NUNCA responden el mensaje genérico de valor vacío (causa raíz corregida, verificado en staging).
- [ ] "catálogo"/"qué tienen" muestra 5 productos con imagen, precio y descripción; "más" pagina al siguiente grupo.
- [ ] Todo mensaje del carrito termina con la mini-guía de opciones.
- [ ] `CONSULTAR` con carrito vacío muestra el catálogo (no solo "está vacío").
- [ ] Descripción vacía no rompe el formato de la tarjeta.
- [ ] Botones interactivos enviados cuando la respuesta los marca; si fallan, el usuario recibe texto plano.
- [ ] Suites `chatbot_cart` y `ai_chatbot_1_portal` en verde.
- [ ] Funciona igual para cualquier cliente del bot (sin datos de negocio hardcodeados).

## Decisiones tomadas y descartadas

- **Tomado:** imagen+caption por producto + botones interactivos Cloud API; **descartado** el catálogo nativo de Meta Commerce Manager (requiere sync de inventario a Facebook, refresh 14-24h, dependencia nueva y pesada para una base de negocios heterogénea).
- **Tomado:** fix del routing DENTRO de esta spec (es la causa real del bloqueo del usuario, no un detalle aparte).
- **Tomado:** comando catálogo universal con paginación; **descartado** carrusel iterativo completo (se va por fases, respetando el patrón de SPEC 27 fase 2).
- **Tomado:** universal, sin hardcodear datos de Karla ni de ningún negocio.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Causa raíz del routing no esté en n8n (p.ej. activación del flujo) | Diagnóstico S1 antes de cualquier fix; ajustar según hallazgo |
| Interactive buttons no soportados por alguna plataforma o cliente | Fallback a texto plano garantizado en el envío |
| Demasiados mensajes de imagen por catálogo (5) | Límite 5 + solo productos con imagen en el envío interactivo |
