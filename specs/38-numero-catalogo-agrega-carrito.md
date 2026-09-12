# SPEC 38 — Seleccionar producto por número desde el catálogo agrega al carrito

> **Status:** Approved
> **Depends on:** — (mismo módulo `chatbot_cart` que SPEC 33/34; independiente de SPEC 37)
> **Date:** 2026-09-12
> **Objective:** Que responder el número de un producto del catálogo o de la búsqueda agregue ese producto al carrito (hoy "2" se interpreta como CONSULTAR y el carrito queda vacío).

## Por qué existe esta spec

Incidente real del 12/9 (bot Karla, sesión +58 414 389 8602): el usuario presionó
"catálogo", eligió Pizza y respondió "2", pero el carrito quedó vacío y "pagar" dijo
"carrito vacío". Verificado en BD leads (`chatbot_session` 1458): `modo=CARRITO`,
`items=[]`, `ultima_busqueda` con los 5 productos del catálogo. El catálogo instruye
"Responde el número para agregarlo" (`product_buscar.py:129-132`), pero el clasificador
nunca mapea un número suelto a AGREGAR: el fallback determinista no lo reconoce y la IA
lo interpreta como CONSULTAR/MODIFICAR (`clasificar_accion_carrito_use_case.py:110`). La
resolución por índice ya existe (`_resolver_producto` usa `ultima_busqueda`) pero solo se
alcanza con acción AGREGAR, que nunca ocurre.

## Scope

**In:**

1. **`chatbot_cart/controllers/chatbot_cart_controller.py` — en `procesar`, tras el bloque
   `pendiente_salida`:** si `valor` es un número suelto (`^\d{1,2}$` o `^el\s+\d{1,2}$`,
   `re.IGNORECASE`) y `ultima_busqueda` no está vacía → forzar `accion='AGREGAR'`,
   `producto_ref` = el número, `cantidad=1` (el número es el índice del producto, no la
   cantidad). Si el número supera `len(ultima_busqueda)` → "Ese número no está en la lista
   (1-N). Responde el número o escribe el nombre." Si es número suelto sin
   `ultima_busqueda` → guía con botones: "Selecciona primero un producto con *catálogo* o
   escribiendo su nombre." + `botones: BOTONES_CARRITO`.
2. **Bump `chatbot_cart` → `19.0.1.6.0`** + tests: número con lista → AGREGAR el item
   correcto; "el 2" → AGREGAR; número fuera de rango → mensaje; número sin lista → guía;
   comandos existentes intactos.
3. **Upgrade + suites en leads** (`docker exec odoo-19-web-leads python3
   /opt/odoo/odoo-core/odoo-bin -d dbodoo19 -u chatbot_cart --test-enable --stop-after-init
   --log-level=test`) + E2E WhatsApp.

**Out of scope:**

- Estado `pendiente_cantidad` para responder "¿Qué cantidad?" tras MODIFICAR sin cantidad
  (hoy la respuesta de cantidad tampoco resuelve; propio fix/spec).
- Imágenes del catálogo (SPEC 39).
- Escalabilidad del catálogo para muchos productos (SPEC 40).
- Cambios en n8n: ninguno (SPEC 37 ya entrega el texto correcto a `/chatbot_cart/procesar`).

## Modelo de datos

Sin estructuras nuevas. Reusa `ultima_busqueda` (índice 0-based) y la acción AGREGAR
existentes.

## Plan de implementación

1. En `procesar`: añadir un helper estático `_es_seleccion_numerica(valor)` que devuelva el
   dígito (o `None`) para `^\d{1,2}$` / `^el\s+\d{1,2}$` (con `re.IGNORECASE`); pre-check
   tras `pendiente_salida`: con `ultima_busqueda` y número ≤ `len(ultima_busqueda)` →
   `AGREGAR`/`producto_ref=dígito`/`cantidad=1`; número fuera de rango → mensaje explícito;
   sin `ultima_busqueda` → guía con `botones`. La clasificación IA/fallback solo se ejecuta
   cuando el pre-check no aplica.
2. Tests (TransactionCase, sin HTTP — mismo patrón que `test_endpoint.py`, que instancia el
   controller): `_es_seleccion_numerica` (casos: "2", "el 2", "EL 2", "12", "quiero 2
   pizzas" → `None`); `_resolver_producto` con `ultima_busqueda` de `common.py`
   (`product_a`/`product_b`) → resuelve el item correcto; número fuera de rango; regresión
   de comandos (catálogo, ver carrito, pagar, ayuda, salir) y de la salida pendiente 1/2/3.
   `MockRequest` (odoo.tests.common) solo si cubrir `procesar` completo es barato.
3. Bump versión + upgrade en leads + suites `chatbot_cart` en verde.
4. E2E WhatsApp: "carrito" → catálogo → "2" → "✅ Agregué 1 x Pizza" → "ver carrito"
   muestra Pizza → "pagar" NO dice vacío.

## Criterios de aceptación

- [ ] Escribir "2" tras ver el catálogo/búsqueda agrega el item 2 (Pizza) con cantidad 1.
- [ ] "el 2" y "EL 2" se comportan igual.
- [ ] Número fuera de rango (ej. "7" con 5 productos) → mensaje explícito "no está en la lista (1-5)".
- [ ] Número suelto sin lista previa → guía con botones (no CONSULTAR).
- [ ] "1"/"2"/"3" pendiente de salida siguen resolviendo la salida (no se rompe SPEC 34).
- [ ] Comandos existentes (catálogo, ver carrito, pagar, ayuda, salir, agregar por nombre) intactos.
- [ ] Suites `chatbot_cart` en verde (leads) y bump a `19.0.1.6.0`.
- [ ] E2E: carrito con 1 item tras seleccionar por número; "pagar" no dice vacío.

## Decisiones tomadas y descartadas

- **Tomado:** pre-check determinista en el controller — **descartado** modificar el
  clasificador (el número suelto es contexto-dependiente y solo el controller conoce
  `ultima_busqueda`).
- **Tomado:** el número es el índice del producto mostrado (con cantidad=1) — coincide con
  la instrucción del catálogo.
- **Tomado:** número sin lista → guía en vez de CONSULTAR (evita el bucle catálogo→catálogo).
- **Tomado:** número fuera de rango → mensaje explícito en vez de caer a la búsqueda por
  nombre ("No encontré '7'"), que confundía.
- **Descartado:** estado `pendiente_cantidad` (la respuesta de cantidad tras "¿Qué
  cantidad?" merece su propio fix/spec).
- **Tomado:** sin cambios n8n (SPEC 37 ya entrega el texto correcto a `/procesar`).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Conflicto con "1/2/3" de la salida pendiente | El pre-check va DESPUÉS del bloque `pendiente_salida` (que retorna antes) |
| "2" como cantidad de MODIFICAR sin estado previo | No existe `pendiente_cantidad`; queda fuera de scope y documentado |
| Número de más de 2 dígitos | Regex `\d{1,2}`: no aplica, sigue el clasificador |

## What is **not** in this spec

- Estado de cantidad pendiente tras "¿Qué cantidad?".
- Imágenes del catálogo (SPEC 39).
- Escalabilidad del catálogo / listas interactivas (SPEC 40).

Cada uno de esos, si llega, va en su propia spec.