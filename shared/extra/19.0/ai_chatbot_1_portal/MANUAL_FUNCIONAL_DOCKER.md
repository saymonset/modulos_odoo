# MANUAL FUNCIONAL - Módulo ai_chatbot_1_portal y el Token de n8n (Para personas de poca experiencia)

Este manual explica **en palabras sencillas** qué hace el módulo `ai_chatbot_1_portal`, cómo se conecta con **n8n** (el robot de la IA), y sobre todo:
cómo configurar el **token de n8n** (la clave secreta con la que n8n y Odoo se reconocen) y cómo manejar n8n en **Docker**.

Si no sabes qué es Docker, tranquilo: aquí solo copias y pegas comandos.

> Si lo que buscas es el **token de Chatwoot** (la bandeja de WhatsApp), ese está explicado el manual del módulo
> `odoo_chatwoot_connector/MANUAL_FUNCIONAL_DOCKER.md`.

---

## 1. Qué hace este módulo

`ai_chatbot_1_portal` es la "puerta de entrada" del chatbot:

- Recibe los mensajes que **n8n** le envía (los pasos que el cliente está siguiendo).
- Recuerda en qué punto va cada conversación (la "sesión").
- Cuando el cliente termina de dar sus datos, **crea el lead (cliente potencial) en el CRM**.
- Le devuelve a n8n la configuración que necesita para responder (prompts, flujos activos, mensaje de respaldo).

### Los "teléfonos" que usa n8n para llamar a Odoo (endpoints)

| Ruta (URL) | Método | Para qué sirve |
|---|---|---|
| `/ai_chatbot_1_portal/inicioagendar` | POST | n8n avisa que empieza un agendamiento (lleva sesión, flujo, equipo asignado) |
| `/ai_chatbot_1_portal/procesar_paso` | POST | n8n guarda cada respuesta del cliente (paso a paso) |
| `/ai_chatbot_1_portal/configuracion_agente` | POST | n8n pide la configuración del agente: **requiere el token de n8n** |
| `/ai_chatbot_1_portal/capturar_lead_http` | POST | n8n pide crear el lead cuando el cliente termina |
| `/ai_chatbot_1_portal/buscar_por_telefono_http` | POST | n8n pregunta si ese teléfono ya existe en el CRM |

Todas las URLs completas usan tu dominio público, por ejemplo:

```
https://aristosoluciones.integraia.lat/ai_chatbot_1_portal/configuracion_agente
```

---

## 2. EL TOKEN DE N8N (la clave que abre la puerta)

### 2.1 Qué es y para qué sirve

El token de n8n (nombre técnico: `CHATBOT_API_TOKEN`, o `ai_chatbot_1_portal.api_token`) es una clave secreta que hace de "contraseña compartida":

> n8n dice a Odoo: "hola, soy el robot, mi carnet es este". Odoo compara con el suyo y, si coinciden, le responde. Si no, lo manda lejos con error `Token inválido` (código 401).

Se usa solo en el endpoint **`/configuracion_agente`** (donde n8n le pide a Odoo la configuración del bot).

### 2.2 Los 2 sitios donde debe estar esa clave (SIEMPRE iguales)

| Lugar | Dónde exactamente |
|---|---|
| **1. Odoo** | Ajustes → sección **"Configuración del agente (n8n)"** → campo **"API Token para n8n"** |
| **2. Docker** | Archivo `docker-compose.n8n.yml`, línea que dice `CHATBOT_API_TOKEN=...` del contenedor de n8n |

**Regla de oro: este valor DEBE ser exactamente el mismo en los dos sitios.** Si solo cambia uno, el bot deja de obtener configuración.

### 2.3 Cómo generar un token nuevo (si quieres cambiarlo)

Un token es solo un texto largo con letras y números al azar. Para generar uno:

```bash
openssl rand -base64 32
```

Copia el resultado (ej: `tX29Qk...largo`). Eso será tu token nuevo.

### 2.4 Cómo poner el token en Odoo (Lugar 1)

1. Entra a Odoo con un usuario **Administrador** (modo desarrollador recomendado: Ajustes → engranaje → *Developer mode*).
2. Ve a **Ajustes**.
3. Busca la sección **"Configuración del agente (n8n)"**.
4. En **"API Token para n8n"** pega el token (el mismo que pondrás en Docker).
5. Pulsa **Guardar**.

Lo que se guarda técnicamente: el parámetro del sistema `ai_chatbot_1_portal.api_token`.

### 2.5 Cómo poner el token en Docker (Lugar 2)

1. Entra al servidor con SSH y ve a la carpeta de compos:

```bash
cd /home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19
```

2. Edita el archivo `docker-compose.n8n.yml` con cualquier editor (ej: `nano docker-compose.n8n.yml`).

3. Busca estas dos líneas dentro del servicio `n8n`:

```yaml
- N8N_EXPRESSIONS_ALLOWED_ENV_VARS=CHATBOT_API_TOKEN   # no la borres
- CHATBOT_API_TOKEN=<EL_TOKEN_QUE_QUIERAS>            # aquí va la clave
```

4. Reemplaza `<EL_TOKEN_QUE_QUIERAS>` por tu token nuevo (el mismo del punto 2.4).

5. Guarda el archivo (en nano: `Control + O`, Enter, `Control + X`).

6. Reinicia el contenedor de n8n para que tome el valor nuevo:

```bash
docker compose up -d --force-recreate n8n
```

7. Verifica que n8n quedó arriba:

```bash
docker compose ps
```

Cuando reinicies, la `N8N_EXPRESSIONS_ALLOWED_ENV_VARS` le da permiso al workflow de n8n para leer la variable `CHATBOT_API_TOKEN` y usarla en los nodos.

### 2.6 Cómo usa n8n ese token dentro del flujo

En el workflow de n8n hay un nodo llamado **`Obtener_configuracion_agente`** que llama a
`https://aristosoluciones.integraia.lat/ai_chatbot_1_portal/configuracion_agente`.

Ese nodo envía la clave en el cuerpo (body) del mensaje así:

```json
{
  "token": "{{ $env.CHATBOT_API_TOKEN || '' }}"
}
```

Traducción: "coge el token de la variable de entorno CHATBOT_API_TOKEN del contenedor". Por eso:

- si cambias el token en el `docker-compose.n8n.yml`, el nodo lo toma solo (no tienes que tocarlo);
- si cambias el token en Odoo y no en Docker (o al revés), la respuesta será **401 Token inválido**.

> Alternativa técnica: n8n podría enviar la misma clave en el encabezado (header) `x-chatbot-token`
> en lugar del campo `token` del cuerpo; Odoo acepta cualquiera de las dos formas.

---

## 3. El workflow de n8n (cómo importarlo)

El robot n8n se program visualmente con "flujos" (workflows). Los flujos oficiales de este proyecto están en la carpeta:
`ai_chatbot_1_portal/n8n/`

| Archivo | Cuál es |
|---|---|
| `chatbot_create_lead_0.json` | El flujo principal y actual (`chatbot_create_lead_0_con_menu_whatsapp`) |
| `chatbot-simple_1_subflow.json` | Un sub-flujo de apoyo/alternativa |

Para importarlo en n8n:

1. Entra a `https://n8n.aristosoluciones.integraia.lat` (usuario `admin` y la contraseña que está en `secrets/n8n_password.txt` del servidor).
2. Pulsa **Workflows** (menú izquierdo) → **Create Workflow** → y con el tres-puntos elige **Import from JSON**.
3. Selecciona el archivo `chatbot_create_lead_0.json`.
4. Revisa que en el nodo **`Obtener_configuracion_agente`** la URL señale tu dominio: `https://aristosoluciones.integraia.lat/ai_chatbot_1_portal/configuracion_agente`.
5. Guarda y deja el flujo **Open** (activado) con el interruptor de la parte superior.

---

## 4. Docker: comandos útiles del n8n (copia y pega)

### Ver registros de n8n en vivo

```bash
cd /home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19
docker compose logs -f n8n
```

Pulsa `Ctrl + C` para salir de la vista en vivo.

### Ver los últimos registros

```bash
docker compose logs --tail 200 n8n
```

### Reiniciar n8n

```bash
docker compose up -d --force-recreate n8n
```

### Estado de todos los servicios

```bash
./6_status_all_services.sh
```

---

## 5. Prueba rápida: comprobar que la llave funciona

Desde el servidor (o desde cualquier cosa que pueda llamar al dominio público), ejecuta:

```bash
curl -X POST https://aristosoluciones.integraia.lat/ai_chatbot_1_portal/configuracion_agente \
  -H "Content-Type: application/json" \
  -d '{"token":"PEGA_AQUI_TU_TOKEN_DE_N8N"}'
```

Resultado esperado:

- **Correcto:** te responde un JSON con `system_prompt`, `fallback_message` y los flujos activos.
- **Error:** `{"success": false, "error": "Token inválido"}` con código 401 → los tokens no coinciden (vuelve a sección 2).

---

## 6. Problemas comunes

| Síntoma | Causa | Solución |
|---|---|---|
| n8n responde con error `401 Token inválido` en `configuracion_agente` | La clave de Odoo y la de Docker no coinciden | Repasa sección 2 (pasos 2.4 y 2.5) |
| El bot responde siempre el "mensaje fallback" | No recibe la configuración desde Odoo | Prueba el curl del punto 5 y revisa `docker compose logs n8n` |
| Odoo no genera el lead tras terminar el chat | El flujo n8n no está activo o el webhook `capturar_lead_http` apunta a otra URL | Activa el flujo en n8n y compara la URL con la sección 1 |
| El bot no conoce el negocio (prompt) | El "Mensaje del sistema (negocio)" en Ajustes → Configuración del agente (n8n) está vacío | Pega ahí la información comercial y Guardar |

---

## 7. Resumen en 6 líneas

1. n8n es el robot que conversa; Odoo guarda los datos y crea los leads.
2. El token de n8n va en **2 sitios iguales**: Ajustes de Odoo → "API Token para n8n" y `docker-compose.n8n.yml` → `CHATBOT_API_TOKEN`.
3. Que **no coincidan** = error `Token inválido` en el nodo `Obtener_configuracion_agente`.
4. El flujo principal se importa desde `ai_chatbot_1_portal/n8n/chatbot_create_lead_0.json`.
5. Después de cambiar el token en Docker: `docker compose up -d --force-recreate n8n`.
6. ¿Dudas? Mira `docker compose logs n8n` antes de tocar nada.