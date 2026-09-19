# SPEC 54 — Carrito ➕/➖ con estado y quitar por número (experiencia para todos)

> **Status:** Implemented
> **Depends on:** SPEC 45 (botones), SPEC 50 (vendedor IA), SPEC 52 (selección numérica), SPEC 53 (captura guiada)
> **Date:** 2026-09-16
> **Objective:** Que agregar, modificar y eliminar sea responder número + signo desde la foto (`1 ➕`, `1 ➖`) o con botones ➕/➖ sobre el producto seleccionado, mostrando en cada imagen cuántas unidades ya lleva y respetando el inventario al sumar.

## Por qué existe esta spec

El E2E real mostró: "quitar 1" falla cuando ya no hay catálogo ("Ese producto no está en tu carrito" — el resolver solo mira la última búsqueda), y para un usuario poco letrado es difícil escribir "quitar Aros de Hamburguesa" o "cambiar X a 3". La prioridad del proyecto es buena experiencia para el usuario analfabeta digital: el estado se ve en la imagen y la acción es un número + signo.

## Scope

**In:**

1. **Fix `quitar N` / `cambiar N a M`**: si la última lista no existe o N no está en ella, el índice N resuelve contra el **índice del carrito** (`items[N-1]`).
2. **Caption de imágenes con estado del carrito**: cada imagen de catálogo/búsqueda añade la línea `🛒 en tu carrito: N` (o `(no está en tu carrito)`); el pie del mensaje explica la regla: "responde `1 ➕` para sumar, `1 ➖` para restar".
3. **Parse número + signo**: `N ➕` / `➕ N` / `suma N` → MAS sobre el índice N del listado mostrado; `N ➖` / `➖ N` → MENOS (y 0 elimina). Sin índice (`➕`, `➖`, `mas`, `menos`) → operan sobre el **producto seleccionado** (el último agregado/citado/modificado); sin selección → pide índice mostrando el listado del carrito.
4. **Botones post-carrito**: con items → `[➕ Sumar, ➖ Quitar, pagar]` (el listado textual lleva la pista `N ➕ / N ➖`); `➕ Sumar`/`➖ Quitar` por botón = MAS/MENOS del seleccionado.
5. **Inventario al sumar**: solo productos `type == 'product'` se limitan con `free_qty`; si se excede no incrementa y responde "solo quedan X de Y — te dejo en X"; `consu`/servicio sin límite.
6. **➖ hasta 0 elimina**: mensaje amistoso ("quité el producto; tu carrito quedó…") y estado de carrito actualizado (vacío → catálogo).
7. **IA**: redacción SPEC 50 con listados intangibles; el parse ➕/➖ es determinista (la IA nunca ejecuta).
8. **Tests + E2E lead**: quitar-índice-carrito, MAS/MENOS con y sin índice, cap de inventario, ➖→0 elimina, botones, regresión SPEC 52 (`del 2 quiero 5`).

**Out of scope (para futuras specs):**

- Mensajes tipo lista de WhatsApp (list_reply, hasta 10 filas) con filas `➕ producto` — alternativa cuando varios productos hagan incómodos los 3 botones.
- n8n y exports (los botones salen del array `botones` que ya viaja, SPEC 45).
- Validación del picking de entrega (política estándar Odoo; hoy el pago confirma la sale.order y reserva stock).

## Data model

Sin modelos nuevos. Cambios de contrato en el JSON del carrito (`chatbot.session`):

```python
carrito['producto_seleccionado'] = product_id   # último agregado/citado/modificado
# parse MAS/MENOS en el clasificador determinista:
# 'N ➕' -> ('MAS', N); '➖' -> ('MENOS', None)
```

## Implementation plan

1. `_resolver_producto`: fallback QUITAR/MODIFICAR → índice del carrito. Manual en lead: `quitar 1` tras ver carrito sin catálogo resuelve el item 1.
2. Acciones `MAS`/`MENOS` en el clasificador determinista + `_ejecutar`: incrementar/decrementar con cap `free_qty` (`type=='product'`), MENOS a 0 elimina con aviso. Manual: `2 ➕`, `1 ➖`.
3. Estado `producto_seleccionado` en cada acción de carrito; botones `[➕ Sumar, ➖ Quitar, pagar]` post-carrito; hint textual `N ➕ / N ➖`.
4. Caption de imágenes: línea de estado del carrito + regla `N ➕ / N ➖` según el índice mostrado.
5. AYUDA y prompt vendedor: regla ➕/➖ (determinista; la IA solo redacta, listados intangibles).
6. Tests (índice de carrito, MAS/MENOS ±índice, cap, selección, botones) + suite + E2E lead de los 6 casos.

## Criterios de aceptación

- [x] `quitar 1` con "ver carrito" y sin catálogo previo quita el item 1 del carrito.
- [x] Cada imagen de catálogo/búsqueda muestra `🛒 en tu carrito: N` o `(no está en tu carrito)`.
- [x] `1 ➕` suma 1 del producto 1 del listado; `1 ➖` resta 1; a 0 lo elimina con aviso.
- [x] `➕`/`➖` sin índice operan sobre el producto seleccionado; sin selección piden índice con listado del carrito.
- [x] Con `type=='product'` sin stock libre no incrementa; dice "solo quedan X de Y" y respeta el cap.
- [x] `consu`/servicio no tienen cap al sumar.
- [x] Botones post-carrito: `[➕ Sumar, ➖ Quitar, pagar]` funcionan por palabra/botón.
- [x] `1, quiero 3` y `del 2 quiero 5` siguen directo (SPEC 52) y "quiero un 4" sigue preguntando (SPEC 53).
- [x] Suite `chatbot_cart` en verde (salvo los 2 FAIL preexistentes `test_recibo_pago`) + E2E lead de los 6 casos.

## Fixes tras el E2E real (misma spec, 2026-09-16)

El E2E WhatsApp mostró comportamiento extraño al tocar los botones ➕/➖:

1. **n8n extractor** (`Obtener_Info_basica`, workflow `ycloud_create_lead_0_con_menu_whatsapp`): la cadena de extracción tenía `text.body` primero y al tocar un botón el gateway devuelve el echo del cuerpo anterior — el bot recibía basura (saludo + etiqueta). Reordenado: `interactive.button_reply/list_reply` primero, luego captions, `text.body` al final. Aplicado al export `n8n_json/ycloud/` (rama `lead` del skeleton) y al workflow live (bd n8n + restart).
2. **Robustez del controller**: `_decision_mas_menos` ahora evalúa solo la ÚLTIMA línea (y cola de 24 chars con signo) para tolerar ecos residuales; los hints del propio bot ("Responde *1 ➕*…") no activan nada; `_ajustar_cantidad` usa el **único producto del carrito** como seleccionado cuando no hay selección.
3. Tests: parse de eco (`eco + etiqueta`),guards contra hints; suite en verde; E2E HTTP lead con eco simulado en verde.

## Decisiones tomadas y descartadas

- **Tomado:** botones ➕/➖ sobre el producto seleccionado (decisión del usuario).
- **Tomado:** cap de inventario solo en `type=='product'` con `free_qty` (decisión del usuario).
- **Tomado:** ➖ a 0 elimina con aviso amable (decisión del usuario).
- **Tomado:** estado del carrito visible en el caption de cada imagen (decisión del usuario).
- **Descartado:** botones ➕/➖ nativos por producto dentro de la imagen (WhatsApp limita a 3 quick replies por mensaje).
- **Descartado:** mensajes list_reply por producto (opción futura si el trío de botones se siente incómodo).
- **Descartado:** tocar la lógica de pago/inventario (hoy ya confirma sale.order y reserva stock con picking).

## What is **not** in this spec

- Cambios al n8n/exports (SPEC 43).
- Paginación/list_reply, pago, ecommerce web, validación de picking.

Cada uno de esos, si llega, va en su propia spec.
