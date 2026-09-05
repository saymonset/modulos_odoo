# SPEC 12 — Cerrar el gap prod: upgrade del chatbot tras SPEC 10/11

> **Status:** Approved
> **Depends on:** SPEC 10, SPEC 11
> **Date:** 2026-09-05
> **Objective:** Que el endpoint `/ai_chatbot_1_portal/configuracion_agente` funcione en prod (`integraia.lat` / `dbodoo19`) aplicando el código ya testado de SPEC 10/11, sin escribir código nuevo.

## Por qué existe

Error real (2026-09-05, nodo n8n `Obtener_configuracion_agente` del workflow `ycloud_create_lead_0_con_menu_whatsapp.json`): HTTP 500 — `column chatbot_config.menu_generated_mode does not exist`. Los campos de SPEC 10 existen en el código que sirve el clon prod, pero el módulo nunca fue upgradeado en la BD de prod. El bot de prod está caído para todo mensaje entrante.

## Scope

**In:**

- Despliegue operativo a prod: `git pull` en `/home/odoo/prod/modulos_odoo` (clon limpio), upgrade `-u ai_chatbot_1_portal,ai_chatbot_0_core` en `odoo-19-web`, restart, health check `:18069`.
- Chequeo previo de sincronización del clon prod (`git status` limpio, `git fetch` + comparar con `main`) — si hay cambios locales que colisionen, se reportan antes de tocar nada.
- Post-deploy manual: regenerar menú del cliente afectado vía botón/sync (sin automatizar).
- Verificación: replay del nodo n8n → 200 con `flow_map`/`fallback_message` presentes; además, query SQL confirmando la columna.

**Out of scope:**

- Cualquier cambio de código, tests o n8n (el código ya pasó tests en staging).
- Regeneración automática de menús de otros clientes.

## Implementation plan

1. En lead: `git status` limpio; en prod: `git -C /home/odoo/prod/modulos_odoo status` y `git fetch origin main` + `rev-parse HEAD` vs `origin/main`. Si hay cambios locales colisionando → parar y reportar.
2. `git pull` (o `merge --ff-only`) en prod.
3. `docker exec odoo-19-web python3 /opt/odoo/odoo-core/odoo-bin -d dbodoo19 -u ai_chatbot_1_portal,ai_chatbot_0_core --stop-after-init` — log sin errores.
4. `docker restart odoo-19-web` + health check `:18069`.
5. Verificación: SQL `SELECT menu_generated_mode FROM chatbot_config LIMIT 1;` y replay del nodo n8n (200, JSON completo con `success: true`).
6. Post-deploy: regenerar el menú del cliente afectado (botón "Regenerar menú según rol"); confirmar `menu_generated_mode = 'ia'` (o warning accionable si IA cae, según SPEC 10).
7. Mensaje "Hola" al bot de prod → responde sin 500.

## Acceptance criteria

- [ ] Clon prod en `origin/main` y limpio antes del deploy.
- [ ] La columna `menu_generated_mode` existe en `chatbot_config` de `dbodoo19` (prod).
- [ ] Replay del nodo n8n `Obtener_configuracion_agente` → 200 con `success: true`.
- [ ] Health check `:18069` OK tras restart.
- [ ] "Hola" al bot de prod recibe respuesta normal (sin error 500 en n8n).
- [ ] Menú del cliente afectado regenerado (o warning accionable documentado).

## Decisions

- **Yes:** spec operativo, sin código — el gap es de deploy, no de software (el código ya pasó tests en staging).
- **Yes:** chequeo de git limpio en prod antes — el deploy `--ff-only` falla con cambios locales colisionando.
- **Yes:** verificación por replay n8n + SQL — reproduce el caso de fallo exacto.
- **No:** regeneración automática de menús post-upgrade — costo IA sorpresivo (mismo criterio que SPEC 10); se hace manual por cliente.

## Risks

| Risk | Mitigation |
| --- | --- |
| Cambios sin commitear en prod bloquean el pull | Chequeo en paso 1; si hay, reportar antes de decidir |
| El upgrade de `ai_chatbot_1_portal` arrastra dependencias no upgradeadas | La cadena relevante es corta (0_core + 1_portal); log del upgrade en el paso 3 |
| IA caída al regenerar el menú | El botón avisa con warning accionable (SPEC 10) — se reintenta cuando la key funcione |
