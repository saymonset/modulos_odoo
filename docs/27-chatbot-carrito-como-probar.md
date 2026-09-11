# Cómo probar `chatbot_cart` (staging)

> **Módulo:** `shared/extra/19.0/chatbot_cart`
> **Spec:** `specs/27-chatbot-carrito-whatsapp.md`
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
chatbot_cart: 46 tests 3.82s 1120 queries
```

Sin errores (`ERROR:`/`FAILED`). Los tests cubren: CRUD del carrito, resumen
VES/USD/COP, búsqueda de productos, materialización de `sale.order`, clasificador
determinista y prompt del carrito.

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

### b) Agregar al carrito (usa el nombre, no el número)

```bash
curl -s -X POST http://localhost:28069/chatbot_cart/procesar \
  -H 'Content-Type: application/json' -d '{"session_id":"demo-001","valor":"agrega 2 pizzas"}'
```

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

## 4. Nivel 3 — Flujo WhatsApp real (opcional, requiere infra n8n)

1. Verificar que el prompt del agente incluye el carrito:

```bash
curl -s -X POST http://localhost:28069/ai_chatbot_1_portal/configuracion_agente \
  -H 'Content-Type: application/json' \
  -H 'x-chatbot-token: OOm8oXtJ3Df03_El39HoYcor2myq7eKcg22_uxXabrg' -d '{}'
```

El `system_prompt` devuelto debe contener `=== CARRITO DE COMPRAS (flujo_carrito) ===`.
(El token está en `ir_config_parameter.ai_chatbot_1_portal.api_token`.)

2. Escribir al WhatsApp del negocio, pedir un producto y confirmar la compra → n8n activa
`flujo_carrito` y delega a `/chatbot_cart/procesar`. Requiere `waba.account` configurado y
webhook `/whatsapp/webhook` verificado en Meta.

## 5. Limitaciones actuales (importantes al probar)

- **"Responde el número" no funciona aún:** `ultima_busqueda` no se guarda al buscar, así
  que la referencia numérica de la lista no resuelve. **Usa el nombre del producto.**
- **Partner genérico al pagar sin teléfono:** `_resolver_partner` sin teléfono toma el
  último `whatsapp.history` entrante global (sin filtrar por conversación) o crea
  "Cliente Chatbot {session_id}".
- **COP desactivado** en esta BD (`cop_show_fields=False`); para probar COP hay que
  activarlo en la compañía y re-fetchear la tasa.

## 6. Mapa de criterios de aceptación del spec

| Criterio | Cómo probarlo |
|---|---|
| Búsqueda devuelve imagen + precio VES/USD | `buscar` con "pizza" |
| Agregar / modificar / quitar | `procesar` con "agrega 2 pizzas", "cambia la pizza a 3", "quita la pizza" |
| "ver carrito" con totales consistentes | `procesar` con "ver carrito" o `consultar` |
| COP según `cop_show_fields` | activar/desactivar el flag en la compañía y repetir `consultar` |
| "cancelar" no destruye el carrito | `procesar` con "cancelar" (ofrece guardar/vaciar/seguir) |
| "ayuda" disponible | `procesar` con "ayuda" |
| Vaciar pide confirmación | `procesar` con "vaciar" (solicita confirmación) |
| Producto inexistente con mensaje amigable | `procesar`/`buscar` con "zzznoexiste" |
| Mini-estado tras cada operación | observar `texto_para_usuario` tras agregar/quitar |
| Pagar materializa `sale.order` | `pagar` + consulta en BD (`sale_order`) |
| Carrito persiste entre mensajes | repetir llamadas con el mismo `session_id` |