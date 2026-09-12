# SPEC 40 — Catálogo escalable: búsqueda-first + categorías interactivas

> **Status:** Approved
> **Depends on:** SPEC 38 (número→AGREGAR), SPEC 37 (mapeo `list_reply` — ya en vivo)
> **Date:** 2026-09-12
> **Objective:** Que comprar por WhatsApp escale de 5 a 1000+ productos usando búsqueda por texto como mecanismo principal y categorías como lista interactiva nativa, dejando la paginación como respaldo para catálogos pequeños.

## Por qué existe esta spec

El catálogo actual pagina 5 productos por página con "más" (`CATALOG_LIMIT=5`): 1000
productos = 200 páginas — inusable. Verificado contra la API de YCloud/Meta: los list
messages permiten **máx. 10 filas en total** (no escalan a productos), el catálogo nativo
(`product_list`) requiere Meta Commerce Manager por negocio (descartado), y la única pieza
sin límite es la búsqueda por texto (ya existe `buscar()` y SPEC 38 hace numerable cualquier
lista). El límite de las listas es ideal para **categorías** (≤10), y SPEC 37 ya mapea
`interactive?.list_reply?.title` en el webhook.

## Scope

**In:**

1. **`chatbot_cart` — umbral de escalabilidad:** con **≤10 productos** vendibles, UX actual
   (catálogo paginado). Con **>10**, UX nueva: al entrar al carrito o pedir "catálogo" →
   mensaje *"Tenemos N productos en M categorías. Escribe lo que buscas, o elige una 👇"*
   + **list message** (botón "Ver categorías", ≤10 categorías por conteo de productos,
   descripción "N productos").
2. **Servicio de categorías:** método en `product_buscar.py` que devuelve las categorías
   (`categ_id`) de productos vendibles con conteo, top 10. La respuesta del controller
   incluye campo nuevo `lista_categorias` (title/description/id por fila).
3. **Selección de categoría:** WhatsApp devuelve `list_reply` → SPEC 37 lo entrega como
   `valor` → pre-check en `procesar`: si `valor` coincide con nombre de categoría →
   catálogo restringido a esa categoría (paginado 5, footer con número→AGREGAR).
4. **Búsqueda mejorada:** multi-palabra (AND de términos), sin acentos (extensión
   `unaccent` en Postgres con fallback a `ilike` plano si no está instalada), y aviso
   *"Encontré 47 — muestra 5, afina tu búsqueda"* cuando hay más resultados que el límite.
5. **n8n — `Unificar_salida_carrito`:** si la respuesta trae `lista_categorias` →
   construir `whatsappPayload` type `list` (sections/rows) en vez de reply buttons. Export
   actualizado en la ruta prod.
6. **Bump `chatbot_cart`** a `19.0.1.7.0` + tests + upgrade en leads.

**Out of scope:**

- Imágenes/miniaturas (SPEC 39).
- Catálogo nativo de WhatsApp / Meta Commerce Manager (integración externa por negocio).
- Paginación de la lista de categorías (máx. 10 — si hay más, se muestran las 10 mayores y
  la búsqueda cubre el resto).
- Cambios en el flujo de pago.

## Modelo de datos

Sin modelos nuevos. Reusa `product.template.categ_id` (conteo de vendibles por categoría) y
`ultima_busqueda`/`pagina_catalogo` del carrito de sesión. Campo nuevo en la respuesta de
`/chatbot_cart/procesar`: `lista_categorias: [{id, title, description}]`.

## Plan de implementación

1. `product_buscar.py`: `categorias_con_conteo(env)` (top 10 por conteo) + mejora de
   `buscar()` (multi-término AND + `unaccent` con fallback).
2. Controller: umbral >10 → respuesta búsqueda-first con `lista_categorias`; pre-check de
   categoría por nombre en `procesar` (tras pendiente_salida y comandos deterministas);
   footer de búsqueda con conteo.
3. Tests: umbral (5 productos → catálogo clásico; mock >10 → lista), selección de
   categoría, búsqueda multi-palabra/sin acentos, regresión SPEC 38/33/34.
4. n8n `Unificar_salida_carrito`: rama `lista_categorias` → payload list; export a la ruta
   prod.
5. Upgrade en leads (`docker exec odoo-19-web-leads python3 /opt/odoo/odoo-core/odoo-bin -d
   dbodoo19 -u chatbot_cart --test-enable --stop-after-init --log-level=test`) + E2E.

## Criterios de aceptación

- [ ] Con ≤10 productos: UX actual sin cambios (regresión).
- [ ] Con >10: entrar al carrito/"catálogo" entrega prompt de búsqueda + list message con
      categorías.
- [ ] Tocar una categoría muestra sus productos (paginado) y el número agrega (SPEC 38).
- [ ] "pizza mozzarella" encuentra "Pizza Mozzarella Andina" (multi-palabra).
- [ ] "catalogo" (sin acento) encuentra "Catálogo" (unaccent).
- [ ] >5 resultados → mensaje con conteo total + los 5 primeros.
- [ ] Negocio sin categorías asignadas → degrada a solo prompt de búsqueda (sin list).
- [ ] Suites `chatbot_cart` en verde; export n8n actualizado solo en la ruta prod.

## Decisiones tomadas y descartadas

- **Tomado:** híbrido búsqueda-first + categorías — **descartado** solo-paginación (200
  páginas) y catálogo nativo Meta (configuración externa por negocio).
- **Tomado:** `categ_id` (categoría interna) — fiables según el negocio; categorías
  públicas solo si hay e-commerce.
- **Tomado:** list message para categorías (límite 10 filas = natural para categorías).
- **Tomado:** pre-check determinista de categoría en el controller (mismo patrón que
  SPEC 38) — **descartado** clasificar nombres de categoría por IA (ambiguo y caro).
- **Tomado:** umbral 10 productos para cambiar de UX (parametrizable en código).
- **Descartado:** paginar la lista de categorías (la búsqueda cubre el exceso).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| `unaccent` no instalado en leads/prod | Fallback a `ilike` plano (búsqueda con acentos exactos) |
| Categorías sin asignar en algún negocio | Detección: sin categorías → degrada a prompt de búsqueda |
| `list_reply` con payload distinto (YCloud) | SPEC 37 ya mapea `title \|\| id`; E2E con botón real |
| Nombre de categoría que coincide con un comando ("salir") | Pre-check de categoría va tras pendiente_salida y comandos deterministas |

## What is **not** in this spec

- Imágenes del catálogo (SPEC 39).
- Catálogo nativo Meta / feeds.
- Paginación de la lista de categorías.

Cada uno de esos, si llega, va en su propia spec.