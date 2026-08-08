# MANUAL FUNCIONAL - Chatwoot, n8n y Odoo (Para personas de poca experiencia)

Este manual explica **en palabras sencillas** cómo funciona la integración entre **Chatwoot, n8n y Odoo**, y sobre todo:
dónde se consiguen y dónde se pegan los **tokens (claves de acceso)**, y cómo revisar los servicios en **Docker** si algo falla.

Si no sabes qué es Docker, no te preocupes: aquí solo tienes que **copiar y pegar comandos** de la forma exacta en que aparecen.

---

## 1. El equipo que trabaja detrás del WhatsApp

Imagina tres personas trabajando juntas:

| Pieza | Qué hace | Dónde vive (Docker) |
|---|---|---|
| **Chatwoot** | La bandeja donde los agentes atienden WhatsApp | Contenedor `chatwoot-app` (puerto 3000) |
| **n8n** | El robot que lee el mensaje, piensa con la IA y responde | Contenedor `n8n-container` (puerto 5678) |
| **Odoo** | El CRM donde se crean los clientes potenciales (leads) | Contenedor `odoo-19-web` |

Una persona **no** puede hablar con la otra sin presentarse. El "carnet de identidad" que usan para darse permiso es el **token** (una clave secreta larga).

### Cómo se mueve un mensaje (solo para que entiendas el flujo)

```
El cliente escribe por WhatsApp
        ↓
Chatwoot recibe el mensaje (inbox/cuenta)
        ↓
n8n lo procesa y decide a qué equipo corresponde la consulta (ej: "Agendamiento_Directo")
        ↓
n8n avisa a Odoo (por "webhook", que es un teléfono interno)
        ↓
Odoo crea el lead en el equipo correcto
        ↓
Odoo le dice a Chatwoot: "asigna esta conversación al agente X"
        ↓
El agente recibe la conversación y atiende
```

Para que cada paso funcione, la integración necesita **dos tokens**:

1. **Token de Chatwoot** (este manual, sección 2)
2. **Token de n8n** (explicado en el manual del módulo `ai_chatbot_1_portal/MANUAL_FUNCIONAL_DOCKER.md`)

---

## 2. EL TOKEN DE CHATWOOT (la clave más importante)

### 2.1 Qué es y para qué sirve

Es una clave secreta que le dice a Chatwoot: *"esta aplicación (Odoo, n8n) tiene permiso para asignar conversaciones, poner etiquetas y enviar mensajes"*.

Se usa en **dos lugares** (debe ser el MISMO valor en ambos):

1. **En Odoo** → para que Odoo pueda asignar conversaciones a agentes.
2. **En n8n** → para que n8n pueda responderle al cliente por Chatwoot.

### 2.2 Cómo sacar el token de Chatwoot (paso a paso)

1. Abre tu navegador y entra a: `https://chatwoot.aristosoluciones.integraia.lat`
2. Inicia sesión (correo y contraseña del agente administrador).
3. En el **borde inferior izquierdo** de la pantalla verás tu avatar (foto) o tu nombre. **Haz clic ahí**.
4. Del menú que se abre, elige **"Ajustes de perfil"** (en inglés: *Profile Settings*).
5. Baja con el ratón hasta el **final** de la página.
6. Verás una sección que dice **"Token de acceso"** (en inglés: *Access Token*) con un botón **"Copiar"**.
7. Pulsa **Copiar**. Ese texto largo es tu token.

> IMPORTANTE: El token **solo se puede copiar desde esta pantalla**. En la base de datos de Chatwoot está guardado cifrado (hasheado), así que **nunca intentes sacarlo de la base de datos** porque no lo vas a encontrar.

### 2.3 Dónde pegar el token en Odoo (Lugar 1)

1. Entra a tu Odoo con un usuario **Administrador**.
   (Para trabajar mejor, activa el **Modo Desarrollador**: Ajustes → botón que dice "Activate Developer Mode" o engranaje → *Developer mode*).
2. Ve al menú **Ajustes** (engranaje).
3. Baja hasta encontrar una sección llamada **"Chatwoot Integration"** (puede estar al final de la página).
4. Rellena los 3 campos así:

| Campo | Qué pones | Explicación |
|---|---|---|
| **Chatwoot base URL** | `http://chatwoot-app:3000` | Es la dirección *interna* de Docker. NO pongas el dominio de internet: esta dirección es más segura y más rápida. |
| **Chatwoot API token** | pega aquí el token que copiaste en el paso 2.2 | El token del perfil de Chatwoot |
| **Chatwoot timeout (s)** | `3` | No lo cambies si no entiendes qué significa. |

5. Pulsa **Guardar**.

> ANOTACIÓN TÉCNICA (no la necesitas para operar): Odoo guarda esta configuración en los parámetros del sistema `chatwoot.base_url` y `chatwoot.api_access_token` de la tabla `ir_config_parameter`.

### 2.4 Pegar el token en n8n (Lugar 2)

El mismo token se usa en los nodos de n8n que **envían mensajes a Chatwoot**.

1. Abre n8n: `https://n8n.aristosoluciones.integraia.lat` (usuario y contraseña normalmente `admin` y la que esté en `secrets/n8n_password.txt`).
2. Abre el workflow (flujo) que se llama algo así como `chatbot_create_lead_0_con_menu_whatsapp`.
3. Busca los nodos que se llaman **`Enviar_mensaje_de_IA`**, **`Enviar_mensaje_de_IA1`**, **`Enviar_mensaje_de_IA2`** y **`Enviar_mensaje_de_IA3`**.
4. Haz doble clic en uno. En la parte **"Headers"** o **"Encabezados"** verás una fila llamada **`api_access_token`**.
5. Pega el token nuevo ahí, en la columna **Value**.
6. OJO: haz lo mismo en TODOS los nodos de Enviar de IA (son 4 normalmente). Si te olvidas de uno, ese nodo fallará.
7. Pulsa **Save** y en la parte superior derecha activa el flujo (**Open** si estaba cerrado).

> REGLA DE ORO: el token que ponga en Odoo y el que ponga en los 4 nodos de n8n **deben ser idénticos**. Si no, Odoo no podrá asignar conversaciones ni n8n podrá responder.

---

## 3. LOS CHATWOOT MAPPINGS (para qué sirven)

No es un token, pero es la otra parte de la configuración de este módulo.

Un Mapping es una "receta" que le dice a Odoo:

> "Cuando n8n te diga que la consulta es `CITAS_MP`, asigna la conversación a la bandeja (inbox) 7 y al agente 9".

Para crear uno:

1. Entra en Odoo → **Chatwoot** → **Mappings** (o **Ajustes → Chatwoot Mappings**).
2. Pulsa **Nuevo**.
3. Rellena:
   - **Name**: un nombre para reconocerlo (ej: `citas_medios_propios`).
   - **Flujo (opcional)**: el flujo del bot (ej: `flujo_citas_medios_propios`).
   - **Equipo CRM**: el equipo de Odoo al que llegará el lead (ej: "Grupo Citas").
   - **Equipo Asignado**: ELIGE de la lista el valor que envía n8n. No lo inventes.
   - **Chatwoot inbox id**: el número de la bandeja. Se ve en la barra del navegador cuando entras a la bandeja (ej: `/inbox/1` → id = 1).
   - **Chatwoot agent id**: el número del agente.
   - **Chatwoot agent email**: el correo del agente.
   - **Intentar asignar al agente primero**: marcado para que la conversación vaya a la persona; si falla se queda en la bandeja.
   - **Tags (CSV)**: etiquetas para la conversación (ej: `whatsapp,citas`).
   - **Active**: el tick de ACTIVO (marcado).
4. Guarda.

Para el detalle completo de la tabla de equivalencias entre WhatsApp ↔ clave técnica ↔ flujo ↔ grupo CRM → **mira el archivo** `README_MENU.md` del módulo `ai_chatbot_1_portal`.

---

## 4. LA PARTE TÉCNICA EN DOCKER (con comandos listos para copiar)

### 4.1 Dónde vive todo

Toda la "fábrica" Docker está en esta carpeta del servidor:

```
/home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/
```

Los archivos más importantes:

| Archivo | Contiene |
|---|---|
| `docker-compose.yaml` | El que une todos los servicios |
| `docker-compose.chatwoot.yml` | Chatwoot (app, base de datos y sidekiq) |
| `docker-compose.n8n.yml` | n8n (aquí está el token CHATBOT_API_TOKEN) |
| `docker-compose.odoo.yml` | Odoo, PostgreSQL y Redis |
| `secrets/` | Contraseñas secretas en archivos de texto |
| `v19/` | Los datos guardados (bases de datos, filestore, backups) |

### 4.2 Comandos básicos de Docker (copia y pega en la terminal)

Primero entra al servidor con SSH (ej: `ssh usuario@ip-del-servidor`) y ve a la carpeta:

```bash
cd /home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19
```

**Ver si todos los servicios están en línea:**

```bash
docker compose ps
```

**Ver el estado de la "fábrica" (alternativa más simple):**

```bash
./6_status_all_services.sh
```

### 4.3 Ver los registros (logs) de cada servicio

**Registros de Chatwoot (ver si Chatwoot está respondiendo):**

```bash
docker logs chatwoot-app --tail 200
```

**Registros de n8n:**

```bash
docker compose logs --tail 200 n8n
```

**Registros de Odoo (buscar mensajes de la integración):**

```bash
docker logs odoo-19-web --tail 300 2>&1 | grep -E 'RR\[session\]|RR\[mapping\]'
```

### 4.4 Reiniciar o actualizar un servicio después de un cambio

**Reiniciar Chatwoot (cuando cambiaste algo de su configuración):**

```bash
docker compose up -d chatwoot-app
```

**Reiniciar Odoo (por ejemplo después de cambiar un parámetro en base de datos):**

```bash
docker restart odoo-19-web
```

**Reiniciar n8n (después de cambiar `CHATBOT_API_TOKEN`):**

```bash
docker compose up -d --force-recreate n8n
```

**Detener todo / encender todo:**

```bash
./3_stop-all.sh          # apaga todo
./4_start-all.sh         # enciende todo
```

**Ver los logs de todos a la vez:**

```bash
./7_logs_all_services.sh
```

### 4.5 Cómo se actualiza el código de los módulos

Los módulos de Odoo se guardan en el servidor (fuera del contenedor) y Odoo los ve automáticamente:

- La carpeta de módulos: `/home/odoo/prod/modulos_odoo/shared/extra/19.0/`
- Dentro del contenedor de Odoo, esa carpeta aparece como `/opt/odoo/custom-addons/extra`

Por eso, cuando cambias un archivo de estos módulos, solo tienes que:

1. Entrar a Odoo → **Aplicaciones** → **Actualizar lista de aplicaciones**.
2. Busca el módulo (`ai_chatbot_1_portal` u `odoo_chatwoot_connector`).
3. Pulsa **Actualizar** (Upgrade) en el módulo.
4. Listo. No hay que montar ni copiar nada manualmente.

---

## 5. Solución de problemas (lo más común)

| Síntoma | Causa probable | Qué haces |
|---|---|---|
| En Odoo aparece el error `missing_configuration_or_ids` | Falta el token o la URL en Ajustes → Chatwoot Integration | Vuelve a hacer el punto 2.3 y Guardar. Si lo hiciste directo en BD, reinicia Odoo con `docker restart odoo-19-web`. |
| El chat se asigna a la bandeja pero no al agente | El ID o el correo del agente no coinciden entre Odoo y Chatwoot | Revisa el mapping (punto 3) y compara el ID/correo con los datos reales del agente |
| La conversación no llega a Chatwoot | Token mal copiado en el mapping o token equivocado en Odoo | Revisa punto 2 y punto 3 |
| n8n no puede responder al cliente | El token `api_access_token` de los nodos `Enviar_mensaje_de_IA` no coincide | Revisa punto 2.4 |
| Odoo responde `Token inválido` (401) | El token de n8n no coincide con Odoo | Está explicado en el manual de `ai_chatbot_1_portal` (sección token de n8n) |
| No llega correo de notificación al agente | No existe usuario en Odoo con el correo del agente | Crea el usuario en Ajustes → Usuarios con el MISMO correo del agente y agrégalo al Equipo CRM |

### Cómo buscar el detalle del error en los registros

```bash
cd /home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19
docker logs odoo-19-web --tail 500 2>&1 | grep -E 'RR\[session\]|RR\[mapping\]|ERROR|Traceback'
```

Si la línea dice `NO SE ENCONTRÓ MAPPING`: revisa que el valor `equipo_asignado` del mapping sea **exactamente igual** (mayúsculas, guiones bajos) al que envía n8n.

---

## 6. Colección rápida (lo más importante del mundo)

1. El token de Chatwoot solo se copia en la **pantalla de perfil de Chatwoot** (no se saca de las bases).
2. Ese token va en **2 lugares**: uno en Odoo (Ajustes → Chatwoot Integration) y otro en los 4 nodos `Enviar_mensaje_de_IA` de n8n.
3. Los dos deben ser **iguales**.
4. El token de n8n (para que n8n hable con Odoo) está explicado en el manual del módulo `ai_chatbot_1_portal`.
5. Todo se reinicia desde la carpeta Docker con `docker compose up -d --force-recreate <servicio>`.
6. Cuando dudes: mira los registros antes de tocar nada (punto 5).