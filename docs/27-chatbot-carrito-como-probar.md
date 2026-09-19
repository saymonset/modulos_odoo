# Cómo probar `chatbot_cart` (staging)

> **Módulo:** `shared/extra/19.0/chatbot_cart`
> **Spec:** `specs/27-chatbot-carrito-whatsapp.md` (implementación) y `specs/28-carrito-fixes-prueba-whatsapp.md` (fixes + prueba WhatsApp)
> **Entorno de pruebas:** contenedor `odoo-19-web-leads`, base `dbodoo19`, URL `http://localhost:28069`

## 1. Cómo encaja (30 segundos)

En producción el flujo es: **WhatsApp → Meta webhook → n8n → Odoo**. n8n pide a Odoo el
prompt vía `configuracion_agente` (que `chatbot_cart` extiende con las instrucciones del
carrito). Cuando el usuario confirma que quiere comprar, n8n activa `flujo_carrito` y
delega el mensaje a **`/chatbot_cart/procesar`**; Odoo devuelve `texto_para_usuario`
(+ `imagenes`) y n8n lo envía por WhatsApp.

**Para probar sin WhatsApp ni n8n, llamamos los endpoints REST directamente**
(son `auth='public'`, `csrf=False`). Eso es lo práctico de este tutorial.

## 2. Nivel 1 — Tests automáticos (ya en verde)

```bash
# 1. Limpiar cache de bytecode
find shared/extra/19.0/chatbot_cart -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; true

# 2. Upgrade + tests en una sola pasada
docker exec odoo-19-web-leads python3 /opt/odoo/odoo-core/odoo-bin \
    -d dbodoo19 -u chatbot_cart --test-enable --stop-after-init --log-level=test
```

Resultado esperado:

```
chatbot_cart: 55 tests 4.93s 1345 queries
```

Sin errores (`ERROR:`/`FAILED`). Los tests cubren: CRUD del carrito, resumen
VES/USD/COP, búsqueda de productos, materialización de `sale.order`, clasificador
determinista, prompt del carrito, guardado de `ultima_busqueda` y resolución de
partner por teléfono/sesión (SPEC 28).

## 3. Nivel 2 — Prueba manual por HTTP

**Prerrequisitos (ya listos en staging):**

- Módulo `chatbot_cart` instalado (`ir_module_module.state = installed`).
- Productos reales para buscar: *Pizza* (id 237), *Refresco*, *Servicio Mantenimiento VPS*.
- La tasa BCV se auto-fetchea (con "pizza" verás `Bs. 9,989.86 / $12.00`).
- COP desactivado en esta BD (`res.company.cop_show_fields = False`).

**Regla de oro:** usa **siempre el mismo `session_id`** (ej. `demo-001`). El carrito vive
en `chatbot.session` por ese ID.

### a) Buscar productos

```bash
curl -s -X POST http://localhost:28069/chatbot_cart/buscar \
  -H 'Content-Type: application/json' -d '{"session_id":"demo-001","query":"pizza"}'
```

Devuelve `texto_para_usuario` (lista numerada con precios VES/USD) + `imagenes`.

### b) Agregar al carrito (por nombre o por número de la lista)

```bash
curl -s -X POST http://localhost:28069/chatbot_cart/procesar \
  -H 'Content-Type: application/json' -d '{"session_id":"demo-001","valor":"agrega 2 pizzas"}'
```

También funciona la referencia numérica tras una búsqueda (`ultima_busqueda` se guarda
automáticamente): busca "pizza", y luego `"valor":"agrega 1"` añade el primer resultado.

Respuesta esperada:

```
✅ Agregué 2 x Pizza al carrito. 🛒 1 item(s) — $24.00
```

> **Nota:** `procesar` clasifica la acción con IA (`gpt-4o-mini`, hay un `openai.config`
> activo). Si la API falla, cae a un clasificador determinista por palabras clave. Para
> forzar el determinista sin costo: desactivar `openai.config` en Ajustes.

### c) Ver carrito / modificar / quitar

```bash
... -d '{"session_id":"demo-001","valor":"ver carrito"}'
... -d '{"session_id":"demo-001","valor":"cambia la pizza a 3"}'
... -d '{"session_id":"demo-001","valor":"quita la pizza"}'
```

### d) Ayuda / cancelar / vaciar

```bash
... -d '{"session_id":"demo-001","valor":"ayuda"}'
... -d '{"session_id":"demo-001","valor":"cancelar"}'
... -d '{"session_id":"demo-001","valor":"vaciar"}'
```

### e) Resumen JSON (para inspeccionar items/totales)

```bash
curl -s -X POST http://localhost:28069/chatbot_cart/consultar \
  -H 'Content-Type: application/json' -d '{"session_id":"demo-001"}'
```

### f) Pagar (materializa `sale.order` + `action_confirm`)

```bash
curl -s -X POST http://localhost:28069/chatbot_cart/pagar \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"demo-001","conversation_id":"conv-test","account_id":"1"}'
```

Respuesta esperada: `✅ Pedido SO… confirmado!`. Crea un `sale.order` en estado `sale` y
un partner ("Cliente Chatbot demo-001" si no hay teléfono).

### Verificar en BD

```bash
docker exec odoo-db19-leads psql -U odoo -d dbodoo19 -c \
  "SELECT session_id, estado FROM chatbot_session WHERE session_id='demo-001';"

docker exec odoo-db19-leads psql -U odoo -d dbodoo19 -c \
  "SELECT name, state, partner_id FROM sale_order WHERE client_order_ref='demo-001';"
```

El JSON de `estado` debe contener `"modo": "CARRITO"` y el `carrito` con los `items`.

## 4. Nivel 3 — Flujo WhatsApp real (end-to-end, staging)

El objetivo es probar el flujo completo con el WhatsApp real del negocio, pero
**apuntando n8n a staging** para no tocar prod.

**Prerrequisitos (verificados en staging):**

- Cuenta `waba.account` "whatsapp 0412" activa con `access_token` y `phone_number_id`.
- `flujo_carrito` activo en `chatbot.flujo` (routing_key `flujo_carrito`).
- Módulo `chatbot_cart` instalado y la tasa BCV auto-fetcheada.

### a) Redirigir n8n a staging (temporal)

Meta sigue enviando los mensajes del mismo número a n8n. Lo único que cambia es a qué
Odoo llama n8n:

1. En el workflow de n8n, cambiar la **URL base de Odoo** de los nodos HTTP de prod
   (`http://<prod>:18069` o el dominio) a staging (`http://<staging>:28069`).
2. Verificar con `curl` que staging responde: `curl -s -o /dev/null -w "%{http_code}" http://localhost:28069/web/login` → `200`.
3. **Importante:** esto desvía el tráfico real de prod. Usa una ventana corta de prueba y
   revierte el paso (f) al terminar.

### b) Verificar el prompt del agente

```bash
curl -s -X POST http://localhost:28069/ai_chatbot_1_portal/configuracion_agente \
  -H 'Content-Type: application/json' \
  -H 'x-chatbot-token: OOm8oXtJ3Df03_El39HoYcor2myq7eKcg22_uxXabrg' -d '{}'
```

El `system_prompt` devuelto debe contener `=== CARRITO DE COMPRAS (flujo_carrito) ===`.
(El token está en `ir_config_parameter.ai_chatbot_1_portal.api_token`.)

> **Token staging:** al redirigir n8n a staging, el `CHATBOT_API_TOKEN` de n8n debe
> coincidir con `ai_chatbot_1_portal.api_token` de la **BD de staging** (`dbodoo19`),
> o `Obtener_configuracion_agente` devolverá 401 "Token inválido" (gotcha de la spec 08).

### c) Configuración en n8n (única modificación requerida)

**No se edita ningún prompt.** El prompt ya se baja automático en el nodo
`Obtener_configuracion_agente`. Lo único que falta es la **rama de ruteo** para
`flujo_carrito`, porque `/chatbot_cart/procesar` es un endpoint nuevo que el workflow
actual no conoce:

```
[Obtener_configuracion_agente]            ← sin cambios (prompt + flow_map)
        ↓
[Agente OpenAI]                           ← sin cambios (responde JSON con flow_name)
        ↓
[Switch/IF: flow_name == 'flujo_carrito'] ← NUEVO
   ├─ true  → [HTTP POST /chatbot_cart/procesar]  ← NUEVO
   │            body: {session_id, conversation_id, account_id, platform, valor}
   │          → [Enviar texto_para_usuario (+ imagenes) por WhatsApp]  ← NUEVO
   └─ false → [camino actual: inicioagendar / respuesta normal]
```

Config del nodo **HTTP Request** (rama `true`):

- **Method:** `POST`
- **URL:** `http://<staging>:28069/chatbot_cart/procesar` (sin token; endpoint `auth='public'`)
- **Body (JSON):**

```json
{
  "session_id": "{{ $('Recibir mensaje').item.json.session_id }}",
  "conversation_id": "{{ $('Recibir mensaje').item.json.conversation_id }}",
  "account_id": "{{ $('Recibir mensaje').item.json.account_id }}",
  "platform": "whatsapp",
  "valor": "{{ $('Agente OpenAI').item.json.input }}"
}
```

(Ajusta los nombres de los nodos a los de tu workflow; `session_id`, `conversation_id`
y `account_id` salen del webhook de WhatsApp que n8n ya procesa.)

Respuesta del endpoint: `texto_para_usuario` (lo envías por WhatsApp) y `imagenes`
(lista de URLs `/web/image/...` que puedes descargar y mandar como media si quieres
mostrar la foto del producto).

El camino `false` (ningún flujo o flujos normales) sigue como hoy.

### d) Ejecutar el flujo por WhatsApp

Fases y criterio de éxito:

1. **Activación por el agente.** Escribe al WhatsApp del negocio pidiendo un producto
   (ej. "tienen pizza?") y confirma la compra cuando el bot la ofrezca (ej. "sí quiero
   comprar"). El agente debe activar `flujo_carrito` (política `confirmation`). Si no
   activa, prueba con frases más directas: "quiero pedir", "quiero comprar".
2. **Operaciones del carrito.** Con el carrito activo: "agrega 2 pizzas", "ver carrito",
   "cambia la pizza a 3", "quita la pizza", "ayuda", "cancelar". Cada respuesta debe
   confirmar la acción y mostrar el mini-estado (items + total).
3. **Pago.** Escribe "pagar". Debe responder `✅ Pedido SO… confirmado!`. En BD, la orden
   debe quedar `state=sale` con el **partner resuelto por el teléfono** del mensaje (ya no
   usa historial global).
4. **Vaucher por imagen.** Envía una foto del vaucher por WhatsApp. Debe descargarse
   (`waba.account.download_media`) y quedar adjunta como `ir.attachment` a esa orden.

### e) Verificar en BD (tras la prueba)

```bash
# Orden + partner
docker exec odoo-db19-leads psql -U odoo -d dbodoo19 -c \
  "SELECT so.name, so.state, rp.name AS partner, rp.phone \
     FROM sale_order so JOIN res_partner rp ON rp.id = so.partner_id \
    WHERE so.client_order_ref IS NOT NULL ORDER BY so.id DESC LIMIT 5;"

# Vaucher adjunto a la orden
docker exec odoo-db19-leads psql -U odoo -d dbodoo19 -c \
  "SELECT name, res_model, res_id, mimetype FROM ir_attachment \
    WHERE res_model='sale.order' ORDER BY id DESC LIMIT 5;"
```

### f) Revertir la redirección

Al terminar, volver a apuntar los nodos HTTP de n8n a prod y confirmar que el WhatsApp
del negocio responde normal.

## 5. Comando catálogo (SPEC 33)

Desde cualquier turno del carrito, el usuario puede pedir el catálogo general:

```bash
# Catálogo (primeros 5 productos vendibles)
curl -s -X POST http://localhost:28069/chatbot_cart/procesar \
  -H 'Content-Type: application/json' -d '{"session_id":"demo-001","valor":"catálogo"}'
```

También responden a "qué tienen?", "productos", "qué venden?". La respuesta lista
hasta 5 productos con **precio + descripción** (`description_sale`) y la mini-guía
persistente. Para la siguiente página:

```bash
... -d '{"session_id":"demo-001","valor":"más"}'
```

Notas:

- La paginación vive en `carrito.pagina_catalogo` de la sesión.
- Con el carrito vacío, "ver carrito" muestra el catálogo en vez de "está vacío" (SPEC 33).
- La respuesta marca `botones` (`catálogo` / `ver carrito` / `pagar`); n8n los envía como
  interactive buttons si la plataforma lo soporta, con fallback a texto plano.

## 6. Limitaciones actuales (importantes al probar)

- **COP desactivado** en esta BD (`cop_show_fields=False`); para probar COP hay que
  activarlo en la compañía y re-fetchear la tasa.
- **Partner sin teléfono en la sesión:** si ni el mensaje ni `estado['datos_paciente']`
  tienen teléfono, el pago crea el partner genérico "Cliente Chatbot {session_id}". Con
  teléfono (recibido o capturado en la sesión), se resuelve/crea por ese número.
- **La clasificación IA depende de OpenAI:** si `openai.config` falla, `procesar` cae al
  clasificador determinista por palabras clave; los comandos base ("agrega", "ver
  carrito", "pagar", etc.) funcionan igual.

## 7. Mapa de criterios de aceptación del spec

| Criterio | Cómo probarlo |
|---|---|
| Búsqueda devuelve imagen + precio VES/USD | `buscar` con "pizza" |
| "Responde el número" agrega el producto correcto | `buscar` "pizza" y luego `procesar` "agrega 1" |
| Agregar / modificar / quitar | `procesar` con "agrega 2 pizzas", "cambia la pizza a 3", "quita la pizza" |
| Partner por teléfono (recibido o de la sesión) | `pagar` con/sin `phone` y consultar `res_partner` de la orden |
| "ver carrito" con totales consistentes | `procesar` con "ver carrito" o `consultar` |
| COP según `cop_show_fields` | activar/desactivar el flag en la compañía y repetir `consultar` |
| "cancelar" no destruye el carrito | `procesar` con "cancelar" (ofrece guardar/vaciar/seguir) |
| "ayuda" disponible | `procesar` con "ayuda" |
| Vaciar pide confirmación | `procesar` con "vaciar" (solicita confirmación) |
| Producto inexistente con mensaje amigable | `procesar`/`buscar` con "zzznoexiste" |
| Mini-estado tras cada operación | observar `texto_para_usuario` tras agregar/quitar |
| Pagar materializa `sale.order` | `pagar` + consulta en BD (`sale_order`) |
| Carrito persiste entre mensajes | repetir llamadas con el mismo `session_id` |
| "catálogo" muestra 5 productos con precio+descripción | `procesar` con "catálogo"; "más" pagina (SPEC 33) |
| "ver carrito" con carrito vacío muestra catálogo | `procesar` con "ver carrito" sin items (SPEC 33) |
| Respuestas del carrito marcan `botones` | inspeccionar `botones` en el JSON de `procesar` (SPEC 33) |
| Descripción vacía no rompe la tarjeta | producto sin `description_sale` en el catálogo (SPEC 33) |