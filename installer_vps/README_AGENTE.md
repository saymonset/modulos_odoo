# README_AGENTE.md — Instalador de VPS para cliente (kit `installer_vps/`)

Guía para que un **agente de IA** aprovisione un VPS nuevo para un cliente de Odoo 19
(usuario, repos, Docker, stack `postiz-n8n-chatwoot-pgadmin-odoo_19` y nginx+SSL).

Este kit es **portable**: se lleva por `scp`/`rsync` a cualquier VPS
o se encuentra dentro del repo `odoo19-skeleton` (carpeta `installer_vps/`).
No depende de estar dentro de un clon del skeleton.

---

## 1. Prerrequisitos

| Requisito | Detalle |
|---|---|
| SO | Ubuntu 22.04 / 24.04 |
| VPS nuevo | Sin usuario odoo previo; puertos 80 y 443 libres |
| IP pública | La del VPS (los A records DNS deben apuntar a ella) |
| Datos del cliente | Nombre/marca, dominio, SMTP (se piden al usuario) |

Datos que debes **preguntar al usuario** antes de empezar:

1. Nombre/marca del cliente (slug): para torteralevis es `torteralevis`.
2. Dominio base: para torteralevis es `integraia.lat` → FQDN `torteralevis.integraia.lat`.
3. SMTP del cliente (host, puerto, usuario, password, from).
4. Confirmación de que puede agregar una llave SSH pública a GitHub.

> Todos estos datos ya vienen pre-llenados en `config_instalacion.env` para torteralevis
> (excepto `SMTP_PASSWORD`, que lo pide `instalar_todo.sh`).

---

## 2. Flujo de instalación (2 fases)

### FASE ROOT — solo la primera conexión (una vez)

Entra como root y ejecuta el **bootstrap**. Solo crea el usuario odoo con
superpoderes y deja el kit en su home. No instala nada más.

```bash
# (el tarball ya está extraído en esta máquina, ej. /root/installer)
sudo ./0_crear_usuario_odoo.sh
```

Qué hace:
- Crea grupos `docker`, `odoo`, `odoogroup`.
- Crea usuario `odoo` (uid 1001, grupos `adm,sudo,docker,odoogroup`).
  El grupo `sudo` da superpoderes **con password** (no NOPASSWD).
- **NO fija password**: lo defines tú con `sudo passwd odoo`.
- Copia el kit a `/home/odoo/installer_vps` y lo deja de odoo.

> **Root ya no se usa más.** El resto corre como odoo.

### FASE ODOO — instalación completa

```bash
sudo passwd odoo                    # (una vez) ponle el password a odoo
su - odoo                           # o: ssh odoo@<IP>
cd ~/installer_vps
./instalar_todo.sh                  # todo (pregunta por nginx)
# o:  ./instalar_todo.sh --skip-nginx   # si el DNS aún no está listo
```

`instalar_todo.sh` verifica que corre como odoo y que `sudo` funciona, y
encadena en orden:

| Paso | Script | Qué hace |
|---|---|---|
| 1 | `1_preparar_ssh_git.sh` | Llave ed25519, `~/.ssh/config` GitHub, `.gitconfig`, **pausa** para agregar la llave a GitHub, test `ssh -T` |
| 2 | `2_clonar_repos.sh` | Clona `modulos_odoo` y `odoo19-skeleton` en `~/prod/` + `bin/`, `dynamicconfig/`, `opencode/` |
| 3 | `3_instalar_docker.sh` | Docker engine + compose plugin + red externa `odoo_network_19` (sin borrar nada) |
| 3.5 | `3.5_instalar_nginx_certbot.sh` | nginx + certbot + snippets + render del conf del cliente + verificación DNS + emisión de certs SSL (opcional en el orquestador) |
| 4 | `4_desplegar_stack.sh` | Carpetas `v19/` con ownerships correctos, secrets auto-generados, `.env` del stack, `odoo.conf`, override, tokens nuevos |
| 5 | `5_post_instalacion.sh` | Crontab del monitor 6_5, rclone opcional, checklist final |

**Pausas obligatorias:**

- Tras el paso 1: el usuario debe agregar la llave pública impresa a GitHub y
  confirmar antes de continuar (`ssh -T git@github.com` debe responder `Hi ...!`).
- Antes del paso 3.5: el DNS debe apuntar al VPS **antes** de emitir certs.
  El script lo verifica con `dig`; si falla, aborta con mensaje claro.

**No ejecutar en el VPS nuevo:** el `0_install_docker_and_setup.sh` del stack
(borra `v19/`, `secrets/`, todo). El kit reemplaza esa función.

---

## 3. Configurar el `.env` del stack tras clonar odoo19-skeleton

Cuando `2_clonar_repos.sh` baja `odoo19-skeleton` de GitHub, el stack queda en:

```
~/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/
```

El paso `4_desplegar_stack.sh` **ya configura** `.env` y los compose por ti
usando `config_instalacion.env`. No lo hagas a mano. El modelo de URLs sigue el
patrón por cliente `$CLIENTE_SLUG.$DOMINIO_BASE` (ej. `torteralevis.integraia.lat`):

| Archivo del stack | Variables de URL a adaptar |
|---|---|
| `.env` (desde `env-example`) | `N8N_EDITOR_BASE_URL`, `CHATWOOT_FRONTEND_URL`, `CHATWOOT_RAILS_HOST`, `ASSET_HOST`, `ACTIVE_STORAGE_HOST`, `RAILS_STORAGE_HOST`, `MAIN_URL`, `FRONTEND_URL`, variables SMTP (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `ACTION_MAILER_*`, `MAILER_SENDER_EMAIL`) y `BACKUP_NOTIFY_TO` |
| `docker-compose.chatwoot.yml` | `RAILS_HOST`, `FRONTEND_URL`, `APP_HOST`, `ASSET_HOST`, `ACTIVE_STORAGE_HOST`, `RAILS_STORAGE_HOST`, `RAILS_ASSET_HOST`, `ACTIVE_STORAGE_URL_HOST` |
| `docker-compose.n8n.yml` | `N8N_HOST`, `WEBHOOK_URL`, `N8N_EDITOR_BASE_URL`, `CHATBOT_API_TOKEN` (token nuevo) |
| `docker-compose.postiz.yml` | `MAIN_URL`, `FRONTEND_URL`, `NEXT_PUBLIC_BACKEND_URL` |

> Los compose del repo están **commiteados con URLs y secretos del cliente de
> referencia** (actualmente `torteralevis`). El paso 4 los reemplaza con un patch
> **agnóstico de valores** (regex por patrón de URL y por longitud de hex de los
> secretos), así que un cliente nuevo no hereda URLs ni secretos del anterior.

Referencia completa: `MANUAL-NGINX-INSTALACION.md` (paso 1) del skeleton.

---

## 4. Compatibilidad de los scripts existentes del stack

Los scripts del stack (`1_despliegue_*`, `2_despliegue_*`, `4_start-all.sh`,
`5_res_start-all.sh`, `6_status_all_services.sh`, `7_logs_see_all_services.sh`,
`9_1_backup_sistema_completo.sh`, `9_2_restore_sistema_ultimo.sh`, etc.)
**funcionan igual en el VPS nuevo** porque el kit replica las condiciones exactas:

| Dependencia | Cómo la cubre el kit |
|---|---|
| Rutas relativas (`./v19/`, `./secrets/`, `./backup/backup.sh`) | Mismo layout de carpetas |
| Rutas absolutas (`/home/odoo/prod/modulos_odoo/shared/{extra,oca}/19.0`) | Se crean en la misma ruta en el VPS nuevo |
| Red docker `odoo_network_19` (external) | La crea `3_instalar_docker.sh` con el mismo nombre |
| Container names (`odoo-db19-n8n`, `odoo-19-web`, ...) y DB `dbodoo19` | Idénticos en compose |
| Secrets en `./secrets/*.txt` | Los genera `4_desplegar_stack.sh` |

**Excepciones / adaptaciones puntuales:**

- Los compose vienen **commiteados con URLs y secretos reales del cliente de
  referencia** (torteralevis). El paso 4 los reemplaza con regex agnóstico de
  valores: URLs `<svc>.torteralevis.integraia.lat` → `<svc>.<CLIENTE_FQDN>` y
  secrets hex (`POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `SECRET_KEY_BASE`) → los
  generados para el cliente. Genera además `CHATBOT_API_TOKEN` nuevo. El token
  debe coincidir con Odoo (`ir.config_parameter`) durante el onboarding del cliente
  (ver `tools/TUTORIAL_NUEVO_CLIENTE.md`).
- `6_6_monitor_cliente_testusuario.sh` es un monitor **específico del cliente actual**.
  Para un cliente nuevo no se instala en crontab (el paso 5 solo usa `6_5`).
- Backups remotos R2 (`9_1_backup_sistema_completo.sh`): requiere credenciales R2
  + rclone config en el VPS nuevo. Se configuran manualmente (ver sección 6).
- `configure_new_client.sh` sigue disponible para reconfigurar URLs/tokens después
  (es interactivo: pregunta el dominio).

---

## 5. Despliegue del stack (después del paso 4)

Desde `~/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/`:

```bash
cd ~/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19
./1_despliegue_reconstruye_imagen_servicios_adicionales.sh   # construye imagen odoo-pers:19
./2_despliegue_servicios_adicionales.sh                      # sube servicios adicionales
./4_start-all.sh                                             # docker compose up -d
./6_status_all_services.sh                                   # estado
```

> El kit no duplica estos scripts: los usa tal cual.

---

## 6. Pasos manuales que quedan (documentados, no automatizables)

1. **Password de odoo** (tras el bootstrap): `sudo passwd odoo`.
2. **Agregar la llave SSH a GitHub** (tras paso 1).
3. **DNS** (Namecheap): A records `@`, `chatwoot`, `n8n`, `postiz`, `pgadmin`,
   `temporal` (y `lead` si aplica) → IP del VPS. Ver `MANUAL-NGINX-INSTALACION.md` paso 0.
4. **R2 backups**: llenar `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ACCOUNT_ID`,
   `R2_CRYPT_PASSWORD`, `R2_CRYPT_PASSWORD2` en `.env` + regenerar `~/.config/rclone/rclone.conf`
   con `rclone obscure "<valor del .env>"`.
5. **Onboarding del chatbot** del cliente: `tools/TUTORIAL_NUEVO_CLIENTE.md`.

## 6.5 CI/CD y despliegue de módulos (multi-VPS)

- El pipeline de `modulos_odoo` (`.github/workflows/deploy-prod.yml`) corre **solo
  en el VPS central** (runner self-hosted con label `odoo-prod`).
- **No registrar el runner en VPS cliente**: dos runners con el mismo label se
  repartirían los jobs al azar y un push podría desplegar en el VPS equivocado.
- En un VPS cliente, el despliegue de módulos es manual con el script del propio
  repo `modulos_odoo` (se clona junto con el skeleton):

  ```bash
  cd ~/prod/modulos_odoo
  ./actualizar_modulos.sh                # todos los extra/19.0
  ./actualizar_modulos.sh mod1 mod2      # solo los indicados
  ```

  Hace `git pull --ff-only`, `-u` de los módulos en el contenedor de producción,
  restart y health check (convenciones del kit: `odoo-19-web`, `dbodoo19`, `:18069`).

> **Importante:** este kit `installer_vps/` es portable y se empaqueta por sí solo.
> Su hogar canónico es el repo `odoo19-skeleton`. Un VPS nuevo lo recibe del tarball
> (`empaquetar_instalador.sh`) o del clon del skeleton. Antes de dar de alta un VPS,
> asegúrate de que la versión corregida del kit esté publicada en `odoo19-skeleton main`.

---

## 7. Empaquetado portable

Para generar el tarball listo para llevar a otro VPS:

```bash
cd ~/odoo19-skeleton   # o donde esté el repo
./installer_vps/empaquetar_instalador.sh
# genera: installer_vps_torteralevis.tar.gz
```

Llevarlo al VPS nuevo:

```bash
scp installer_vps_torteralevis.tar.gz root@<IP_VPS>:/tmp/
ssh root@<IP_VPS> "mkdir -p /root/installer && tar -xzf /tmp/installer_vps_torteralevis.tar.gz -C /root/installer"
ssh root@<IP_VPS>
cd /root/installer
sudo ./0_crear_usuario_odoo.sh      # bootstrap (root, una vez)
# luego: passwd odoo -> su - odoo -> cd ~/installer_vps -> ./instalar_todo.sh
```