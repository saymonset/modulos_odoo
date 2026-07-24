# Tutorial: Importar Precios por Nivel desde Excel

## Requisitos

Archivo Excel (`.xlsx`) con **tres columnas** en este orden:

| default_code | tier_type | price_usd |
|---|---|---|
| AROA-001 | retail | 20.15 |
| AROA-001 | wholesale | 15.50 |

- **default_code** — código interno del producto (debe existir en Odoo)
- **tier_type** — nivel: `retail` (Menudeo), `wholesale` (Mayoreo) o `mercadolibre`
- **price_usd** — precio en dólares (número, mayor a 0)

La primera fila debe ser el encabezado con esos nombres exactos.

---

## Pasos

1. Ve a **Ventas → Productos → Importar desde Excel**

2. Se abre una ventana. Haz clic en **Archivo Excel** y selecciona tu archivo `.xlsx`.

3. Haz clic en **Importar**.

4. El sistema procesa cada fila:
   - Busca el producto por `default_code`
   - Si ya existe un precio para ese producto y nivel, lo actualiza
   - Si no existe, lo crea
   - Calcula `price_ves` y `price_cop` automáticamente con las tasas vigentes

5. Al terminar, muestra una tabla con el resultado de cada fila:
   - **Creado** (verde) — se insertó un nuevo precio
   - **Actualizado** (amarillo) — se actualizó un precio existente
   - **Error** (rojo) — algo falló (producto no encontrado, nivel inválido, etc.)

6. Revisa los errores (si los hay), corrige tu Excel y vuelve a intentarlo.

---

## Posibles errores

| Error | Causa |
|---|---|
| `No se encontró producto con código 'XXX'` | El `default_code` no existe en `product.template`. Verifica que el código esté bien escrito. |
| `tier_type inválido` | El nivel no es `retail`, `wholesale` ni `mercadolibre`. |
| `price_usd debe ser mayor a 0` | El precio está vacío, es texto o es 0. |
| `default_code vacío` | La celda del código está en blanco. |

---

## Notas

- `price_ves` y `price_cop` se calculan automáticamente usando la tasa BCV y la tasa COP configuradas en la compañía del producto.
- El proceso no se detiene ante errores individuales — sigue con las demás filas y los reporta al final.
