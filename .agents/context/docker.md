# Docker Context — Rutas y Contenedores

## Dos clones del mismo repo

- `/home/odoo/lead/modulos_odoo` — **staging/pruebas**. Contenedor `odoo-19-web-leads`. Aquí se edita, se testea y se push.
- `/home/odoo/prod/modulos_odoo` — **producción**. Contenedor `odoo-19-web`. Solo `git pull`. **Jamás editar código aquí.**

## Contenedores

| Propósito | Contenedor | Puertos | BD |
|-----------|------------|---------|-----|
| PROD | `odoo-19-web` | 18069/18072 | `dbodoo19` (en `odoo-db19-n8n`) |
| STAGING | `odoo-19-web-leads` | 28069/28072 | `odoo-db19-leads` |

## Compose files

- PROD: `/home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/docker-compose.odoo.yml`
- STAGING: `~/lead/odoo19-skeleton/.../docker-compose.leads.yml`

## Addons path (en odoo.conf del contenedor)

`/opt/odoo/odoo-core/addons,/opt/odoo/custom-addons/extra,/opt/odoo/custom-addons/oca,/opt/odoo/custom-addons/enterprise`

Bind mounts:
- `shared/extra/19.0` → `.../extra`
- `shared/oca/19.0` → `.../oca`

## Docker gotchas

1. Tras editar `.py`, borrar `__pycache__` y reiniciar: `docker restart odoo-19-web`.
2. Upgrade CLI: `docker exec odoo-19-web odoo -d dbodoo19 -u <modulo> --stop-after-init`
3. `Registry.new(db, update_module=True)` **no carga** `addons_path` custom. Para forzar recarga de vistas: subir `version` en `__manifest__.py`, reiniciar y Upgradar desde UI.
4. Snippets Python vía `docker exec ... python3 -c "..."` siempre en **una sola línea**.
5. Token chatbot (n8n ↔ Odoo): verificar que coincida en TODAS las BDs (lead.integraia.lat → leads/dbodoo19; integraia.lat → prod/dbodoo19).

## Scripts con rutas desactualizadas

README y scripts referencian `/home/odoo/modulos_odoo/` (ruta vieja, **no existe**). Scripts `3_ver_modulos.sh` y `9_3_mover_destino_aqui.sh` tienen rutas hardcodeadas desactualizadas.
