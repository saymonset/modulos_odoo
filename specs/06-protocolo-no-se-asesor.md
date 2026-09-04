# SPEC 06 — Protocolo "no sé": RAG primero y derivación a asesor solo con confirmación

> **Status:** Implemented
> **Depends on:** SPEC 01 (esqueleto universal del prompt), SPEC 03 (única fuente de configuración / RAG)
> **Date:** 2026-09-04
> **Objective:** Endurecer el prompt universal para que toda pregunta del cliente se
> responda primero (RAG + cálculo/razonamiento) y la derivación a un asesor sea honesta
> y solo tras confirmación explícita — nunca un flujo directo ante una pregunta.

## Por qué existe esta spec

Transcript real (2026-09-04): el cliente preguntó "¿Y no podemos concretar por aquí?"
y el bot disparó `flujo_ventas` con el aviso enlatado "¡Excelente! Para continuar..."
(chatbot_session.py:241), pidiendo teléfono sin responder nada. Las reglas 2, 3, 13 y
16 de `_UNIVERSAL_SKELETON` ya prohíben esto, pero el caso "pregunta de
negociación/cierre" queda ambiguo para el modelo y no existe protocolo explícito de
"no puedo responder". Nota clave: al dispararse un flujo, el output del LLM se
descarta y el cliente solo ve el aviso de Odoo — por eso la derivación honesta debe
ocurrir SIN disparar flujo en ese mensaje (pregunta Sí/No); el flujo va solo tras el
"sí" (ahí el aviso de Odoo es apropiado porque hubo consentimiento).

## Scope

**In:**

- `prompt_renderer.py` — extender regla 13 (CONOCIMIENTO/RAG) con escalera obligatoria:
  consultar `Base_Conocimiento_RAG` → calcular/razonar con lo devuelto y el contexto →
  comparar con lo que pide el cliente → solo entonces protocolo "no sé".
- `prompt_renderer.py` — protocolo "NO SÉ" en regla 13: wording honesto + confirmación
  "¿Quieres que un asesor de la empresa te contacte? Responde Sí o No"; al "sí" →
  `flujo_agendamiento_otra_consulta` (regla 12); jamás flujo sin "sí".
- `prompt_renderer.py` — nueva regla 17: "UNA PREGUNTA NUNCA ES UNA CONFIRMACIÓN" —
  preguntas de negociación/cierre ("¿Y no podemos concretar por aquí?", "¿cómo pago?",
  "¿me haces un descuento?", "¿puedo hacerlo yo mismo?") se responden primero (qué SÍ
  se gestiona por chat, qué requiere asesor) y cierran con la confirmación de regla 16.
- `prompt_renderer.py` — refuerzo en el bloque IMPORTANTE de `_render_flujos`.
- Tests exactos en `tests/test_prompt_renderer.py` de los tres textos nuevos.
- Bump `__manifest__.py` 1.0.23 → 1.0.24 y upgrade `--test-enable` en staging.
- Replay manual del transcript en staging como verificación final.

**Out of scope (specs futuros):**

- Cambios en el aviso fijo `chatbot_session.py:241` (solo se ve tras el "sí").
- Cambios en el workflow n8n (contrato y heurísticas intactos).
- Guardrail determinista en `/inicioagendar` (exigir confirmación previa registrada).
- Textos configurables por cliente en `chatbot.config`.
- Responder dudas de negocio DENTRO del túnel de un flujo (out desde SPEC 04).

## Data model

Esta feature no introduce estructuras de datos nuevas. Solo cambia el texto del
esqueleto universal `_UNIVERSAL_SKELETON` (y el bloque IMPORTANTE de
`_render_flujos`) en `services/prompt_renderer.py`. Wordings propuestos:

```
# Regla 13 (extensión final):
"Antes de declarar que no puedes responder: (a) consulta Base_Conocimiento_RAG,
(b) intenta CALCULAR o razonar la respuesta con lo que devuelva el RAG, la
conversación y el CONOCIMIENTO DEL NEGOCIO, y (c) compara lo que tienes con lo
que el cliente pide. Solo si tras eso no puedes responder con seguridad usa el
PROTOCOLO 'NO SÉ': admítelo con naturalidad ('No tengo esa información precisa
en este momento') y pregunta SIEMPRE antes de derivar: '¿Quieres que un asesor
de la empresa te contacte para asesorarte? Responde Sí o No'. Cuando responda
'sí', activa flujo_agendamiento_otra_consulta."

# Regla 17 (nueva):
"17. UNA PREGUNTA NUNCA ES UNA CONFIRMACIÓN: mensajes interrogativos de
negociación o cierre ('¿Y no podemos concretar por aquí?', '¿cómo pago?',
'¿me haces un descuento?', '¿puedo hacerlo yo mismo?') son consultas: responde
primero (regla 13), explicando qué SÍ puedes gestionar por este chat y qué
requiere un asesor. Jamás dispares un flujo directamente ante una pregunta:
cierra con la pregunta de confirmación (regla 16) y espera el 'sí'."
```

## Implementation plan

1. Extender regla 13 del `_UNIVERSAL_SKELETON` con la escalera + protocolo "NO SÉ".
   Funcional por sí solo: cualquier config renderiza el prompt nuevo.
2. Añadir regla 17 (pregunta ≠ confirmación, con los ejemplos del transcript).
3. Refuerzo en `_render_flujos` (bloque IMPORTANTE): "Tampoco las preguntas de
   negociación o cierre disparan flujos: respóndelas primero y ofrece la
   derivación con confirmación."
4. `tests/test_prompt_renderer.py`: asserts exactos de (a) escalera + protocolo
   "NO SÉ" con `flujo_agendamiento_otra_consulta`, (b) regla 17 con "concretar
   por aquí", (c) refuerzo del bloque IMPORTANTE; regresión de asserts existentes.
5. Bump manifest 1.0.23→1.0.24 + upgrade `-u ai_chatbot_1_portal,ai_chatbot_0_core
   --test-enable` en `odoo-19-web-leads` (0 FAIL) + replay manual del transcript
   vía el bot de staging.

## Acceptance criteria

- [ ] El prompt renderizado (con cualquier config activa) contiene la escalera
      RAG→calcular/razonar→comparar y el protocolo "NO SÉ" con confirmación Sí/No
      y destino `flujo_agendamiento_otra_consulta`.
- [ ] El prompt renderizado contiene la regla "UNA PREGUNTA NUNCA ES UNA
      CONFIRMACIÓN" con los ejemplos "concretar por aquí" y "cómo pago".
- [ ] Replay en staging: "¿Y no podemos concretar por aquí?" recibe una respuesta
      (RAG/razonamiento o protocolo "no sé") — `equipo_asignado`/`flow_name`
      vacíos, sin aviso de flujo.
- [ ] Replay en staging: al responder "sí" a la oferta de asesor se dispara
      `flujo_agendamiento_otra_consulta` (no `flujo_ventas`); el aviso de Odoo
      aparece solo entonces.
- [ ] Regresión: consultas informativas (precios/servicios) siguen respondiéndose
      sin flujo; tests existentes del renderer pasan sin cambios.
- [ ] `-u ai_chatbot_1_portal,ai_chatbot_0_core --test-enable` en staging termina
      0 FAIL/0 ERROR.

## Decisions

- **Yes:** fix solo en el prompt (Odoo) — la clasificación vive en el LLM de n8n
  pero se rige por el system prompt que Odoo sirve; cero cambios de contrato.
- **Yes:** confirmar antes de derivar — resuelve además que el output del LLM se
  descarta al disparar flujo: en el camino "no sé" no se dispara flujo, así el
  wording honesto sí llega al cliente.
- **Yes:** destino `flujo_agendamiento_otra_consulta` — su `descripcion_intencion`
  ya es exactamente "asesor contacte por consulta no cubierta"; cero cambios de datos.
- **Yes:** regla 17 separada (no dentro de la 16) — diff claro y asserts exactos
  triviales; el modelo lee el principio con su propio encabezado.
- **Yes:** textos universales del esqueleto, no configurables — misma línea que
  SPEC 04 (el protocolo es del núcleo universal).
- **No:** tocar el aviso `chatbot_session.py:241` — con confirmación previa,
  "¡Excelente! Para continuar..." solo aparece tras el "sí" y ahí es apropiado.
- **No:** cambios en n8n — el contrato de respuesta no cambia (línea SPEC 02/03/04).
- **No:** guardrail determinista en `/inicioagendar` — spec futuro si el prompt no basta.

## Risks

| Risk | Mitigation |
| --- | --- |
| El LLM puede seguir incumpliendo la regla (prompt ≠ determinismo) | Ejemplos literales del transcript en regla 17 + refuerzo en FLUJOS DISPONIBLES (sección que el modelo lee junto a la decisión de flujo); si persiste, guardrail determinista como spec futuro |
| n8n cachea el system prompt y no ve el cambio | El endpoint sirve el prompt fresco; el replay manual post-deploy lo verifica |
| El "sí" del cliente responde a otra confirmación previa y dispara el flujo equivocado | La oferta del protocolo "NO SÉ" nombra explícitamente el asesor y la regla 12 mantiene el mapeo al flujo pendiente correcto |
| Prompt más largo (costo tokens) | Incremento marginal (~15 líneas); el resto de secciones sigue condicionado por config |

## What is **not** in this spec

- Cambios en el aviso de inicio de flujo, workflow n8n, guardrail determinista en
  `/inicioagendar`, textos por cliente en `chatbot.config`, respuestas de negocio
  dentro del túnel. Cada uno, si llega, va en su propio spec.