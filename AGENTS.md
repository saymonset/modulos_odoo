# AGENTS.md — Central de Módulos Odoo

Monorepo que centraliza módulos de la OCA y desarrollos propios/terceros ("extra") para Odoo 18.0 y 19.0. Git: `git@github.com:saymonset/modulos_odoo.git`, rama `main`.

## Estructura

- `shared/oca/{18.0,19.0}/<modulo>` — módulos OCA **vendored** (copiados, sin `.git` interno ni submodules). Se actualizan re-clonando de OCA; no editar salvo migración puntual.
- `shared/extra/{18.0,19.0}/<modulo>` — módulos propios/terceros. **Aquí está el desarrollo activo.**
- Reglas: nunca mezclar OCA con extra; siempre organizar por subcarpeta de versión (`18.0`/`19.0`).
- No desarrollar en staging dirs: `shared/oca/19.0.delete/` (OCA a eliminar) y `shared/oca/19.0/temp_oca_modules/`.

## Módulos propios clave (`extra/19.0`)

- `bcv_rate_update_venezuela` — tasa BCV + recálculo precios USD/VES/COP (moneda base de la compañía = VES).
- `currency_rate_update_base` / `currency_rate_update_venezuela` / `currency_rate_update_colombia` / `currency_rate_update_costa_rica` — proveedores de tasa; cadena de dependencias típica: `base` → `venezuela`/`colombia`/`costa_rica` → `bcv_rate_update_venezuela`.
- `pos_venezuela_dual_currency`, `product_import_xlsx`, `ai_chatbot_0_core` / `ai_chatbot_1_portal`, `whatsapp_cloud_integration`, `odoo_chatwoot_connector`, `mrp_bom_cost_update`.

## Rutas: OJO con clones y flujo staging→prod

- **Dos clones del mismo repo** (`git@github.com:saymonset/modulos_odoo.git`):
  - `/home/odoo/lead/modulos_odoo` — **staging/pruebas**. Docker monta este en el contenedor Odoo. Aquí se edita y se prueba; si OK, `git push`.
  - `/home/odoo/prod/modulos_odoo` — **producción**. Se actualiza solo con `git pull` desde el repo. **No editar directamente**: los cambios saltarían el flujo de prueba y, además, no se reflejarían en el contenedor (que monta `lead`).
- `opencode.jsonc` (en ambos clones) apunta con ruta absoluta a `/home/odoo/lead/modulos_odoo/instructions.md`; `instructions.md` es idéntico en ambos.
- README y scripts referencian `/home/odoo/modulos_odoo/` (ruta vieja, **no existe**). Los scripts `3_ver_modulos.sh` y `9_3_mover_destino_aqui.sh` tienen rutas hardcodeadas desactualizadas.
- Docker: el compose real es `~/lead/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/docker-compose.leads.yml` (el `docker-compose.yaml` del mismo dir solo hace `extends` de este). Mapea `/home/odoo/lead/modulos_odoo/shared/...` a `/opt/odoo/custom-addons/{extra,oca}` dentro del contenedor.
- `addons_path` (en `odoo.conf` del contenedor): `/opt/odoo/odoo-core/addons,/opt/odoo/custom-addons/extra,/opt/odoo/custom-addons/oca,/opt/odoo/custom-addons/enterprise`. Bind mounts: `shared/extra/19.0`→`.../extra`, `shared/oca/19.0`→`.../oca`.

## Verificación / Tests

- **No hay CI ni runner local**; no hay comando único para correr tests. Solo 4 módulos extra/19.0 tienen `tests/`: `product_import_xlsx`, `bcv_rate_update_venezuela`, `ai_chatbot_1_portal`, `odoo_chatwoot_connector`.
- La verificación real es contra el contenedor Odoo en ejecución. Contenedor/BD principales para este repo: `odoo-19-web-leads` (puertos 28069/28072) + DB `dbodoo19` en `odoo-db19-leads` (Postgres 15). Existe un contenedor separado `odoo-19-web` para otras BDs.

## Workflow Docker (gotchas comprobados)

1. Tras editar `.py`, borra `__pycache__` del módulo y reinicia solo el web: `docker restart odoo-19-web-leads`. Los `.pyc` cacheados pueden cargar bytecode viejo aunque el bind mount ya vea el archivo.
2. Upgrade CLI (más confiable que la UI): `docker exec odoo-19-web-leads odoo -d dbodoo19 -u <modulo> --stop-after-init`.
3. `Registry.new(db, update_module=True)` como one-liner **no carga** los `addons_path` custom → las vistas XML custom no se procesan. Para forzar recarga de vistas: subir `version` en `__manifest__.py` (ej. `19.0.1.0.5` → `19.0.1.0.6`), reiniciar contenedor y Upgradar desde la UI.
4. Snippets Python vía `docker exec ... python3 -c "..."` siempre en **una sola línea**; el shell conserva indentación multi-línea → `IndentationError`.

## Odoo 19 específico (lecciones verificadas en este repo)

- En vistas XML, `attrs` ya no existe: usa atributos directos `invisible="..."`/`required="..."`.
- QWeb: `hasclass('...')` en vez de `contains(@class, ...)`; `t-set` no se comparte entre bloques `<xpath>` (inline la búsqueda en cada uso, ej. `env.ref('base.USD', raise_if_not_found=False)`).
- Moneda COP no tiene xml_id garantizado: `env.ref('base.COP', raise_if_not_found=False) or env['res.currency'].sudo().search([('name','=','COP')], limit=1)`.
- Campos monetarios con `$` ambiguo (USD/COP): añadir etiqueta explícita `COP`.
- Toggles de `res.company` (ej. `cop_show_fields`): aplicar la misma puerta `invisible` en **todas** las ocurrencias, no solo en el footer del form.
- Overrides de métodos core (ej. `_prepare_account_move_line`): mantener la firma exacta del padre, sin `*args/**kwargs`.

## Convenciones

- `opencode.jsonc` carga `instructions.md` (respuestas cortas, código en inglés, comentarios en español solo si aportan, clean code/SOLID/DRY) y el skill `~/.agents/skills/odoo-19`. No repetir esas reglas aquí.

## Notas de git

- `session-ses_*.md` están en `.gitignore` (no commitear).
- Tags: usar anotados (`git tag -a <nombre> -m "..."`); `git push origin <tag>` es necesario — un `git push` normal no sube tags.
- Commits convencionales (`feat:`, `chore:`, `fix:`...). Branches remotas por cliente: `aristosoluciones_client`, `horebplus`, `lead`, `unisa`.
- Flujo: editar/probar en `lead` → `push` → `pull` en `prod`. Rama default: `main` en `lead`, `mainfix` en `prod` (== `origin/main`).
