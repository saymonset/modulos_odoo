# SPEC 43 — Workspace n8n_json en lead: copia de trabajo con promoción manual a prod

> **Status:** Approved
> **Depends on:** —
> **Date:** 2026-09-15
> **Objective:** Crear `/home/odoo/lead/odoo19-skeleton/n8n_json/` como copia de trabajo de los exports de n8n (leer/modificar ahí durante el desarrollo), actualizando `/home/odoo/prod/odoo19-skeleton/n8n_json/` solo con cambios probados vía copia manual.

## Por qué existe esta spec

Hoy la regla (AGENTS.md:11-12, 18) obliga a escribir los exports n8n SIEMPRE en `/home/odoo/prod/odoo19-skeleton/n8n_json/` ("única fuente de verdad"), mezclando trabajo en curso con estado desplegado. Esta spec mueve el trabajo de desarrollo a lead (como `/home/odoo/lead/modulos_odoo`), dejando prod como registro versionado que solo cambia cuando hay certeza de que el cambio está probado.

## Scope

**In:**

1. **Copia inicial en disco** de `/home/odoo/prod/odoo19-skeleton/n8n_json/` → `/home/odoo/lead/odoo19-skeleton/n8n_json/` (estructura idéntica: `chatwoot/` 3 JSON + `ycloud/` 3 JSON). Sin commit inicial en la rama `lead`.
2. **Regla nueva de trabajo**: durante el desarrollo los exports se leen/escriben en lead `n8n_json`; los cambios de desarrollo se commitean en la rama `lead` de `odoo19-skeleton` a partir del primer cambio.
3. **Actualización de `AGENTS.md`** de `modulos_odoo` (líneas 11-12 y 18): el export de desarrollo va a lead; prod se actualiza solo con la promoción de cambios probados.
4. **Promoción manual documentada** lead → prod: `cp`/`rsync` de los archivos cambiados + commit en la rama `main` de prod + push. Solo tras E2E WhatsApp y suites en verde.
5. **Verificación** de que la copia lead es idéntica a prod (`diff -r`) y de que prod queda intacto tras un export de prueba en dev.

**Out of scope:**

- Automatización de la promoción (script `promote_n8n.sh` o git subtree): queda manual.
- Commit inicial de la copia en la rama `lead` (decisión: solo disco).
- Cambios al flujo del n8n vivo (`n8n-container`): se sigue exportando desde la misma instancia en vivo; solo cambia el destino del archivo.
- Actualizar specs históricas que citan la ruta prod (SPEC 31, 32, 34, 35, 36, 37): son registro; la nueva regla aplica a partir de esta spec.
- Actualizar `MANUAL_FUNCIONAL_DOCKER.md` ni `configure_new_client.sh` de prod (describen el despliegue prod).
- Migrar/editar los workflows ya desplegados.

## Modelo de datos

Sin estructuras nuevas. Copia de directorio:

```text
/home/odoo/lead/odoo19-skeleton/n8n_json/
├── chatwoot/
│   ├── chatbot-simple_1_subflow.json
│   ├── chatbot_create_lead_0_con_menu_whatsapp.json
│   └── chatwoot-Sistema RAG standar Lead.json
└── ycloud/
    ├── yclod-simple_1_subflow.json
    ├── ycloud-Sistema RAG standar Leads.json
    └── ycloud_create_lead_0_con_menu_whatsapp.json
```

## Plan de implementación

1. `diff -r` de baseline de prod `n8n_json` (evidencia del estado de partida).
2. Copiar `/home/odoo/prod/odoo19-skeleton/n8n_json/` → `/home/odoo/lead/odoo19-skeleton/n8n_json/` (sin commit en la rama `lead`).
3. `diff -r` lead vs prod → sin diferencias.
4. Actualizar `AGENTS.md` de `modulos_odoo`: nueva regla de exports n8n (lead durante desarrollo; promoción manual a prod solo probado).
5. Validar: un export de prueba en dev escribe en lead `n8n_json` y `git status` de prod queda limpio.

## Criterios de aceptación

- [ ] `/home/odoo/lead/odoo19-skeleton/n8n_json/` existe con `chatwoot/` y `ycloud/` idénticos a prod (`diff -r` sin diferencias).
- [ ] La copia lead no crea commit inicial en la rama `lead` (solo archivos en disco).
- [ ] `AGENTS.md` de modulos_odoo refleja: desarrollo → lead n8n_json; prod solo con cambios probados vía promoción manual.
- [ ] Un export de prueba en dev escribe en lead n8n_json y `/home/odoo/prod/odoo19-skeleton/n8n_json/` no cambia (`git status` de prod limpio).
- [ ] La promoción manual (cp + commit en main de prod) queda documentada en la spec y en AGENTS.md.

## Decisiones tomadas y descartadas

- **Tomado:** copia inicial solo en disco — **descartado** commit inicial en la rama `lead` (el usuario quiere versionar con el primer cambio real).
- **Tomado:** promoción manual vía `cp`/`rsync` + commit en `main` — **descartado** git subtree checkout y script automatizado.
- **Tomado:** una sola n8n en vivo (`n8n-container`); el export de desarrollo siempre sale de ahí y su destino es lead — **descartado** una instancia n8n de prod separada.
- **Tomado:** gatillo manual de promoción (E2E WhatsApp + suites en verde) ejecutado por el usuario — **descartado** checklist/script automatizado.
- **Tomado:** actualizar solo `AGENTS.md` — **descartado** reescribir specs históricas y `MANUAL_FUNCIONAL_DOCKER.md` (documentan el estado desplegado).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Divergencia silenciosa si alguien edita prod n8n_json directamente | Regla en AGENTS.md + verificación `diff -r` antes de cada promoción |
| Olvidar el commit en `main` tras copiar a prod | Paso explícito en la promoción documentada |
| Copia lead sin versionar al inicio puede perderse | Aceptado por decisión; el primer cambio de desarrollo la commitea |

## What is **not** in this spec

- Automatización de la promoción lead→prod.
- Commit inicial de la copia en la rama `lead`.
- Cambios al flujo del n8n vivo ni a los workflows desplegados.
- Actualización de specs históricas que citan la ruta prod.

Cada uno de esos, si llega, va en su propia spec.