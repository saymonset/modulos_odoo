# SPEC 27 — Ocultar el nombre del flujo en el aviso inicial del bot

> **Status:** Approved
> **Depends on:** —
> **Date:** 2026-09-11
> **Objective:** Que cada flujo decida si su nombre técnico se muestra en el aviso inicial del bot, ocultándolo por defecto para evitar ruido al cliente.

## Scope

**In:**

- Campo Boolean `mostrar_nombre_en_aviso` en `chatbot.flujo`, default `False` (oculto).
- En `iniciar_flujo` (`models/chatbot_session.py:241`), omitir el sufijo ` ({flow_name})` cuando el flujo no lo pide o no existe registro (fallback al default).
- Añadir el campo al form de flujo (`views/chatbot_flujo_views.xml`).
- Tests del aviso con y sin el flag.
- Bump de versión del módulo.

**Out of scope:**

- Cambiar el texto del aviso ("¡Excelente!...", "salir").
- Cambiar los nombres técnicos de los flujos.
- Config global o mostrar un label amigable en su lugar.

## Data model

Nuevo campo en `chatbot.flujo`:

```python
mostrar_nombre_en_aviso = fields.Boolean(
    string="Mostrar nombre del flujo en el aviso",
    default=False,
    help="Si está activo, el aviso inicial muestra el nombre técnico "
         "del flujo (p. ej. (flujo_agendamiento_precios)). "
         "Por defecto se oculta para no causar ruido al cliente.",
)
```

No se introducen tablas nuevas ni relaciones.

## Implementation plan

1. Añadir el campo `mostrar_nombre_en_aviso` en `models/chatbot_flujo.py`.
2. Añadir el campo al form en `views/chatbot_flujo_views.xml` (grupo principal, junto a `politica_inicio`).
3. En `models/chatbot_session.py:241`, buscar el flujo por `name` y construir el aviso condicionalmente:
   ```python
   flujo = self.env['chatbot.flujo'].search([('name', '=', flow_name)], limit=1)
   mostrar_nombre = flujo.mostrar_nombre_en_aviso if flujo else False
   sufijo_nombre = f" ({flow_name})" if mostrar_nombre else ""
   aviso_flujo = (f"¡Excelente! Para continuar, le haré unas breves preguntas y "
                  f"un asesor de la empresa lo contactará.{sufijo_nombre}\n"
                  f"Si no desea continuar, escriba \"salir\".\n\n")
   ```
4. Bump `__manifest__.py` a `1.0.35`.
5. Añadir tests en `tests/test_aviso_flujo.py`: sin flag el aviso NO contiene el nombre del flujo; con flag activo SÍ lo contiene.

## Acceptance criteria

- [ ] Con el flag desactivado (default), `iniciar_flujo` produce un aviso sin `(flujo_...)`.
- [ ] Con el flag activado, el aviso incluye `(flow_name)` exactamente como hoy.
- [ ] Si no existe el registro `chatbot.flujo`, el aviso sale sin nombre (fallback seguro para tests).
- [ ] El campo aparece en el formulario de flujo.
- [ ] Los tests del módulo pasan.

## Decisions

- **Sí:** control por flujo (Boolean en `chatbot.flujo`) y no global. Cada flujo decide; más flexible y sigue el patrón de configuración por flujo ya existente (`routing_key`, `politica_inicio`).
- **Sí:** oculto por defecto. Es el comportamiento que pide el usuario y evita tocar flujos existentes para limpiar el mensaje.
- **No:** mostrar `routing_key` o un label amigable en el aviso. Agrega complejidad sin necesidad; se deja como futuro spec si se pide.
- **No:** migración `post-migrate`. El campo tiene default y Odoo crea la columna automáticamente.

## What is **not** in this spec

- Cambiar el texto del aviso ni el mecanismo de "salir".
- Config global para todos los flujos.
- Labels amigables en el aviso (p. ej. "(Precios)").

Cada uno de esos, si llega, va en su propio spec.