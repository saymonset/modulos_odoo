# SPEC 52 — Descubrimiento del carrito: números en fotos, cantidad por frase y acciones visibles

> **Status:** Implemented
> **Depends on:** SPEC 38 (selección numérica), SPEC 39 (imágenes), SPEC 50 (vendedor IA), SPEC 51 (fix prompt)
> **Date:** 2026-09-16
> **Objective:** Que el cliente entienda cómo comprar desde la foto (número en el caption), pueda pedir cantidad en la misma frase, y descubra siempre las acciones del carrito (quitar, cambiar, vaciar, pagara, cotización, salir) con una pista de una línea.

## Por qué existe

El E2E WhatsApp del usuario mostró: la foto del producto no indica su número del listado; elegir por número solo agrega 1; quitar/modificar/vaciar/cotización existen pero nadie sabe que se puede; el `ayuda` es tosco y denso. Todo existía en el motor: el problema es descubrimiento.

## Scope

**In:**
1. Caption de imágenes de catálogo/búsqueda con número: `1. Nombre — Bs. X / $Y` (+ COP si aplica).
2. Clasificador: `AGREGAR` por frase `N, quiero M` / `del N quiero M` / `N y quiero M` (número de lista + cantidad); solo `N` sigue agregando 1.
3. Hint de una línea con acciones rápidas después de AGREGAR/QUITAR/MODIFICAR/CONSULTAR (con items).
4. `AYUDA` redactada por el vendedor IA con fallback a plantilla compacta (incluye ejemplo de cantidad).
5. Tests + regresión + E2E HTTP lead de los 5 casos.

**Out of scope:**
- n8n, SPEC 47, `chatbot_cotizacion`, SPEC 51.

## Data model

Sin modelo nuevo. Contrato:
- `_decision_seleccion_numerica` ahora también detecta cantidad en la frase (retorno `('AGREGAR', numero, cantidad)`).
- Caption de imágenes incluye índice de la lista.

## Implementation plan

1. `_decision_seleccion_numerica` con cantidad + wire en `procesar` (AGREGAR con qty).
2. `_imagenes_de_productos` con índice; callers pasan la posición.
3. Hint de acciones rápidas (constante) en AGREGAR/QUITAR/MODIFICAR/CONSULTAR.
4. `AYUDA` IA + plantilla compacta.
5. Extra (hallado en E2E): `cambiar <prod> a 2` ya no toma '5' de '2.5' (`_extraer_cantidad` prefiere la cola 'a N') y `_resolver_producto` hace matching por nombre antes del índice con verbos QUITAR/MODIFICAR.
6. Tests + suite + E2E lead.

## Acceptance criteria

- [ ] Captions de catálogo/búsqueda llevan `N.` como el listado de texto.
- [ ] `1, quiero 3` agrega 3 unidades del producto 1; `2` sigue agregando 1.
- [ ] Cada acción de carrito termina con la línea de acciones rápidas.
- [ ] `ayuda` responde IA amigable con fallback compacto que menciona cantidad.
- [ ] Suite verde + E2E HTTP lead de los 5 casos.

## Decisions

- **Sí:** cantidad en la misma frase con regex del clasificador determinista (decisión del usuario).
- **Sí:** hint de 1 línea tras cada acción (decisión del usuario).
- **Sí:** `ayuda` por IA con fallback compacto (decisión del usuario).
- **No:** tocar n8n ni SPEC 47.

## What is **not** in this spec

- Cambios de catálogo paginado (SPEC 40), outputs de pago (SPEC 41) ni n8n.
