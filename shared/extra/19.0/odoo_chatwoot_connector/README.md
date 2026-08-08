# Odoo Chatwoot Connector

Este módulo conecta **Odoo 19** con **Chatwoot** a través de **n8n/OpenAI**. Relaciona el valor `equipo_asignado` que clasifica el bot/IA con la bandeja de entrada, el agente responsable en Chatwoot y el equipo CRM de Odoo que debe recibir el lead.

---

## 1. Características Principales

*   **Asignación de Conversaciones:** Asigna chats automáticamente a agentes específicos (`agent_id` / `agent_email`) o bandejas de entrada (`inbox_id`) en Chatwoot.
*   **Aplicación Automática de Etiquetas (Tags):** Etiqueta las conversaciones en Chatwoot con las tags configuradas.
*   **Enrutamiento CRM:** Vincula la oportunidad (`crm.lead`) al equipo CRM correcto en Odoo.
*   **Trazabilidad:** Guarda logs detallados del proceso de asignación y posibles errores en la pestaña "Chatwoot / Odoo" del lead.

---

## 2. El Algoritmo Round Robin (Rotación de Agentes)

Cuando varios agentes comparten el mismo flujo o área de atención comercial, el sistema reparte de forma equitativa las conversaciones entrantes para no sobrecargar a un solo vendedor.

### ¿Cómo funciona la rotación?
1. **Búsqueda de Candidatos:** Odoo busca todos los registros activos en *Chatwoot Mappings* que compartan el mismo contexto.
2. **Prioridad de Coincidencia:**
   1. Mappings con el mismo `equipo_asignado` (ej. `CITAS_MP`).
   2. Si no hay, mappings con el mismo flujo (`flow_name`).
   3. Si no hay, mappings con el mismo equipo CRM (`team_id`).
3. **Rotación Circular:** Si encuentra varios candidatos válidos, el sistema lee el ID del último mapping asignado (guardado en `ir.config_parameter`) y le entrega la nueva conversación al siguiente agente en la lista (ordenados de forma ascendente por su ID).
4. **Respaldo (Fallback):** Si la asignación al agente falla o el agente no está disponible, la conversación se mantiene en el inbox configurado como respaldo.

### Ejemplo Práctico:
Tienes dos mappings activos para el código `CITAS_MP`:
*   *Mapping A (ID 8)*: Asignado al Agente 1 (Simon).
*   *Mapping B (ID 9)*: Asignado al Agente 2 (María).

**Flujo de asignación:**
*   Cliente 1 escribe → Se asigna al Agente 1 (Simon).
*   Cliente 2 escribe → Se asigna al Agente 2 (María).
*   Cliente 3 escribe → Rota de nuevo al Agente 1 (Simon).

---

## 3. Guía de Depuración y Logs (Para Desarrolladores)

### Logs de Asignación en Odoo
Toda la lógica de rotación y asignación del conector inicia con el prefijo `RR[session]` y `RR[mapping]`. Puedes filtrar los logs del contenedor ejecutando:
```bash
docker logs odoo-19-web --tail 300 2>&1 | grep -E 'RR\[session\]|RR\[mapping\]'
```

### Consultar mappings activos desde Odoo Shell
Puedes inspeccionar el funcionamiento del Round Robin abriendo la consola interactiva:
```python
# Buscar mappings activos
self.env['chatwoot.mapping'].sudo().search([('active', '=', True)])

# Probar la rotación de un flujo
self.env['chatwoot.mapping'].sudo().select_round_robin_mapping(equipo_asignado='Agendamiento_Directo')
```

---

## 4. Estructura del Módulo

*   `models/`: Contiene los modelos del conector (mappings, cliente de API Chatwoot, herencias de lead y chatbot session).
*   `views/`: Formularios, listas y vistas heredadas en Odoo.
*   `__init__.py` / `__manifest__.py`: Metadata y ganchos de inicio.
*   `PROMPT_ARISTOSOLUCIONES_UV.txt`: Prompt oficial que define el comportamiento del bot en n8n.
*   `MANUAL_FUNCIONAL_DOCKER.md`: Manual funcional paso a paso (tokens Chatwoot, mappings y comandos Docker) para personas sin experiencia.
*   `README_ROUND_ROBIN.md`: Explicación sencilla de la rotación de agentes.

> Para el token de n8n (clave `CHATBOT_API_TOKEN` / `x-chatbot-token`) y los detalles del contenedor de n8n,
> consulta `ai_chatbot_1_portal/MANUAL_FUNCIONAL_DOCKER.md`.
