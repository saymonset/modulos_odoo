# 🚀 Guía de Implementación: Recursos Humanos (Odoo 18.0)

Esta guía detalla el proceso estructurado para la instalación y configuración de los módulos de Gestión de Personal en Odoo, asegurando una base sólida y funcional para la administración de RRHH.

---

## 🛠️ Requisitos Previos

Antes de comenzar la instalación de los módulos, es imperativo habilitar el entorno de administración avanzado.

> [!IMPORTANT]
> **Activar Modo Desarrollador:**
> 1. Ve a la aplicación **Ajustes**.
> 2. Desplázate hasta la sección **Herramientas de desarrollador**.
> 3. Haz clic en **Activar modo desarrollador**. Esto permitirá la visibilidad de configuraciones técnicas y módulos avanzados.

---

## 📅 Fase 1: Fundación y Gestión de Empleados

En esta etapa inicial, establecemos los pilares de la información del personal y la estructura organizativa.

### 📦 Módulos Base de Odoo
Instala estos módulos desde el menú **Aplicaciones** antes de proceder con las extensiones OCA:
- `hr` (Empleados)
- `hr_contract` (Contratos)
- `hr_holidays` (Ausencias)
- `account` (Contabilidad)

### 👤 Datos Maestros del Empleado
Instala los siguientes módulos en el orden sugerido para enriquecer el perfil del empleado:

| Módulo Técnico | Funcionalidad Principal |
| :--- | :--- |
| `hr_employee_firstname` | Separa nombres y apellidos en campos independientes. |
| `hr_employee_ssn` | Añade el campo oficial para el Número de Seguridad Social. |
| `hr_department_code` | Permite la codificación interna de departamentos. |
| `hr_employee_id` | Añade un campo de Identificación Única de Empleado. |
| `hr_employee_birthday_mail` | Automatiza el envío de felicitaciones por cumpleaños. |
| `hr_employee_medical_examination` | Registro y seguimiento de revisiones médicas. |
| `hr_employee_document` | Gestión de expedientes y documentos adjuntos al perfil. |

### 🎓 Estructura y Capacitación
Una vez consolidada la base de datos, añade capacidades de formación y recursos:

| Módulo Técnico | Funcionalidad Principal |
| :--- | :--- |
| `hr_course` | Gestión integral de cursos y capacitación interna. |
| `hr_job_category` | Clasificación avanzada y etiquetado de puestos de trabajo. |
| `hr_personal_equipment_request` | Sistema de solicitudes de equipo (IT, telefonía, etc.). |

---

## ⚖️ Fase 2: Gestión de Nóminas y Contratos

Configuración del motor financiero de los Recursos Humanos.

> [!TIP]
> Asegúrate de que `hr_contract` esté correctamente instalado antes de iniciar esta fase.

### 💰 Configuración de Nómina
El módulo central de esta fase es `payroll`.

- **Instalación:** Busca e instala el módulo `payroll`.
- **Efecto:** Odoo gestionará automáticamente la instalación de `hr_payroll` y todas sus dependencias necesarias.

### 📝 Extensiones de Contratos y Finanzas

| Módulo Técnico | Funcionalidad Principal |
| :--- | :--- |
| `hr_contract_renew` | Flujo de renovación automática basado en contratos previos. |
| `hr_contract_reference` | Añade identificadores de referencia personalizados a contratos. |
| `payroll_account` | Integración contable para la generación de asientos automáticos. |
| `payroll_contract_advantages` | Gestión de beneficios y compensaciones adicionales. |

---

## ⏱️ Fase 3: Control de Asistencia y Jornada

Implementación del registro de tiempos y análisis de productividad.

### 🏁 Módulo Oficial Obligatorio
Antes de añadir extensiones OCA, es estrictamente necesario instalar el módulo oficial:
👉 **Asistencias (`hr_attendance`)**

### 🧩 Extensiones OCA Disponibles
Optimiza el control de presencia con estas funcionalidades adicionales:

| Módulo Técnico | Funcionalidad Principal |
| :--- | :--- |
| `hr_attendance_reason` | Obliga a especificar un motivo en caso de correcciones manuales. |
| `hr_attendance_rfid` | Conectividad con lectores físicos de tarjetas y tags RFID. |
| `hr_attendance_calendar_view` | Visualización de registros de entrada/salida en formato calendario. |
| `hr_attendance_rest_time_included` | Configuración para incluir tiempos de descanso en la jornada. |
| `hr_attendance_report_theoretical_time` | Comparativa entre horas asistidas vs. jornada teórica. |

---

## ⚠️ Gestión de Dependencias

Odoo utiliza un sistema inteligente de resolución de dependencias.

> [!WARNING]
> Si durante la instalación de un módulo el sistema solicita instalar otros componentes adicionales, **acepta la sugerencia**. Esto garantiza la integridad de los datos y el funcionamiento correcto de las interconexiones entre aplicaciones.

**Recomendación:** Realiza una verificación funcional tras completar cada fase para asegurar que la configuración se adapta a las necesidades específicas de tu organización.
