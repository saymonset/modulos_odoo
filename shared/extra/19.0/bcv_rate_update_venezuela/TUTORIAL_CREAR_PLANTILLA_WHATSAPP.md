# Tutorial: Crear plantilla WhatsApp `pedido_confirmado_ubicacion`

## 1. Requisito previo

La plantilla ya debe existir en **Meta** (Administrador de WhatsApp) con:
- Nombre: `pedido_confirmado_ubicacion`
- Idioma: Spanish
- Tipo: Utility
- Parámetros: `{{1}}` a `{{6}}`

![Plantilla en Meta](https://i.imgur.com/placeholder.png)

## 2. Crear en Odoo

**Ir a**: WhatsApp → Plantillas → **Nuevo**

| Campo | Valor |
|---|---|
| **Nombre para mostrar** | `Pedido Confirmado Ubicación` |
| **Nombre técnico** | `pedido_confirmado_ubicacion` |
| **Idioma** | `Español` |
| **Encabezado de video** | No marcar |
| **Esquema de parámetros (JSON)** | `{"1": "nombre", "2": "num_orden", "3": "direccion", "4": "horario", "5": "telefono", "6": "empresa"}` |
| **Cantidad de parámetros** | `6` |
| **Active** | ✅ |

### 3. Mapeo de parámetros Meta ↔ Odoo

| Parámetro Meta | JSON label | Origen en Odoo (código) |
|---|---|---|
| `{{1}}` | `nombre` | `order.partner_id.name` |
| `{{2}}` | `num_orden` | `order.name` |
| `{{3}}` | `direccion` | Dirección de la empresa (calle + ciudad + zip) |
| `{{4}}` | `horario` | `order.company_id.schedule_info` |
| `{{5}}` | `telefono` | Teléfono de empresa (limpio: `0414...`) |
| `{{6}}` | `empresa` | `order.company_id.name` |

### 4. Verificar

1. Guardar la plantilla en Odoo
2. Ir a WhatsApp → Cuentas WABA → Abrir `WhatsappSaymon`
3. Click **"Probar conexión"** → debe responder OK
4. Hacer una compra de prueba en la tienda

### 5. Troubleshooting

| Síntoma | Causa probable |
|---|---|
| No llega el mensaje | Partner sin teléfono o template no activa |
| Error "Template does not exist" | El nombre técnico no coincide con Meta (exacto) |
| WABA test connection falla | Token expirado o Phone Number ID incorrecto |
