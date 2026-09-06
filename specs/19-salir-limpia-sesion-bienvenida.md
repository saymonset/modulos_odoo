# SPEC 19 — "Salir" limpia sesión y el siguiente mensaje va a bienvenida

> **Status:** Implemented
> **Depends on:** SPEC 14, SPEC 18
> **Date:** 2026-09-06
> **Objective:** Que tras "salir" (o expiración/sesión inexistente) el backend `procesar_paso` no devuelva el mensaje IA genérico "no tenemos una conversación activa", sino un estado limpio `MENU_PRINCIPAL` que deja a n8n servir su saludo conversacional real.

## Por qué existe esta spec

Bug real (2026-09-06, chat de prod): el usuario estaba en el flujo de agendamiento, escribió "salir" (bot respondió "¡Hasta luego!"), y al siguiente mensaje ("que hacen ustedes?") el backend respondió *"Parece que no tenemos una conversación activa en este momento…"* en vez del saludo conversacional de SPEC 18.

Causa raíz (`ai_chatbot_1_portal/models/chatbot_session.py`):

1. `procesar_paso` rama `es_salida` (~línea 399): marca la sesión como `modo='COMPLETADO'` pero **no la borra**.
2. El siguiente mensaje cae en la rama `if registro.modo == 'COMPLETADO'` (~línea 343) → unlink + `_generar_mensaje_sin_sesion(valor)` (~línea 980): mensaje IA genérico de "sin sesión" con `modo: MENU_PRINCIPAL` pero sin menú ni introducción real.
3. Mismo patrón en la rama de expiración (~línea 362, `_generar_mensaje_expirado`) y sin registro (~línea 329).

## Scope

**In:**

- **Odoo — rama salida:** al detectar "salir", además de responder el mensaje de despedida, **unlink** de la sesión (no queda registro `COMPLETADO`).
- **Odoo — ramas de bienvenida limpia:** `modo COMPLETADO` (residual), expiración por inactividad y sin registro devuelven `{'modo': 'MENU_PRINCIPAL', 'texto_para_usuario': ''}` (texto vacío; sin llamada a GPT para "sin sesión"). n8n sirve el saludo.
- **Odoo — respaldo determinista:** `_generar_mensaje_sin_sesion` se conserva pero sin IA: devuelve texto determinista fijo como fallback si algo más lo usa.
- **n8n — ambos JSON (`chatbot_create_lead_0_con_menu_whatsapp` y `yclod_...`):** cuando `Consultar_estado_Odoo` devuelva `modo=MENU_PRINCIPAL` con texto vacío, enrutar al nodo de saludo/introducción conversacional (SPEC 18) en vez de pasar `texto_para_usuario` tal cual. Doble capa: texto presente → se respeta; vacío → saludo.
- Bump de versión + tests deterministas.

**Out of scope:**

- Cambiar el flujo de agendamiento, el clasificador de SPEC 18 o la ingestión RAG.
- Cambiar el comportamiento de `es_desvio` (permanece intacto).
- Automatizar el import de workflows n8n (import manual).

## Data model

Sin modelos ni campos nuevos. Solo cambia el contrato de salida de `procesar_paso` en los casos "sin sesión activa":

```
{'success': True, 'modo': 'MENU_PRINCIPAL', 'texto_para_usuario': '', ...}
```

## Implementation plan

1. **Odoo:** rama `es_salida` → unlink de la sesión tras responder la despedida. Ramas `COMPLETADO`/expirada/sin registro → respuesta limpia `MENU_PRINCIPAL` sin texto IA; `_generar_mensaje_sin_sesion` pasa a determinista sin GPT. Commit verificable.
2. **n8n:** editar ambos JSON en repo: ruta explícita a saludo conversacional cuando Odoo devuelva `MENU_PRINCIPAL` con texto vacío.
3. **Tests `ai_chatbot_1_portal`:** (a) tras "salir" no queda sesión `COMPLETADO`; (b) mensaje posterior sin sesión → `modo=MENU_PRINCIPAL` sin mensaje IA genérico; (c) sesión expirada → mismo criterio.
4. **Staging:** `-u ai_chatbot_1_portal --test-enable` en `odoo-19-web-leads`; suite completa pasa.
5. **Deploy:** push → prod (upgrade sin tests) + import manual de los 2 workflows en n8n prod.

## Acceptance criteria

- [ ] "salir" en un flujo borra la sesión: no quedan registros `chatbot.session` en modo `COMPLETADO` para esa `session_id`.
- [ ] Mensaje posterior a "salir" → `procesar_paso` devuelve `modo=MENU_PRINCIPAL` con texto vacío (o saludo determinista), nunca el texto IA "no tenemos una conversación activa".
- [ ] Sesión expirada por inactividad y mensaje sin sesión → mismo contrato de salida.
- [ ] n8n: `MENU_PRINCIPAL` con texto vacío dispara el saludo conversacional (introducción IA con marca, SPEC 18).
- [ ] Sin llamada a GPT en los caminos de "sin sesión".
- [ ] Suite de staging pasa (105+ tests).

## Decisions

- **Yes:** corrección en ambos lados (Odoo root cause + n8n defensa en doble capa).
- **Yes:** borrar la sesión al salir (no conservar registro `COMPLETADO` por auditoría).
- **Yes:** cubrir los 3 casos hermanos (salida, expiración, sin registro) — misma rama de código.
- **Yes:** aplicar a ambos workflows n8n (chatwoot prod y ycloud lead).
- **No:** conservar el mensaje IA "sin sesión" con contenido orientado al menú — se elimina de raíz.

## Risks

| Risk | Mitigation |
| --- | --- |
| Otro consumidor espere texto en `texto_para_usuario` al recibir `MENU_PRINCIPAL` | n8n enruta a saludo cuando el texto va vacío; tests cubren el contrato |
| Despedida de "salir" se pierde al hacer unlink antes de responder | Respuesta se construye antes del unlink (orden: mensaje → unlink) |
| Divergencia entre los 2 JSON de n8n | Mismo cambio aplicado a ambos + checklist de import en ambos VPS |
| Regresión en flujo activo | `es_desvio` y pasos del flujo intactos; solo cambian caminos de salida/sin sesión |
