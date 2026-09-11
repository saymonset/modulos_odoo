# SPEC 29 — Flujo de carrito universal creado inactivo, activación manual

> **Status:** Implemented
> **Depends on:** SPEC 28 (fixes carrito + prueba WhatsApp)
> **Date:** 2026-09-11
> **Objective:** Que el flujo del carrito se cree siempre con el nombre `flujo_carrito_compra`, nacido **inactivo** y sin pasos; solo se activa manualmente si la empresa lo desea, y el prompt del agente solo lo menciona cuando el negocio tiene productos vendibles con precio y el flujo está activo.

## Por qué existe esta spec

Caso real (2026-09-11, bot Karla Campoverde): `flujo_carrito` existía activo por defecto pero fuera de la config del cliente, y el bot respondía consultas de producto con el RAG del negocio ("no ofrecemos pizzas"). Decisión del usuario: el carrito debe estar **siempre creado** (para que exista y se pueda activar fácil), pero **inactivo por defecto** — la empresa decide si lo enciende. Y con gate: sin productos o sin módulo, ni se dispara ni se inyecta en el prompt.

## Scope

**In:**

- **Renombre:** el flujo pasa a llamarse `flujo_carrito_compra` (data file, `prompt_carrito.py`, tests, n8n Switch y docs). El record XML existente `flujo_carrito` se renombra por migración.
- **Creado inactivo y sin pasos:** en `data/chatbot_flujo_carrito_data.xml`, el record nace con `active = False` y `generar_pasos_automatico = False`; la migración borra los 13 pasos genéricos existentes y desactiva el flujo ya creado.
- **Activación manual:** sin código nuevo — la empresa activa `flujo_carrito_compra` en "Flujos de este cliente" (mecanismo existente). Documentado en la guía.
- **Gate de prompt:** `configuracion_agente` inyecta el bloque `=== CARRITO DE COMPRAS ===` solo si `CartService.disponible(env)` (∃ `product.template` con `sale_ok=True` y `list_price > 0`) **y** `flujo_carrito_compra` está activo. Con el flujo inactivo o sin productos, el agente no lo menciona.
- **n8n:** el valor del Switch del carrito pasa de `flujo_carrito` a `flujo_carrito_compra` (solo el valor de comparación; URLs y tokens intactos).
- Bump de versión de `chatbot_cart` → `19.0.1.2.0` + tests deterministas actualizados.

**Out of scope (para futuras specs):**

- Auto-activación del carrito en la sync desde RAG (descartada: activación manual por empresa).
- Deploy a producción.
- Alta/baja automática del catálogo.
- Otros canales (Instagram/Messenger), carrusel o catálogo iterativo.

## Data model

Sin campos nuevos. Cambios de comportamiento sobre datos existentes:

```
chatbot.flujo:
  antes: flujo_carrito (active=True, 13 pasos genéricos)
  después: flujo_carrito_compra (active=False, paso_ids vacío, generar_pasos_automatico=False)
```

## Implementation plan

1. `CartService.disponible(env)` (gate) + `configuracion_agente`: inyectar el bloque solo si gate y flujo activo.
2. Renombrar a `flujo_carrito_compra` y crear inactivo sin pasos: data file + migración `19.0.1.2.0/post-migrate.py` (renombra `flujo_carrito` → `flujo_carrito_compra`, `active=False`, borra `paso_ids`, `generar_pasos_automatico=False`).
3. `prompt_carrito.py`: `_FLOW_CARTO='flujo_carrito_compra'` y texto del bloque actualizado.
4. n8n: actualizar el valor del Switch a `flujo_carrito_compra` en `ycloud_create_lead_0_con_menu_whatsapp.json`.
5. Tests deterministas actualizados (prompt, gate, migración) + bump versión + suite completa en verde.

## Acceptance criteria

- [ ] Instalación del módulo crea `flujo_carrito_compra` **inactivo**, con `paso_ids` vacío y `generar_pasos_automatico=False`.
- [ ] Upgrade desde `19.0.1.1.0`: el `flujo_carrito` existente queda renombrado a `flujo_carrito_compra`, inactivo y sin pasos.
- [ ] Con el flujo inactivo (estado por defecto), el `system_prompt` del agente NO incluye el bloque CARRITO, aunque haya productos.
- [ ] Con el flujo activo y productos vendibles con precio, el bloque CARRITO se inyecta.
- [ ] Con el flujo activo pero sin productos vendibles con precio, el bloque NO se inyecta.
- [ ] El prompt del carrito usa el nombre `flujo_carrito_compra` (no `flujo_carrito`).
- [ ] n8n Switch compara con `flujo_carrito_compra` (sin tocar URLs/tokens).
- [ ] Suite completa de `chatbot_cart` en verde con tests actualizados.
- [ ] Versión del manifest = `19.0.1.2.0`.

## Decisions

- **Sí:** flujo siempre creado e **inactivo por defecto**; activación manual por empresa (mecanismo existente de "Flujos de este cliente").
- **Sí:** renombrar a `flujo_carrito_compra` — nombre más claro y evita colisión conceptual con el endpoint `/chatbot_cart/procesar`.
- **Sí:** gate de prompt = productos vendibles con precio **y** flujo activo: ni se promete el carrito sin catálogo ni se sugiere cuando la empresa no lo activó.
- **Sí:** eliminar los pasos genéricos: el carrito lo gestiona el endpoint, no la captura clásica (`inicioagendar`).
- **No:** auto-activación universal en la sync (descartada por el usuario).
- **No:** flag adicional por cliente — la activación manual del flujo ya es el control.

## Risks

| Riesgo | Mitigación |
|---|---|
| Productos placeholder con precio ≠ 0 (Tips, Anticipo) | El gate exige venta con precio; el flujo además está inactivo hasta que la empresa lo active a propósito |
| Renombrado rompe la rama n8n del SPEC 28 | Se actualiza el valor del Switch al mismo tiempo que el prompt/data (mismo commit) |
| `chatbot_cart` desinstalado a mitad de vida | Odoo elimina el flujo con la desinstalación; el prompt deja de inyectarlo |

## What is **not** in this spec

- Auto-activación del carrito por sync o detección.
- Deploy a producción.
- Nuevos nodos o workflows de n8n (solo el valor de comparación del Switch).
- Otros canales, carrusel o gestión del catálogo.