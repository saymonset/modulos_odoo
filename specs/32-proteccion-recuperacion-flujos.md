# SPEC 32 — Protección y auto-recuperación de flujos + anuncio determinista

> **Status:** Approved
> **Depends on:** SPEC 31 (restauración del gate del carrito), SPEC 29/30 (flujo carrito y botón)
> **Date:** 2026-09-12
> **Objective:** Que `flujo_carrito_compra` y los flujos base sobrevivan a la limpieza manual de la UI, que la sync los recupere solos si se borran, y que el anuncio 💡 "Escribe «carrito»…" sea determinista vía n8n — sin dañar lo existente.

## Por qué existe esta spec

Verificado el 12/9 con la BD de n8n y los logs de Odoo: el usuario borró los 7 flujos desde Chatbot → Flujos (`unlink` vía UI a las 11:06:51), incluido `flujo_carrito_compra` (tercera vez en el día). La sync rearma solo los 6 flujos base; el del carrito solo lo recupera el botón "Activar carrito" (SPEC 30). Sin el flujo, el gate del prompt da False → ni anuncio ni disparo (la prueba de "carrito" a las 11:13:55 recibió un system prompt de 18.137 chars sin el bloque CARRITO). Además el anuncio por prompt sigue siendo probabilístico (el saludo de 7:08 con el bloque presente no lo aplicó). La feature no depende del azar: el sistema debe defender el flujo y garantizar el cartel.

## Scope

**In:**

1. **Protección de borrado (`ai_chatbot_1_portal/models/chatbot_flujo.py`):**
   - Constante `_FLUJOS_PROTEGIDOS` (los 6 flujos base del catálogo + `flujo_carrito_compra`), junto a `_FLUJOS_NO_AUTODETECTADOS`.
   - Override de `unlink`: si un flujo protegido se intenta borrar (y no viene `context.force_delete=True`) → `UserError` amigable: "Este flujo del sistema no se puede borrar; desactívalo desde la ficha del cliente (botón 'Activar/Desactivar carrito') o el filtro Archivados."
   - `force_delete` en contexto permite borrados legítimos (shell/migraciones), documentado.
2. **Auto-recuperación en la sync (`chatbot_config.py` + `chatbot_flujo.py`):**
   - `_ensure_flujo_carrito(env)`: dentro de `action_recargar_todo_desde_rag`, tras `_ensure_catalogo_flujos`, si `flujo_carrito_compra` no existe → crearlo **inactivo y sin pasos** (igual a la data de SPEC 29). La activación sigue siendo manual (marca o botón).
3. **Anuncio determinista en n8n (solo el code node `Unificar_salida`):**
   - Si el system prompt trae `=== CARRITO DE COMPRA ===`, la salida no contiene `«carrito»` y no hay activación de flujo (`flow_name`/`equipo_asignado` no vacíos) → añadir `\n💡 Escribe «carrito» para ver nuestro catálogo y comprar por WhatsApp.`
   - Backup del JSON del workflow antes de editar; importar/activar en n8n y verificar.
4. **Tests deterministas** (sin RAG real): unlink protegido con mensaje correcto; `force_delete` permite borrar; sync recrea `flujo_carrito_compra` inactivo si falta.
5. **Bumps:** `ai_chatbot_1_portal` → `1.0.39`; export n8n actualizado en `n8n_json/ycloud/`.

**Out of scope:** datos de clientes/Karla, menú, RAG, otras apps, deploy a producción, auto-reparación fuera de la sync.

## Plan de implementación

- **S1:** `ai_chatbot_1_portal`: `_FLUJOS_PROTEGIDOS` + guard `unlink` + `_ensure_flujo_carrito` en la sync + tests → suite verde.
- **S2:** n8n: backup → editar `Unificar_salida` → aplicar en la instancia → verificar nodo.
- **S3:** `action_activar_carrito` en config Karla (recrea el flujo borrado) → restart → prompt en vivo con el bloque.
- **S4:** Pruebas end-to-end WhatsApp: "hola" (anuncio determinista) y "carrito" (llega a `/chatbot_cart/procesar`, verificable en log) → spec `Implemented` + commit.

## Criterios de aceptación

- [ ] `unlink` de un flujo protegido → `UserError` informativo (test).
- [ ] `unlink` con `context.force_delete=True` permite borrar (test).
- [ ] La sync recrea `flujo_carrito_compra` inactivo si falta (test).
- [ ] `POST /ai_chatbot_1_portal/configuracion_agente` devuelve el bloque CARRITO cuando el flujo está activo.
- [ ] Toda respuesta conversacional del bot termina con el anuncio 💡 (determinista en n8n).
- [ ] WhatsApp "carrito" → `/chatbot_cart/procesar` responde (log en vivo).
- [ ] Suites `ai_chatbot_1_portal` + `chatbot_cart` en verde.

## Riesgos

- El guard de borrado puede molestar si alguien quiere eliminar flujos default → se libera con `force_delete` (shell), documentado en la guía.
- `Unificar_salida` no debe anexar el anuncio cuando el carrito ya está activo/el flujo devolvió texto (la condición "sin activación de flujo" lo evita).