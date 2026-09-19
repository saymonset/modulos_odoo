# SPEC 30 — Botón "Activar carrito" en la ficha del cliente

> **Status:** Implemented
> **Depends on:** SPEC 29 (flujo_carrito_compra inactivo por defecto, exclusión de auto-detección)
> **Date:** 2026-09-12
> **Objective:** Activar o desactivar el carrito de compra con un clic desde la ficha del cliente, con el mismo gate del sistema (productos vendibles con precio), sin depender del filtro "Archivados".

## Por qué existe esta spec

Tras SPEC 29, el flujo `flujo_carrito_compra` nace inactivo y la sync nunca lo enciende. El usuario descubrió que activarlo a mano requiere conocer el filtro "Archivados" (no aparece ni el nombre). Este botón hace la activación/desactivación obvia y segura desde la ficha de la `chatbot.config` del cliente.

## Scope

**In:**

- **Método `action_activar_carrito` en `chatbot.config` (definido en `chatbot_cart`)** — sin dependencia inversa:
  - Si `flujo_carrito_compra` está inactivo:
    1. Gate `CartService.disponible(env)` (∃ `product.template` con `sale_ok=True` y `list_price>0`); si falla → notificación *"Carrito omitido: el negocio no tiene productos vendibles con precio"* y aborta (no activa).
    2. Si el flujo no existe (módulo instalado pero flujo borrado a mano) → lo crea con los mismos valores de la data (sin pasos, `politica_inicio=confirmation`).
    3. Desarchiva y activa el flujo (`active=True`); el write de `active` dispara la cascada existente de `chatbot.flujo.write` hacia mappings.
    4. Lo agrega a `config.flujo_ids` (marca manual que el sync preserva, SPEC 29/Opción A).
    5. Notificación de éxito.
  - Si está activo: lo desactiva (`active=False`), lo desmarca de `flujo_ids` y notifica.
- **Botón dinámico en la vista de config** (`views/chatbot_config_views.xml` heredada desde `chatbot_cart`), junto a "Flujos de este cliente":
  - Etiqueta dinámica: `Activar carrito` / `Desactivar carrito` según estado del flujo (campo computed `carrito_compra_activo`).
  - Sin tocar la vista de lista ni la ficha del flujo.
- Gate de prompt y exclusiones de SPEC 29 se quedan intactos (el gate del botón es el mismo criterio).
- Bump `chatbot_cart` → `19.0.1.3.0` + tests deterministas.

**Out of scope (para futuras specs):**

- Botón en lote en la lista de configs.
- Confirmación de seguridad intermedia (el toggle con gate basta).
- Deploy a producción.

## Data model

Sin campos persistentes nuevos. Un campo computed no-almacenado:

```python
# chatbot.config (extensión en chatbot_cart)
carrito_compra_activo = fields.Boolean(compute='_compute_carrito_compra_activo')
# → bool(flujo_carrito_compra.active) si el flujo existe; False si no
```

## Implementation plan

1. `chatbot_cart/models/chatbot_config.py`: extensión de `chatbot.config` con `carrito_compra_activo` (computed) y `action_activar_carrito` (toggle con gate, create-if-missing, marca en `flujo_ids`, notificaciones).
2. `chatbot_cart/views/chatbot_config_views.xml` (nuevo): herencia de `ai_chatbot_1_portal.view_chatbot_config_form` → botón dentro del grupo "Flujos de este cliente" con etiqueta dinámica según `carrito_compra_activo`.
3. Tests deterministas: toggle activa y marca/desmarca; gate sin productos aborta; flujo inexistente se recrea; computed correcto con/sin flujo.
4. Bump a `19.0.1.3.0` + suites en verde + reinicio contenedor.

## Acceptance criteria

- [ ] Con flujo inactivo y productos vendibles: "Activar carrito" → flujo activo, marcado en `flujo_ids`, notificación de éxito.
- [ ] Con flujo activo: botón muestra "Desactivar carrito" → al pulsar queda inactivo, fuera de `flujo_ids`, y la cascada de mappings lo refleja.
- [ ] Sin productos vendibles con precio: al pulsar no activa y muestra la advertencia con el motivo.
- [ ] Flujo borrado a mano: el botón lo recrea con `generar_pasos_automatico=False`, sin pasos y `politica_inicio=confirmation`.
- [ ] Tras activar por botón, un "Sincronizar todo desde RAG" NO lo desactiva (preservación SPEC 29) y el prompt del agente sí inyecta el bloque CARRITO.
- [ ] Tests deterministas en verde; versión `19.0.1.3.0`.

## Decisions

- **Sí:** botón en `chatbot_cart` (extensión de modelo + herencia de vista): la funcionalidad es del carrito, no del portal; evita dependencia `ai_chatbot → chatbot_cart`.
- **Sí:** toggle: un solo control para ambas direcciones, coherente con "la empresa decide".
- **Sí:** mismo gate que el prompt (`disponible(env)`): jamás se activa un carrito que no puede ofrecer nada.
- **Sí:** marcar en `flujo_ids` al activar: hace visible el flujo en el onboarding y garantiza que el sync lo preserve (SPEC 29/Opción A).

## Risks

| Riesgo | Mitigación |
|---|---|
| Herencia de vista frágil contra cambios de `ai_chatbot_1_portal` | xpath sobre el grupo "Flujos de este cliente" (estable por nombre de grupo) |
| Empresas con productos placeholder (precio≠0) activan el carrito "vacío" | El criterio de gate es el mismo del prompt; una spec futura puede endurecerlo (stock/imagen) |
| Doble fuente de verdad (botón vs "Flujos de este cliente") | El toggle SIEMPRE actualiza `flujo_ids` en ambas direcciones — la marca y el estado nunca divergen |

## What is **not** in this spec

- Acción en lote sobre varias configs.
- Otros controles del carrito en UI (formatos, textos).
- Cambios a n8n o al gate de prompt (SPEC 28/29 quedan intactas).