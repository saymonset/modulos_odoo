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
   - **De**: aparecerá un número como `+1 555 190 5155` (es tu número de prueba). Copia su **ID** (generalmente un número largo, p.ej. `1062113076989009`). No cierres esta pantalla.
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

## 🧩 **Paso 2: Crear una plantilla de mensaje en Meta (fundamental y engorroso)**

**Sin una plantilla aprobada, no podrás enviar mensajes.** La Cloud API de Meta exige que uses plantillas predefinidas para todo mensaje saliente (excepto en el modo de prueba limitado, pero igual debes crearlas).

### 2.1 Acceder al administrador de plantillas

1. Dentro de tu app de Meta Developers, ve a **WhatsApp** → **Administrador de plantillas**.
2. Haz clic en **Crear plantilla**.

### 2.2 Configurar la plantilla

- **Nombre de la plantilla**: Solo minúsculas, números y guiones bajos. Ejemplo: `pedido_confirmado_con_ubicacion`.
- **Categoría**: Siempre elige **Utilidad** para mensajes transaccionales (confirmaciones, códigos, facturas). No uses Marketing si no es promocional, ya que tiene reglas más estrictas.
- **Idioma**: Elige `Español (ES)` o `Inglés (US)`. Debe coincidir con el idioma que luego seleccionarás en Odoo.

### 2.3 Escribir el cuerpo del mensaje con variables

El cuerpo puede incluir texto fijo y variables `{{1}}`, `{{2}}`, etc. Cada variable será reemplazada al enviar el mensaje.

**Ejemplo de cuerpo para confirmación de pedido con retiro o entrega:**
Hola {{1}},

✅ Tu pedido #{{2}} ha sido confirmado.

📍 Dirección / lugar de retiro o entrega:
{{3}}

🕒 Horario : {{4}}

📞 Consultas o dudas: {{5}}

Gracias por comprar en {{6}} 🛍️

text

- Las variables están numeradas en el orden de aparición.
- Puedes usar hasta 20 variables.

### 2.4 Enviar a revisión y aprobación

- Haz clic en **Enviar para revisión**.
- Estado: *Borrador* → *En revisión* → *Aprobada*. Puede tardar desde segundos hasta horas.
- **Solo las plantillas aprobadas** pueden usarse con números reales. Durante el desarrollo con números de prueba, Meta permite el envío sin aprobación, pero igual debes crearlas.

---

## 📦 **Paso 3: Instalación del módulo en Odoo**

1. Copia la carpeta `whatsapp_cloud_integration` dentro de la carpeta `addons` de tu Odoo 19.
2. Ve a **Aplicaciones** → **Actualizar lista de módulos**.
3. Busca `WhatsApp Cloud API Integration` e instálalo.

---

## ⚙️ **Paso 4: Configurar la cuenta WhatsApp (WABA) en Odoo**

1. Ve al menú **WhatsApp** → **Cuentas WABA**.
2. Crea un nuevo registro y completa:
   - **Nombre de la cuenta**: Por ejemplo, *WhatsApp Pruebas*.
   - **Número de teléfono visible**: El número de prueba de Meta (ej. `+1 555 190 5155`).
   - **Phone Number ID**: El ID numérico que copiaste (ej. `1062113076989009`).
   - **Access Token**: El token del usuario del sistema.
   - **WhatsApp Business Account ID**: El ID de la WABA (ej. `1634570824541885`).
   - **Verify Token para Webhook**: El mismo token secreto que usaste en Meta (ej. `miclave123`).
   - Marca el campo **Activo**.
3. Guarda y haz clic en **Test Connection** para verificar que todo es correcto.

---

## 🧩 **Paso 5: Registrar la plantilla dentro del módulo de Odoo**

Este paso es **obligatorio** para que el módulo sepa qué plantillas tienes disponibles. No se sincroniza automáticamente con Meta; debes crear un registro manual por cada plantilla que hayas creado en Meta.

### 5.1 Ir a WhatsApp → Plantillas

Desde el menú principal: **WhatsApp** → **Plantillas**.

### 5.2 Crear un nuevo registro

Haz clic en **Nuevo** y completa los siguientes campos:

| Campo | Explicación | Ejemplo |
|-------|-------------|---------|
| **Nombre para mostrar** | Texto amigable que verán los usuarios de Odoo al seleccionar la plantilla. | `Confirmación de pedido con ubicación` |
| **Nombre técnico** | **Debe coincidir exactamente** con el nombre que pusiste en Meta (case-sensitive). | `pedido_confirmado_con_ubicacion` |
| **Idioma** | El mismo idioma que elegiste en Meta. | `Español` |
| **Esquema de parámetros (JSON)** | **Opcional pero muy recomendado**. Es un objeto JSON que describe cada variable `{{n}}`. Ayuda a documentar y a validar la cantidad de parámetros. | `{"1": "nombre_cliente", "2": "numero_pedido", "3": "direccion", "4": "horario", "5": "telefono", "6": "tienda"}` |
| **Active** | Mantén marcado para que la plantilla esté disponible. | ✔️ |

> **Nota sobre el esquema JSON**: Si no lo rellenas, la `Cantidad de parámetros` se mostrará como 0 y el módulo no podrá verificar que envías el número correcto de valores. Pero técnicamente no es obligatorio para el envío. Es solo una ayuda visual y de validación.

### 5.3 Guardar

Al guardar, si has rellenado el esquema correctamente, el campo **Cantidad de parámetros** se calculará automáticamente (p.ej. 6).

---

## 💬 **Paso 6: Enviar un mensaje usando la plantilla**

### 6.1 Envío manual desde un contacto

1. Abre cualquier contacto (partner) que tenga un número de teléfono en el campo **Móvil** (formato internacional sin espacios, ej. `+584142711347`).
2. En la vista formulario del contacto, busca el botón **Enviar mensaje WhatsApp** (está dentro del menú **Acción** o como botón inteligente si configuraste la vista). Si no lo ves, puedes ir a **WhatsApp** → **Enviar mensaje** (acción de ventana que puede estar en el menú o en las acciones del contacto).
3. Se abrirá un wizard con los siguientes campos:

   - **Cliente**: ya seleccionado.
   - **Cuenta WhatsApp**: elige la cuenta WABA que configuraste.
   - **Plantilla**: selecciona la plantilla que creaste previamente (aparecerá con el "Nombre para mostrar").
   - **Valores de parámetros (JSON)**: aquí debes escribir un array JSON con los valores para `{{1}}`, `{{2}}`, etc., **en el mismo orden** que definieron las variables.

   **Ejemplo para la plantilla de 6 variables:**

   ```json
   ["Simón Alberto", "s0003", "CC El Mercado, Av. Llano Adentro, Porlamar", "Abierto - Cierra a las 7:00 p.m.", "+584142711347", "integraia.lat"]
Haz clic en Enviar. Odoo mostrará una notificación con el ID del mensaje si todo fue bien. También se registrará en WhatsApp → Historial.

6.2 Envío programático desde otros modelos (ventas, facturas, etc.)
Puedes llamar al método send_to_partner del modelo whatsapp.template desde cualquier parte de Odoo. Ejemplo desde un pedido de venta:

python
def action_send_whatsapp_confirmation(self):
    template = self.env['whatsapp.template'].search([('name', '=', 'pedido_confirmado_con_ubicacion')], limit=1)
    if not template:
        raise UserError('Plantilla no encontrada')
    # Los valores deben estar en el orden correcto
    parameter_values = [
        self.partner_id.name,
        self.name,  # número de pedido
        self.partner_id.street or 'Dirección no disponible',
        '09:00 a 18:00 horas',
        self.company_id.phone,
        self.company_id.name,
    ]
    return template.send_to_partner(self.partner_id, parameter_values)
Este método crea internamente el wizard y lo envía automáticamente, mostrando el resultado como notificación.

📜 Paso 7: Historial y recepción de mensajes
Todos los mensajes enviados se guardan en WhatsApp → Historial.

Los mensajes entrantes (clientes que escriben a tu número) también se almacenan automáticamente si el webhook está funcionando.

Si el remitente no existe como partner, se crea automáticamente con su número de teléfono como nombre y como móvil.

🛠️ Solución de problemas frecuentes
Error en Odoo / Meta	Causa probable	Solución
❌ Error 132001: Template does not exist in translation	El nombre técnico o idioma no coinciden con los registrados en Meta.	Verifica el nombre exacto (incluyendo mayúsculas y guiones bajos) y el idioma.
❌ Error al enviar: esperaba 6 parámetros pero se recibieron 5	El array JSON tiene menos elementos que las variables {{n}} de la plantilla.	Cuenta las variables en el cuerpo de la plantilla y ajusta el array.
❌ Error 133010: Account not registered	El número de prueba no está registrado en la Cloud API.	Realiza el registro manual: POST https://graph.facebook.com/v25.0/{phone_number_id}/register con {"messaging_product":"whatsapp","pin":"123456"}. Puedes hacerlo con Postman o desde la terminal con curl.
El webhook no se verifica	Verify token incorrecto o URL no accesible.	Asegúrate de que tu Odoo sea público (usa ngrok si es local) y que el token coincida exactamente.
No aparece la plantilla en el wizard de envío	No se ha creado el registro en WhatsApp → Plantillas, o no está activo.	Ve a Plantillas y crea el registro con el nombre técnico correcto.
ValueError: Cannot convert whatsapp.template.display_name to SQL	Error antiguo por usar display_name en lugar de friendly_name.	Asegúrate de haber actualizado el módulo con el código corregido (versión que usa friendly_name).
🔁 Cron y tareas programadas
El módulo incluye un cron opcional (Check WhatsApp Incoming Messages) que está desactivado por defecto. Solo actívalo si tu Odoo no puede recibir webhooks (por ejemplo, en redes internas sin acceso público). La recepción por webhook es instantánea y más eficiente.

📚 Notas para producción
Cuando pases a producción:

Adquiere y verifica un número de teléfono real en Business Manager → Cuentas de WhatsApp.

Configura un método de pago en Meta Developers.

Solicita la aprobación de tus plantillas (si no lo has hecho).

Los números de prueba tienen validez de 90 días.

Las plantillas aprobadas pueden ser usadas con cualquier número real.

🤝 Soporte
Para incidencias, revisa primero:

Los logs de Odoo (Ajustes → Técnico → Logs).

El historial de WhatsApp (estado de los mensajes enviados).

La documentación oficial de Meta Cloud API.

Si el problema persiste, contacta al desarrollador del módulo.

Versión del módulo: 19.0.1.0.0
Compatibilidad: Odoo 19 (Community / Enterprise)
Licencia: LGPL-3