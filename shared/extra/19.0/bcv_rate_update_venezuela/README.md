. Instalar dependencias Python:
```bash
uv pip install requests beautifulsoup4
```
# Configuración de moneda en listas de precios (Pricelists) para Odoo 19

## Problema
Los precios de los productos aparecen en la tienda web con valores extremadamente altos (ej: 1.001.842 Bs en lugar de 2.001 Bs). Esto ocurre cuando la **lista de precios (pricelist)** activa en el sitio web tiene una moneda diferente a la moneda base de la compañía.

### Causa principal
- La moneda base de la compañía está configurada en **VES** (Bolívar Soberano).
- La lista de precios del sitio web estaba en **VEF** (Bolívar Fuerte, moneda obsoleta donde 1 VES = 100.000 VEF).
- Odoo intenta convertir el precio del producto (en VES) a la moneda de la lista de precios (VEF), multiplicando por la tasa de conversión, generando valores desorbitados.

## Solución
**Todas las listas de precios utilizadas en el comercio electrónico deben tener la misma moneda que la moneda base de la compañía (en este caso, VES).**

### Pasos a seguir
1. Ve a **Ventas → Productos → Listas de precios** (Sales → Products → Pricelists).
2. Identifica la lista de precios activa para tu sitio web (normalmente "Public Pricelist" o "Default").
3. Edita la lista de precios y cambia el campo **"Moneda"** (Currency) de **VEF** a **VES**.
4. Guarda los cambios.
5. Borra la caché del navegador y recarga la tienda online.
6. (Opcional) Actualiza los assets web desde **Ajustes → Técnico → Parámetros del Sistema** → selecciona `web_assets_frontend` y ejecuta **"Actualizar Assets"**.

## Verificación
Después del cambio:
- Los precios en la tienda mostrarán el valor real en **VES** (ej: 2.001,84 Bs).
- Los precios en USD calculados con la tasa BCV se mostrarán correctamente debajo.
- Los totales del carrito y la conversión a USD funcionarán sin errores.

## Nota importante
> Si alguna lista de precios (incluso las no usadas directamente) tiene moneda VEF, cámbiala a VES o desactívala para evitar confusiones. La moneda base de la compañía debe ser VES, y todas las listas de precios del e-commerce deben coincidir con ella.

## Resumen técnico
- **Moneda base compañía:** VES (tasa 1.000000)
- **Moneda USD:** tasa 500.4606 (ejemplo BCV)
- **Moneda VEF:** no debe usarse. Si aparece, reemplazar por VES.

---

Este documento explica por qué ocurría la multiplicación anómala y cómo corregirla.