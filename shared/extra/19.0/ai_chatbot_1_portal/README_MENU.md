# README_MENU - Guia de mapeo del menu WhatsApp

Objetivo
- Explicar de forma simple que pasa cuando el usuario pulsa una opcion en WhatsApp.
- Mostrar a que flujo de Odoo corresponde esa opcion.
- Indicar que grupo de Odoo recibe el lead.
- Indicar que agente o inbox de Chatwoot recibe la conversacion.

Como leer este manual
- Texto en WhatsApp: lo que ve el usuario.
- Clave tecnica: el valor que envia n8n a Odoo.
- Flujo de Odoo: el flujo interno que se usa.
- Grupo Odoo: el equipo CRM que recibe el lead.
- Chatwoot: agente o inbox que recibe la conversacion.

Mapa principal

| Texto en WhatsApp | Clave tecnica | Flujo de Odoo | Grupo Odoo | Chatwoot |
| --- | --- | --- | --- | --- |
| Medios propios | `CITAS_MP` | `flujo_citas_medios_propios` | Grupo Citas | Inbox 7, agente 9 si esta activo |
| Seguro medico | `CITAS_SEGUROS` | `flujo_citas_seguro` | Grupo Citas | Inbox / agente configurado |
| Precios | `Agendamiento_Precios` | `flujo_agendamiento_precios` | Grupo Informativo | Inbox / agente configurado |
| Servicios | `Agendamiento_Servicios` | `flujo_agendamiento_servicios` | Grupo Ventas | Inbox / agente configurado |
| Otra consulta | `Agendamiento_Otra_Consulta` | `flujo_agendamiento_otra_consulta` | Grupo Citas | Inbox / agente configurado |
| Ventas | `Ventas_UNISA` | `flujo_ventas_unisa` | Grupo Ventas | Inbox / agente de ventas |
| Resultados laboratorio | `RESULTADOS_LAB` | `flujo_resultados_laboratorio` | Grupo Laboratorio | Inbox / agente de laboratorio |
| Resultados imagenes | `RESULTADOS_IMAGENES` | `flujo_resultados_imagenes` | Grupo Imagenologia | Inbox / agente de imagenologia |

Regla simple
- Si el usuario pulsa una opcion en WhatsApp, n8n traduce esa opcion a una clave tecnica.
- Odoo busca esa clave en el mapping.
- Odoo asigna el lead al grupo correcto.
- Chatwoot recibe la conversacion en el agente o inbox configurado.

Como configurar un mapping en Odoo
1. Ir a Chatwoot -> Mappings -> Nuevo.
2. Escribir un nombre facil de reconocer.
3. Elegir `Equipo Asignado` desde la lista. No escribirlo a mano.
4. Elegir el `Flujo` correcto.
5. Elegir el `Equipo CRM` correcto.
6. Poner el `Chatwoot inbox id`.
7. Poner el `Chatwoot agent id` o el `Chatwoot agent email`.
8. Marcar `Intentar asignar a agente primero` si quieres que llegue primero a una persona.
9. Poner tags si hace falta.
10. Guardar.

Ejemplo practico
- WhatsApp: Medios propios
- Clave tecnica: `CITAS_MP`
- Flujo: `flujo_citas_medios_propios`
- Grupo Odoo: Grupo Citas
- Chatwoot inbox: 7
- Chatwoot agent id: 9
- Chatwoot agent email: `saymon_set@hotmail.com`

Que debe pasar
- El lead se crea en Grupo Citas.
- La conversacion llega a Chatwoot.
- Si el agente 9 existe, la conversacion se asigna a ese agente.
- Si no, queda en la inbox 7.

Como revisar si algo no funciona
- Si no llega al agente, revisar el id o el email del agente.
- Si no llega al inbox, revisar el inbox id.
- Si el lead cae en otro grupo, revisar el mapping en Odoo.
- Si el usuario cambio el texto en WhatsApp, revisar que n8n siga enviando la misma clave tecnica.

Buenas practicas
- Usar siempre la clave tecnica oficial.
- No inventar nombres nuevos en Odoo.
- Mantener un inbox de respaldo.
- Usar agent id cuando sea posible.
- Revisar los mappings si cambian los botones del bot.

Resumen rapido
- Texto WhatsApp -> n8n -> clave tecnica -> mapping Odoo -> grupo Odoo -> agente o inbox Chatwoot.
