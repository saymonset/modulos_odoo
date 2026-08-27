# SPEC 03 — Única fuente visible de configuración del chatbot

> **Status:** Approved
> **Depends on:** SPEC 01
> **Date:** 2026-08-28
> **Objective:** Consolidar toda la configuración del negocio del chatbot en una única fuente visible (`chatbot.config`), eliminando los duplicados de Ajustes generales y de la vista Configuración de la app Chatwoot.

## Scope

**In:**

- Eliminar de Ajustes generales todos los bloques del chatbot: "Chat Bot Integra" y "Configuración del agente (n8n)" (ai_chatbot_1_portal) y "Chatwoot Integration" (odoo_chatwoot_connector).
- Migrar los campos visibles al cliente final — nombre de marca y atribución de plataforma — desde `res.config.settings` a `chatbot.config`.
- La vista "Configuración" de la app Chatwoot queda solo con lo operativo: conexión Chatwoot, webhook n8n, token API, mensaje fallback, pasos opcionales.
- Botón "Activar flujos de esta configuración" en la ficha `chatbot.config` (reemplaza al botón "Detectar flujos automáticamente" de Ajustes).
- Aviso visible en la vista Configuración de la app Chatwoot cuando no hay `chatbot.config` activa, con acceso directo a Configuraciones de negocio.
- Runtime de marca/attribution: lee config activa primero, fallback a los `ir.config_parameter` actuales (modo legacy).
- Migración de datos: valores actuales de marca/attribution se copian a la config activa; los params NO se borran.
- Tests, bump de versión de ambos módulos y actualización del `MANUAL_FUNCIONAL_PROMPT_CONFIG.md`.

**Out of scope (specs futuros):**

- Multi-cliente por instancia (varias configs activas por cuenta/inbox de Chatwoot): el modelo es una instancia Odoo por cliente con UNA config activa.
- Eliminación del prompt legacy (`ai_chatbot_1_portal.system_prompt`): queda como fallback oculto sin UI.
- Cambios en el workflow de n8n.

## Data model

Campos nuevos en `chatbot.config` (ai_chatbot_1_portal):

```python
brand_name = fields.Char(
    string="Nombre de marca",
    help="Marca que ve el cliente final. Si está vacío se usa el nombre del negocio.",
)
attribution_enabled = fields.Boolean(string="Atribución de plataforma")
attribution_text = fields.Char(string="Texto de atribución", default="@integraiaconodoo")
```

Helper único en `chatbot.config`:

```python
@api.model
def _get_brand_settings(self):
    """(brand_name, attribution_enabled, attribution_text) desde la config
    activa; fallback a ir.config_parameter si no hay config (modo legacy)."""
```

Campos eliminados de `res.config.settings` (ai_chatbot_1_portal): `chat_bot_brand_name`, `chat_bot_platform_promotion_enabled`, `chat_bot_platform_promotion_text`, `chat_bot_system_prompt` (+ su lógica `default_get`/`set_values`/onchange y `action_detectar_flujos`). Se conservan: `chat_bot_webhook_url`, `chat_bot_fallback_message`, `chat_bot_api_token`, `chat_bot_include_optional_steps`. No hay modelos nuevos.

## Implementation plan

1. `models/chatbot_config.py`: campos de marca + helper `_get_brand_settings()`. Additive y funcional por sí solo.
2. Migración post-migrate: copiar valores de `ai_chatbot_1_portal.brand_name` / `platform_promotion_enabled` / `platform_promotion_text` a la config activa (si hay); params intactos. Actualizar seed `data/chatbot_config_data.xml` con los campos nuevos.
3. Runtime: `ChatBotUtils._get_brand_name` y atribución (`chatbot_utils.py:916,:933-936`), `chatbot_flujo.py:308` y `chatwoot_client.py:493-495` usan el helper. Manual: sin config activa, mensajes idénticos a hoy.
4. `views/chatbot_config_views.xml`: campos de marca en la ficha + botón "Activar flujos de esta configuración" (activa `flujo_ids` + default, archiva el resto).
5. Limpieza de Ajustes generales: eliminar `view_chatbot_res_config_settings` (ai_chatbot_1_portal) y `view_chatwoot_settings_inherit` (odoo_chatwoot_connector).
6. Vista dedicada Chatwoot (`view_chatwoot_settings_menu_form`): quitar marca y bloque "Configuración del agente (n8n)"; añadir aviso condicional de modo legacy (computed `has_active_business_config`) + botón que abre `action_chatbot_config`.
7. `models/res_config_settings.py`: eliminar campos migrados y lógica muerta; conservar operativos.
8. Tests: (a) helper devuelve marca de config activa; (b) sin config devuelve params legacy; (c) computed del aviso true/false; (d) actualizar tests que referencien campos eliminados. Bump de `__manifest__.py` en ambos módulos y del manual funcional.
9. Upgrade + `--test-enable` en staging (`odoo-19-web-leads`, cadena `ai_chatbot_1_portal,odoo_chatwoot_connector`) + verificación manual de UI.

## Acceptance criteria

- [ ] Ajustes generales no muestra ningún bloque del chatbot ("Chat Bot Integra", "Configuración del agente (n8n)", "Chatwoot Integration").
- [ ] La vista Configuración de la app Chatwoot solo expone campos operativos (conexión Chatwoot, webhook, token, fallback, pasos opcionales).
- [ ] El nombre de marca y el texto de atribución se editan únicamente en la ficha Configuraciones de negocio.
- [ ] Con config activa, los mensajes al cliente usan la marca/attribution de la ficha; sin config activa, usan los params legacy (sin regresión).
- [ ] Sin config activa, la vista Configuración de la app Chatwoot muestra el aviso de modo legacy con acceso a Configuraciones de negocio; con config activa, el aviso no aparece.
- [ ] El botón "Activar flujos de esta configuración" activa los flujos marcados + default y archiva el resto.
- [ ] El prompt que n8n recibe no cambia (config activa gana; legacy sigue de fallback oculto).
- [ ] `--test-enable` pasa con la cadena `ai_chatbot_1_portal,odoo_chatwoot_connector` en staging.

## Decisions

- **Yes:** todo el chatbot fuera de Ajustes generales — el funcional configura en un solo lugar por tipo de cosa: negocio → `chatbot.config`, operación → app Chatwoot.
- **Yes:** marca y atribución migran a `chatbot.config` — son del cliente configurado (la clínica tendrá su marca), no de la plataforma.
- **Yes:** prompt legacy como fallback oculto sin UI — rollback instantáneo, cero cambios de runtime (conserva la decisión de SPEC 01).
- **Yes:** una instancia por cliente con UNA config activa — modelo de despliegue actual de IntegraIA (VPS por cliente).
- **Yes:** aviso visible en modo legacy — evita confusión cuando no hay config activa.
- **No:** multi-cliente por instancia — requiere enrutamiento por cuenta/inbox (spec futuro si llega).
- **No:** borrar los `ir.config_parameter` de marca/prompt — siguen como fallback del modo legacy.

## Risks

| Risk | Mitigation |
| --- | --- |
| Instancia sin config activa al migrar | Params intactos y helper con fallback legacy: comportamiento idéntico a hoy. |
| Tests existentes referencian campos/vistas eliminadas | Paso 8 los actualiza antes del upgrade final. |
| El funcional edita el prompt por `ir.config_parameter` por costumbre | Aviso de modo legacy + manual actualizado apuntando a Configuraciones de negocio. |

## What is **not** in this spec

- Multi-cliente por instancia (enrutamiento de config por cuenta/inbox de Chatwoot).
- Eliminación del prompt legacy.
- Cambios en el workflow de n8n.