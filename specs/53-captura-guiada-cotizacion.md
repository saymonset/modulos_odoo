# SPEC 53 — Captura guiada de datos y pedidos sin errores en el carrito

> **Status:** Approved
> **Depends on:** SPEC 47 (cotización IA), SPEC 50 (vendedor IA), SPEC 52 (selección numérica + cantidad)
> **Date:** 2026-09-16
> **Objective:** Que la cotización anuncie "te pediré unos datos, empezamos por el teléfono" y los pida uno por mensaje, que los números ambiguos se confirmen antes de agregar, y que tras cada AGREGAR se vea el carrito con acciones quitar/modificar.

## Por qué existe esta spec

El E2E WhatsApp real mostró tres fallos de conversación: al pedir la cotización el anuncio de datos y el pedido "correo y nombre" iban juntos en un mismo turno (confunde al usuario, que ya no sabe qué responder); frases ambiguas como "quiero un 4" agregan unidades sin confirmar (¿4 del producto 1 o 1 del producto 4?); y tras agregar no se ve lo que se llevas ni se descubre quitar/modificar. Todo el motor existe; la spec ajusta el diálogo.

## Scope

**In:**

1. **Anuncio de datos de cotización** (`_pedir_email_cotizacion`): el primer mensaje dice que se pedirán unos datos y empezamos por el teléfono; cada turno pide **un solo dato**.
2. **Cliente nuevo paso a paso** (`_cotizacion_turno_telefono`): teléfono no registrado → "se creará tu ficha, ¿cuál es tu **nombre**?" ; luego **solo correo**. Partner existente → "¿eres {nombre}?" (sí → crear cotización; no → sigue como cliente nuevo).
3. **Confirmación de números ambiguos**: frase no explícita ("quiero un 4", "un X", cantidades en palabras) → **nada se agrega**: el bot responde con lo que entendió + las 2 interpretaciones (4 unidades de X / 1 unidad del producto 4) o pide reescribir claro. Explícito ("1, quiero 3", "del 2 quiero 5", `N` solo) sigue directo (SPEC 52).
4. **Respuestas no explícitas**: el vendedor IA (SPEC 50) nunca ejecuta nada no confirmado — reformula lo que entendió y pide confirmación o redacción clara.
5. **Menú post-agregar**: tras cada AGREGAR con items, lista compacta del carrito (nombre × cant, total Bs./$) + acciones `quitar N / cambiar N / ver carrito / pagar / 🚫 vaciar`.

**Out of scope (para futuras specs):**

- n8n y exports (SPEC 43).
- Endpoints de `chatbot_cotizacion` (se consumen sin modificar).
- Catálogo paginado (SPEC 40) ni pago/recibo (SPEC 41).

## Data model

Sin modelos nuevos. Cambios de contrato en el JSON del carrito (`chatbot_cart`, sesión `chatbot.session`):

```python
# pendiente_cotizacion['paso']: pasos existentes telefono/email/nombre
# más un paso nuevo tras el match de partner:
estado = {'paso': 'confirmar_partner', 'telefono': ..., 'partner_id': N}

# intención de alta que espera confirmación antes de ejecutar:
pendiente_confirmar = {
    'opciones': [('1', 'AGREGAR', producto_id, 4),   # 4 unidades de X
                 ('2', 'AGREGAR', producto_id_otro, 1)],  # 1 unidad del producto 4
    'pregunta': 'texto mostrado al usuario',
}
```

## Implementation plan

1. `chatbot_cart/controllers/chatbot_cart_controller.py`: anuncio de datos en `_pedir_email_cotizacion` + cliente nuevo paso a paso (nombre → correo) + paso `confirmar_partner` con "¿eres {nombre}?" y rama "no eres tú" re-pidiendo los datos. Manual: mensajes de cotización en lead.
2. `_decision_seleccion_numerica`: nueva rama `AMBIGUO` para frases no explícitas; handler de `pendiente_confirmar` (sí/"1" ejecuta la opción, "2"/otro responde la segunda o pide reescritura, 🚫 Cancelar limpia). Manual: "quiero un 4" pregunta antes de agregar.
3. `chatbot_cart/services/prompt_carrito.py`: regla del vendedor — frase no explícita = reformular lo que entendió y pedir confirmación; nunca agregar sin confirmación.
4. Post-agregar: lista compacta del carrito + acciones quitar/cambiar/ver/pagar (redactada por IA de SPEC 50 con fallback a plantilla).
5. Tests: rama AMBIGUO + `pendiente_confirmar`, `confirmar_partner`, flujo cliente nuevo nombre→correo, anuncio de datos, menú post-agregar. Suite + E2E lead de los 5 casos.

## Acceptance criteria

- [x] `cotización` con carrito no vacío: el primer mensaje anuncia que se pedirán unos datos y pide solo el teléfono.
- [x] Teléfono no registrado: el siguiente turno pide **solo nombre**; el siguiente **solo correo**; nunca ambos juntos.
- [x] Teléfono registrado → Confirmar. ¿Eres {nombre}? → "Sí" crea la cotización; "No" pide los datos como cliente nuevo.
- [x] "Quiero un 4" no agrega nada: responde lo que entendió + opciones; sí/"1" agrega.
- [x] "1, quiero 3" sigue agregando 3 directo (SPEC 52 sin regresión).
- [x] Después de cada AGREGAR se puede ver la lista del carrito con total y acciones quitar/cambiar/ver/pagar.
- [x] Respuesta IA no explícita nunca ejecuta acciones sin confirmación.
- [x] Suite `chatbot_cart` en verde + E2E lead de los 5 casos.

## Decisiones tomadas y descartadas

- **Tomado:** un dato por turno, orden teléfono → nombre → correo (decisión del usuario).
- **Tomado:** confirmar el partner registrado con "¿eres {nombre}?" (decisión del usuario).
- **Tomado:** confirmación obligatoria ante ambigüedad (decisión del usuario).
- **Tomado:** mostrar el carrito compacto tras cada AGREGAR (decisión del usuario).
- **Descartado:** pedir teléfono+nombre+correo en un mismo mensaje (causa del fallo del transcript).
- **Descartado:** cambios a endpoints de `chatbot_cotizacion` (la spec los solo consume).

## What is **not** in this spec

- n8n/exports (SPEC 43).
- Catálogo paginado, pago/recibo, ecommerce web.

Cada uno de esos, si llega, va en su propia spec.
