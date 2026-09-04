# SPEC 08 — Unificar token del chatbot: BD leads alineada al CHATBOT_API_TOKEN de n8n

> **Status:** Approved
> **Depends on:** (ninguno)
> **Date:** 2026-09-05
> **Objective:** Eliminar el 401 "Token inválido" del nodo `Obtener_configuracion_agente` igualando el `ai_chatbot_1_portal.api_token` de la BD leads (`dbodoo19`) al `CHATBOT_API_TOKEN` de n8n — vía UI de Ajustes — y documentar en AGENTS.md dónde vive el token para evitar re-desalineaciones.

## Por qué existe esta spec

Transcript real (2026-09-04 19:32): el nodo `Obtener_configuracion_agente` del workflow
`ycloud_create_lead_0_con_menu_whatsapp` (n8n 2.2.6, contenedor único) devuelve
401 "Token inválido" al POST a `https://lead.integraia.lat/ai_chatbot_1_portal/configuracion_agente`.

Diagnóstico verificado: el n8n (compose `docker-compose.n8n.yml`) define
`CHATBOT_API_TOKEN=<valor prod>` y el workflow lo envía vía `$env.CHATBOT_API_TOKEN`.
`lead.integraia.lat` → nginx upstream `odoo_leads` (127.0.0.1:28069) →
`odoo-19-web-leads` → BD `dbodoo19` (odoo-db19-leads). En esa BD, la clave
`ai_chatbot_1_portal.api_token` tiene **otro valor** distinto al de n8n.

El único endpoint que valida el token es `configuracion_agente`
(`chatbot_0_inicio_agendar_procesar_paso_conroller.py:392-404`). Por eso
`procesar_paso`, `inicioagendar` y `session/*` sí funcionaban sin token: el input
del nodo mostraba `success: true` (llegaba de `procesar_paso`) pero el flujo
no podía completar el paso de configuración.

## Scope

**In:**

- Setear el parámetro `ai_chatbot_1_portal.api_token` en la BD `dbodoo19`
  (odoo-db19-leads) al mismo valor que `CHATBOT_API_TOKEN` del
  `docker-compose.n8n.yml`, vía UI de Ajustes de `lead.integraia.lat`.
- Verificación con curl: POST a `lead.integraia.lat/...configuracion_agente`
  con el token → 200 con `system_prompt`/`fallback_message`/`flow_map`;
  con token erróneo → 401 (validación sigue activa).
- Replay del workflow `ycloud_create_lead_0_con_menu_whatsapp` con un mensaje
  real de WhatsApp (número de prueba acordado, NO con pinData del manual trigger):
  el nodo pasa y la ejecución termina con el menú/texto entregado.
- No-regresión prod: POST a `integraia.lat/...configuracion_agente` con el
  mismo token → 200.
- Bullet en AGENTS.md (sección "Workflow Docker (gotchas comprobados)",
  ítem 5) documentando dónde vive el token, la regla de coincidencia entre
  entornos y el endpoint que lo valida.
- Commit (`docs:`) desde lead, push, pull en prod; hash idéntico de AGENTS.md
  en ambos clones.

**Out of scope (specs futuros / ops):**

- Segundo token por entorno (`CHATBOT_API_TOKEN_LEADS`) — sobreingeniería
  para un único contenedor n8n.
- Rotación del token (nuevo valor) — se reutiliza el existente de prod.
- Validación de token en los demás endpoints (`procesar_paso`, `inicioagendar`,
  `session/*`).
- Cambios en JSON de workflows n8n ni en el compose de n8n.
- Cambios de código en `shared/` (no aplica `--test-enable`; ya existe
  `test_flow_routing_map.py` que cubre el contrato del endpoint).

## Data model

Esta feature no introduce estructuras nuevas. Cambia el **valor** de un registro
existente:

```sql
-- Clave que almacena el token en ir_config_parameter
-- BD: dbodoo19 (odoo-db19-leads, sirve lead.integraia.lat)
-- Valor canónico: CHATBOT_API_TOKEN del docker-compose.n8n.yml de n8n
-- (No se inlinea aquí: el repo está en git.)
```

`CHATBOT_API_TOKEN` vive en `docker-compose.n8n.yml` del directorio de
producción de n8n (fuera de este repo). `ai_chatbot_1_portal.api_token` es el
`config_parameter` que el campo `chat_bot_api_token` de `res.config.settings`
escribe y que `configuracion_agente` lee con `get_param()`.

## Implementation plan

1. **Setear el token vía UI de Ajustes.** Ir a `https://lead.integraia.lat`
   → Ajustes → campo "Chat bot API token" (`chat_bot_api_token`) → pegar
   el valor de `CHATBOT_API_TOKEN` del `docker-compose.n8n.yml` → Guardar.
   *Invalida correctamente la caché de `ir.config_parameter`; sin restart.*
   *Sistema funcional inmediatamente.*

2. **Verificar leads con curl.** Desde el host:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" \
     -X POST https://lead.integraia.lat/ai_chatbot_1_portal/configuracion_agente \
     -H "Content-Type: application/json" \
     -d '{"token":"<VALOR_CHATBOT_API_TOKEN>","text":"test"}'
   # Debe devolver 200
   ```
   Con token erróneo debe devolver 401 (validación activa).

3. **Replay del workflow en n8n.** En la UI de n8n, re-ejecutar el workflow
   `ycloud_create_lead_0_con_menu_whatsapp` con un mensaje real de WhatsApp
   (número de prueba acordado) — NO con el pinData del manual trigger
   `When clicking 'Execute workflow'`. Verificar que el nodo
   `Obtener_configuracion_agente` pasa sin error y la ejecución completa
   termina con el menú/texto entregado.

4. **No-regresión prod.** Verificar `https://integraia.lat/ai_chatbot_1_portal/configuracion_agente`
   con el mismo token → 200. El token de prod no se toca, pero se confirma
   que no hubo efecto colateral.

5. **Documentar en AGENTS.md.** Añadir ítem 5 en "Workflow Docker (gotchas
   comprobados)":
   ```
   5. Token del chatbot (n8n ↔ Odoo): el nodo `Obtener_configuracion_agente`
      de los workflows n8n envía `$env.CHATBOT_API_TOKEN` (definido en
      `docker-compose.n8n.yml` de n8n) y solo `/ai_chatbot_1_portal/configuracion_agente`
      lo valida contra `ir.config_parameter` clave `ai_chatbot_1_portal.api_token`
      (Ajustes → "Chat bot API token") de la BD que sirve cada dominio
      (lead.integraia.lat → leads/dbodoo19; integraia.lat → prod/dbodoo19).
      Tras cambiar el token en cualquiera de los lados, verificar que el
      valor coincida en TODAS las BDs servidas antes de re-ejecutar flujos
      (401 "Token inválido" = desalineado).
   ```
   Commit (`docs:`), push desde lead, pull en prod; verificar
   `git hash-object AGENTS.md` idéntico en ambos clones.

6. **Marcar spec Implemented.** Cambiar `Status: Draft` a `Status: Implemented`
   y commit (`docs:`).

## Acceptance criteria

- [ ] En `dbodoo19` (odoo-db19-leads), `ai_chatbot_1_portal.api_token` ==
      `CHATBOT_API_TOKEN` del `docker-compose.n8n.yml`.
- [ ] POST a `https://lead.integraia.lat/ai_chatbot_1_portal/configuracion_agente`
      con ese token → 200 con JSON que incluye `system_prompt`, `fallback_message`
      y `flow_map`.
- [ ] El mismo POST con token erróneo → 401 (validación sigue activa).
- [ ] Replay del workflow `ycloud_create_lead_0_con_menu_whatsapp` con mensaje
      real de WhatsApp: el nodo no arroja 401 y la ejecución completa termina
      con el menú/texto entregado.
- [ ] POST a `https://integraia.lat/ai_chatbot_1_portal/configuracion_agente`
      → 200 (no-regresión prod).
- [ ] AGENTS.md contiene el ítem 5 del token (dónde vive + regla de
      coincidencia) y es idéntico en ambos clones (mismo hash tras push/pull).
- [ ] Git limpio en código: ningún archivo de `shared/`, compose ni JSON de
      n8n fue modificado.

## Decisions

- **Yes:** unificar al valor de n8n (prod ya lo usa; mismo n8n sirve ambos
  entornos) — cero cambios en n8n ni re-import de workflows.
- **Yes:** seteo vía UI de Ajustes — invalida caché de `ir.config_parameter`
  correctamente, sin restart ni SQL directo.
- **Yes:** doc en AGENTS.md — el coste del 401 fue no saber dónde vive el
  token; el bullet ataca la recurrencia.
- **Yes:** replay del flujo completo — el 401 solo se ve con el env real de
  n8n; curl no es suficiente porque el workflow hace el POST real.
- **Yes:** no inlinear el valor del token en el spec ni en AGENTS.md — el
  repo está en git; el valor canónico vive en el compose (fuera del repo).
- **No:** `CHATBOT_API_TOKEN_LEADS` (dos valores por entorno) — sobreingeniería
  para un único contenedor n8n que sirve ambos entornos.
- **No:** quitar la validación — endpoint público; regresión de seguridad.
- **No:** validar token en los demás endpoints — otro spec si llega.

## Risks

| Risk | Mitigation |
| --- | --- |
| Caché de `ir.config_parameter` stale si alguien usa SQL directo en vez de UI | Criterio de aceptación del 200 verifica el efecto real; el plan exige UI |
| El token de n8n rota en el futuro y vuelve a desalinearse | Bullet de AGENTS.md con regla "verificar coincidencia en todas las BDs servidas tras rotar" |
| Replay con pinData del manual trigger en vez de mensaje real de WhatsApp | Criterio explícito: mensaje real de WhatsApp (número de prueba acordado) |
| El valor de `CHATBOT_API_TOKEN` es visible en el compose y ahora en el spec | El spec no lo inlinea (referencia al compose); el compose ya lo contiene en texto plano |

## What is **not** in this spec

- Segundo token por entorno (`CHATBOT_API_TOKEN_LEADS`), rotación de token,
  validación en otros endpoints, cambios en n8n (JSON/compose), cambios de
  código en `shared/`. Cada uno, si llega, va en su propio spec.
