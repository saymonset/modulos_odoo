# SPEC 62 — Propagar el canal real (plataforma) hasta la creación del lead

> **Estado:** Approved
> **Depende de:** SPEC 61 (switch `Indentifica_canal` tolera Telegram), SPEC 43 (workspace n8n_json en lead)
> **Fecha:** 2026-09-19
> **Objetivo:** Que el lead creado desde el bot registre la plataforma real de la conversación (Telegram, Instagram, etc.) en vez de asumir WhatsApp, propagando `platform` desde n8n/Chatwoot hasta `datos_paciente` de la sesión Odoo.

## Por qué existe esta spec

Diagnóstico verificado en prod (lead 112, 19/09/2026): la conversación llegó por Telegram pero el lead quedó con `description` "Plataforma: WhatsApp", `medium_id` WhatsApp, `source_id` "WhatsApp Bot IntegraIA" y tag WhatsApp. El nodo n8n `Obtener_Info_basica` calcula bien `platform='telegram'` desde el webhook de Chatwoot y lo envía a Odoo en `/procesar_paso`, pero Odoo nunca lo persiste en `datos_paciente` de la sesión: `inicioagendar` no lo recibe, `iniciar_flujo` no lo guarda, y `procesar_paso` ignora su parámetro `platform`. Al crear el lead, `capturar_lead` usa `datos.get('plataforma', 'whatsapp')` → default WhatsApp.

## Scope

**In:**

1. Helper `ChatBotUtils._normalizar_plataforma(value)` que stripa prefijo `Channel::`, hace lowercase y usa `'whatsapp'` como default.
2. `iniciar_flujo(..., plataforma=None)` (chatbot_session.py:186): siembra `datos_paciente['plataforma']` normalizado.
3. `procesar_paso` (chatbot_session.py:332): sincroniza el `platform` del input en `datos_paciente['plataforma']` cuando hay sesión (write dedicado con try/except).
4. Controller `inicio_agendar` (chatbot_0_...:102): acepta `plataforma` opcional y lo pasa a `iniciar_flujo`.
5. Uso defensivo del helper en `capturar_lead` (chatbot_session.py:914) y `capturar_lead_http` (chatbot_3_...:204).
6. n8n chatwoot: nodo `paso_0_inicio_agendar` agrega `"plataforma"` al body JSON.
7. Bump `ai_chatbot_1_portal` a `1.0.42` + test de propagación.
8. Aplicación en vivo: import del JSON corregido en el n8n vivo y re-export (patrón SPEC 61/48).

**Out of scope (para futuras specs):**

- Campo estructurado `canal` en `crm.lead` (el canal sigue viviendo en description/UTM/tag).
- Workflow ycloud (integración WhatsApp directa, sin Telegram — mismo criterio de SPEC 61).
- `Seteamos_variables` (ruta de prueba chatTrigger que hardcodea `Channel::Whatsapp`; no es producción).
- Promoción a prod (`/home/odoo/prod/odoo19-skeleton/n8n_json/`): solo tras E2E verde (SPEC 43).

## Modelo de datos

Sin estructuras nuevas. Clave `plataforma` (string normalizado) en `datos_paciente` del JSONB `estado` de `chatbot.session` y en el body del nodo n8n `paso_0_inicio_agendar`:

```jsonc
// body de paso_0_inicio_agendar (n8n) — referencia al output del subflow
"plataforma": "{{ $(\"Call 'chatbot-simple_1_subflow'\").item.json.platform || 'whatsapp' }}"
```

```python
# normalización (helper)
'Channel::Telegram' -> 'telegram'
'telegram'          -> 'telegram'
'' / None           -> 'whatsapp'
```

## Plan de implementación

1. Agregar `_normalizar_plataforma` a `ChatBotUtils` y aplicarlo en `capturar_lead` y `capturar_lead_http`. Manual: `create_resultados_lead` con `plataforma='Channel::Telegram'` produce "Plataforma: Telegram".
2. `iniciar_flujo`: nuevo param `plataforma=None`; tras construir `datos_paciente`, `datos_paciente['plataforma'] = ChatBotUtils._normalizar_plataforma(plataforma)`.
3. `procesar_paso`: al encontrar `registro`, si `platform` está presente, sincronizar `registro.estado['datos_paciente']['plataforma']` (normalizado) con write dedicado y try/except.
4. Controller `inicio_agendar`: `plataforma = data.get('plataforma')` y pasarlo a `iniciar_flujo`.
5. Test en `tests/test_lead_creation.py`: sesión iniciada con `iniciar_flujo(plataforma='telegram')` + pasos procesados → lead con "Plataforma: Telegram" y tag/UTM Telegram. Regresión: sin plataforma → whatsapp.
6. Editar `/home/odoo/lead/odoo19-skeleton/n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json`: agregar `plataforma` al body de `paso_0_inicio_agendar`. Validar `python3 -m json.tool`.
7. Bump `1.0.42`, correr suites de `ai_chatbot_1_portal` en lead.
8. Usuario: import del JSON en el n8n vivo, probar con un mensaje Telegram, re-export a `n8n_json/chatwoot/` + commit en la rama `lead` de odoo19-skeleton.

## Criterios de aceptación

- [ ] Lead creado tras conversación Telegram registra "Plataforma: Telegram", UTM medium/source Telegram y tag "Telegram Bot".
- [ ] Regresión: WhatsApp sigue registrando "Plataforma: WhatsApp".
- [ ] `Channel::Telegram` recibido se normaliza a `telegram` por el helper.
- [ ] Flujo completado solo con datos precargados (sin pasar por `procesar_paso`) respeta la plataforma enviada en `inicioagendar`.
- [ ] Test nuevo pasa y suites de `ai_chatbot_1_portal` quedan en verde.
- [ ] `paso_0_inicio_agendar` incluye `plataforma` en su body y el JSON es válido (`python3 -m json.tool`).
- [ ] Export re-hecho en `n8n_json/chatwoot/` + commit en la rama `lead`.
- [ ] Los JSON de ycloud no se modifican.

## Decisiones tomadas y descartadas

- **Tomado:** Odoo + n8n — **descartado** solo Odoo (falla el flujo 100% precargado) y solo n8n (Odoo no persiste `plataforma` aunque la reciba).
- **Tomado:** helper normalizador central — **descartado** guardar valor crudo (`Channel::Telegram` no matchea el mapping de `setup_utm`).
- **Tomado:** sync en `procesar_paso` (write dedicado) + seed en `iniciar_flujo` — cubre flujos completos y flujos ya en curso.
- **Tomado:** en n8n referenciar el output del subflow (`$("Call 'chatbot-simple_1_subflow'")`) en vez de `$json.platform` — el output del agente langchain no garantiza arrastrar `platform`.
- **Tomado:** sin campo `canal` estructurado — se corrige la propagación existente (description/UTM/tag).
- **Tomado:** solo workflow chatwoot — **descartado** ycloud (mismo criterio de SPEC 61).
- **Descartado:** tocar `Seteamos_variables` (ruta de prueba).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Expresión `$("Call 'chatbot-simple_1_subflow'")` rota si el nodo cambia de nombre | Fallback `|| 'whatsapp'`; validar import en vivo |
| Write de `estado` en `procesar_paso` pise datos concurrentes | Write dedicado solo de `datos_paciente.plataforma` + try/except |
| `platform` con valor `Channel::Whatsapp` (ruta chatTrigger de prueba) | El helper normaliza a `whatsapp` |
| Regresión en tags/UTM de leads existentes | Test de regresión WhatsApp en verde antes de promoción |

## What is **not** in this spec

- Campo estructurado `canal` en `crm.lead`.
- Workflow ycloud.
- `Seteamos_variables` / ruta chatTrigger.
- Promoción a prod (solo tras E2E verde, SPEC 43).

Cada uno de esos, si llega, va en su propia spec.