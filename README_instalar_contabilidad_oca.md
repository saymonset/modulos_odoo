# 📊 Guía de Instalación: Contabilidad OCA (Odoo 19.0)

Esta guía detalla el proceso para descargar, organizar e instalar los módulos contables de la **OCA (Odoo Community Association)** necesarios para el ecosistema de Odoo 19.0.

---

## 🛠️ Paso 0: Descarga y Preparación de Módulos

Para mantener la "Central de Módulos" limpia, seguimos un proceso de **Clonar → Extraer → Limpiar**. 

### 1. Descargar Repositorios OCA
Ejecuta estos comandos para bajar los repositorios necesarios en una ubicación temporal o directamente si solo necesitas un módulo específico:

```bash
# 🔹 Herramientas financieras (usability)
git clone -b 19.0 --single-branch --depth 1 git@github.com:OCA/account-financial-tools.git /home/odoo/modulos_odoo/shared/oca/19.0/temp_tools

# 🔹 Motor de reportes (xlsx helpers)
git clone -b 19.0 --single-branch --depth 1 git@github.com:OCA/reporting-engine.git /home/odoo/modulos_odoo/shared/oca/19.0/temp_reporting

# 🔹 Reportes financieros (financial report)
git clone -b 19.0 --single-branch --depth 1 git@github.com:OCA/account-financial-reporting.git /home/odoo/modulos_odoo/shared/oca/19.0/temp_financial

# 🔹 Server UX (date ranges)
git clone -b 19.0 --single-branch --depth 1 git@github.com:OCA/server-ux.git /home/odoo/modulos_odoo/shared/oca/19.0/temp_ux
```

> [!IMPORTANT]
> **Limpieza Crítica**: Una vez clonado, debes mover las carpetas de los módulos que necesitas a `/home/odoo/modulos_odoo/shared/oca/19.0/` y **eliminar** la carpeta original que contiene el `.git` para evitar conflictos de sub-repositorios.

---

## 🚀 Paso 1: Orden de Instalación en Odoo

Es vital seguir este orden para evitar errores de dependencias:

1.  **`account_usability`**: Base para mejoras contables.
2.  **`report_xlsx`** y luego **`report_xlsx_helper`**: Necesarios para exportaciones Excel.
3.  **`date_range`**: Manejo de periodos de fechas.
4.  **`account_financial_report`**: Motor de informes financieros OCA.
5.  **`partner_statement`**: Estados de cuenta de clientes/proveedores.

---

## 📋 Paso 2: Configuración Post-Instalación

Una vez instalados los módulos, realiza los siguientes ajustes en la interfaz de Odoo:

### ✅ Activar Estados de Actividad
1. Ve a **Ajustes** → **Contabilidad**.
2. Busca la sección **Declaraciones de los socios**.
3. Marca la casilla **Activity Statements**.

### ✅ Configuración de Contactos
1. Ve a **Contactos** → **Configuración**.
2. Configura las **Cuentas por Pagar** según los requerimientos del cliente.

---

## ⚠️ Notas de Versión

> [!WARNING]
> **`account_asset_management`**: El módulo de Gestión de Activos Fijos actualmente solo está disponible de forma estable para **Odoo 18.0**. No intentes forzar su instalación en la 19.0 a menos que se haya completado su migración técnica.

---

## 💡 Tips Pro

*   **¿Módulo ya existe?**: Si al mover un módulo recibes un error de "Directorio no vacío", borra la versión antigua en el destino antes de mover la nueva para asegurar una instalación limpia.
*   **Actualizar Lista**: No olvides ejecutar `Actualizar lista de aplicaciones` en el modo desarrollador de Odoo tras mover los archivos.

---

> [!TIP]
> Puedes usar el script `./9_3_mover_destino_aqui.sh` para automatizar el movimiento de módulos desde la carpeta de descarga a la central.

---

*Desarrollado con ❤️ para el equipo de Odoo 19*
*Última actualización: Mayo 2026*