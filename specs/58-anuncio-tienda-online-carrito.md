# SPEC 58 — Anuncio de compra por enlace a la tienda online en vez de "Escribe carrito"

> **Estado:** Approved
> **Depende de:** SPEC 46 (enlace tienda online), SPEC 32 (anuncio determinista n8n)
> **Fecha:** 2026-09-17
> **Objetivo:** Que el anuncio de compra de las respuestas generales del bot deje de invitar a escribir «carrito» y muestre el enlace público de la tienda ecommerce de Odoo cuando exista, sin anunciar nada cuando no hay tienda pública.

## Por qué existe esta spec

En vivo el mensaje de bienvenida y las respuestas generales terminan con `💡 Escribe «carrito» para ver nuestro catálogo y comprar por WhatsApp.`, invitando al usuario a entrar al flujo del carrito. El flujo tiene problemas de usabilidad y el negocio prefiere llevar al usuario a la tienda ecommerce pública cuando existe. El anuncio actual es un texto fijo en dos lugares: la instrucción al LLM (`prompt_carrito.py:8`) y el fallback determinista de n8n (`Unificar_salida`, SPEC 32). La línea de tienda de SPEC 46 (`_linea_tienda`) ya resuelve la URL pública por negocio; esta spec la convierte en el anuncio único, reemplazando la invitación a escribir «carrito».

El disparo por la palabra «carrito» **no cambia**: si un usuario escribe «carrito», sigue entrando al flujo. Solo se deja de anunciar/incitar.

## Scope

**In:**

1. **Nuevo anuncio en `prompt_carrito.py`:** el anuncio de las respuestas normales pasa a ser la línea de tienda de SPEC 46 (`_linea_tienda(env)` → `❗ Visita nuestra tienda online: <url>`). Sin tienda pública → sin línea de anuncio. Se elimina la constante `_ANUNCIO_CARRITO` y el texto `Escribe «carrito»...`.
2. **Template condicional:** la frase "En cualquier otra respuesta normal, termina SIEMPRE con esta línea exacta:" solo se incluye cuando hay anuncio (con URL). Sin URL, el bloque no lleva instrucción de cierre. Se retira la colocación duplicada de `linea_tienda` al final del bloque (el anuncio ya la contiene).
3. **n8n `Unificar_salida` (`ycloud_create_lead_0_con_menu_whatsapp.json`):** el fallback determinista extrae la línea de tienda del `system_prompt` (regex sobre `❗ Visita nuestra tienda online: <url>`) y la anexa a la salida si el carrito está activo, la salida no la contiene y no hay activación de flujo ni menú. Sin línea de tienda en el prompt → no anexa nada (ni «Escribe carrito» ni enlace).
4. **Tests actualizados:** `test_prompt_carrito.py` (sin `_ANUNCIO_CARRITO`; anuncio = línea de tienda con URL / ausente sin URL) y `test_enlace_tienda.py` (ajustar si aplica).
5. **Bump `chatbot_cart` → `19.0.1.17.0`**, export n8n en `n8n_json/ycloud/` (rama `lead` de `odoo19-skeleton`, SPEC 43), upgrade en lead + E2E WhatsApp.

**Out of scope (para futuras specs):**

- Desactivar el flujo o el disparo del carrito (el trigger «carrito» sigue activo).
- Fixes de usabilidad del flujo del carrito (SPEC 54–57 y siguientes).
- Flag de configuración por negocio para elegir anuncio (la URL resuelta ya es per-negocio).
- Cambios al catálogo/buscador (ya usan `obtener_url_tienda_enlace`, SPEC 46 intacto).

## Modelo de datos

Sin modelos ni campos nuevos. Cambios de contrato en el bloque del prompt y en el nodo n8n:

```python
# Antes: anuncio fijo, siempre presente.
_ANUNCIO_CARRITO = '💡 Escribe «carrito» para ver nuestro catálogo y comprar por WhatsApp.'

# Después: anuncio = línea de tienda de SPEC 46, o '' si no hay tienda pública.
anuncio = _linea_tienda(env)  # '❗ Visita nuestra tienda online: <url>' | ''
```

```js
// n8n Unificar_salida: extrae el anuncio del system_prompt, no lo hardcodea.
const match = sistema.match(/❗ Visita nuestra tienda online: \S+/);
const anuncio = match ? '\n' + match[0] : '';
```

## Plan de implementación

1. **`prompt_carrito.py`:** refactor de `_render_instrucciones(anuncio='')` — el parámetro recibe `_linea_tienda(env)` o `''`. La sección "En cualquier otra respuesta normal, termina SIEMPRE con esta línea exacta:\n{anuncio}" se incluye solo si `anuncio` no es vacío. Eliminar `_ANUNCIO_CARRITO` y la `{linea_tienda}` del final del bloque. `render_instrucciones_carrito(env)` → `_render_instrucciones(_linea_tienda(env))`.
2. **Tests:** actualizar `test_prompt_carrito.py` (quitar imports/asserts de `_ANUNCIO_CARRITO`; test nuevo: con URL el bloque incluye `❗ Visita nuestra tienda online: <url>`; sin URL no incluye anuncio ni la frase de cierre) y `test_enlace_tienda.py` (verificar que el anuncio condicional reemplaza la línea de tienda del final). Suite `chatbot_cart` en verde.
3. **n8n:** backup del workflow → editar el nodo `Unificar_salida` de `ycloud_create_lead_0_con_menu_whatsapp.json` → importar/activar en la instancia n8n → verificar el nodo.
4. **Bump `19.0.1.17.0`** + upgrade en lead.
5. **E2E WhatsApp:** welcome sin "Escribe «carrito»"; con tienda pública (INTEGRAIA → `https://integraia.lat/shop`) termina con la línea de tienda; escribir "carrito" sigue entrando al flujo.

## Criterios de aceptación

- [ ] `_ANUNCIO_CARRITO` eliminado; ninguna respuesta general contiene "Escribe «carrito»".
- [ ] Con tienda pública (URL resuelta por `obtener_url_tienda_enlace`): el bloque instruye terminar las respuestas con `❗ Visita nuestra tienda online: <url>`.
- [ ] Sin tienda pública: el bloque no contiene línea de anuncio ni la frase "termina SIEMPRE con esta línea exacta".
- [ ] n8n `Unificar_salida`: sin línea de tienda en el `system_prompt` → no anexa nada; con línea y salida que no la incluye → la anexa.
- [ ] Escribir "carrito" sigue activando `flujo_carrito_compra` (sin cambios en el disparo).
- [ ] Suites `chatbot_cart` en verde + bump `19.0.1.17.0` + export n8n commiteado en rama `lead` de `odoo19-skeleton`.

## Decisiones tomadas y descartadas

- **Tomado:** el anuncio es el enlace de tienda de SPEC 46 cuando la URL se resuelve; sin URL no hay anuncio — **descartado** mantener "Escribe «carrito»" como fallback (el usuario quiere eliminar esa invitación).
- **Tomado:** cambio global basado en datos (cada negocio muestra su enlace si tiene tienda pública) — **descartado** flag de configuración por negocio (redundante: la URL resuelta ya es per-negocio).
- **Tomado:** el disparo «carrito» sigue activo — **descartado** desactivar el carrito por completo (el usuario solo pidió no anunciarlo).
- **Tomado:** n8n extrae el anuncio del `system_prompt` en vez de hardcodear — **descartado** texto fijo nuevo en n8n (una sola fuente: el prompt, que genera Odoo).
- **Tomado:** la línea de tienda vive solo en el anuncio (se retira `linea_tienda` del final del bloque) — **descartado** duplicarla en la frase de activación (el anuncio ya la cubre).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Negocios con carrito activo y sin tienda pública pierden el anuncio de descubrimiento del carrito | Aceptado por decisión del usuario; el trigger «carrito» sigue funcionando para quien lo conoce |
| `web.base.url` puede apuntar a una URL interna/no pública en algunos deploys → enlace incorrecto | Override `chatbot_cart.tienda_url` (SPEC 46) corrige sin tocar código |
| El LLM puede no respetar el anuncio | El fallback determinista de n8n lo garantiza con el mismo texto extraído del prompt |
| `Unificar_salida` anexa el enlace en salidas donde ya aparece el carrito activo | La condición "sin activación de flujo ni menú" se mantiene (SPEC 32) |

## What is **not** in this spec

- Desactivar el flujo o el disparo del carrito.
- Fixes de usabilidad del flujo del carrito.
- Flag de configuración por negocio para el anuncio.
- Cambios al catálogo/buscador (SPEC 46 intacto).

Cada uno de esos, si llega, va en su propia spec.