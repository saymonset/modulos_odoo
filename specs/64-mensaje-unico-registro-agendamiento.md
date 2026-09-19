# SPEC 64 — Mensaje único de confirmación (sin audit técnico) al completar un flujo

> **Estado:** Approved
> **Depende de:** SPEC 61, SPEC 62 (canal Telegram→lead, ya implementados en código), SPEC 43 (workspace n8n_json)
> **Fecha:** 2026-09-19
> **Objetivo:** Que el cliente reciba un solo bloque de confirmación al completar un flujo — "Tu consulta sobre X ha sido registrada." + la respuesta final (Referencia/Próximo paso) — eliminando la sección técnica "Flujo/Estado/Pasos" y el email del agente.

## Por qué existe esta spec

Hoy el cliente recibe dos mensajes al completar el flujo `flujo_agendamiento_directo`:

1. Bloque 1 = `notify_message` de `_build_notify_message_with_audit` (chatbot_utils.py:1103), que `assign_conversation` publica directo en Chatwoot (chatwoot_client.py:488) con el audit técnico ("Flujo/Estado/Pasos") y el email del agente → confunde al cliente.
2. Bloque 2 = respuesta final (`_generar_mensaje_finalizacion` en ruta sesión / `generate_response` en ruta HTTP) que n8n publica.

El audit ya queda persistido en `chatwoot_assign_log` del lead, así que eliminarlo del chat no pierde información. La unificación se hace en Odoo: la respuesta final viaja en `texto_para_usuario` y n8n la envía tal cual → no se toca ningún JSON n8n.

Además, SPEC 61+62 (canal Telegram→lead) ya están implementados y commiteados (código `_normalizar_plataforma`, body `plataforma` en el JSON, módulo `1.0.42`). El lead 113 salió "Plataforma: WhatsApp" porque el ambiente en vivo aún no tiene el fix aplicado. Esta spec incluye verificar ese despliegue.

## Scope

**In:**

1. Helper `ChatBotUtils._encabezado_registro(equipo_asignado)` → `"Tu consulta sobre {equipo} ha sido registrada."` (equipo con `_`→espacio; fallback `"Tu consulta ha sido registrada."`).
2. Anteponer el encabezado en `_generar_mensaje_finalizacion` (chatbot_session.py:1006) — ruta sesión (`/procesar_paso`).
3. Anteponer el encabezado en `generate_response` (chatbot_utils.py:1132), en ambas ramas (IA y fallback) — ruta HTTP (`/capturar_lead_http`).
4. Eliminar el posteo del notify al cliente: quitar `notify_message` del mapping en los dos callers (`chatbot_3_crear_el_lead_finish_controller.py:310` y `chatbot_session_inherit.py:130`) y eliminar el bloque de posteo + el override del branch `preserve` en `assign_conversation` (chatwoot_client.py:390-400 y 487-502).
5. Eliminar `_build_notify_message_with_audit` (queda sin uso).
6. Bump `ai_chatbot_1_portal` a `1.0.43` y `odoo_chatwoot_connector` a `1.0.13`.
7. Tests del encabezado, del mensaje final sin audit y de que el mapping ya no lleva `notify_message`.
8. Verificación de despliegue en vivo del canal (SPEC 61+62): upgrade de módulo + import de JSON n8n + prueba Telegram → lead "Plataforma: Telegram".

**Out of scope (para futuras specs):**

- Cambiar el texto del mensaje final generado por IA.
- Modificar JSONs n8n (la respuesta única viaja en `texto_para_usuario`).
- Promoción a prod (`/home/odoo/prod/odoo19-skeleton/n8n_json/`): solo tras E2E verde (SPEC 43).
- Workflow ycloud.
- El mensaje "Ya tienes una solicitud en curso..." (branch `preserve`): se elimina con el notify post.

## Modelo de datos

Sin estructuras nuevas. El encabezado es un string calculado:

```python
# ChatBotUtils (chatbot_utils.py), junto a _pie_mensaje
@staticmethod
def _encabezado_registro(equipo_asignado):
    equipo = (equipo_asignado or '').replace('_', ' ').strip()
    if equipo:
        return f"Tu consulta sobre {equipo} ha sido registrada."
    return "Tu consulta ha sido registrada."
```

Forma del mensaje único (cliente):

```
Tu consulta sobre Agendamiento Directo ha sido registrada.

[respuesta final: gracias + Referencia + Próximo paso]

_Atención automatizada por @integraiaconodoo_
```

## Plan de implementación

1. Agregar `_encabezado_registro` a `ChatBotUtils`. Manual: `_encabezado_registro('Agendamiento_Directo')` → `"Tu consulta sobre Agendamiento Directo ha sido registrada."`.
2. `generate_response`: prepender `ChatBotUtils._encabezado_registro(equipo_asignado) + "\n\n"` antes del `mensaje_final + pie` (rama IA, chatbot_utils.py:1160) y antes de las `lines` (fallback, :1183).
3. `_generar_mensaje_finalizacion` (chatbot_session.py:1037): retornar `encabezado + "\n\n" + msg + "\n\n" + pie`.
4. Quitar `notify_message` del mapping en `chatbot_3_crear_el_lead_finish_controller.py:310` y `chatbot_session_inherit.py:130`.
5. En `chatwoot_client.py::assign_conversation`, eliminar el override de `notify_message` del branch `preserve` (390-400) y el bloque de posteo al final (487-502).
6. Eliminar `_build_notify_message_with_audit` (chatbot_utils.py:1103).
7. Agregar `tests/test_mensaje_unico_registro.py`: encabezado (normalización + fallback), `_generar_mensaje_finalizacion` inicia con el encabezado y NO contiene `Flujo:`/`Estado:`/`Pasos:`/email, y el mapping a `assign_conversation` no lleva `notify_message`.
8. Bump versiones (1.0.43 y 1.0.13), correr suites de `ai_chatbot_1_portal` y `odoo_chatwoot_connector` en lead.
9. Aplicación en vivo (usuario): actualizar módulos en la DB viva; importar los JSON n8n corregidos de SPEC 61+62 (`chatbot_create_lead_0_con_menu_whatsapp.json` + `chatbot-simple_1_subflow.json`) si no están; re-exportar a `n8n_json/chatwoot/` + commit en rama `lead`.

## Criterios de aceptación

- [ ] Completar un flujo vía `/procesar_paso` envía un solo mensaje que inicia con "Tu consulta sobre X ha sido registrada." e incluye Referencia y Próximo paso.
- [ ] El mensaje único NO contiene "Flujo:", "Estado:", "Pasos:", ni el email del agente.
- [ ] `assign_conversation` ya no publica ningún `notify_message` en la conversación (log sin `notify_failed`/post).
- [ ] Regresión: ruta HTTP (`/capturar_lead_http`) también produce el mensaje único con encabezado.
- [ ] El branch `preserve` no deja mensajes pendientes al cliente.
- [ ] Tests nuevos pasan y las suites de `ai_chatbot_1_portal` y `odoo_chatwoot_connector` quedan en verde.
- [ ] Módulos versionados 1.0.43 / 1.0.13.
- [ ] Canal: reserva vía Telegram crea el lead con "Plataforma: Telegram" y tag/UTM Telegram; regresión WhatsApp → "Plataforma: WhatsApp".
- [ ] Los JSON n8n no se modifican por esta spec.

## Decisiones tomadas y descartadas

- **Tomado:** unificar en la respuesta final (header prepend) — **descartado** publicar el notify como nota privada Chatwoot (el audit ya vive en `chatwoot_assign_log`; el usuario pidió eliminarlo del chat).
- **Tomado:** ocultar el email del agente al cliente — **descartado** mantenerlo ("Agente asignado: oraclefedora@gmail.com" es dato personal del equipo y confunde).
- **Tomado:** eliminar el posteo del notify por completo (incluido branch `preserve`) — la respuesta final única es el único acuse.
- **Tomado:** cambio solo en Odoo — **descartado** tocar n8n (la respuesta única viaja en `texto_para_usuario`).
- **Tomado:** eliminar `_build_notify_message_with_audit` (código muerto tras los cambios).
- **Tomado:** canal Telegram → verificar despliegue en vivo de SPEC 61+62 (código ya commiteado) — **descartado** re-investigar el bug de código.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Ruta 100% precargada (`iniciar_flujo` → `flow_completed`) solo acusaba vía notify; tras eliminarlo quedaría sin mensaje | El export n8n actual nunca envía `telefono` a `/inicioagendar`, así que esa ruta no se dispara hoy; se documenta para una futura spec |
| Branch `preserve` pierde el aviso "Ya tienes una solicitud en curso..." | La respuesta final cubre el acuse; cambio aceptado por el usuario |
| Algún caller externo dependa del posteo de `assign_conversation` | Solo 2 callers, ambos actualizados; se elimina el bloque muerto |
| Despliegue del canal incompleto en vivo | Criterio de aceptación con prueba Telegram→lead antes de cerrar |

## What is **not** in this spec

- Cambiar el texto del mensaje final generado por IA.
- Modificar JSONs n8n (el merge es 100% Odoo).
- Promoción a prod (solo tras E2E verde, SPEC 43).
- Workflow ycloud.
- El aviso "Ya tienes una solicitud en curso..." del branch `preserve`.

Cada uno de esos, si llega, va en su propia spec.