# SPEC 01 — Prompt universal multicliente para el chatbot

> **Status:** Draft
> **Depends on:** (ninguno)
> **Date:** 2026-08-27
> **Objective:** Permitir que cualquier cliente (inmobiliaria, clínica, doctor, mecánico, gobernación) tenga su propio prompt de negocio generado desde una configuración guardada en Odoo, reutilizando un esqueleto universal único (JSON, clasificación de intención, flujos, límites por plataforma).

## Scope

**In:**

- Plantilla/prompt universal reutilizable por cualquier cliente.
- Config por cliente en un modelo Odoo nuevo (`chatbot.config`): marca, contenido, intenciones, menú, flujos, respuestas.
- Render del prompt final en runtime a partir de esa config.
- Intenciones configurables con núcleo común universal (agendar, consulta general, archivo/imagen).
- Adaptar el normalizador y la auto-detección de flujos a la config.
- Migrar el prompt actual de IntegraIA como primer caso de validación (seed de config).

**Out of scope (specs futuros):**

- n8n (los pasos de los flujos viven ahí).
- Portal web / hooks Chatwoot / UI de sesiones.
- Migración de sesiones existentes.
- Facturación o cobro de planes por cliente.

## Data model

Nuevos modelos en `ai_chatbot_1_portal`:

```python
# chatbot.config — config de negocio de un cliente
class ChatbotConfig(models.Model):
    _name = "chatbot.config"
    name = fields.Char(required=True)            # nombre del cliente/negocio
    role = fields.Text()                          # "TÚ ERES" / objetivo de venta
    cta_url = fields.Char()                       # web (ej. integraia.lat)
    contacto = fields.Text()                      # tel/horario/email
    bloque_conocimiento = fields.Text()           # base de conocimiento libre (precios/servicios/requisitos)
    intencion_ids = fields.One2many("chatbot.intencion", "config_id")
    flujo_ids = fields.Many2many("chatbot.flujo") # flujos activos del cliente
    output_instagram = fields.Boolean()           # ¿genera variante corta por plataforma?

# chatbot.intencion — una intención con su clasificación y respuesta
class ChatbotIntencion(models.Model):
    _name = "chatbot.intencion"
    config_id = fields.Many2one("chatbot.config", required=True)
    nombre = fields.Char(required=True)           # ej. PRECIOS, AGENDAR_VISITA
    keywords = fields.Char()                      # "precio,planes,costo,tasa"
    prioridad = fields.Integer()                  # orden en la clasificación
    tipo_pregunta = fields.Char()                 # mapeo al JSON (PRECIOS, CITA_DIRECTA, ...)
    output_largo = fields.Text()                  # whatsapp/otros
    output_corto = fields.Text()                  # instagram/meta
    flow_id = fields.Many2one("chatbot.flujo")    # flujo que dispara (opcional)
    es_menu = fields.Boolean()                    # si muestra el menú
```

Núcleo universal fijo (no en config): estructura JSON de 10 claves, límites por plataforma, regla de aviso previo de flujo, manejo de imágenes (CONFIRMACION_IMAGEN → flujo_resultados_imagenes), normalización de texto, lógica del "sí", comandos (menu/cancelar/salir) y fallback.

## Implementation plan

1. Crear `models/chatbot_config.py` y `models/chatbot_intencion.py` (migración + `security/ir.model.access.csv` + menú/vista). Queda funcional: modelos instalables.
2. Crear `services/prompt_renderer.py` con `render_prompt(config) -> str`: arma el prompt = esqueleto universal + secciones del cliente (rol, conocimiento, menú, prioridades generadas, respuestas). Manual: unit test del renderer con una config mínima.
3. Integrar el render en `res_config_settings.py`/`chatbot_session.py`: el `system_prompt` se genera desde la config activa en runtime; se mantiene el prompt legacy como fallback si no hay config (retrocompat).
4. Adaptar `chatbot_prompt_normalizer.py` y `aplicar_deteccion_automatica` para leer la config (flujos por cliente) en vez de solo parsear texto.
5. Seed XML con la config de **IntegraIA** traducida desde `prompt_integraia_v2.txt` (migración de datos). `prompt_integraia_v2.txt` pasa a ser artefacto exportado, no fuente de verdad.
6. Tests: `tests/test_prompt_renderer.py` — (a) la config IntegraIA renderiza un prompt con las mismas intenciones/flujos/JSON; (b) una config de cliente nuevo (ej. clínica) produce un prompt válido con sus propias intenciones; (c) detección de flujos desde config.

## Acceptance criteria

- [ ] Un cliente nuevo se configura desde Odoo (contenido, intenciones, menú, flujos) sin tocar código y el chatbot responde con esa lógica.
- [ ] La config de IntegraIA migrada conserva las mismas intenciones, flujos (`flujo_agendamiento_directo`, `flujo_agendamiento_otra_consulta`, `flujo_resultados_imagenes`) y el JSON de 10 claves.
- [ ] Los límites de caracteres por plataforma y el manejo de imágenes funcionan idéntico para cualquier cliente.
- [ ] `--test-enable` pasa en `ai_chatbot_1_portal` con los tests nuevos.
- [ ] Sin config creada, el sistema sigue funcionando con el prompt legacy (sin regresión).

## Decisions

- **Yes:** config en modelo Odoo (`chatbot.config`) en vez de archivos externos: consultable, editable desde UI, migrable.
- **Yes:** render del prompt en runtime desde la config (no archivo estático por cliente como fuente de verdad).
- **Yes:** intenciones configurables por cliente con núcleo común universal (agendar/consulta/archivo).
- **Yes:** flujos como catálogo de tipos que el cliente activa (`Many2many` a `chatbot.flujo`).
- **Yes:** menú configurable (el cliente define sus opciones; ya no fijo en 4).
- **No:** n8n, portal y facturación de planes (specs separados).

## Risks

| Risk                                                                 | Mitigation                                                                                                            |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Migrar IntegraIA altera su comportamiento                            | Test de paridad: la config migrada debe renderizar las mismas intenciones/flujos que el prompt actual; revisar el diff. |
| Prompt renderizado demasiado largo (costo tokens)                    | Secciones condicionales: solo se incluyen bloques configurados.                                                       |
| Auto-detección de flujos acoplada al texto                           | Migrar la detección a leer `chatbot.config`/`chatbot.flujo`.                                                          |

## What is **not** in this spec

- n8n, portal Chatwoot, migración de sesiones, facturación de planes. Cada uno, si llega, va en su propio spec.