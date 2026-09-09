# SPEC 26 — Instalación portable para VPS nuevos

> **Status:** Obsolete
> **Depends on:** —
> **Date:** 2026-09-09
> **Objective:** Que el repo funcione como plantilla: un VPS nuevo se instala con `install.sh` y un único archivo de config local, sin editar código ni el workflow.

> **Obsoleta:** el trabajo se redirigió al kit real `installer_vps/` (corregido el 2026-09-09,
> ver `installer_vps/CAMBIOS.md`). La parametrización de `deploy-prod.yml` se descartó:
> el pipeline corre solo en el VPS central y los VPS cliente despliegan con
> `actualizar_modulos.sh`.

## Scope

**In:**

- `vps.env.example` versionado + `vps.env` local (gitignored) con rutas de `lead`/`prod`, contenedores, BDs, puertos y health URLs. Solo versión 19.0.
- `install.sh`: clona el repo en `lead` y `prod`, genera `vps.env`, valida prerequisitos (docker, git ssh, claves ssh, agente ssh, runner registrado) con mensajes accionables. No automatiza secrets.
- `.github/workflows/deploy-prod.yml` parametrizado: cada job hace `source vps.env` → `$GITHUB_ENV`. Cero rutas absolutas en el YAML.
- Scripts raíz `3_ver_modulos.sh` y `9_3_mover_destino_aqui.sh` portables: derivan la raíz del repo con `git rev-parse --show-toplevel` en vez de rutas hardcodeadas.
- `README.md` corregido (estructura real, scripts en raíz, `addons_path` por contenedor) + `docs/INSTALACION_VPS.md` con checklist paso a paso.
- `opencode.jsonc`: `instructions.md` relativo (hoy apunta al clon prod).
- Contextos `.agents/context/docker.md` y `.agents/context/cicd.md` actualizados al esquema nuevo.

**Out of scope:**

- Infra para Odoo 18.0 (queda como vendored en `shared/oca/18.0` sin bootstrap ni pipeline).
- Automatizar creación de secrets (SSH keys, agente, registro del GitHub runner). Solo validación y documentación.
- Cambiar la topología lead/staging + prod dual ni el pipeline self-hosted.
- Tocar módulos de `shared/`.

## Data model

Este feature introduce **una nueva estructura de configuración**, no un modelo de datos:

```bash
# vps.env — config local por VPS (gitignored). Plantilla: vps.env.example
VPS_ROOT=/home/odoo
LEAD_REPO=${VPS_ROOT}/lead/modulos_odoo
PROD_REPO=${VPS_ROOT}/prod/modulos_odoo

LEAD_WEB=odoo-19-web-leads
PROD_WEB=odoo-19-web

LEAD_DB=odoo-db19-leads
PROD_DB=dbodoo19

LEAD_HEALTH=http://localhost:28069/web/health
PROD_HEALTH=http://localhost:18069/web/health

RUNNER_LABEL=odoo-prod
```

Convenciones:

- El único valor que varía por servidor es `VPS_ROOT` (y en multi-VPS, `RUNNER_LABEL`).
- `vps.env.example` se commitea con valores de ejemplo; cada VPS genera su `vps.env` local ignorado por git.
- Los scripts del repo raíz no leen `vps.env`; derivan su raíz de su propia ubicación.

## Implementation plan

1. Crear `vps.env.example` y añadir `vps.env` al `.gitignore`. El repo sigue funcional sin cambios.
2. Parametrizar `deploy-prod.yml`: cada job hace `source vps.env` al inicio y exporta los valores a `$GITHUB_ENV`, sustituyendo los hardcodeados. Verificación: push de prueba con el pipeline en verde.
3. Hacer portables `3_ver_modulos.sh` y `9_3_mover_destino_aqui.sh` usando `git rev-parse --show-toplevel`. Renombrar el segundo a `mover_modulos_aqui.sh` (origen editable como variable, ya es one-off).
4. Crear `install.sh` con modo `--dry-run` que valida prerequisitos sin tocar nada fuera del repo, y modo normal que clona lead+prod y genera `vps.env`.
5. Crear `docs/INSTALACION_VPS.md`, corregir `README.md`, ajustar `opencode.jsonc` y actualizar los contextos `.agents/context/docker.md` y `.agents/context/cicd.md`.

## Acceptance criteria

- [ ] `grep -rn "/home/odoo" 3_ver_modulos.sh mover_modulos_aqui.sh install.sh .github/workflows/deploy-prod.yml` no devuelve hits; `vps.env*` y docs solo lo mencionan como ejemplo.
- [ ] `./install.sh --dry-run` en este VPS pasa todos los checks de prerequisitos.
- [ ] Pipeline `deploy-prod` en verde leyendo los valores de `vps.env` (push de prueba en `main`).
- [ ] `git status` en el clon prod queda limpio tras el deploy (`vps.env` local no choca con `merge --ff-only`).
- [ ] Un clon fresco del repo en una ruta distinta funciona con solo crear su `vps.env`.

## Decisions

- **Sí:** `vps.env.example` versionado + `vps.env` local gitignored. El deploy exige clon prod limpio (`ff-only`); un config editado localmente en prod chocaría con `git pull`.
- **No:** un único `vps.env` versionado con valores de prod. Chocaría con `ff-only` en cada deploy.
- **Sí:** validar secrets en `install.sh`, no automatizarlos. Generar SSH/runner es operación sensible de cada servidor.
- **No:** automatizar la creación de SSH keys, agente ssh y registro del runner. Fuera de alcance; se documenta.
- **Sí:** solo infra 19.0. La infra actual es 19.0; 18.0 es vendored sin bootstrap.
- **No:** cubrir 18.0 y 19.0 en bootstrap/pipeline. Duplicaría la complejidad sin uso actual.
- **Sí:** replicar la topología lead+prod dual con runner en todo VPS nuevo.
- **Sí:** incluir `install.sh` como entregable.

## Risks

| Riesgo                                                             | Mitigación                                                                 |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| Dos VPS comparten repo y runner label `odoo-prod` duplicado         | `RUNNER_LABEL` en `vps.env`, único por servidor.                            |
| Health check depende de la red interna de docker                    | URLs de health configuradas por VPS en `vps.env`, documentadas en la guía.  |
| Cambiar el YAML rompe el deploy en este VPS si falta `vps.env`      | `install.sh --dry-run` valida prerequisitos; `vps.env` se genera localmente.|

## What is **not** in this spec

- Infra para Odoo 18.0 (otro spec si se necesita).
- Automatización de secrets (SSH, agente, runner).
- Cambios en la topología lead/prod ni en el pipeline self-hosted.
- Modificación de módulos en `shared/`.

Cada uno de esos, si llega, va en su propio spec.
