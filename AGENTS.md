# AGENTS.md — Contexto del Proyecto

## Proyecto
- **Módulos**: `ai_chatbot_1_portal` + `odoo_chatwoot_connector` (Odoo 19.0)
- **Clínica**: UNISA Salud — Venezuela
- **Chatbot**: WhatsApp (vía Chatwoot + n8n + OpenAI)
- **Ruta base módulos**: `shared/extra/19.0/`

## Estructura clave

| Archivo | Propósito |
|---|---|
| `ai_chatbot_1_portal/controllers/chatbot_utils.py` | Utilidades: crear leads, formatear mensajes, mapeo grupos, `get_team_unisa`, `assign_lead_round_robin` |
| `ai_chatbot_1_portal/controllers/chatbot_3_crear_el_lead_finish_controller.py` | Endpoint HTTP `/ai_chatbot_1_portal/capturar_lead_http` — crear leads desde n8n |
| `ai_chatbot_1_portal/controllers/chatbot_0_inicio_agendar_procesar_paso_conroller.py` | Endpoint `/inicioagendar` — inicia flujo |
| `ai_chatbot_1_portal/models/chatbot_session.py` | Modelo `chatbot.session` — gestiona sesiones, flujos, pasos |
| `ai_chatbot_1_portal/models/chatbot_flujo.py` | Modelo `chatbot.flujo` — define pasos por tipo de flujo |
| `odoo_chatwoot_connector/models/chatwoot_mapping.py` | Modelo `chatwoot.mapping` + round-robin (`select_round_robin_mapping`) |
| `odoo_chatwoot_connector/models/chatwoot_client.py` | Cliente API Chatwoot: asignación, labels, agent details, inbox members |
| `odoo_chatwoot_connector/models/chatbot_session_inherit.py` | Hook `capturar_lead` en `chatbot.session` (RPC path) |
| `odoo_chatwoot_connector/models/lead_inherit.py` | Campos extra en `crm.lead`: `chatwoot_processing_status`, `chatwoot_assigned_agent_name`, etc. |
| `odoo_chatwoot_connector/views/crm_lead_views.xml` | Vista heredada de `crm.lead` con pestaña Chatwoot |
| `odoo_chatwoot_connector/views/chatwoot_mapping_views.xml` | Vistas de mapping |
| `ai_chatbot_1_portal/n8n/chatbot_create_lead_0.json` | Export JSON del workflow de n8n |

## Mapeo flujos → Grupo CRM

| `equipo_asignado` (n8n) | `name_flow` | Grupo CRM |
|---|---|---|
| `Agendamiento_Directo` | `flujo_agendamiento_directo` | *(sin agente)* |
| `Agendamiento_Precios` | `flujo_agendamiento_precios` | *(sin agente)* |
| `Agendamiento_Servicios` | `flujo_agendamiento_servicios` | *(sin agente)* |
| `Agendamiento_Otra_Consulta` | `flujo_agendamiento_otra_consulta` | Grupo Citas |
| `Ventas_UNISA` | `flujo_ventas_unisa` | Grupo Ventas |
| `CITAS_MP` | `flujo_citas_medios_propios` | Grupo Citas |
| `CITAS_SEGUROS` | `flujo_citas_seguro` | Grupo Citas |
| `RESULTADOS_LAB` | `flujo_resultados_laboratorio` | Grupo Laboratorio |
| `RESULTADOS_IMAGENES` | `flujo_resultados_imagenes` | Grupo Imagenología |

## Integración con n8n
- Webhook Chatwoot → n8n → OpenAI (gpt-4o-mini) → decide `equipo_asignado` y `tipoPregunta`
- Si hay `equipo_asignado` → llama a `/inicioagendar` → inicia flujo en Odoo
- El `equipo_asignado` se envía tal cual a Odoo (sin mapear)

## Reglas importantes
- Actualizar módulos via: `-u ai_chatbot_1_portal -u odoo_chatwoot_connector`
- Los cambios Python requieren `-u` y reinicio del server dev
- Para leads de resultados (LAB/IMAGENES) se usa `create_resultados_lead`, para el resto `create_lead`
- Todos los mapeos están duplicados en 3 lugares (controller, session_model, utils) — mantener sincronizados
- En `auth='public'` routes, `request.env` es el user público. Usar `request.env(user=admin_uid)` para cambiar user. Para acceder a campos que referencian `res.users` (ej. `crm.team.member_ids`), usar `.sudo()` en el recordset: `team.sudo().member_ids`
- **Servidor dev**: puerto 38069, arrancar desde: `clientes/integraiadev_19/`
- **Log Odoo**: `clientes/integraiadev_19/log/odoo.log`
- **Python/venv**: `.venv/bin/python3`

## Estado actual (Jun 08 2026)

### ✅ Completado
- **Round-robin Chatwoot**: Rotación entre mappings del mismo `equipo_asignado`. Alterna entre IDs 3 y 9 para CITAS_MP (agent_id=14). Verificado via JSON-RPC. Funciona correctamente.
- **Round-robin Odoo** (usuarios CRM): `assign_lead_round_robin` en `chatbot_utils.py` rota entre miembros del equipo. Equipo Grupo Citas tiene 4 miembros (IDs 5,6,7,8).
- **HTTP endpoint reparado**: Error `"Failed to write field crm.team.member_ids. Public user (id=3) doesn't have read access to User (res.users)"` resuelto.
  - **Causa raíz**: `team` era un recordset en el env del user público (uid=3). Acceder a `team.member_ids` (campo Many2many a `res.users`) requiere permisos que el user público no tiene.
  - **Solución**: `chatbot_3_crear_el_lead_finish_controller.py:242`: usar `team_sudo = team.sudo()` y acceder `team_sudo.member_ids`. También se agregó `.sudo()` en la búsqueda fallback de equipos en `chatbot_utils.py:228-230`.
  - **Endpoint verificado**: POST a `/ai_chatbot_1_portal/capturar_lead_http` retorna HTTP 200 con lead creado (ID 151).
- **Logging `RR[...]`**: Agregado en `chatwoot_mapping.py`, `chatbot_3_crear_el_lead_finish_controller.py`, `chatbot_session_inherit.py`, `chatbot_utils.py`, `chatwoot_client.py`.
- **Chatwoot Mappings activos**: 12 registros (IDs 3-14) con pares duplicados (ID 3 y 9 ambos con agent_id=14, etc.). Todos inbox 7.
- **Preservación de assignee en Chatwoot**: Cuando una conversación ya tiene un agente asignado y está `open`/`pending`, Odoo **NO reasigna** — preserva el agente actual. Cuando está `resolved`, reasigna normalmente.
  - `chatwoot_client.py:assign_conversation` → verifica `_get_conversation_details` al inicio; si hay assignee activo, retorna `assigned_to='preserved'` sin llamar al API de assignments.
  - `chatbot_session_inherit.py` → maneja `assigned_to='preserved'` sin publicar chatter, guarda log.
  - `chatbot_3_crear_el_lead_finish_controller.py` → mismo manejo.

### 🔄 Pendiente
- **Probar flujo completo con preservación**: n8n → Odoo → lead creado → conversación con assignee activo → preservación. Requiere prueba con conversación real de Chatwoot.
- **Limpiar mappings duplicados**: IDs 9-14 son duplicados de IDs 3-8. Se pueden desactivar (archivar) para evitar confusión en la rotación.

### 📝 Notas técnicas
- `get_team_unisa` en `chatbot_utils.py:293` usa `sudo().with_context(lang='en_US')` para buscar equipos por nombre traducido.
- Correo de notificación configurado: `email_from = admin@unisasalud.com`. Alias domain con `default_from = 'admin'`.
- Chatwoot: inbox 7 (WhatsApp +58 424 8221683). Agents: 1 (admin), 9-18 (ejecutivos).
- Admin UNISA: user 13, login `admin@unisasalud.com`, password `Unisa2024!`.
- `conversation_id` en n8n: `body.conversation?.id` (corregido, antes usaba `messages[0].conversation_id`).
