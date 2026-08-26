# AGENTS.md — Central de Módulos Odoo

Monorepo que centraliza módulos de la OCA y desarrollos propios/terceros ("extra") para Odoo 18.0 y 19.0. Git: `git@github.com:saymonset/modulos_odoo.git`, rama `main`.

## Estructura!!!!

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
- `opencode.jsonc` apunta con ruta absoluta a `/home/odoo/prod/modulos_odoo/instructions.md` en este clon (y a `/home/odoo/lead/modulos_odoo/instructions.md` en el clon lead); `instructions.md` es idéntico en ambos.
- README y scripts referencian `/home/odoo/modulos_odoo/` (ruta vieja, **no existe**). Los scripts `3_ver_modulos.sh` y `9_3_mover_destino_aqui.sh` tienen rutas hardcodeadas desactualizadas.
- Docker: el compose real de PROD es `/home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/docker-compose.odoo.yml` (el `docker-compose.yaml` del mismo dir solo hace `extends` de este). Mapea `/home/odoo/prod/modulos_odoo/shared/...` a `/opt/odoo/custom-addons/{extra,oca}` dentro del contenedor. El clon lead tiene su propio compose `~/lead/odoo19-skeleton/.../docker-compose.leads.yml`.
- `addons_path` (en `odoo.conf` del contenedor): `/opt/odoo/odoo-core/addons,/opt/odoo/custom-addons/extra,/opt/odoo/custom-addons/oca,/opt/odoo/custom-addons/enterprise`. Bind mounts: `shared/extra/19.0`→`.../extra`, `shared/oca/19.0`→`.../oca`.

## Verificación / Tests

- La verificación real es contra el contenedor Odoo en ejecución. Contenedor/BD principales para este repo (PROD): `odoo-19-web` (puertos 18069/18072) + DB `dbodoo19` en `odoo-db19-n8n` (Postgres 15). El par `odoo-19-web-leads` (28069/28072) + `odoo-db19-leads` es el entorno de staging/pruebas.
- **Todos los módulos `extra/19.0` tienen tests** (patrón OCA: `TransactionCase` + `@tagged` + `setUpClass` sin tracking).

### Convenciones de testing (patrón OCA 19.0)

- `@tagged("-at_install", "post_install")` en toda clase de test.
- `setUpClass` con env sin tracking: `mail_create_nolog=True`, `mail_create_nosubscribe=True`, `mail_notrack=True`, `no_reset_password=True`, `tracking_disable=True`.
- `Form` API para ejercitar onchanges/wizards.
- `unittest.mock.patch` para HTTP externo (`requests.get`/`requests.post`); `HttpCase` para controllers propios.
- `@mute_logger("odoo.models.unlink")` para suprimir logs esperados.
- `tests/__init__.py` con imports explícitos (no wildcard). `common.py` importado primero si existe.
- Fixtures binarias en `tests/fixtures/`.
- `Command` (`from odoo import Command`) para m2m/o2m.
- `invalidate_recordset()` tras writes antes de assertar campos computed.
- Skeleton base: ver `bcv_rate_update_venezuela/tests/common.py` o `ai_chatbot_1_portal/tests/common.py`.

### Cómo correr tests

Tras modificar cualquier módulo de `extra/19.0`:

```bash
# 1. Limpiar cache de bytecode
find shared/extra/19.0/<module> -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true

# 2. Upgrade + tests en una sola pasada
docker exec odoo-19-web python3 /opt/odoo/odoo-core/odoo-bin -d dbodoo19 \
    -u <module> --test-enable --stop-after-init --log-level=test 2>&1 | tee /tmp/test_<module>.log

# Si el modulo tiene dependencias custom (ej. bcv_rate_update_venezuela),
# upgrade todo el chain: -u bcv_rate_update_venezuela,currency_rate_update_venezuela,currency_rate_update_base
```

Para `odoo-19-web-leads` (contenedor de pruebas/staging):
```bash
docker exec odoo-19-web-leads python3 /opt/odoo/odoo-core/odoo-bin -d dbodoo19 \
    -u <module> --test-enable --stop-after-init --log-level=test
```

### Regla obligatoria

Todo módulo de `extra/19.0` modificado debe pasar sus tests (`--test-enable`) antes de hacer `git push`.

## CI/CD (GitHub Actions)

- Workflow: `.github/workflows/deploy-prod.yml`. Trigger: `push` a `main`. Runner: **self-hosted** en el servidor (label `odoo-prod`), instalado como servicio en `/home/odoo/actions-runner`.
- Workflow secundario: `.github/workflows/opencode.yml` — corre opencode en GitHub-hosted runners al comentar `/oc` o `/opencode` en issues/PRs (usa `secrets.OPENCODE_API_KEY`).
- Pipeline serializado (`concurrency: deploy-prod`): `changes` (detecta módulos `extra/19.0` tocados y resuelve la cadena de deps custom en orden topológico) → `lint` (compileall, claves de manifest, anti-patrón `attrs=` en XML) → `test` (rsync de los módulos al clon **lead**, restart `odoo-19-web-leads`, `-u <cadena> --test-enable` contra staging `dbodoo19`; log como artifact) → `deploy` (`git fetch + merge --ff-only` en el clon **prod**, `-u <cadena>` sin tests en `odoo-19-web`, restart + health check :18069).
- Push sin cambios en `extra/19.0` → lint/test se skipean y deploy solo hace `git pull`.
- OJO: el deploy exige clon prod limpio (`merge --ff-only`); cambios locales sin commitear que colisionen harán fallar el job. Mantener el flujo lead→push→pull.
- Auth del runner (deploy): el job `deploy` hace `git fetch origin main` en el clon prod. El runner corre **sin ssh-agent**, así que el clon **prod** tiene `core.sshCommand` que usa el **agente persistente** de `odoo` con la llave personal `id_ed25519`:
  ```
  git -C /home/odoo/prod/modulos_odoo config core.sshCommand "ssh -o BatchMode=yes -o IdentityAgent=/home/odoo/.ssh/agent.sock"
  ```
  `IdentityAgent=` apunta al socket del agente persistente (que ya tiene `id_ed25519` cargada), de modo que git del runner autentica sin depender de su entorno. El agente persistente (`ssh-agent -a /home/odoo/.ssh/agent.sock -D`) es un proceso **detached** (`setsid`) que sobrevive al cierre de sesión pero **no a un reinicio del sistema**; tras un reinicio, ejecutar `/home/odoo/.local/bin/ssh-agent-recovery.sh` (pide la passphrase una vez). Nota: la deploy key `~/.ssh/id_ed25519_deploy` ya no se usa (GitHub la rechaza); la llave personal `id_ed25519` (con passphrase) también es la de los pushes interactivos desde lead.

## Workflow Docker (gotchas comprobados)

1. Tras editar `.py`, borra `__pycache__` del módulo y reinicia solo el web: `docker restart odoo-19-web`. Los `.pyc` cacheados pueden cargar bytecode viejo aunque el bind mount ya vea el archivo.
2. Upgrade CLI (más confiable que la UI): `docker exec odoo-19-web odoo -d dbodoo19 -u <modulo> --stop-after-init`. Para staging usar `odoo-19-web-leads`.
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
- Flujo: editar/probar en `lead` → `push` → `pull` en `prod`. Rama default: `main` en ambos clones.
