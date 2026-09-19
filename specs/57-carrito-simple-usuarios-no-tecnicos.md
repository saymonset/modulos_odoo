# SPEC 57 — Carrito simple para usuarios no técnicos

> **Estado:** Approved
> **Depende de:** SPEC 54 (➕/➖), SPEC 55 (catálogo visual), SPEC 56 (botón Pagar)
> **Fecha:** 2026-09-17
> **Objetivo:** Que el carrito sea usable por un usuario no técnico: un comando que funcione, sin texto duplicado, sin IA que modifique las respuestas, y un resumen limpio tipo "lista" en vez de imágenes con captions repetidos.

## Por qué existe esta spec

En vivo (17/9) se detectaron 5 problemas que hacen el carrito inusable para usuarios no técnicos:

1. **"del 5 solo 4" → agrega 5 unidades en vez de cambiar a 4.** El clasificador detecta "quiero" (en `_PALABRAS_AGREGAR`) y clasifica como AGREGAR con `cantidad = 5` (primer número en el texto). El usuario quería MODIFICAR producto #5 a 4 unidades.
2. **Texto duplicado en imágenes:** cada caption de imagen incluye " Tu carrito: N unid. en M producto(s) — $X" — si se muestran 5 imágenes, el total aparece **5 veces**.
3. **IA agrega texto innecesario:** `_redactar()` pone "¡Hola! 😊 He agregado... Aquí tienes un resumen" — el usuario solo quiere ver "✅ 4 unid. de X agregado. Total: $Y. 💳 Pagar".
4. **Imágenes no se envían:** `ycloud_carrito_subflow.json` no tiene nodos para enviar media messages — las imágenes existen en el JSON de Odoo pero nunca llegan a WhatsApp.
5. **Sin lista interactiva para el carrito:** WhatsApp List Messages existen en el flujo (para categorías) pero no se usan para mostrar el carrito. Una lista es más legible que texto libre.

WhatsApp tiene límites reales: no permite imágenes inline en listas ni botones por producto. Pero una **lista interactiva limpia** + **comandos que funcionen** + **respuestas directas** es lo más cercano a la imagen de referencia que funciona en chat.

## Scope

**In:**

1. **Fix clasificador "del N solo X" / "quiero del N solo X" → MODIFICAR cantidad a X.** Regex nuevo + prioridad antes de AGREGAR.
2. **Quitar línea duplicada de total en captions de imágenes:** eliminar el `if items_carrito:` que agrega "🛒 Tu carrito: N unid..." a **cada** imagen. Dejar solo "en tu carrito: N unid." por producto.
3. **Sin IA para respuestas del carrito (AGREGAR/QUITAR/MODIFICAR/CONSULTAR/PAGAR):** `_ejecutar_item` y `_ejecutar` (CONSULTAR, PAGAR) usan **texto determinista directo** sin `_redactar`. Solo el prompt del vendedor IA usa redacción; las operaciones del carrito son mecánicas.
4. **WhatsApp List Message para el carrito (CONSULTAR):** en vez de texto + imágenes con captions, usar un interactive list con filas `Nombre — Qty — Subtotal` (máx. 10 filas por sección). Botón "💳 Pagar" como quick reply debajo.
5. **Respuesta de AGREGAR minimalista:** "✅ *N unid. de [nombre]* agregado.\nTotal: $Y. 💳 Pagar o sigue buscando." Sin saludo, sin redacción IA.
6. **Botones post-AGREGAR:** `['➕ Sumar', '➖ Quitar', '💳 Pagar']` (ya implementado en SPEC 56).

**Out of scope:**

- Imágenes de producto en el carrito (WhatsApp List Messages no admiten imágenes por fila; las imágenes se muestran solo en catálogo/búsqueda).
- Botones ➕/➖ inline por fila (WhatsApp limita a 3 quick replies por mensaje; ya cubierto por SPEC 54 con `N ➕` / `N ➖`).
- Carrito web embebido (requiere iframe o redirección; otra spec).
- Telegram integration (otra spec).

## Modelo de datos

Sin modelos nuevos. Cambios de contrato:

```python
# CONSULTAR (ver carrito) — ahora usa lista interactiva en vez de texto:
extra = {
    'botones': ['➕ Sumar', '➖ Quitar', '💳 Pagar'],
    'lista_carrito': {                          # NUEVO (reemplaza texto para WhatsApp)
        'button': 'Ver carrito',
        'sections': [{
            'title': 'Tu carrito',
            'rows': [
                {'id': 'modificar_1', 'title': 'Camisa Roja — 2 unid.', 'description': '$13.00'},
                {'id': 'modificar_2', 'title': 'Pantalón — 1 unid.', 'description': '$25.00'},
            ]
        }]
    },
}

# AGREGAR respuesta — texto determinista directo:
texto = "✅ *2 unid. de Camisa Roja* agregado.\nTotal: $38.00. 💳 Pagar o sigue buscando."
```

## Plan de implementación

1. **Classifier fix (`clasificar_accion_carrito_use_case.py`):**
   - Nueva regex `_RE_MODIFICAR_SOLO`: `r'del\s+(\d{1,2})\s+solo\s+(\d{1,3})'` y `r'quiero\s+del\s+(\d{1,2})\s+solo\s+(\d{1,3})'`
   - Evaluar antes del fallback AGREGAR (prioridad sobre "quiero").
   - Si match → MODIFICAR con producto=grupo1, cantidad=grupo2.

2. **Caption fix (`chatbot_cart_controller.py` `_imagenes_de_productos`):**
   - Eliminar el `if items_carrito:` que agrega el total del carrito a cada caption.
   - Dejar solo "🛒 en tu carrito: N unid." por producto individual.

3. **Sin IA para operaciones del carrito (`chatbot_cart_controller.py`):**
   - `_ejecutar_item` (AGREGAR/QUITAR/MODIFICAR): usar `self._texto_operacion()` en vez de `self._redactar()`.
   - `_ejecutar` (CONSULTAR, PAGAR): mismo tratamiento — texto determinista directo.
   - Mantener `_redactar` solo para el prompt del vendedor IA y mensajes de bienvenida.

4. **WhatsApp List Message para carrito (`chatbot_cart_controller.py`):**
   - Nuevo método `_lista_interactiva_carrito(resumen)` → construye `lista_categorias`-style dict con `sections[0].rows`.
   - CONSULTAR con items: en vez de `texto + imagenes`, devolver `texto` mínimo + `lista_carrito` en `extra`.
   - El n8n `Unificar_salida_carrito` ya maneja `lista_categorias` → reutilizar la misma ruta.
   - Máx. 10 filas (si >10, paginar con "más").

5. **Respuesta AGREGAR minimalista:**
   - Nuevo método `_texto_agregar(producto, cantidad, resumen)` → string determinista.
   - Reemplaza el bloque AGREGAR en `_ejecutar_item`.

6. **Tests:**
   - `test_01_del_N_solo_X`: clasifica MODIFICAR.
   - `test_02_quiero_del_N_solo_X`: clasifica MODIFICAR.
   - `test_03_sin_duplicado_en_captions`: caption no tiene "🛒 Tu carrito: N unid.".
   - `test_04_sin_ia_en_agregar`: texto AGREGAR no tiene saludo IA.
   - `test_05_lista_interactiva_carrito`: CONSULTAR con items devuelve `lista_carrito`.
   - `test_06_respuesta_minimalista`: AGREGAR devuelve texto corto sin redacción.
   - Regresión suite `chatbot_cart`.

7. **Bump versión** `19.0.1.15.0` + upgrade en lead + E2E WhatsApp.

## Criterios de aceptación

- [ ] "del 5 solo 4" → MODIFICAR producto #5 a 4 unidades (no AGREGAR 5).
- [ ] "quiero del 5 solo 4" → MODIFICAR producto #5 a 4 unidades.
- [ ] Caption de imágenes: sin línea "🛒 Tu carrito: N unid. en M producto(s) — $X" duplicada.
- [ ] Respuesta AGREGAR: sin "¡Hola! 😊", sin "He agregado... Aquí tienes un resumen". Solo "✅ X unid. de Y agregado. Total: $Z."
- [ ] CONSULTAR con items: devuelve WhatsApp List Message con filas `Nombre — Qty — Subtotal`.
- [ ] Botones post-CONSULTAR: `['➕ Sumar', '➖ Quitar', '💳 Pagar']`.
- [ ] Lista del carrito ≤ 10 filas (paginación "más" si >10).
- [ ] Suite `chatbot_cart` en verde + bump `19.0.1.15.0`.

## Decisiones tomadas y descartadas

- **Tomado:** clasificador con regex `_RE_MODIFICAR_SOLO` con prioridad sobre AGREGAR — **descartado** fuzzy matching (confunde más).
- **Tomado:** sin IA para respuestas mecánicas del carrito — **descartado** `_redactar` con instrucciones "sin saludo" (el modelo IA es impredecible; determinista > IA para operaciones).
- **Tomado:** WhatsApp List Message para carrito — **descartado** enviar imágenes del carrito (WhatsApp no permite imágenes inline en lists; las imágenes van solo en catálogo/búsqueda).
- **Tomado:** caption sin total duplicado — **descartado** mantener total en cada imagen (5 veces = confusión visual).
- **Tomado:** respuesta AGREGAR minimalista — **descartado** redacción IA con template fijo (el modelo agrega texto fuera del template).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| List Message de carrito sin imágenes (el usuario ve nombre pero no foto) | Las imágenes ya se muestran en catálogo/búsqueda (antes de agregar). El carrito solo confirma qty + precio. |
| WhatsApp List Messages requieren que el usuario toque la fila para interactuar | La fila envía "modificar_N" que se clasifica como MODIFICAR → abre flujo de cambio de cantidad. Alternativa: el usuario escribe "5 ➖" directamente. |
| IA del vendedor sigue redactando si se activa | El vendedor IA solo se activa en fallback del clasificador. Las acciones directas (AGREGAR/QUITAR/MODIFICAR/CONSULTAR/PAGAR) pasan por el clasificador determinista y nunca entran al vendedor. |
| n8n `Unificar_salida_carrito` debe soportar `lista_carrito` igual que `lista_categorias` | Reutilizar la misma lógica (ya existe para categorías). Solo cambia el nombre de la key en el JSON. |

## What is **not** in this spec

- Imágenes en el carrito (WhatsApp List Messages no las soporta; otra spec si se quiere carrito web).
- Botones ➕/➖ inline por producto (ya cubierto por SPEC 54 con texto `N ➕` / `N ➖`).
- Telegram integration (otra spec).
- Carrito web embebido (otra spec).

Cada uno de esos, si llega, va en su propia spec.
