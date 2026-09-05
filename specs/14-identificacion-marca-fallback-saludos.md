# SPEC 14 — Identificación humana de marca en menú y FALLBACK

> **Status:** Approved
> **Depends on:** SPEC 11, SPEC 13
> **Date:** 2026-09-05
> **Objective:** Que el bot se presente siempre como humano y identifique a la empresa — menú y FALLBACK abren con una bienvenida cálida que saluda de parte de *MARCA* (sin nombre de asistente), seguida del menú completo; saludos comunes y textos ≤2 caracteres fuerzan este menú determinista.

## Por qué existe esta spec

Tras SPEC 13 el menú es determinista pero suena a robot: `¡Hola! 👋 ¿Qué necesitas hoy?` + lista sin identificación humana de la empresa. Además el FALLBACK ("no entendí") no identifica a la empresa, "hola" no está en las keywords de MENU y un mensaje ultra-corto ("k") cae a fallback genérico. Prioridad del usuario: **toda respuesta identifica a la empresa con tono humano**.

## Scope

**In:**
- **Bienvenida humana con marca (Odoo):** el menú generado (`_generar_menu_desde_flujos`) abre siempre con saludo cálido que mencione la empresa de forma natural, ejemplo determinista sin IA: `¡Hola! 👋 Te saluda *INMOBILIARIA KARLA CAMPOVERDE*. Encantados de ayudarte 😊`. La IA (tagline del rol) debe seguir esta pauta de tono; si falla, cae al determinista cálido (nunca al "¿Qué necesitas hoy?" robótico).
- **Cierre conversacional:** el menú cierra con `Escríbeme el número de lo que necesitas o cuéntame con tus palabras qué buscas 😊` (reemplaza el cierre actual).
- **FALLBACK con marca + menú (Odoo):** al regenerar menú / recargar desde RAG, el `output_largo` de FALLBACK se actualiza con la misma bienvenida + `No entendí tu mensaje 🤔, aquí te dejo el menú para que me orientes:` + menú completo.
- **Keywords de saludo (Odoo):** MENU keywords += `hola,buenas,buenos días,buenas tardes`.
- **Ultra-cortos (n8n):** en `Separar_variables_en_json` (ambos workflows: `ycloud_…` lead y `chatbot_…` prod), texto ≤2 caracteres fuerza el menú determinista. Import manual por UI (los dos VPS).
- Bump `ai_chatbot_1_portal` + tests.

**Out of scope:**
- Nombre de asistente/persona (decisión: solo la empresa).
- Marca en respuestas informativas/RAG exitosas.
- Automatización del import n8n; migración automática de configs (regeneración manual por botón).

## Data model

Sin modelos ni campos nuevos. Cambian valores generados:
- Header del menú (fallback determinista): `¡Hola! 👋 Te saluda *{marca}*. Encantados de ayudarte 😊`.
- Cierre: `Escríbeme el número de lo que necesitas o cuéntame con tus palabras qué buscas 😊`.
- FALLBACK `output_largo`: `{bienvenida}\n\nNo entendí tu mensaje 🤔, aquí te dejo el menú para que me orientes:\n\n{menú}`.

## Implementation plan

1. Odoo: keywords MENU; `_generar_menu_desde_flujos` — header determinista cálido con marca, cierre conversacional, y pauta de tono humano pasada a `generar_menu_por_rol`; helper `_generar_fallback_con_marca(menu_texto)` llamado desde `action_regenerar_menu` y `action_recargar_todo_desde_rag`.
2. Tests: FALLBACK con `*MARCA*` + "No entendí" + menú; menú fallback sin IA contiene "Te saluda *" y el cierre nuevo (y NO "¿Qué necesitas hoy?"); keywords incluyen "hola"; regla ≤2 chars por replay.
3. n8n (ambos JSON): `esMenu` también si `textoUsuario.length <= 2`; exportar para import manual.
4. Despliegue: upgrade en prod, regeneración manual por cliente, import manual de ambos workflows.
5. Verificación: "hola" / "k" → bienvenida con marca + menú; "xyzabc123" → FALLBACK con marca + menú; informativa → sin regresión.

## Acceptance criteria

- [ ] Menú y FALLBACK abren con bienvenida humana que incluye `*MARCA*`; nunca `¿Qué necesitas hoy?` como encabezado.
- [ ] Mensaje no entendido → bienvenida + "No entendí" + menú completo.
- [ ] "hola"/"buenas"/"buenos días"/"buenas tardes" y textos ≤2 chars → menú con marca aunque la IA no etiquete MENU.
- [ ] La marca nunca se hardcodea en n8n: proviene de Odoo.
- [ ] Ambos workflows actualizados e importados en lead (ycloud) y prod (chatbot).
- [ ] Informativas y flujos sin regresión.

## Decisions

- **Yes:** presentación solo con la empresa (sin nombre de asistente) — menos config, tono cálido igual.
- **Yes:** lista numerada se conserva (compatibilidad con menú interactivo WhatsApp y SPEC 13), precedida de bienvenida humana.
- **Yes:** FALLBACK con menú completo debajo (menos ida y vuelta).
- **No:** marca en respuestas RAG exitosas — spec futura si se pide.

## Risks

| Risk | Mitigation |
| --- | --- |
| Tagline IA salga robótico igual | Pauta de tono en el prompt + fallback determinista cálido |
| "buenas tardes" matchea mensajes largos | Match por inclusión como hoy; riesgo bajo |
| Divergencia entre los 2 JSON de n8n | Mismo script de edición + checklist de import en ambos VPS |
