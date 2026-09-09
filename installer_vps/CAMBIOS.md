# CAMBIOS.md — Correcciones al kit `installer_vps/`

Revisión del instalador el 2026-09-09 contra el stack real en producción
(`/home/odoo/prod/odoo19-skeleton`). Todas las correcciones se validaron con
evidencia de los compose reales y del layout de `v19/` en el VPS.

## Correcciones críticas

### 1. `4_desplegar_stack.sh` — patch de compose obsoleto (rompía clientes nuevos)
**Problema:** los compose del repo están commiteados con URLs
`*.torteralevis.integraia.lat` y **secretos reales de torteralevis**
(`POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY_BASE` en hex). Los `sed`
viejos buscaban `n8n.integraia.lat`, `aristosoluciones` y un hex antiguo que ya
no existen → un cliente nuevo heredaba URLs y secretos del anterior.
**Fix:** `patch_compose` ahora es **agnóstico de valores** (regex):
- URLs: `<svc>.torteralevis.integraia.lat` → `<svc>.<CLIENTE_FQDN>` (más legacy).
- Secrets: cualquier hex de 32+ bytes en `POSTGRES_PASSWORD`, `REDIS_PASSWORD`,
  `SECRET_KEY_BASE` (formato `:` o `=`) → secretos generados para el cliente.

### 2. `4_desplegar_stack.sh` — ownerships de `v19/` incorrectos
**Problema:** `redis_data` y `chatwoot_pgdata` se chowneaban a `1001:1001` /
`1000:1000`, pero en el stack real son `999` (UID por defecto de las imágenes
redis/postgres). Además el compose monta `./v19/addons` y `./v19/backups` que el
kit no creaba.
**Fix:** chowns alineados con el stack real (`redis_data` 999:1001,
`chatwoot_pgdata` 999:1000) y creación de `v19/addons` + `v19/backups`.

### 3. `4_desplegar_stack.sh` — `odoo.conf` no idempotente
**Problema:** regeneraba `admin_passwd` aleatorio en cada ejecución (cambiaba el
master password en silencio).
**Fix:** `admin_passwd` persistido en `secrets/odoo_admin_passwd.txt`; si
`odoo.conf` ya existe, no se sobrescribe.

### 4. `3.5_instalar_nginx_certbot.sh` y `5_post_instalacion.sh` — prereqs faltantes
**Problema:** el paso 3.5 usa `dig` para verificar DNS y `curl`/`unzip`; el paso
5 usa `curl`/`unzip` para rclone. En un VPS fresco no están garantizados
(`unzip` no existía ni en este VPS) y el script crasheaba con error críptico.
**Fix:** instalación idempotente de `dig`, `curl`, `unzip` al inicio del paso 3.5
y de `curl`/`unzip` en la rama rclone del paso 5.

## Correcciones menores

5. **`1_preparar_ssh_git.sh` + config** — `GIT_NAME`/`GIT_EMAIL` ahora vienen de
   `config_instalacion.env` (añadidos al `.example`), no hardcodeados al email personal.
6. **`3.5_instalar_nginx_certbot.sh`** — el render del conf sale a
   `/tmp/nginx-render-<slug>.conf` (antes ensuciaba `ejemplos/` del repo).
7. **`0_crear_usuario_odoo.sh`** — typo "odoO" → "odoo".
8. **`4_desplegar_stack.sh`** — eliminados los `sed` muertos (`redis123`,
   `chatwoot123`, hex largo de chatwoot) que no matcheaban nada.
9. **`README_AGENTE.md`** — secciones 3-4 actualizadas: el repo commitea
   URLs/secretos del cliente de referencia (torteralevis) y el patch ahora es por
   regex, no por valores exactos.

## Validación realizada

- `bash -n` en los 9 scripts: OK.
- `patch_compose` probado contra copias de los compose reales simulando un
  cliente nuevo: 0 URLs viejas residuales, 0 secrets sin reemplazar.
- Ownerships de `v19/` contrastados contra el layout real en producción.

## Fuera de alcance

- No se tocó la copia en `prod` (`/home/odoo/prod/odoo19-skeleton/installer_vps`).
- Los compose del repo conservan URLs/secretos de torteralevis commiteados; el
  kit los reemplaza en cada instalación. Si se quiere, una tarea futura es
  sustituirlos por placeholders en el repo del skeleton.

## Decisiones de arquitectura multi-VPS

- **Runner CI/CD solo en el VPS central.** Dos runners con el label `odoo-prod`
  se repartirían los jobs al azar y un push podría desplegar en el VPS equivocado.
- **VPS cliente → deploy manual** con `actualizar_modulos.sh` (raíz de
  `modulos_odoo`): `git pull` + `-u` + restart + health check.
- **Hogar canónico del kit:** repo `odoo19-skeleton`. Un VPS nuevo lo baja de
  ahí (clon o tarball). Esta copia corregida en `modulos_odoo` es para review/PR;
  debe llegar a `odoo19-skeleton main` antes de dar de alta un VPS nuevo, o el
  VPS descargará el kit viejo con bugs. Ruta intermedia: generar el tarball con
  `empaquetar_instalador.sh` desde esta copia corregida.