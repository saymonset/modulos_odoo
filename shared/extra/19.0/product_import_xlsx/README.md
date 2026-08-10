# Importación de Productos desde XLSX — Odoo 19 CE

Módulo para importar productos, variantes y atributos desde un archivo XLSX, con
soporte opcional de imágenes desde un ZIP.

## Requisitos

- Odoo 19 CE
- Módulos: `product`, `sale`, `stock`
- Python: `openpyxl` (se instala automáticamente con `pip install openpyxl`)

## Instalación

```bash
# 1. Copiar el módulo a la ruta de addons de Odoo
cp -r product_import_xlsx /opt/odoo/custom-addons/

# 2. Instalar openpyxl en el entorno de Odoo
pip install openpyxl

# 3. Actualizar lista de módulos en Odoo
#    Activar modo desarrollador → Aplicaciones → Actualizar lista de módulos

# 4. Instalar el módulo
#    Aplicaciones → buscar "Importación de Productos" → Instalar
```

## Tutorial paso a paso

### 1. Preparar el archivo XLSX

El archivo debe tener las siguientes columnas (en cualquier orden, el sistema
detecta los nombres automáticamente):

| Columna | Requerido | Descripción | Ejemplo |
|---|---|---|---|
| `Producto` | ✅ | Nombre del producto | `Alexa Show 8` |
| `Tipo` | ✅ | `Simple`, `Padre` o `Variante` | `Padre` |
| `Referencia` | ✅ | Código interno (default_code) | `ALEXA-8` |
| `Precio ($)` | ✅ | Precio de venta | `129.99` |
| `Atributo` | * | Nombre del atributo (solo Padre/Variante) | `Referencia` |
| `Valor Atributo` | * | Valor del atributo (solo Variante) | `115` |
| `Imagen (nombre archivo)` | | Nombre del archivo de imagen en el ZIP | `alexa_show8.jpg` |

#### Producto Simple

Una sola fila:

| Producto | Tipo | Referencia | Precio ($) | Atributo | Valor Atributo | Imagen |
|---|---|---|---|---|---|---|
| Marsriva | Simple | MARS-001 | 49.99 | | | marsriva.jpg |

#### Producto con variantes

Una fila **Padre** + varias filas **Variante**:

| Producto | Tipo | Referencia | Precio ($) | Atributo | Valor Atributo | Imagen |
|---|---|---|---|---|---|---|
| Alexa Show 8 | Padre | ALEXA-8 | 129.99 | Referencia | | alexa_show8.jpg |
| Alexa Show 8 | Variante | ALEXA-8-115 | 119.99 | Referencia | 115 | |
| Alexa Show 8 | Variante | ALEXA-8-155 | 139.99 | Referencia | 155 | |
| Alexa Show 8 | Variante | ALEXA-8-255 | 149.99 | Referencia | 255 | |

> **Nota:** El `Atributo` se escribe solo en la fila Padre. Las filas Variante
> heredan el atributo del Padre. Todos los productos con el mismo `Producto`
> se agrupan automáticamente.

### 2. Preparar el ZIP de imágenes (opcional)

Crear un archivo ZIP con las imágenes. Los nombres de archivo deben coincidir
con la columna `Imagen (nombre archivo)` del XLSX.

```
imagenes_productos.zip
├── marsriva.jpg
├── alexa_show8.jpg
├── protector_voltaje.jpg
└── ...
```

### 3. Importar desde Odoo

1. Ir a **Ventas → Configuración → Importar productos desde XLSX**
2. Seleccionar el archivo XLSX
3. (Opcional) Seleccionar el ZIP de imágenes
4. (Opcional) Elegir una categoría de producto
5. Click en **Importar**
6. Revisar el log de resultados

![Wizard de importación](static/description/wizard_screenshot.png)

### 4. Comportamiento

| Situación | Acción |
|---|---|
| `default_code` ya existe | Se omite (no se modifica) |
| Atributo ya existe | Se reutiliza |
| Valor de atributo ya existe | Se reutiliza |
| Producto Padre con variantes | Se crea el template + las variantes |
| Imagen no encontrada en ZIP | Se omite (producto sin imagen) |
| Error en un producto | Se loguea el error, continúa con el siguiente |

## Uso programático (desde otros módulos)

```python
from odoo import models, api

class MiModelo(models.Model):
    _name = 'mi.modelo'

    def importar_desde_api(self, xlsx_content, zip_content=None, categ_id=None):
        imp = self.env['product.xlsx.import'].create({
            'name': 'Importación desde API',
            'xlsx_file': xlsx_content,
            'imagenes_zip': zip_content,
            'categ_id': categ_id,
        })
        imp.action_import()
        return {
            'products': imp.created_products,
            'variants': imp.created_variants,
            'skipped': imp.skipped_count,
            'errors': imp.error_count,
            'log': imp.log,
        }
```

## Columnas detectadas automáticamente

El sistema reconoce estos nombres de columna (sin distinguir mayúsculas):

| Campo | Nombres aceptados |
|---|---|
| Producto | `producto`, `name`, `nombre`, `product name` |
| Tipo | `tipo`, `type` |
| Referencia | `referencia`, `reference`, `default_code`, `código`, `codigo` |
| Precio | `precio`, `price`, `list_price`, `precio ($)`, `precio (usd)` |
| Atributo | `atributo`, `attribute`, `attribute name` |
| Valor Atributo | `valor atributo`, `valor_atributo`, `attribute value`, `value`, `valor` |
| Imagen | `imagen`, `image`, `imagen (nombre archivo)` |

## Solución de problemas

| Problema | Causa | Solución |
|---|---|---|
| `openpyxl no instalado` | Falta dependencia Python | `pip install openpyxl` |
| Producto no se importa | `default_code` duplicado | Revisar log, cambiar referencia |
| Imagen no asignada | Nombre no coincide con ZIP | Verificar nombres exactos |
| Atributo no aparece | Fila Padre sin `Atributo` | Agregar nombre de atributo |
| Variante no tiene precio | Fila Variante sin `Precio ($)` | Agregar precio |

## Licencia

LGPL-3
