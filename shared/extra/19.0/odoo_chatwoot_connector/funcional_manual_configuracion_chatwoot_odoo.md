# Guía Definitiva de Mapeo y Configuración: Chatwoot ↔ n8n ↔ Odoo
### (Manual Detallado "Para Principiantes")

Este documento explica de forma sencilla y visual cómo interactúan los tres sistemas (**Chatwoot, n8n y Odoo**) para clasificar y asignar las conversaciones y los leads en el CRM, y cómo agregar nuevos flujos en el futuro.

---

## 1. El Glosario: ¿Quién es quién en este laberinto?

Para entender el sistema, primero debemos entender qué es cada concepto en cada plataforma:

*   **`equipo_asignado` (n8n / AI Bot):** Es la etiqueta técnica que la Inteligencia Artificial (en n8n) le pone al mensaje del cliente tras analizar lo que este quiere. Es el "puente" o "código" común que entienden todos los sistemas (ej: `Agendamiento_Directo`).
*   **`crm.team` (Odoo - Equipos de Ventas/Grupos):** Son los equipos reales en Odoo a los que se asignan las oportunidades (leads). Por ejemplo, el equipo de ventas, el equipo de citas, etc.
*   **`chatbot.flujo` (Odoo - Flujos):** La secuencia de preguntas o pasos predefinidos que sigue el bot para recopilar los datos del cliente (nombre, teléfono, cédula).
*   **`chatwoot.mapping` (Odoo - Mapeo):** Es la tabla en Odoo que dice: *"Si n8n clasificó la consulta con el código X, asígnale este chat al Agente Y y en la Bandeja Z de Chatwoot"*.

---

## 2. La Tabla de Equivalencias (La "Verdad Absoluta")

Aquí puedes ver cómo se traduce cada código enviado por n8n a los nombres de equipos de Odoo:

| 1. Código n8n (`equipo_asignado`) | 2. Nombre del Flujo (`name_flow`) | 3. Equipo CRM en Odoo (`crm.team`) | 4. Propósito / Área |
| :--- | :--- | :--- | :--- |
| **`Agendamiento_Directo`** | `flujo_agendamiento_directo` | **Grupo Informativo** | Consultas directas de información general. |
| **`Agendamiento_Precios`** | `flujo_agendamiento_precios` | **Grupo Informativo** | Información sobre tienda virtual y planes de precios. |
| **`Agendamiento_Servicios`** | `flujo_agendamiento_servicios` | **Grupo Ventas** | Información sobre agentes de Inteligencia Artificial. |
| **`Agendamiento_Otra_Consulta`** | `flujo_agendamiento_otra_consulta`| **Grupo Citas** | Consultas técnicas, desarrollo y consultorías a medida. |
| **`Ventas_UNISA`** | `flujo_ventas_unisa` | **Grupo Ventas** | Ventas generales, hosting y dominios. |
| **`CITAS_MP`** | `flujo_citas_medios_propios` | **Grupo Citas** | Citas solicitadas por medios propios (sin seguro). |
| **`CITAS_SEGUROS`** | `flujo_citas_seguro` | **Grupo Citas** | Citas solicitadas a través de seguros médicos. |
| **`RESULTADOS_LAB`** | `flujo_resultados_laboratorio` | **Grupo Laboratorio** | Solicitud y entrega de resultados de laboratorio. |
| **`RESULTADOS_IMAGENES`**| `flujo_resultados_imagenes` | **Grupo Imagenología** | Solicitud y entrega de resultados de rayos X, eco, etc. |

---

## 3. El Camino de un Mensaje (Paso a Paso)

¿Qué pasa cuando un cliente escribe por WhatsApp?

```
[Cliente escribe por WhatsApp]
        │
        ▼
1. Chatwoot recibe la conversación.
        │
        ▼
2. n8n ejecuta el flujo del Bot e identifica la intención.
   - El bot responde en base a las tarifas de Aristo Soluciones.
   - Si requiere cotizar, n8n decide, por ejemplo:
     "equipo_asignado": "Agendamiento_Otra_Consulta"
        │
        ▼
3. Odoo recibe el JSON de n8n y ejecuta 'capturar_lead(datos)':
   a) Odoo crea el Lead en el CRM.
   b) Odoo busca en su tabla interna: "Agendamiento_Otra_Consulta" -> Pertenece al "Grupo Citas".
   c) Asigna el Lead al Equipo CRM de Odoo llamado "Grupo Citas".
   d) Odoo busca un "Chatwoot Mapping" que coincida con "Agendamiento_Otra_Consulta".
        │
        ▼
4. Odoo encuentra el mapping "OtraConsulta" y lee sus valores:
   - Chatwoot Inbox ID: 1
   - Chatwoot Agent ID: 1 (Simon)
   - Chatwoot Agent Email: saymon_set@hotmail.com
        │
        ▼
5. Odoo se comunica internamente con Chatwoot a través de su API:
   - Agrega a Simon como miembro de la bandeja 1 (si no lo estaba).
   - Asigna la conversación en Chatwoot a Simon.
   - Cambia el estado del chat a "Abierto" (Open).
   - Odoo busca un usuario en Odoo con login 'saymon_set@hotmail.com', le asigna el lead en el CRM y le envía un correo electrónico de notificación.
```

---

## 4. Guía para agregar un nuevo departamento/flujo en el futuro
*(Por ejemplo, si deseas agregar un departamento de "Soporte Técnico" con el código `Soporte_Tecnico`)*

Sigue estos 5 pasos exactos:

### Paso 1: Agregar el código en la base de datos de Odoo
Modifica el campo de selección (`Selection`) en Odoo para permitir el nuevo código técnico.
*   Abre el archivo: [chatwoot_mapping.py](file:///home/odoo/prod/modulos_odoo/shared/extra/19.0/odoo_chatwoot_connector/models/chatwoot_mapping.py#L9-L29)
*   Agrega la nueva opción en `EQUIPO_ASIGNADO_SELECTION`:
    ```python
    ('Soporte_Tecnico', 'Soporte Técnico'),
    ```

### Paso 2: Configurar la correspondencia en Odoo
Dile a Odoo a qué Equipo CRM y a qué descripción corresponde ese nuevo código.
*   Abre el archivo: [chatbot_flujo.py](file:///home/odoo/prod/modulos_odoo/shared/extra/19.0/ai_chatbot_1_portal/models/chatbot_flujo.py#L408-L439)
*   En `_get_mapeo_equipo_grupo`, agrega tu nuevo código y el nombre del equipo CRM que lo recibirá:
    ```python
    "Soporte_Tecnico": "Grupo Soporte",
    "flujo_soporte_tecnico": "Grupo Soporte",
    ```
*   En `_get_mapeo_equipo_descripcion` (línea 455), agrega la descripción legible:
    ```python
    "Soporte_Tecnico": "soporte técnico y garantías de equipos",
    ```

### Paso 3: Crear el Mapping en la Interfaz de Odoo
Ve a **Odoo → Ajustes → Chatwoot Mappings** (o a la lista de mappings) y crea un registro:
*   **Name:** `Soporte Técnico`
*   **Equipo CRM:** `Grupo Soporte` *(Crea este equipo en Odoo primero si no existe)*
*   **Equipo Asignado:** Elige `Soporte Técnico` de la lista desplegable.
*   **Chatwoot inbox id:** `1` *(el ID de tu canal de WhatsApp)*
*   **Chatwoot agent id / email:** Escribe el ID y el correo del agente de Chatwoot encargado de soporte (ej: `soporte@aristosoluciones.com`).

### Paso 4: Configurar el Vendedor en Odoo
*   Ve a **Ajustes → Usuarios**.
*   Asegúrate de que el encargado de soporte tenga un usuario en Odoo cuyo **login** de inicio de sesión sea exactamente `soporte@aristosoluciones.com` y agrégalo como miembro del equipo CRM `Grupo Soporte`.

### Paso 5: Modificar el Prompt de la Inteligencia Artificial (n8n)
*   Abre el archivo del Prompt de tu IA: [PROMPT_ARISTOSOLUCIONES_UV.txt](file:///home/odoo/prod/modulos_odoo/shared/extra/19.0/odoo_chatwoot_connector/PROMPT_ARISTOSOLUCIONES_UV.txt)
*   Instruye al modelo de lenguaje en la sección de prioridades y reglas para que, cuando el usuario pregunte por fallas, ayuda técnica o garantías, devuelva en el JSON:
    ```json
    "equipo_asignado": "Soporte_Tecnico"
    ```

---

## 5. Resumen de Conexión de API (Para Recordar)

*   **URL de Conexión:** En Odoo Settings, usa `http://chatwoot-app:3000` (URL local del contenedor Docker). Es mucho más rápido y evita caídas por vencimientos de certificados SSL.
*   **Token API de Chatwoot:** Se saca ingresando a Chatwoot en el navegador → haciendo clic en tu perfil abajo a la izquierda → **Ajustes de Perfil** → scroll hasta el final → **Token de acceso**. Copia ese valor e insértalo en Odoo en **Ajustes → Chatwoot Integration → Chatwoot API token**.
