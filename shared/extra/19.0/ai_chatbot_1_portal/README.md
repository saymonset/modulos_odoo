# ai_chatbot_1_portal

Módulo de portal para Chatbot de IA. Proporciona la interfaz y componentes de portal para el chatbot de Inteligencia Artificial (visualizar y gestionar mensajes, transcripción y análisis de textos).

## 🚀 Instalación y Despliegue en Odoo 19

Este módulo está desarrollado para **Odoo 19.0**. A diferencia de versiones anteriores, no requiere modificaciones manuales en la base de datos de PostgreSQL ni copiar directorios manualmente si está montado como volumen en docker.

> [!NOTE]
> El campo `birthdate` (Fecha de Nacimiento) y otros campos requeridos se definen nativamente en el modelo `ResPartner` (`models/partner.py`) y Odoo los creará automáticamente al instalar o actualizar el módulo. No es necesario ejecutar sentencias `ALTER TABLE` manuales.

### 1. Copiar o Asegurar el Módulo en la Central
Si se utiliza el entorno centralizado de Odoo 19:
El módulo debe estar ubicado en `/home/odoo/lead/modulos_odoo/shared/extra/19.0/ai_chatbot_1_portal` (que se monta automáticamente en el contenedor Odoo en la ruta `/opt/odoo/custom-addons/extra`).

### 2. Actualizar la Lista de Aplicaciones e Instalar
1. Inicia sesión en Odoo como Administrador con el Modo Desarrollador activo.
2. Ve a **Aplicaciones**.
3. Haz clic en **Actualizar lista de aplicaciones**.
4. Busca `ai_chatbot_1_portal` e instálalo.

---

## 🔗 Configuración de Integración con n8n (Webhooks)

Para integrar las peticiones de entrada desde n8n al chatbot en Odoo:

### Configurar Webhook en n8n
En el flujo de n8n, dentro del nodo HTTP Request `capturar_lead_odoo1`, actualiza la URL según corresponda:

*   **URL de Producción / Staging:**
    `https://<tu-dominio>/ai_chatbot_1_portal/capturar_lead_http`

> [!IMPORTANT]
> Asegúrate de usar la ruta final `/ai_chatbot_1_portal/capturar_lead_http` (con el sufijo `_http`), que es la ruta registrada por el controlador en `chatbot_3_crear_el_lead_finish_controller.py`.

---

## ⚙️ Reglas de Automatización en CRM

Para procesar de manera automática los leads entrantes creados desde WhatsApp:

1.  Ve a: **CRM** ➔ **Configuración** ➔ **Automatización** ➔ **Reglas de Automatización**.
2.  Crea una nueva regla:
    *   **Nombre:** "Procesar Leads WhatsApp Bot"
    *   **Condición:** Etiquetas ➔ contiene ➔ `WhatsApp Bot`
    *   **Acciones:** [Configura las acciones necesarias para tu flujo de ventas o asignación]