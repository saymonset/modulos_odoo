# Manual de Configuración y Mapeo Paso a Paso
### (Guía para Consultores Funcionales y Administradores)

Este manual contiene las instrucciones detalladas para instalar, configurar y mantener la integración de **Chatwoot ↔ Odoo 19** para futuros clientes y departamentos.

---

## 1. Obtención de Parámetros de Chatwoot

Para conectar Odoo con Chatwoot, necesitas obtener y configurar dos credenciales clave:

### A. La URL Base de Chatwoot (`base_url`)
*   **Recomendado (Conexión Interna de Docker):** Si Odoo y Chatwoot corren en el mismo servidor web y están bajo la misma red virtual de Docker, usa el nombre del servicio de la base: `http://chatwoot-app:3000`.
    *   *¿Por qué?* Es más segura, mucho más rápida y no se ve afectada si expira el certificado SSL de la web o si hay microcortes de internet.
*   **Conexión Externa:** Si los sistemas están en servidores físicos independientes, usa el dominio público: `https://chatwoot.tu-dominio.com`.

### B. El Token de Acceso del Agente (`api_access_token`)
El token le da permiso a Odoo para asignar chats y enviar mensajes automáticos. Debes obtenerlo de la interfaz gráfica de Chatwoot:
1. Inicia sesión en Chatwoot (`https://chatwoot.aristosoluciones.integraia.lat/`).
2. En la esquina inferior izquierda, haz clic en tu avatar o nombre y selecciona **Ajustes de perfil** (Profile Settings).
3. Desplázate hasta el final de la página de perfil.
4. En la sección **Token de acceso** (Access Token), haz clic en **Copiar**.
   *(Ejemplo de token: `c7fBLQfMkLwGwtbV97iDrKNR`)*

> [!IMPORTANT]
> El token que se copia del perfil en la interfaz está encriptado en la base de datos de Chatwoot por seguridad. Siempre debes copiar el token **desde la pantalla de perfil de la aplicación**, no intentes sacarlo directamente de las tablas SQL ya que allí se guarda hasheado.

---

## 2. Configuración en Odoo

Una vez que tengas la URL y el Token, agrégalos a los parámetros generales de Odoo:

1. Ve a **Odoo → Ajustes**.
2. Busca la sección **Chatwoot Integration** (al final de la página).
3. Introduce los valores correspondientes:
   *   **Chatwoot base URL:** `http://chatwoot-app:3000` *(o tu URL externa)*
   *   **Chatwoot API token:** `TU_TOKEN_DE_ACCESO_COPIADO`
   *   **Chatwoot timeout (s):** `3`
4. Haz clic en **Guardar**.

*(Si necesitas configurarlo directo en base de datos por motivos de automatización, los nombres de los parámetros del sistema son `chatwoot.base_url` y `chatwoot.api_access_token` en la tabla `ir_config_parameter`).*

---

## 3. Mapeo de Agentes y Equipos (Chatwoot Mappings)

Los mappings le indican a Odoo a qué bandeja de Chatwoot y a qué vendedor debe asignar cada consulta.

Ve a **Ajustes → Chatwoot Mappings** (o a la lista correspondiente) y crea un registro por cada flujo:

*   **Name:** Nombre descriptivo para reconocer el mapping (ej: `aristosolucionesapp`).
*   **Flujo (opcional):** Elige el flujo de chatbot correspondiente (ej: `flujo_agendamiento_directo`).
*   **Equipo CRM:** El equipo de ventas en Odoo que recibirá el Lead (ej: `Grupo Ventas`).
*   **Equipo Asignado:** ⚠️ **Este valor técnico debe coincidir exactamente con el código que envía n8n.** Se elige de la lista desplegable (ej: `Agendamiento Directo`).
*   **Chatwoot inbox id:** ID de la bandeja de Chatwoot. *(Puedes encontrarlo en la barra de direcciones de tu navegador al entrar a la bandeja en Chatwoot, ej: `/inbox/1` -> ID = 1)*.
*   **Chatwoot agent id (User id):** ID numérico del agente en Chatwoot (ej: `1`).
*   **Chatwoot agent email:** Email del agente en Chatwoot (ej: `saymon_set@hotmail.com`).
*   **Intentar asignar a agente primero:** Si está marcado, Odoo intentará asignarle la conversación al vendedor. Si falla, el chat se quedará en la bandeja del inbox sin asignar como respaldo.
*   **Tags (CSV):** Etiquetas separadas por comas que se aplicarán automáticamente a la conversación en Chatwoot (ej: `aristosolucionesapp,WhatsApp`).
*   **Active:** Debe estar marcado para que el mapping sea utilizado por el sistema.

---

## 4. Vincular el Vendedor en Odoo

Para que la asignación sea completa y se envíen las notificaciones:
1. Asegúrate de crear un usuario en Odoo cuyo **login / email** coincida exactamente con el correo del agente en Chatwoot (ej: `saymon_set@hotmail.com`).
2. Agrega a este usuario como miembro del **Equipo CRM** correspondiente (ej: `Grupo Ventas`).
3. De esta forma, Odoo le asignará el Lead en el CRM, creará la notificación y le mandará el correo electrónico automáticamente.

---

## 5. Tabla de Equivalencias de Equipos y Flujos

| Código Técnico (`equipo_asignado`) | Nombre del Flujo (`name_flow`) | Equipo CRM en Odoo (`crm.team`) |
| :--- | :--- | :--- |
| **`Agendamiento_Directo`** | `flujo_agendamiento_directo` | **Grupo Informativo** |
| **`Agendamiento_Precios`** | `flujo_agendamiento_precios` | **Grupo Informativo** |
| **`Agendamiento_Servicios`** | `flujo_agendamiento_servicios` | **Grupo Ventas** |
| **`Agendamiento_Otra_Consulta`** | `flujo_agendamiento_otra_consulta`| **Grupo Citas** |
| **`Ventas_UNISA`** | `flujo_ventas_unisa` | **Grupo Ventas** |
| **`CITAS_MP`** | `flujo_citas_medios_propios` | **Grupo Citas** |
| **`CITAS_SEGUROS`** | `flujo_citas_seguro` | **Grupo Citas** |
| **`RESULTADOS_LAB`** | `flujo_resultados_laboratorio` | **Grupo Laboratorio** |
| **`RESULTADOS_IMAGENES`**| `flujo_resultados_imagenes` | **Grupo Imagenología** |

---

## 6. Guía para agregar un nuevo flujo comercial en el futuro
*(Ejemplo: Agregar departamento de "Soporte Técnico" con el código `Soporte_Tecnico`)*

1.  **Código en Odoo (chatwoot_mapping.py):**
    Añade la opción técnica al campo de selección en el código del módulo [chatwoot_mapping.py](file:///home/odoo/prod/modulos_odoo/shared/extra/19.0/odoo_chatwoot_connector/models/chatwoot_mapping.py#L9-L29):
    ```python
    ('Soporte_Tecnico', 'Soporte Técnico'),
    ```
2.  **Configurar Correspondencia (chatbot_flujo.py):**
    En [chatbot_flujo.py](file:///home/odoo/prod/modulos_odoo/shared/extra/19.0/ai_chatbot_1_portal/models/chatbot_flujo.py#L408-L439), añade tu código en `_get_mapeo_equipo_grupo` y `_get_mapeo_equipo_descripcion` para vincularlo al equipo de Odoo deseado:
    ```python
    "Soporte_Tecnico": "Grupo Soporte",
    "flujo_soporte_tecnico": "Grupo Soporte",
    ```
3.  **Crear el Mapping en Odoo:**
    Crea el mapping en **Ajustes → Chatwoot Mappings** relacionando el código `Soporte Técnico` con el agente y bandeja de soporte correspondientes en Chatwoot.
4.  **Configurar Vendedor en Odoo:**
    Crea el usuario en Odoo con el mismo correo del agente de soporte y agrégalo al Equipo CRM `Grupo Soporte`.
5.  **Entrenar a la IA (n8n):**
    Modifica el archivo de prompt del chatbot [PROMPT_ARISTOSOLUCIONES_UV.txt](file:///home/odoo/prod/modulos_odoo/shared/extra/19.0/odoo_chatwoot_connector/PROMPT_ARISTOSOLUCIONES_UV.txt) para que el bot de n8n clasifique la consulta como `"equipo_asignado": "Soporte_Tecnico"` cuando corresponda.

---

## 7. Solución de Problemas y Diagnóstico

### ❌ Error `missing_configuration_or_ids`
*   **Causa:** Falta configurar el URL o el Token de Chatwoot en Ajustes de Odoo.
*   **Solución:** Ve a Ajustes en Odoo y configúralos. Si lo hiciste por base de datos, debes reiniciar el contenedor con `docker restart odoo-19-web` para forzar a Odoo a refrescar la caché de parámetros.

### ❌ El chat se asigna al inbox pero no al agente
*   **Causa:** El ID o el email del agente configurados en el mapping de Odoo no coinciden con los datos reales en Chatwoot.
*   **Solución:** Revisa que el ID y el correo electrónico del agente sean idénticos en ambos sistemas, y verifica que el agente sea miembro de la bandeja de entrada configurada.
