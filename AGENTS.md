# AGENTS.md — Contexto del Proyecto

## Proyecto
- **Módulo**: `ai_chatbot_1_portal` (Odoo 19.0)
- **Clínica**: UNISA Salud — Venezuela
- **Chatbot**: WhatsApp (vía Chatwoot + n8n + OpenAI)
- **Ruta base**: `shared/extra/19.0/ai_chatbot_1_portal/`

## Estructura clave

| Archivo | Propósito |
|---|---|
| `controllers/chatbot_utils.py` | Utilidades: crear leads, formatear mensajes, mapeo grupos |
| `controllers/chatbot_3_crear_el_lead_finish_controller.py` | Endpoint HTTP `/capturar_lead_http` |
| `controllers/chatbot_0_inicio_agendar_procesar_paso_conroller.py` | Endpoint `/inicioagendar` — inicia flujo |
| `models/chatbot_session.py` | Modelo `chatbot.session` — gestiona sesiones, flujos, pasos |
| `models/chatbot_flujo.py` | Modelo `chatbot.flujo` — define pasos por tipo de flujo |
| `n8n/` | Export JSON del workflow de n8n |

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
- El mapeo `Ventas_UNISA → flujo_ventas_unisa` se hace en n8n (código JS del nodo `Separar_variables_en_json`)
- El `equipo_asignado` se envía tal cual a Odoo (sin mapear)

## Reglas importantes
- El módulo se actualiza vía `-u ai_chatbot_1_portal`
- Los cambios Python requieren actualizar el módulo (Odoo no recarga automático)
- Para leads de resultados (LAB/IMAGENES) se usa `create_resultados_lead`, para el resto `create_lead`
- Todos los mapeos están duplicados en 3 lugares (controller, session_model, utils) — mantener sincronizados
