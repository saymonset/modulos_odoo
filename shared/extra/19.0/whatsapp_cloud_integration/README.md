# Módulo WhatsApp Cloud API para Odoo 19

Este módulo integra Odoo 19 con la **Cloud API de WhatsApp Business** de Meta. Permite enviar mensajes usando plantillas aprobadas, recibir mensajes entrantes mediante webhook y llevar un historial completo de conversaciones.

## 📋 Requisitos previos

- Odoo 19 instalado y accesible desde internet (para el webhook).
- Una cuenta de **Facebook Business Manager**.
- Una **aplicación de negocio** en [Meta for Developers](https://developers.facebook.com/apps).
- Un número de **WhatsApp de prueba** (proporcionado por Meta) o un número verificado (para producción).

---

## 🚀 Paso 1: Configuración en Meta

### 1.1 Crear la app de negocio

1. Ve a [developers.facebook.com/apps](https://developers.facebook.com/apps) → **Crear app**.
2. Selecciona **Negocio** → completa el nombre y correo.
3. Una vez creada, en el menú lateral elige **WhatsApp** → **Configuración de la API**.

### 1.2 Obtener número de prueba

1. Dentro de **Configuración de la API**, en la sección *Enviar y recibir mensajes*:
   - **De**: aparecerá un número como `+1 555 190 5155` (es tu número de prueba). Copia su **ID** (generalmente un número largo, p.ej. `1062113076989009`). No cierres esta pantalla, la necesitarás.
   - **Para**: agrega el número de WhatsApp de tu cliente o del tester (máximo 5 números). Formato internacional sin el signo `+`, por ejemplo `584142711347`.

### 1.3 Generar token de acceso (System User)

**Importante**: No uses el token que genera el panel de "Inicio rápido". Necesitas un token de **Usuario del Sistema**.

1. Ve a **Business Manager** → **Configuración** → **Usuarios del sistema**.
2. Crea un nuevo usuario (ej. `whatsapp_integration`).
3. Asígnale los siguientes permisos:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
   - `business_management`
4. Haz clic en **Generar nuevo token**, selecciona tu app y los mismos permisos. Copia el token resultante.
5. (Opcional) Verifica el token en el [depurador de tokens](https://developers.facebook.com/tools/debug/accesstoken/).

### 1.4 Obtener el ID de la WABA (WhatsApp Business Account)

1. En **Business Manager** → **Configuración** → **Cuentas de WhatsApp**.
2. Ahí verás una cuenta (normalmente llamada *Test WhatsApp Business Account*). Copia su **ID** (p.ej. `1634570824541885`).

### 1.5 Configurar el webhook en Meta

1. En tu app de Meta Developers, ve a **WhatsApp** → **Configuración de la API** → **Webhook**.
2. Haz clic en **Editar** e ingresa:
   - **Callback URL**: `https://tudominio.com/whatsapp/webhook` (reemplaza `tudominio.com` con la URL pública de tu Odoo).
   - **Verify token**: Elige un token secreto, por ejemplo `miclave123`. **Guárdalo**, lo usarás en Odoo.
3. Haz clic en **Verificar y guardar**. Meta enviará una solicitud `GET` a tu Odoo. Si la configuración es correcta, se verificará automáticamente.
4. Posteriormente, en la misma sección, suscríbete a los campos deseados (al menos `messages`).

---

## 📦 Paso 2: Instalación del módulo en Odoo

1. Copia la carpeta `whatsapp_cloud_integration` dentro de la carpeta `addons` de tu Odoo 19.
2. Ve a **Aplicaciones** → **Actualizar lista de módulos**.
3. Busca `WhatsApp Cloud API Integration` e instálalo.

---

## ⚙️ Paso 3: Configuración en Odoo

1. Una vez instalado, ve al menú **WhatsApp** → **Configuración** → **Cuentas WABA**.
2. Crea un nuevo registro y completa los siguientes campos:
   - **Nombre de la cuenta**: Por ejemplo, *WhatsApp Pruebas*.
   - **Número de teléfono visible**: `+1 555 190 5155` (el de prueba).
   - **Phone Number ID**: El ID que copiaste antes (ej. `1062113076989009`).
   - **Access Token**: El token del usuario del sistema.
   - **WhatsApp Business Account ID**: El ID de la WABA (ej. `1634570824541885`).
   - **Verify Token para Webhook**: El mismo token secreto que pusiste en Meta (ej. `miclave123`).
   - Activa el registro (campo `Activo`).
3. Guarda los cambios y haz clic en **Test Connection** para verificar que los datos son correctos.

---

## 💬 Paso 4: Enviar mensajes

### Desde un contacto (partner)

1. Abre cualquier contacto que tenga número de teléfono móvil (campo `Móvil`).
2. En el botón **Acción** (o en un botón dedicado) verás **Enviar mensaje WhatsApp**. Haz clic.
3. Completa:
   - **Plantilla**: El nombre exacto de la plantilla aprobada en Meta (ej. `pedido_confirmado_con_ubicacion`).
   - **Parámetros**: Un arreglo JSON con los valores para `{{1}}`, `{{2}}`, etc.  
     Ejemplo: `["Simón", "Orden #123", "+58414271652", "Mi Tienda"]`.
4. Haz clic en **Enviar**. El sistema mostrará una notificación con el ID del mensaje y lo guardará en el historial.

### Desde el menú principal

También puedes usar **WhatsApp** → **Enviar mensaje** (si agregaste una acción de ventana dedicada).

---

## 📜 Paso 5: Historial y recepción de mensajes

- Todos los mensajes enviados se registran en **WhatsApp** → **Historial**.
- Los mensajes **entrantes** (enviados por clientes a tu número de WhatsApp) también se guardan automáticamente cuando el webhook los recibe.
- Los contactos que escriban por primera vez se crearán automáticamente como un partner con su número de teléfono como nombre y móvil.

---

## 🛠️ Solución de problemas frecuentes

| Error en Odoo | Causa posible | Solución |
|---------------|----------------|-----------|
| `❌ Error 133010: Account not registered` | El número de prueba no se ha registrado en la Cloud API. | Ejecuta manualmente el registro usando Postman: `POST /{phone_number_id}/register` con `{"messaging_product":"whatsapp","pin":"123456"}`. |
| `❌ Error 100: The parameter pin is required` | El PIN es obligatorio al registrar el número. | Incluye el campo `pin` en la llamada de registro. |
| `❌ Error 132001: Template does not exist in translation` | El idioma de la plantilla no coincide. | Asegúrate de que la plantilla exista en español y usa `"language": {"code": "es"}`. |
| El webhook no se verifica | Verify token incorrecto o URL no accesible. | Verifica que tu Odoo sea público (o usa un túnel como ngrok). Revisa que el token coincida exactamente. |
| Los mensajes no se reciben | El webhook no está suscrito a los campos adecuados o Meta no envía las notificaciones. | En la configuración de la app en Meta, ve a **Webhook** y suscríbete a `messages`. Revisa los logs de Odoo (`/web/debug/logs`). |

---

## 🔁 Cron y tareas programadas

El módulo incluye un cron opcional (`Sincronización manual de mensajes WhatsApp`) que está **desactivado por defecto**. Puedes activarlo si tu Odoo no puede recibir webhooks (por ejemplo, en redes internas sin acceso público). Sin embargo, se recomienda usar el webhook, ya que es instantáneo y más eficiente.

---

## 📚 Notas para producción

- Cuando pases a producción, deberás:
  - Agregar un número de teléfono real (verificado) en **Business Manager** → **Cuentas de WhatsApp**.
  - Configurar un **método de pago** en Meta Developers.
  - Solicitar la aprobación de tus plantillas personalizadas.
- Los números de prueba tienen validez de **90 días**. Después de ese período, deberás generar un nuevo número o migrar a uno real.

---

## 🤝 Soporte

Para cualquier incidencia, revisa primero los **logs de Odoo** (ajustes → técnica → logs) y los registros del webhook en **Historial de WhatsApp**. Si el problema persiste, consulta la [documentación oficial de Meta Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api) o contacta al desarrollador del módulo.

---

**Versión del módulo:** 19.0.1.0.0  
**Compatibilidad:** Odoo 19 (Community / Enterprise)  
**Licencia:** LGPL-3