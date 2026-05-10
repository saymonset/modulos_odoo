# 📦 Central de Módulos Odoo

Sistema centralizado para gestionar módulos de la **OCA** y desarrollos **Extra** (propios o terceros) para versiones 18.0 y 19.0.

## 📂 Estructura de Directorios

```text
/home/odoo/modulos_odoo/
├── shared/
│   ├── oca/           # Módulos de la Odoo Community Association
│   │   ├── 18.0/      # Módulos para Odoo 18
│   │   └── 19.0/      # Módulos para Odoo 19
│   └── extra/         # Módulos propios, personalizados o de terceros
│       ├── 18.0/
│       └── 19.0/
├── INVENTARIO.csv     # Registro histórico de módulos
└── Scripts/
    ├── 3_ver_modulos.sh           # Listar módulos en la central
    └── 9_3_mover_destino_aqui.sh  # Mover módulos externos a la central
```

---

## 🚀 Método de Uso: Addons Path Directo

Ya **no se utilizan enlaces simbólicos (`ln -s`)**. Odoo lee los módulos directamente desde esta ubicación centralizada.

### 1. Configuración de Odoo
Añade las rutas de la central a tu `odoo.conf` o variable de entorno `ADDONS_PATH`:

```ini
addons_path = 
    /home/odoo/odoo-from-13-to-18/odoo/addons,
    /home/odoo/modulos_odoo/shared/oca/19.0,
    /home/odoo/modulos_odoo/shared/extra/19.0
```

### 2. Flujo de Trabajo
1.  **Edición**: Edita el código directamente en `shared/extra/VERSION/MODULO`.
2.  **Prueba**: Reinicia el contenedor de Odoo (`docker restart odoo-web`).
3.  **Actualización**: Actualiza la lista de aplicaciones en la interfaz de Odoo.

---

## 🛠️ Scripts Disponibles

### 📊 `3_ver_modulos.sh`
Muestra un resumen de todos los módulos instalados en la central, divididos por categoría y versión.
```bash
./3_ver_modulos.sh
```

### 🚚 `9_3_mover_destino_aqui.sh`
Mueve módulos desde una carpeta temporal o de proyecto hacia `shared/extra/19.0/`.
1. Edita el script para definir la variable `origen`.
2. Ejecuta: `./9_3_mover_destino_aqui.sh`.

---

## ⚠️ Reglas de Oro
1.  **Nunca** mezcles módulos OCA con módulos Extra.
2.  **Siempre** organiza por la subcarpeta de versión (`18.0` / `19.0`).
3.  **Git**: El historial de cada módulo se gestiona de forma independiente dentro de su carpeta.

---

*Última actualización: Mayo 2026*