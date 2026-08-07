# Manual — Configuración del Conector Chatwoot ↔ Odoo (Aristo Soluciones)

Manual de referencia para entender cómo se relaciona Chatwoot con Odoo a través del módulo `odoo_chatwoot_connector`, y qué significan los campos de la configuración.

## 1. Los actores

| Pieza | ¿Qué es? | Dónde está |
|---|---|---|
| **Chatwoot** | La bandeja de WhatsApp donde llegan y se atienden las conversaciones | `chatwoot.aristosoluciones.integraia.lat` (contenedor `chatwoot-app`) |
| **Odoo** | El CRM donde se crean los leads | contenedor `odoo-19-web`, BD `dbodoo19` |
| **n8n** | El orquestador: recibe la respuesta del bot y le avisa a Odoo | contenedor `n8n-container` |
| **odoo_chatwoot_connector** | El módulo que une todo: mapea flujos → asigna conversación en Chatwoot → crea el lead en Odoo | `/home/odoo/prod/modulos_odoo/shared/extra/19.0/odoo_chatwoot_connector` |

**La idea central:** cuando un cliente escribe por WhatsApp, el bot decide a qué "equipo" va la consulta (`equipo_asignado`). Odoo busca ese valor en un **Chatwoot Mapping**, asigna la conversación en Chatwoot al agente correcto y crea el lead en el equipo CRM correcto.

## 2. Datos reales verificados en las bases de datos

| Dato | Valor | Verificado contra |
|---|---|---|
| Usuario Chatwoot | id **1**, Simon, `saymon_set@hotmail.com`, rol **administrator** | tabla `users` |
| Inbox Chatwoot | id **1**, `whatsapp_aristosoluciones` (WhatsApp), cuenta 1 | tabla `inboxes` |
| Cuenta Chatwoot | id **1**, "Aristo Soluciones" | tabla `accounts` |
| Simon es miembro del inbox 1 | Sí | tabla `inbox_members` |
| Equipo CRM Odoo | "Grupo Ventas" (id **5**) | tabla `crm_team` |
| Flujo | `flujo_agendamiento_directo` (id **1**) | tabla `chatbot_flujo` |
| Mapping actual | id **1** `aristosolucionesapp` (activo) | tabla `chatwoot_mapping` |

## 3. El JSON de usuario de Chatwoot, campo por campo

Ese JSON es lo que devuelve la API de Chatwoot cuando consultas un agente/usuario del account:

```json
{
  "id": 1,                    // ← El "Chatwoot agent id (User id)" que pones en Odoo
  "account_id": 1,            // ← A qué cuenta pertenece (debe coincidir con tu account)
  "availability_status": "online",
  "auto_offline": true,
  "confirmed": true,          // ← El email está confirmado (cuenta usable)
  "email": "saymon_set@hotmail.com",  // ← El "Chatwoot agent email" que pones en Odoo
  "provider": "email",
  "available_name": "Simon",
  "name": "Simon",
  "role": "administrator",    // ← Es administrador de la cuenta (puede actuar como agente)
  "thumbnail": "",
  "custom_role_id": null
}
```

**Lo único que de ese JSON te interesa copiar al mapping de Odoo son `id` y `email`.** El resto es información del agente.

## 4. El formulario "Chatwoot Mappings", campo por campo

| Campo | Valor | ¿Por qué es correcto? |
|---|---|---|
| **Name** | `aristosolucionesapp` | Solo un nombre para reconocerlo. Da igual cuál. |
| **Flujo (opcional)** | `flujo_agendamiento_directo` | Debe ser un flujo que **ya exista** en Odoo (verificado: existe, id 1). Es la "receta" del bot para esa consulta. |
| **Equipo CRM** | `Grupo Ventas` | El equipo de Odoo que recibirá el lead (verificado: existe, id 5). |
| **Equipo Asignado** | `Agendamiento Directo` (guarda como `Agendamiento_Directo`) | ⚠️ **Este es el valor clave.** Debe coincidir EXACTO con el `equipo_asignado` que envía n8n. En la base ya está guardado como `Agendamiento_Directo` (con guion bajo). |
| **Chatwoot inbox id** | `1` | Verificado: el inbox de WhatsApp real. |
| **Chatwoot agent id** | `1` | Verificado: Simon. |
| **Chatwoot agent email** | `saymon_set@hotmail.com` | Verificado: coincide con el agente 1. |
| **Intentar asignar a agente primero** | activado | Intenta asignar a Simon; si falla, deja la conversación en el inbox. |
| **Tags (CSV)** | `aristosolucionesapp` | Etiqueta que se le pondrá a la conversación en Chatwoot. |
| **Active** | marcado | Para que el mapping se use. |

> **Regla de oro:** `Equipo Asignado` = lo que manda n8n. No lo inventes. Si n8n envía `Agendamiento_Directo` (con guiones), el mapping debe tener exactamente eso. El flujo y el nombre del mapping son solo etiquetas internas.

## 5. Cómo funciona el flujo completo

```
Cliente escribe por WhatsApp
        │
        ▼
Chatwoot recibe la conversación (inbox 1, cuenta 1)
        │
        ▼
n8n procesa el mensaje con el bot/IA y decide el "equipo_asignado"
        │  envía payload a Odoo:
        │  { account_id: 1, conversation_id: XXX, equipo_asignado: "Agendamiento_Directo", ... }
        ▼
Odoo (chatbot.session.capturar_lead)
        │  1. Crea el lead en el Equipo CRM (Grupo Ventas)
        │  2. Busca el mapping activo con ese equipo_asignado → encuentra "aristosolucionesapp"
        │  3. ¿Existe usuario Odoo con login = saymon_set@hotmail.com?  ← VER PUNTO 6
        ▼
Odoo llama a la API de Chatwoot (chatwoot.client.assign_conversation)
        │  1. Verifica/agrega a Simon como miembro del inbox 1
        │  2. Asigna la conversación a Simon (agent id 1)
        │  3. Abre la conversación en "Open"
        │  4. Crea el tag "aristosolucionesapp"
        │  5. Envía mensaje al cliente: "Tu consulta sobre ... ha sido registrada"
        ▼
Lead creado en Odoo con trazabilidad (chatwoot_conversation_id, etc.)
```

## 6. Nota sobre el usuario de Odoo

El módulo, en `models/chatbot_session_inherit.py`, hace esto:

```
busca un usuario Odoo cuyo login = saymon_set@hotmail.com
```

- ✅ La asignación en Chatwoot funciona con o sin ese usuario (depende solo de Chatwoot).
- ⚠️ Si el usuario no existe, el lead se crea en el equipo "Grupo Ventas" pero **sin usuario asignado** y **no se envía el correo de notificación**.

**Recomendación:** crear un usuario de Odoo con login `saymon_set@hotmail.com` y agregarlo como miembro del equipo "Grupo Ventas".

### Cómo crear el usuario manualmente en Odoo 19

#### Paso 1 — Crear el usuario

1. Ve a **Ajustes** (menú engranaje) → sección **Usuarios y Compañías** → **Usuarios**.
2. Botón **Nuevo**.
3. En **Nombre**: `Simon`.
4. En **Correo electrónico**: `saymon_set@hotmail.com` (esto crea el login y el partner a la vez).
5. En **Contraseña**: pon una temporal (el sistema pedirá confirmarla; luego la cambia él).
6. En **Permisos**, escribe `Ventas` en el buscador de grupos y marca **Ventas: Usuario** (Sales: User).
7. Guarda.

> En Odoo 19 el correo que pongas en "Correo electrónico" se usa como **login**. Debe ser exactamente `saymon_set@hotmail.com`, que es lo que el módulo busca en `chatbot_session_inherit.py`.

#### Paso 2 — Agregarlo al equipo "Grupo Ventas"

1. Ve a **CRM** → **Configuración** → **Equipos**.
2. Abre **Grupo Ventas**.
3. Pestaña **Miembros** → **Añadir una línea** → elige **Simon**.
4. Guarda.

#### Paso 3 — Activar al usuario

- Al crearlo, Odoo deja el usuario **sin confirmar** (aparece en gris). Ábrelo y pulsa **Confirmar/Activar usuario** (o usa "Enviar invitación" si prefieres que Simon ponga su propia contraseña).
- Verifica en la lista que esté **activo** (no en gris).

#### Verificación rápida

Cuando llegue un lead del chatbot, el módulo buscará el login `saymon_set@hotmail.com`, le asignará el lead y le enviará el correo de notificación. Para comprobar que quedó bien, revisa **Ajustes → Usuarios** y confirma que el usuario aparece activo.

## 7. Errores comunes y cómo diagnosticar

1. **Revisar el log de Odoo** — todas las líneas importantes empiezan con `RR[session]` o `RR[mapping]`:

   ```bash
   docker logs odoo-19-web --tail 300 2>&1 | grep -E 'RR\[session\]|RR\[mapping\]'
   ```

2. **¿No encontró mapping?** Busca `NO SE ENCONTRÓ MAPPING`. Revisa que `equipo_asignado` coincida exacto con lo que envía n8n.

3. **¿Falla asignación al agente?** Busca `assign_agent_failed`. Revisa que el agente sea miembro del inbox (el módulo intenta agregarlo solo).

4. **¿No se notifica por correo?** Busca `no se encontró user Odoo para email=...` → es el punto 6.
