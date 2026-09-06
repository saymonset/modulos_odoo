# SPEC 18 — Bot conversacional RAG sin menú (mini-buscador)

> **Status:** Implemented
> **Depends on:** SPEC 13, SPEC 16, SPEC 17
> **Date:** 2026-09-06
> **Objective:** Eliminar el menú numerado del chatbot y reemplazarlo por una introducción conversacional generada por IA desde los temas del RAG, con los mensajes del cliente yendo directo al RAG como un mini-buscador (responde siempre primero, como humano) y los flujos de intención disparándose de forma invisible solo cuando el cliente acepta una sugerencia o pide la acción explícitamente — cambiando código Odoo (`ai_chatbot_0_core`, `ai_chatbot_1_portal`) y los 2 workflows n8n.

## Por qué existe esta spec

Feedback real (2026-09-06): el bot "suena robótico". El menú numerado lo convierte en un kiosco de opciones en vez de un conversador inteligente. El RAG (`n8n_vectors`) existe precisamente para que el bot presente lo que ofrece la empresa conversando y responda con toda la información disponible, esperando el feedback del cliente. Los flujos de intención deben ser invisibles: perciben la intención a través de la conversación (incluida la charla informativa del RAG) sin que el usuario tenga que elegir una opción del menú.

Regla de oro validada con el usuario: **RAG primero, siempre**. Ante cualquier pregunta el bot responde primero como humano con la info disponible del RAG en ese momento; nunca interrumpe una respuesta informativa para saltar a un flujo. Después de responder sugiere naturalmente profundizar/actuar ("¿quieres que te ayude a agendar una visita?"); el flujo predefinido se dispara solo cuando el cliente acepta esa sugerencia o pide la acción explícitamente.

Contexto: SPEC 17 (menú por temas RAG, Implemented) y SPEC 13 (menú determinista servido desde n8n) quedan **preservados tras un flag** para rollback, pero desactivados por defecto.

## Scope

**In:**

- **Saludo sin menú (n8n):** el nodo de bienvenida deja de servir el `MENU.output` determinista y genera una **introducción IA** a partir de temas RAG + marca + rol: "Te saluda *X*, nos dedicamos a… ¿qué te gustaría saber?". Sin lista numerada.
- **Ruteo conversacional (n8n):** nodo IA clasificador que recibe el **historial completo de conversación** (no solo el último mensaje) con dos niveles:
  1. ¿Pregunta de contenido? → directo al nodo "Sistema RAG standar", cuyo prompt se ajusta a respuesta conversacional humana + cierre con sugerencia discreta de acción si aplica (según flujos activos del negocio). Nunca ofrece opciones.
  2. ¿El cliente aceptó una sugerencia o pidió la acción explícitamente? → dispara el flujo de intención predefinido existente, intacto, con su contexto de sesión.
- **RAG sin respuesta** → mensaje honesto "no tengo esa info, ¿te comunico con un asesor?" → flujo asesor.
- **Desempate:** mensaje ambiguo → RAG (el contenido siempre gana; la señal de acción debe ser explícita).
- **Odoo, flag de compatibilidad:** nuevo campo `chatbot.config.menu_enabled` (Boolean, default `False`). Con `True` se conserva el comportamiento exacto de SPEC 13/17 (rollback en caliente). Con `False` (default), el prompt universal omite menú/opciones y la sincronización desde RAG regenera temas/intenciones/keywords pero no menú.
- Nota: una empresa por VPS — el flag es efectivamente por instancia, sin mezclas por BD.
- Bump de versiones + tests deterministas.

**Out of scope:**

- Cambios en la ingestión del RAG (`n8n_vectors`, "Sistema RAG standar" solo cambia su prompt de salida).
- Cambiar el comportamiento interno de los flujos (wizard, configuración, `flow_id`, keywords — todo intacto; solo cambia cómo se percibe la intención).
- Branding/marca (SPEC 16 cerrado).
- Soporte multi-empresa por BD.

## Data model

Un campo nuevo:

```
chatbot.config.menu_enabled: Boolean, default False
  False → modo conversacional (este spec)
  True  → modo menú determinista (SPEC 13/17, rollback)
```

Sin cambios en `chatbot.intencion` ni flujos: `flow_id` y keywords quedan intactos (keywords pasan a ser respaldo; la intención primaria sale del clasificador IA de n8n).

## Implementation plan

1. **Odoo:** campo `menu_enabled` en `chatbot.config` + gating del menú en el prompt universal y en la sync desde RAG (flag off: sin menú; flag on: comportamiento SPEC 17 intacto). Commit verificable.
2. **n8n `chatbot_create_lead_0_con_menu_whatsapp.json` y `ycloud_create_lead_0_con_menu_whatsapp.json`:**
   - Quitar el servido de menú determinista.
   - Saludo = introducción IA desde temas del RAG + marca + rol.
   - Nodo clasificador de intención (con historial) → switch: RAG vs flujo.
   - Prompt del RAG: respuesta humana con la info disponible + sugerencia discreta de acción al cerrar; jamás lista de opciones.
   - Sin info en el RAG → "no tengo esa info" + oferta de asesor → flujo asesor.
3. **Tests Odoo:** prompt sin menú con flag off; flag on preserva SPEC 17 (tests viejos pasan); sync regenera intenciones/keywords sin menú.
4. **Staging (replays):** "hola" → introducción conversacional con marca, sin lista numerada; "¿qué capacidad tiene el edificio?" → primero responde el RAG con el dato, NO arranca flujo; "sí, agéndame" → arranca el flujo de agendamiento con el contexto de lo ya conversado; pregunta sin cobertura → "no tengo esa info" + asesor.
5. **Deploy:** push → prod + import de los 2 workflows actualizados en n8n (editar JSONs en repo → importar en n8n staging → verificar → importar prod).

## Acceptance criteria

- [ ] "hola" no devuelve lista numerada; devuelve introducción conversacional con la marca (SPEC 16).
- [ ] Pregunta de contenido → respuesta del RAG directa, sin opciones ni menú.
- [ ] Pregunta de precio a mitad de charla informativa → primero responde el RAG; el flujo NO se dispara a mitad de la respuesta.
- [ ] Aceptar la sugerencia o pedir la acción ("sí, agéndame") → flujo predefinido se dispara intacto, con contexto de sesión.
- [ ] Pregunta fuera del RAG → "no tengo esa info" + oferta de asesor.
- [ ] `menu_enabled=True` restaura el comportamiento exacto de SPEC 17 (tests viejos pasan).
- [ ] Suite de staging pasa (105+ tests).

## Decisions

- **Yes:** introducción IA desde temas del RAG (opción 1a) — es el modo "mini-buscador de Google" que pide el usuario.
- **Yes:** clasificador IA en n8n con historial completo (opción 2a) — la intención se percibe en la conversación, no en un menú.
- **Yes:** RAG directo como capa principal de respuesta + fallback asesor si no hay info (opción 3).
- **Yes:** editar los 2 workflows n8n como parte de la implementación (opción 4).
- **Yes:** flag `menu_enabled` por compatibilidad/rollback (opción 5b); default off (conversacional).
- **Yes:** regla de oro RAG primero — el flujo solo se dispara tras la sugerencia aceptada o petición explícita.
- **Yes:** los flujos trabajan igual que hoy; solo cambia la percepción de intención (clasificación IA sobre la conversación).
- **No:** eliminar el código del menú por completo — se conserva tras el flag.
- **No:** tocar ingestión del RAG ni el catálogo de flujos.

## Risks

| Risk | Mitigation |
| --- | --- |
| Falso positivo del clasificador (dispara flujo sin intención) | Prompt de clasificación estricto; ambiguo → RAG; acción debe ser explícita o aceptación de sugerencia |
| Sin menú el cliente no sabe qué preguntar | La introducción IA menciona los temas del RAG |
| Flujo arranca a mitad de conversación RAG sin contexto | El clasificador recibe historial completo; la sesión de chatbot trae el contexto ya conversado (verificado en test de staging) |
| Rollback en caliente | Flag `menu_enabled=True` restaura SPEC 17 sin nuevo deploy |
| Workflows n8n editados en prod rompen el bot vivo | Editar JSONs en repo → importar/verificar en n8n staging → importar prod al final |
| Preguntas genéricas del RAG residen en respuestas pobres | Prompt del RAG exige respuesta humana con lo disponible + sugerencia; SPEC 17 ya dejó keywords/intenciones por tema |
