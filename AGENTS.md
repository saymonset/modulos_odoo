# AGENTS.md — Central de Módulos Odoo

Monorepo OCA + extra para Odoo 18.0 y 19.0. Git: `git@github.com:saymonset/modulos_odoo.git`, rama `main`.

## Estructura

- `shared/oca/{18.0,19.0}/<modulo>` — módulos OCA vendored. No editar salvo migración puntual.
- `shared/extra/{18.0,19.0}/<modulo>` — módulos propios/terceros. **Desarrollo activo aquí.**
- Nunca mezclar OCA con extra; organizar por subcarpeta de versión.
- **Exports de workflows n8n (SPEC 43)**: durante el desarrollo se leen/escriben SIEMPRE en
  `/home/odoo/lead/odoo19-skeleton/n8n_json/` (subcarpeta por proveedor, ej. `ycloud/`),
  y los cambios se commitean en la rama `lead` de `odoo19-skeleton`. Nunca crear `n8n_json/`
  dentro de este repo.
- `/home/odoo/prod/odoo19-skeleton/n8n_json/` es el **registro versionado de lo desplegado**:
  solo se actualiza por **promoción manual** de cambios ya probados (E2E WhatsApp + suites en
  verde) vía `cp`/`rsync` + commit en la rama `main` de prod + push.

## Regla crítica: lead vs prod

- **Sesiones de código**: correr opencode **solo** en `/home/odoo/lead/modulos_odoo`.
- Si el working directory es `/home/odoo/prod/modulos_odoo`, detenerse y pedir al usuario mover la sesión a lead. Solo hotfix de emergencia confirmado en prod.
- **Excepción**: los exports de workflows n8n se escriben en
  `/home/odoo/lead/odoo19-skeleton/n8n_json/` (ver Estructura) aunque la sesión de código corra en
  otro working dir; prod (`/home/odoo/prod/odoo19-skeleton/n8n_json/`) solo se toca en la
  promoción manual de cambios probados.
- `opencode.jsonc` apunta a `instructions.md` (clean code, respuestas cortas).

## Contextos disponibles (carga bajo demanda)

| Contexto | Cuándo leer |
|----------|-------------|
| `.agents/context/testing.md` | Escribir o ejecutar tests |
| `.agents/context/cicd.md` | Modificar pipeline, deploy, runner |
| `.agents/context/docker.md` | Rutas, contenedores, bind mounts, gotchas |
| `.agents/context/odoo19.md` | Particularidades Odoo 19 (attrs, QWeb, monedas) |

## Skills

| Skill | Cuándo usar |
|-------|-------------|
| `odoo-19` | Desarrollo Python/XML Odoo 19 |
| `odoo-development` | Desarrollo general Odoo (fuera de v19) |
| `spec` / `spec-impl` | Feature grande: `/spec` → approve → `/spec-impl` |
| `spec-verify` | Verificar un spec: `/spec-verify NN` (agente + comando en `opencode.jsonc`, prompt en `.agents/spec-verify.prompt.md`) |
| `context7-mcp` | Docs de librerías externas |

## Módulos propios clave (`extra/19.0`)

`bcv_rate_update_venezuela`, `currency_rate_update_base`/`venezuela`/`colombia`/`costa_rica`, `pos_venezuela_dual_currency`, `product_import_xlsx`, `ai_chatbot_0_core`/`ai_chatbot_1_portal`, `whatsapp_cloud_integration`, `odoo_chatwoot_connector`, `mrp_bom_cost_update`.
