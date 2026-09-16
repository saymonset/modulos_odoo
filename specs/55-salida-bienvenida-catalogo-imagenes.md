# SPEC 55 — Salida con bienvenida del negocio y compra solo por imágenes

> **Estado:** Approved (brevette)
> **Depende de:** SPEC 49 (salida directa), SPEC 50 (aviso sin IA), SPEC 38 (número→AGREGAR),
> SPEC 39 (imágenes con URL absoluta), SPEC 40 (búsqueda-first >10), SPEC 46 (tienda online)
> **Fecha:** 2026-09-16
> **Objetivo:** Que al salir del carrito el usuario reciba la bienvenida del negocio en lugar del
> "¡Listo! Volvemos al negocio", y que los productos se muestren solo como imágenes con caption
> (Nº + precio + total del carrito) con búsqueda guiada, eliminando la lista textual del catálogo.

## Por qué existe esta spec

En vivo (16/9) al salir del carrito el bot dice "¡Listo! Volvemos al negocio (quedan guardados
1 item(s))..." (`chatbot_cart_controller.py:717`, `_salir_carrito` de SPEC 49) y el usuario se
pierde: esa secuencia no le muestra qué hace el negocio ni cómo volver. Además el catálogo llega
como texto numerado ("Catálogo (1-5 de 163):" con "Aros de Hamburguesa...", `product_buscar.py:282`)
que no se lee y compite con las imágenes (SPEC 39): los productos reales se agregan por imagen/número
y el texto solo confunde. No hay ayuda intuitiva para buscar y el usuario no ve cuánto lleva en el
carrito mientras mira productos.

## Criterios de aceptación

- [ ] Salida con items: bienvenida del negocio (marca + lo que hace + menú determinista de
      `chatbot.config`) + "🛒 Te quedaron N item(s) guardados. Escribe *carrito* para retomar tu
      compra."; NUNCA aparece "¡Listo! Volvemos al negocio".
- [ ] Salida sin items: bienvenida pura del negocio (sin línea de carrito).
- [ ] Aviso sin IA (SPEC 50, `_aviso_sin_ia`) usa la misma bienvenida de salida en vez de
      "Volvemos al negocio:".
- [ ] Catálogo (>10 productos): sin lista textual numerada; mensaje guía con ejemplo real
      ("¿Qué buscas? Escríbelo con tus palabras — p. ej. 'aros de hamburguesa'") + máx. 5
      imágenes destacadas solamente.
- [ ] Caption de cada imagen: "Nº X — Nombre — precios (Bs./$/COP según config) — 🛒 Llevas N
      items ($Y)" con el total real del carrito al momento de la respuesta.
- [ ] Resultados de búsqueda también solo imágenes (sin lista textual numerada).
- [ ] Responder el Nº de una imagen agrega al carrito (SPEC 38 intacto); con más de 5
      resultados se muestra el prompt de conteo + "afina tu búsqueda".
- [ ] Paginación "más" sigue paginando los destacados en el catálogo.
- [ ] Búsqueda sin resultados: sugiere otra palabra + URL de la tienda online (SPEC 46) si existe.
- [ ] Regresión SPEC 38/39/40/49/50/51; suites `chatbot_cart` en verde.

## Scope

**In:**

1. **Salida del carrito con bienvenida (`_salir_carrito`, SPEC 49):** reemplaza "¡Listo!..." por
   la bienvenida determinista del negocio (welcome + menú del generador existente de
   `chatbot.config`, patrón SPEC 14) + línea final de carrito: "🛒 Te quedaron N item(s)
   guardados. Escribe *carrito* para retomar tu compra." (solo si hay items).
2. **Mismo cambio en `_aviso_sin_ia`** (SPEC 50): texto amable del aviso seguido de la bienvenida
   del negocio + línea de carrito, saliendo directo a `modo=NEGOCIO`.
3. **Catálogo búsqueda-first visual (>10 productos):** al entrar al catálogo ya NO va la lista
   textual; respuesta = promoción de la búsqueda con ejemplo real ("Escíbelo con tus palabras —
   p. ej. 'aros de hamburguesa'", tomado de un producto del catálogo) + hasta 5 destacados SOLO
   como imágenes (SPEC 39). El Nº mantiene SPEC 38. "más" pagina los destacados.
4. **Búsqueda = imágenes:** `formato_resultado` deja de imprimir la lista textual; solo header
   de conteo + aviso de recorte + imágenes (máx. 5) con caption completo.
5. **Caption con total del carrito:** cada caption agrega "🛒 Llevas N items — $Y" recalculado
   en el momento de la respuesta (usa `CART_SERVICE.resumen`).
6. **Sin resultados:** sugiere otra palabra + tienda online (SPEC 46) si hay URL.
7. **Tests:** caption (Nº + precios + total), salidas con/sin items, sin IA, ejemplo de producto
   real, ausencia de lista textual, paginación, regresión SPEC 38/39/40/49/50/51.
8. **Bump versión** + upgrade en lead + E2E WhatsApp real.

**Out of scope:**

- Regeneración de imágenes (SPEC 39 ya en vivo; formato `image_128` se mantiene).
- Completar SPEC 40 tal cual (la lista de categorías interactiva queda para spec futura si la
  pide un negocio; aquí la búsqueda + destacados la reemplaza en la entrada).
- Modelos nuevos de productos/categorías/carrito.
- Cambios al subflow del carrito n8n (SPEC 44) — el texto/captions viajan igual por
  `texto_para_usuario` + `imagenes`.
- Checkout/pagos (SPEC 41/42).
- Vendedor IA (SPEC 51).

## Modelo de datos

Sin modelos ni campos nuevos. Solo formato: la respuesta de `/chatbot_cart/procesar` sigue
devolviendo `texto_para_usuario` + `imagenes[{link, caption}]`; el caption se enriquece
(Nº + precios + total del carrito). La bienvenida de salida reutiliza el `texto` del generador
de menú de `chatbot.config` (ya determinista, con fallback sin IA).

## Plan de implementación

1. Controller: helper `_bienvenida_para_salida(env)` — texto welcome+menú determinista de
   `chatbot.config` + línea "🛒 Te quedaron N item(s) guardados..." solo si hay items
   (saldo de `CART_SERVICE.resumen`). Usarlo en `_salir_carrito` y `_aviso_sin_ia`.
2. `product_buscar.py`: vaciar líneas de producto concretos de `formato_lista_catalogo` y
   `formato_resultado` (retiran header + guía con ejemplo real + footer como hoy); añadir
   `total_carrito` a `imagen_caption` ("Nº X — Nombre — precios — 🛒 N items ($Y)").
3. Controller: pasar count/total del carrito a los captions; elegir el producto-ejemplo (real)
   para la guía de búsqueda.
4. Tests nuevos + regresión completa `chatbot_cart`.
5. Bump + upgrade módulo en lead (docker odoo web leads) + E2E WhatsApp: salida con items →
   bienvenida del negocio + aviso; catálogo → guía + solo imágenes con total; Nº agrega;
   búsqueda sin resultados → sugerencia + tienda.

## Decisiones tomadas y descartadas

- **Tomado:** bienvenida completa del negocio + aviso de items al salir (rec. del usuario) —
  **descartado** mantener "¡Listo!" como encabezado (es la frase que pierde al usuario).
- **Tomado:** bienvenida determinista de `chatbot.config` (mi mismo generador de SPEC 14/45) —
  **descartado** generarla con IA (costo, latencia y dependencia nueva en la salida).
- **Tomado:** mismo cambio en `_aviso_sin_ia` para no tener dos salidas contrarias.
- **Tomado:** quitar el catálogo de texto y dejar productos = solo imágenes con Nº en el caption
  (rec. del usuario) — **descartado** conservar la lista textual como respaldo (confunde).
- **Tomado:** guía de búsqueda con ejemplo real del catálogo del negocio — **descartado**
  instrucción genérica o solo categorías interactivas (spec futura).
- **Tomado:** total del carrito dentro de cada caption — **descartado** solo una vez al final
  de la tanda (el usuario pidió que no se pierda al ver cada imagen).
- **Tomado:** `image_128` como hoy — **descartado** cambiar tamaño de imagen.
- **Tomado:** ante búsqueda sin resultados, sugerir otra palabra + tienda (SPEC 46) —
  **descartado** derivar de inmediato al vendedor IA (hace la búsqueda más cara y lenta).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Bienvenida/menú de `chatbot.config` difiere si la config no existe | Fallback determinista ya existente del generador (SPEC 14/45 probado) |
| Quitar la lista textual deja sin numeración visible a productos sin imagen | El caption de imagen SIEMPRE incluye el Nº; productos sin imagen siguen siendo buscados por nombre (flujo normal) |
| El texto de salida crece (bienvenida + menú) | WhatsApp admite mensajes largos; ya es el mismo patrón de bienvenida del negocio |
| Caption largo (Nº + nombre largo + 3 precios total de carrito) | Cap de caption 1024 chars; recorter se testea |
| Orden texto→imágenes puede desfasarse | Igual al E2E de SPEC 39 (aceptado como async natural de WhatsApp) |

## What is **not** in this spec

- Lista de categorías interactiva (SPEC 40 aplazada aquí; una spec futura si la pide el negocio).
- Vendedor IA / SPEC 51.
- Checkout/pagos.
- Cambios al subflow n8n (SPEC 44).

Cada uno de esos, si llega, va en su propia spec.
