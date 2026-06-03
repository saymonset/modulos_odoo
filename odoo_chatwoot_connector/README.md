Odoo Chatwoot Connector
========================

Módulo para integrar Odoo con Chatwoot: asignar conversaciones, añadir tags y notificar agentes desde Odoo.

Instalación
- Copiar este directorio a tu `addons_path`.
- Actualizar la lista de módulos y activar el módulo.

Configuración
- Ajustes -> Chatwoot: configurar `Chatwoot base URL` y `Chatwoot API token`.
- Crear mapeos en "Chatwoot Mappings" para relacionar `equipo_asignado` o flujo con inbox/agent/tags.

Uso
- El módulo añade la llamada a Chatwoot cuando se crea el lead desde el flujo del chatbot.
