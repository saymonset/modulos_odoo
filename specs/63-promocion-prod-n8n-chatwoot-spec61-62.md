# SPEC 63 — Promoción a prod del export chatwoot (SPEC 61 + 62)

> **Estado:** Approved
> **Depende de:** SPEC 43 (promoción manual), SPEC 61, SPEC 62
> **Fecha:** 2026-09-19
> **Objetivo:** Promocionar a prod el export `n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json` (switch Telegram + propagación de plataforma), ya probado en el n8n vivo.

## Por qué existe esta spec

SPEC 61 y 62 están implementados y probados en vivo (conversación Telegram → lead correcto). El registro versionado de prod (`/home/odoo/prod/odoo19-skeleton/n8n_json/`) debe reflejar el estado desplegado según la promoción manual de SPEC 43.

## Scope

**In:**

1. Verificación final: suites de `ai_chatbot_1_portal` y `chatbot_cart` en verde (SPEC 43).
2. `cp` de lead → prod del archivo `chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json`.
3. Confirmar en prod que **solo** ese archivo cambió (`git status` + `git diff --stat`); ycloud intacto.
4. Commit en rama `main` de prod + push a `origin`.
5. Verificación post-promoción: `diff` lead vs prod sin diferencias en el archivo promocionado.

**Out of scope (para futuras promociones):**

- Archivos ycloud (`ycloud_create_lead...`, `yclod-simple_1_subflow`, `ycloud_carrito_subflow`) — pertenecen a otras specs aún sin verificación propia.
- Cambios en el n8n vivo (ya aplicados y probados por el usuario).
- Código Odoo (ya commiteado en `modulos_odoo`).

## Modelo de datos

Sin estructuras nuevas. Un archivo promocionado:

```text
n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json
```

## Plan de implementación

1. Correr suites (`ai_chatbot_1_portal`, `chatbot_cart`) en el contenedor lead → exit 0.
2. `cp` del archivo chatwoot: `/home/odoo/lead/odoo19-skeleton/n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json` → `/home/odoo/prod/odoo19-skeleton/n8n_json/chatwoot/`.
3. En prod: `git status` y `git diff --stat` → solo el archivo chatwoot modificado.
4. `git add` del archivo + commit en `main` (mensaje: promoción SPEC 61/62) + `git push origin main`.
5. `diff -r` lead vs prod → sin diferencias en el archivo promocionado.

## Criterios de aceptación

- [ ] Suites `ai_chatbot_1_portal` y `chatbot_cart` en verde (exit 0).
- [ ] `git status` de prod muestra solo `chatbot_create_lead_0_con_menu_whatsapp.json` modificado.
- [ ] `git log` de prod (`main`) tiene el commit de promoción.
- [ ] `diff` lead vs prod del archivo = sin diferencias.
- [ ] Ningún archivo ycloud cambia en prod.

## Decisiones tomadas y descartadas

- **Tomado:** solo el archivo chatwoot de SPEC 61/62 — **descartado** todo el diff (los 3 ycloud son de otras specs no verificadas; SPEC 43 exige promoción de cambios probados).
- **Tomado:** `cp` + commit + push ejecutados por el agente.
- **Tomado:** correr suites antes de promocionar como verificación (SPEC 43).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Push falla por red/permisos | Verificar `git status`/`git remote` y reintentar; el commit local queda registrado |
| Re-export futuro del n8n vivo re-importe con versionId distinto | La copia es literal (`cp`); el diff post-promoción lo detecta |

## What is **not** in this spec

- Archivos ycloud.
- Cambios de código Odoo.
- Import/probado en el n8n vivo (ya hecho).

Cada uno, si llega, va en su propia promoción/spec.