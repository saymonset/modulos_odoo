# README - Chatwoot Mappings

Manual de uso en español para configurar los mappings entre n8n/OpenAI, Odoo y Chatwoot.

## Resumen

Este módulo relaciona el valor `equipo_asignado` que llega desde n8n/IA con la forma en que se asigna una conversación en Chatwoot y con el equipo CRM de Odoo que debe recibir el lead.

Cuando llega una petición, Odoo busca el mapping por `equipo_asignado`, intenta asignar la conversación en Chatwoot y luego crea o actualiza el lead con trazabilidad.

## Para qué sirve

- Asignar conversaciones a agentes o inboxes en Chatwoot.
- Aplicar tags automáticamente.
- Vincular el lead al equipo CRM correcto en Odoo.
- Registrar trazabilidad del intento de asignación.

## Campos del formulario

### Guía rápida para no perderse

Si vas a crear un mapping nuevo, llena los campos en este orden:

1. `Name`: pon un nombre fácil de reconocer.
2. `Equipo Asignado`: elige una opción de la lista, no la escribas a mano.
3. `Flujo`: selecciona el flujo relacionado, si aplica.
4. `Equipo CRM`: elige el equipo de Odoo que recibirá el lead.
5. `Chatwoot inbox id`: coloca el inbox real de Chatwoot.
6. `Chatwoot agent id` o `Chatwoot agent email`: usa uno de los dos para asignar a un agente.
7. `Intentar asignar a agente primero`: deja activado si quieres priorizar al agente.
8. `Tags (CSV)`: escribe los tags separados por coma.
9. `Active`: déjalo marcado mientras el mapping esté en uso.

Si no tienes un valor claro para alguno de los campos, deja esa duda para soporte técnico antes de guardar.

### Name

Nombre descriptivo del mapping.

Ejemplo: `Agendamiento -> Grupo Citas`.

### Flujo (opcional)

Nombre interno del flujo.

Ejemplo: `flujo_agendamiento_directo`.

Si no sabes cuál usar, revisa la tabla de opciones válidas de `Equipo Asignado` más abajo.

### Equipo CRM?

Equipo comercial de Odoo (`crm.team`) al que se vinculará el lead.

### Grupo Informativo

Campo informativo para clasificación interna. Opcional.

### Equipo Asignado (valor esperado desde n8n/AI)

Este campo no se debe inventar.

Debes copiar exactamente uno de estos valores que salen del workflow n8n:

| Valor `equipo_asignado` | Flujo asociado |
| --- | --- |
| `Agendamiento_Directo` | `flujo_agendamiento_directo` |
| `Agendamiento_Precios` | `flujo_agendamiento_precios` |
| `Agendamiento_Servicios` | `flujo_agendamiento_servicios` |
| `Agendamiento_Otra_Consulta` | `flujo_agendamiento_otra_consulta` |
| `Ventas_UNISA` | `flujo_ventas_unisa` |
| `CITAS_MP` | `flujo_citas_medios_propios` |
| `CITAS_SEGUROS` | `flujo_citas_seguro` |
| `RESULTADOS_LAB` | `flujo_resultados_laboratorio` |
| `RESULTADOS_IMAGENES` | `flujo_resultados_imagenes` |

Si no sabes cuál elegir, usa el que ya viene en el flujo o pídele al equipo técnico el valor exacto.

### Chatwoot inbox id?

ID numérico de la inbox en Chatwoot.

Es el fallback obligatorio si no se asigna a un agente.

### Chatwoot agent id (User id)?

ID numérico del agente en Chatwoot.

Si existe, se intentará asignar primero a ese agente.

### Chatwoot agent email?

Email del agente en Chatwoot.

Se usa como alternativa si no se quiere usar el id.

### Intentar asignar a agente primero

Si está activado:

- intenta asignar al agente primero;
- si falla, usa el inbox como fallback.

### Tags (CSV)?

Tags separados por coma.

Ejemplo: `Citas,WhatsApp,Prioritario`.

### Active

Si está activo, el mapping será usado.

## Cómo obtener los valores

### Inbox ID en Chatwoot

Usa la API de Chatwoot:

```bash
curl -s -H "api_access_token: <TU_TOKEN>" \
  "https://<TU_CHATWOOT_URL>/api/v1/accounts/<ACCOUNT_ID>/inboxes"
```

Busca el campo `id` en la respuesta.

### Agent ID o email en Chatwoot

```bash
curl -s -H "api_access_token: <TU_TOKEN>" \
  "https://<TU_CHATWOOT_URL>/api/v1/accounts/<ACCOUNT_ID>/agents"
```

o

```bash
curl -s -H "api_access_token: <TU_TOKEN>" \
  "https://<TU_CHATWOOT_URL>/api/v1/accounts/<ACCOUNT_ID>/users"
```

Busca `id` y `email`.

### crm.team id en Odoo

#### Desde la interfaz

1. Activa modo desarrollador.
2. Ve a CRM -> Configuración -> Equipos.
3. Abre el equipo.
4. Revisa la URL, el número en `id=` es el `crm.team.id`.

#### Desde Odoo shell

```python
env['crm.team'].search([('name', '=', 'Nombre del equipo')]).id
```

## Ejemplo de mapping

- Name: `Agendamiento Directo -> Grupo Citas`
- Flujo: `flujo_agendamiento_directo`
- Equipo CRM: `Grupo Citas`
- Equipo Asignado: `Agendamiento_Directo`
- Chatwoot inbox id: `5`
- Chatwoot agent id: `0`
- Chatwoot agent email: `agente.citas@unisa.com`
- Intentar asignar a agente primero: activado
- Tags: `Citas,WhatsApp`
- Active: marcado

## Regla importante

- `Flujo` y `Equipo Asignado` no son lo mismo.
- `Equipo Asignado` debe coincidir con el valor que envía n8n.
- No escribas valores nuevos por tu cuenta.

## Payload esperado desde n8n

Ejemplo:

```json
{
  "account_id": 1,
  "conversation_id": 12345,
  "phone": "+58XXXXXXXXXX",
  "message": "Hola, quiero agendar",
  "equipo_asignado": "Agendamiento_Directo",
  "tipoPregunta": "agendamiento"
}
```

## Cómo funciona

1. n8n envía `equipo_asignado` a Odoo.
2. Odoo busca el mapping activo con ese valor.
3. Si hay `account_id` y `conversation_id`, intenta asignar la conversación en Chatwoot.
4. Si existe agente válido, asigna al agente.
5. Si no, usa la inbox como fallback.
6. Aplica tags si fueron configurados.
7. Crea o actualiza el lead y deja trazabilidad.

## Errores comunes

### Inbox id = 0

El inbox no es válido.

Solución: revisar el id real en Chatwoot.

### Agente no encontrado

El email o id del agente no coincide.

Solución: revisar el valor en Chatwoot.

### Error al actualizar el módulo

Si aparece `XMLID not found` o `ParseError`, revisar la vista heredada y volver a actualizar el módulo.

### Timeout con Chatwoot

Si la API responde lento, aumentar `Chatwoot timeout (s)` en Ajustes.

## Prueba rápida

1. Configura la URL y el token de Chatwoot en Ajustes.
2. Crea un mapping con un `equipo_asignado` real.
3. Usa un `inbox id` real.
4. Envía un payload de prueba.
5. Revisa el lead en Odoo y la conversación en Chatwoot.

## Logs y depuración

Para revisar logs de Odoo:

```bash
tail -n 200 /ruta/al/log/odoo.log
```

Odoo shell:

```bash
./odoo/odoo-bin shell -c <cfg> -d <db>
```

## Recomendaciones

- Guardar el token en `ir.config_parameter`.
- Mantener `equipo_asignado` exactamente igual en n8n y en Odoo.
- Usar inbox de fallback siempre.
- Activar el mapping solo cuando esté probado.

## Contacto

Si necesitas extender el flujo o agregar nuevos mappings, contacta al equipo de desarrollo.
