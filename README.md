# Central de Módulos Odoo

Sistema centralizado para gestionar módulos de la **OCA** y desarrollos **Extra** (propios o terceros) para versiones 18.0 y 19.0.

## Estructura de Directorios

```text
modulos_odoo/
├── shared/
│   ├── oca/           # Módulos de la Odoo Community Association
│   │   ├── 18.0/
│   │   └── 19.0/
│   └── extra/         # Módulos propios, personalizados o de terceros
│       ├── 18.0/
│       └── 19.0/
├── installer_vps/     # Kit de instalación para VPS nuevos (ver CAMBIOS.md)
├── 3_ver_modulos.sh        # Listar módulos en la central
├── mover_modulos_aqui.sh   # Mover módulos externos a la central
└── actualizar_modulos.sh   # Desplegar módulos en el VPS local (sin CI/CD)
```

## Regla crítica: lead vs prod

- Las **sesiones de código** corren solo en el clon `lead` (`/home/odoo/lead/modulos_odoo`).
- El clon `prod` (`/home/odoo/prod/modulos_odoo`) solo hace `git pull`. Nunca se edita código ahí.

## Uso: Addons Path Directo

Ya **no se utilizan enlaces simbólicos (`ln -s`)**. El contenedor Odoo lee los módulos por bind mounts en `addons_path`:

```ini
addons_path = /opt/odoo/odoo-core/addons,/opt/odoo/custom-addons/extra,/opt/odoo/custom-addons/oca,/opt/odoo/custom-addons/enterprise
```

Bind mounts (compose del stack odoo19-skeleton):
- `shared/extra/19.0` → `.../custom-addons/extra`
- `shared/oca/19.0` → `.../custom-addons/oca`

### Flujo de trabajo

1. **Edición**: edita el código directamente en `shared/extra/VERSION/MODULO` (clon `lead`).
2. **Prueba**: reinicia el contenedor (`docker restart odoo-19-web-leads`) y actualiza las apps.
3. **Entrega**: push a `main` → el pipeline CI/CD testea en staging y despliega en prod (VPS central).

En VPS cliente sin runner: `./actualizar_modulos.sh` (pull + upgrade + restart + health check).

## Scripts Disponibles

### `3_ver_modulos.sh`
Muestra un resumen de todos los módulos de la central, por categoría y versión. Detecta la raíz del repo automáticamente.

### `mover_modulos_aqui.sh`
Mueve módulos desde una carpeta temporal/proyecto hacia `shared/extra/19.0/`. Edita la variable `ORIGEN` y ejecuta:

```bash
./mover_modulos_aqui.sh
```

### `actualizar_modulos.sh`
Para VPS cliente sin CI/CD: `git pull` + upgrade de módulos en el contenedor de producción + restart + health check.

```bash
./actualizar_modulos.sh mod1 mod2        # módulos específicos
./actualizar_modulos.sh                  # todos los extra/19.0
```

## Reglas de Oro

1. **Nunca** mezcles módulos OCA con módulos Extra.
2. **Siempre** organiza por la subcarpeta de versión (`18.0` / `19.0`).
3. **Git**: el historial de cada módulo se gestiona de forma independiente dentro de su carpeta.

## Instalación en VPS nuevos

El kit completo está en `installer_vps/` (ver `installer_vps/README_AGENTE.md` y `installer_vps/CAMBIOS.md`).