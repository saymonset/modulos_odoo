# README - Round Robin de Chatwoot Mappings

## Objetivo

Este documento explica, en forma simple, cómo se reparten las conversaciones cuando varios agentes comparten el mismo flujo.

La idea es que no siempre le llegue al mismo agente.
El sistema rota entre los mappings activos y evita agentes offline o no confirmados.

## Cuándo aplica

Aplica cuando tienes varios `Chatwoot Mappings` con el mismo:

- `Equipo Asignado`
- o el mismo `Flujo`
- o el mismo `Equipo CRM`

Ejemplo:

- `CITAS_MP` -> `flujo_citas_medios_propios`
- agente 10 -> `saymon_set@hotmail.com`
- agente 9 -> `oraclefedora@gmail.com`

## Qué hace el sistema

1. Busca los mappings activos.
2. Filtra los que coinciden con el flujo o equipo asignado.
3. Si hay varios, elige el siguiente en orden rotativo.
4. Guarda cuál fue el último mapping usado.
5. En la próxima conversación toma el siguiente.

## Reglas de selección

El sistema prioriza así:

1. `equipo_asignado`
2. `flow_name`
3. `team_id`

Luego aplica round robin sobre los candidatos encontrados.

## Qué agentes entran en la rotación

Solo entran los agentes que estén:

- confirmados
- y no estén offline

Si un agente está offline o no confirmado, se salta.

## Dónde queda guardado el estado

El último mapping usado se guarda en `ir.config_parameter`.

Así el sistema recuerda quién fue el último y pasa al siguiente.

## Ejemplo real

Tienes dos mappings para el mismo flujo:

- `CITAS_MP` con agente 10
- `CITAS_MP` con agente 9

Resultado esperado:

- primera conversación -> agente 10
- segunda conversación -> agente 9
- tercera conversación -> agente 10
- y así sucesivamente

Si el agente 9 está offline:

- primera conversación -> agente 10
- segunda conversación -> agente 10
- tercera conversación -> agente 10

## Cómo configurarlo

1. Ir a `Chatwoot -> Mappings`.
2. Crear un mapping por cada agente que quieras usar en el mismo flujo.
3. Usar el mismo `Equipo Asignado` o el mismo `Flujo`.
4. Poner un `chatwoot_agent_id` distinto en cada mapping.
5. Marcar el mapping como `Active`.
6. Guardar.

## Buenas prácticas

- Usa `agent_id` antes que `agent_email`.
- Mantén la inbox como respaldo.
- No mezcles agentes de flujos distintos.
- Revisa que los agentes estén confirmados en Chatwoot.
- Revisa que no estén offline si esperas que entren en la rotación.

## Ejemplo recomendado

Para `CITAS_MP`:

- Mapping 1
  - `Equipo Asignado`: `CITAS_MP`
  - `Flujo`: `flujo_citas_medios_propios`
  - `Chatwoot inbox id`: `7`
  - `Chatwoot agent id`: `10`
  - `Chatwoot agent email`: `saymon_set@hotmail.com`

- Mapping 2
  - `Equipo Asignado`: `CITAS_MP`
  - `Flujo`: `flujo_citas_medios_propios`
  - `Chatwoot inbox id`: `7`
  - `Chatwoot agent id`: `9`
  - `Chatwoot agent email`: `oraclefedora@gmail.com`

## Qué revisar si algo no rota bien

- Que ambos mappings estén `Active`.
- Que ambos agentes existan en Chatwoot.
- Que ambos agentes estén confirmados.
- Que no estén offline.
- Que el flujo o `equipo_asignado` sea el mismo en ambos mappings.

## Resumen corto

El round robin reparte las conversaciones entre varios mappings iguales.
Si un agente no está disponible, se lo salta.
Así evitas cargar siempre al mismo agente.
