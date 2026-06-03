Odoo Chatwoot Connector (Odoo 19 CE)
====================================

Descripción
-----------
Este módulo integra Odoo con Chatwoot para:

- Asignar conversaciones a agentes o inboxes (equipos) en Chatwoot.
- Añadir tags a las conversaciones para facilitar filtros y automatizaciones.
- Enviar un mensaje de notificación a la conversación (opcional).

Diseñado como módulo independiente para mantener la integración desacoplada del flujo de negocio.

Instalación (Odoo 19 CE)
------------------------
1. Copia el directorio `odoo_chatwoot_connector` dentro de tu `addons_path` (por ejemplo: `shared/extra/19.0/`).
2. Actualiza la lista de módulos en Odoo (Actualizar aplicaciones).
3. Instala `Odoo Chatwoot Connector` desde Aplicaciones.

Configuración inicial
---------------------
1. Ir a Ajustes → Chatwoot Settings (o Configuración de sistema) y establecer:
   - Chatwoot base URL (ej: https://chatwoot.unisasalud.com)
   - Chatwoot API token (token con permisos para editar conversaciones y tags)
   - Chatwoot timeout (segundos, p.ej. 3)
2. Ir a Chatwoot → Mappings y crear una fila por cada `equipo_asignado` o flujo a mapear.
   Campos relevantes:
   - Name: etiqueta legible
   - Equipo asignado: (valor que llega desde n8n / AI en `equipo_asignado`)
   - Chatwoot inbox id: id del inbox en Chatwoot (opcional)
   - Chatwoot agent id: id de usuario en Chatwoot para asignación directa (opcional)
   - Chatwoot tags: tags separados por comas (opcional)

Cómo funciona
-------------
1. El flujo del chatbot en Odoo crea el lead mediante `chatbot.session.capturar_lead`.
2. Nuestro módulo extiende `capturar_lead` y, si existen `account_id` y `conversation_id` en `datos`, busca un mapping por `equipo_asignado`.
3. Si encuentra mapping, ejecuta (en este orden):
   - Intentar asignar la conversación a `agent_id` (si está definido).
   - Si no hay `agent_id`, asignar al `inbox_id` (si se definió).
   - Añadir tags definidos en el mapping.
   - Enviar mensaje de notificación (si `notify_message` configurado).

Rutas / API usadas (Chatwoot v4.13.0 - rutas habituales)
------------------------------------------------------
- Asignar / actualizar conversación (PUT):
  PUT /api/v1/accounts/{account_id}/conversations/{conversation_id}
  Body ejemplo: { "inbox_id": 5, "assignee_id": 123, "assignee_type": "User" }
- Añadir tags (POST):
  POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/tags
  Body: { "tags": ["CITAS_MP","flujo_agendamiento"] }
- Enviar mensaje a conversación (POST):
  POST /api/v1/accounts/{account_id}/conversations/{conversation_id}/messages
  Body: { "content": "Nuevo lead asignado..." }

Implementación técnica
----------------------
- Modelos principales:
  - `chatwoot.mapping`: define mappings entre `equipo_asignado`/flujo y los ids/tags de Chatwoot.
  - `chatwoot.client` (AbstractModel): cliente HTTP con método `assign_conversation`.
  - `ResConfigSettings` extiende `res.config.settings` para guardar `base_url` y `api_access_token` en `ir.config_parameter`.
  - Herencia de `chatbot.session.capturar_lead` para llamar al cliente tras crear el lead.

Recomendaciones de normalización
---------------------------------
- Normalizar teléfono (formato E.164) antes de crear lead y antes de enviar a Chatwoot.
- Normalizar vat (sin puntos/guiones) para que coincida con datos en Odoo y Chatwoot.
- Guardar en `datos` la `account_id` y `conversation_id` recibida desde Chatwoot para que `capturar_lead` pueda usarlas.

Buenas prácticas y seguridad
----------------------------
- Guardar el `api_access_token` en `ir.config_parameter` (no en el código).
- Timeouts cortos (2–6s) y capturar excepciones: la llamada a Chatwoot no debe bloquear la creación del lead.
- Registrar en chatter o logs si la notificación a Chatwoot falla para permitir reintentos manuales.

Pruebas sugeridas (staging)
---------------------------
1. Configurar `chatwoot.base_url` y `chatwoot.api_access_token` en staging.
2. Crear mapping `CITAS_MP` con `inbox_id` válido y tag `CITAS_MP`.
3. Ejecutar flujo que termina en `capturar_lead` con `account_id` y `conversation_id` reales.
4. Verificar en Chatwoot: la conversación aparece en el inbox correcto, con las tags y (si configurado) el mensaje de notificación.
5. Probar casos de error: token inválido, agent no verificado, network timeout. Ver logs y que lead siga creándose.

Extensiones posibles
--------------------
- Botón en `crm.lead` para "Reintentar notificar a Chatwoot".
- Cron para reintentos automáticos de leads sin notificación exitosa.
- Almacenamiento del `chatwoot_conversation_id` en el lead para trazabilidad directa.

Contacto
--------
Para dudas sobre la integración o ajustes funcionales, contacta al equipo de desarrollo.
