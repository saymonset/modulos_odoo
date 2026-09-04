# SPEC 04 — Desvío del túnel de flujos y mensajes de validación amigables

> **Status:** Aprobado
> **Depends on:** SPEC 01 (motor de flujos y use cases que se extienden)
> **Date:** 2026-09-04
> **Objective:** Humanizar el túnel de flujos del chatbot: mensajes de error de validación en lenguaje de cliente final (sin jerga técnica) y explicación amable del túnel con repetición de la pregunta pendiente cuando el usuario hace preguntas fuera del flujo.

## Scope

**In:**

- Reescribir los fallbacks robóticos de `ChatBotUtils.validar_valor` (ai_chatbot_1_portal, controllers/chatbot_utils.py:1237-1304): boolean, integer, float, date, datetime, teléfono, imagen y tipo no soportado.
- Reescribir los fallbacks de `validacion_amigable_use_case._validacion_tradicional` (ai_chatbot_0_core), incluido "Debe ser un booleano (true/false)".
- Dict único de mensajes amigables en un módulo de constantes de `ai_chatbot_0_core` (p. ej. `uses_cases/mensajes_validacion.py`), importado por ambos validadores (DRY; 0_core es base de 1_portal).
- Extender `detectar.intencion.salida.use.case` a clasificación 3-vías — respuesta válida / salida / desvío (pregunta fuera de flujo) — en la **misma única llamada IA por mensaje** que hoy, con clave nueva `es_desvio` y fallback determinista por palabras clave.
- Endurecer el fallback determinista actual: matching por palabra exacta, no por substring (`'no'` como substring hoy marca salida ante "no tengo cédula").
- `chatbot_session.py::procesar_paso`: si hay desvío → responder con explicación amable del túnel (datos obligatorios + opción "salir") + repetir la pregunta pendiente desde el `mensaje_prompt` almacenado; **no** guardar el mensaje como dato ni consumir el paso (cubre pasos `text` y no-`text`).
- Constantes de textos nuevos a nivel de módulo en `chatbot_session.py`.
- Tests con mock de `gpt.service` (patrón de `tests/test_imagenes_flujo.py`) + tests unitarios de mensajes.
- Bump de versión de ambos manifests.

**Out of scope (specs futuros):**

- Responder dudas de negocio dentro del túnel (ej. dar el precio sin salir).
- Textos configurables por cliente en `chatbot.config`.
- Cambios en el workflow de n8n (el contrato de respuesta no cambia).
- Detección de desvío fuera del túnel (modo INICIO/MENU_PRINCIPAL).
- Cambios en `_generar_pregunta_amigable` (la generación de preguntas ya es amigable).

## Data model

Esta feature no introduce modelos ni campos nuevos. Reutiliza el modelo de SPEC 01. Únicos cambios de estructura:

```python
# detectar.intencion.salida.use.case — retorno extendido (retrocompatible)
{"es_salida": bool, "es_desvio": bool, "mensaje": str}
# es_desvio=True solo cuando es_salida=False y el mensaje es una
# pregunta/petición de información fuera del paso actual.

# ai_chatbot_0_core/uses_cases/mensajes_validacion.py (nuevo, constantes)
MENSAJES_VALIDACION = {
    "boolean": "No entendí tu respuesta. Por favor escribe 'sí' o 'no'.",
    "integer": "Necesito un número entero, sin decimales ni letras. Ejemplo: 2",
    "float": "Necesito un número decimal. Ejemplo: 1.5",
    "date": "No reconocí la fecha. Escríbela como día/mes/año. Ejemplo: 15/05/1990",
    # ... datetime, teléfono, imagen, tipo no soportado
}
```

El estado de sesión (`chatbot.session.estado`) no cambia: un desvío no avanza el flujo ni escribe en `datos_paciente`.

## Implementation plan

1. Crear `ai_chatbot_0_core/uses_cases/mensajes_validacion.py` con el dict `MENSAJES_VALIDACION` (todos los tipos). Funcional por sí solo.
2. `validacion_amigable_use_case._validacion_tradicional`: usar el dict en vez de los strings robóticos. Manual: validar "Dame precio" contra paso boolean → mensaje sin "true/false".
3. `chatbot_utils.validar_valor`: importar el dict y usarlo (mensajes idénticos en ambos validadores).
4. `detectar_intencion_salida_use_case`: prompt 3-vías (respuesta/salida/desvío, criterio: solo preguntas o peticiones explícitas de información, respuestas cortas válidas jamás son desvío) + fallback determinista: palabras exactas de salida (sin 'no' como substring) y keywords de desvío ('?', 'cuanto', 'cuánto', 'precio', 'costo', 'dame', 'dime', 'cómo', 'cuál', 'información'...) excluyendo palabras de control ('no','sí','si','listo','omitir','saltar','continuar','siguiente').
5. `gpt_service.detectar_intencion_salida`: passthrough de `es_desvio` (firma y options iguales).
6. `chatbot_session.procesar_paso`: tras la detección de salida (:384), si `es_desvio` → return modo FLUJO con `texto_para_usuario` = constante `EXPLICACION_TUNEL` + `estado['mensaje_prompt']`, sin writes ni consumo de paso.
7. Tests `ai_chatbot_1_portal/tests/test_desvio_flujo.py`: (a) desvío en paso boolean ("Dame precio primero" → explicación + pregunta repetida, sin "booleano"); (b) desvío en paso text ("Pero quiero saber cuanto sale" → NO guardado como nombre, paso sigue pendiente); (c) respuestas válidas avanzan igual (regresión); (d) "salir" sigue cerrando; (e) IA caída → fallback por keywords. Tests de mensajes en `ai_chatbot_0_core/tests/`.
8. Bump manifests (`ai_chatbot_0_core` 19.0.1.0.1→19.0.1.0.2; `ai_chatbot_1_portal` 1.0.22→1.0.23) + upgrade con `--test-enable` en staging (`odoo-19-web-leads`, cadena `ai_chatbot_1_portal`).

## Acceptance criteria

- [ ] Replay del transcript: en el paso de consentimiento, "Dame precio primero" y "Dime el precio" reciben explicación del túnel + repetición de la pregunta; ningún mensaje al usuario contiene "booleano" ni "true/false".
- [ ] En el paso de nombre, "Pero quiero saber cuanto sale" NO queda en `datos_paciente` y el paso sigue pendiente.
- [ ] La explicación menciona amablemente que solo se atienden los pasos del registro y cómo salir ("salir").
- [ ] Respuestas válidas (teléfono, nombre, 'sí'/'no', fechas) avanzan el flujo igual que hoy.
- [ ] "salir" (y variantes) sigue cerrando el flujo; "no" como respuesta boolean sigue siendo respuesta, no salida.
- [ ] Sin OpenAI configurado o IA caída: mensajes amigables y desvío por keywords funcionan deterministamente.
- [ ] El contrato hacia n8n no cambia (`texto_para_usuario`, `modo`, `paso_actual`, `success`).
- [ ] `--test-enable` pasa con la cadena en staging.

## Decisions

- **Yes:** reescribir mensajes de TODOS los tipos, no solo boolean — mismo problema de clase, mismo costo.
- **Yes:** ante desvío, explicar túnel + repetir pregunta (no responder la duda dentro del túnel) — evita IA respondiendo contenido del negocio con riesgo de invención.
- **Yes:** detectar desvío también en pasos `text` — corrige el bug de guardar preguntas como nombre/dato.
- **Yes:** clasificación 3-vías en la llamada IA existente — cero llamadas extra, cero latencia nueva.
- **Yes:** repetir la pregunta desde el `mensaje_prompt` almacenado — sin regeneración IA extra.
- **Yes:** dict de mensajes compartido en ai_chatbot_0_core, importado por 1_portal — DRY respetando la dirección de dependencias.
- **Yes:** endurecer el fallback por substring ('no') — bug latente en el mismo código que se reescribe.
- **No:** responder dudas de negocio en el túnel — spec futuro si llega.
- **No:** textos en `chatbot.config` — el tono es parte del núcleo universal (línea SPEC 01); configurabilidad, spec futuro.
- **No:** cambios en n8n.

## Risks

| Risk | Mitigation |
| --- | --- |
| Falso positivo: respuesta válida de paso `text` clasificada como desvío | Prompt con criterio restrictivo (solo preguntas/peticiones explícitas) + keywords de desvío excluyen palabras de control; el usuario reintenta sin perder progreso |
| IA no disponible en la instancia | Fallback determinista por keywords (más grueso pero funcional); mensajes amigables sin IA |
| Fallback de desvío captura una respuesta real ("no tengo costo...") | Lista de exclusión de palabras de control y matching por palabra exacta |
| Regresión en detección de salida | Tests (d) y (c) cubren ambos caminos antes del upgrade |

## What is **not** in this spec

- Responder dudas de negocio dentro del túnel, textos configurables en `chatbot.config`, cambios en n8n, desvío fuera del túnel. Cada uno, si llega, va en su propio spec.
