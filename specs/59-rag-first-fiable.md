# SPEC 59 — RAG-first fiable en modo conversacional: que el bot conteste con el negocio

> **Estado:** Approved
> **Depende de:** SPEC 18 (modo conversacional), SPEC 14 (identificación marca fallback saludos), SPEC 55 (sanitizador), SPEC 58 (anuncio tienda)
> **Fecha:** 2026-09-17
> **Objetivo:** Que en modo conversacional el bot conteste siempre primero con la información del negocio (RAG) y la intención FALLBACK solo aplique a mensajes que no tratan del negocio — eliminando la respuesta "Disculpa, no entendí" ante "que hacen" o "ghola".

## Por qué existe esta spec

Evidencia de ejecuciones de n8n (17/9, workflow `ycloud_create_lead_0_con_menu_whatsapp`): la IA responde la intención FALLBACK ("Disculpa, no entendí 🤔...") pese a que el RAG (`n8n_vectors` en la BD de lead) tiene 12 documentos íntegros del negocio ("TÚ ERES: BOT INTEGRAIA...", "== QUÉ ES EL PRODUCTO =="...). El modo conversacional está activo (SPEC 18: el RAG responde primero) y el system prompt que Odoo entrega ya instruye "responde PRIMERO con la información disponible del RAG", pero la IA igual elige FALLBACK — la decisión es probabilística (la IA no llama a la tool del RAG antes de responder). En la misma sesión, antes del deploy de SPEC 58 el bot sí respondió contenido del negocio ("¿Te ayudo con alguna cotización..."); tras el deploy contesta FALLBACK a "ghola" y "que hacen". La fiabilidad de la respuesta del negocio no debe depender de que la IA decida usar la herramienta de RAG.

También cae a FALLBACK el saludo con typo "ghola": el sanitizador de SPEC 55 solo limpia símbolos; no empatiza typos de letra.

## Scope

**In:**

1. **Instrucción RAG-first incuestionable en el prompt de negocio** (`ai_chatbot_1_portal` — generación del `system_prompt` en `chatbot_config.py`): añadir una sección determinista de reglas de PRIORIDAD al final del prompt del negocio (antes del bloque del carrito):
   - Responder SIEMPRE con la información disponible en el documento (RAG); NUNCA usar la intención FALLBACK si la pregunta guarda relación con el negocio.
   - FALLBACK solo cuando el mensaje no se interprete y no trate del negocio; para saludos y preguntas generales, presentar las capacidades del negocio.
2. **Saludo con typo (`ghola`)**: en el sanitizador determinista actual (SPEC 55), si el texto normalizado contiene `hola` como subcadena, clasificar SALUDO/Bienvenida del negocio — sin pasar por la IA ni el FALLBACK.
3. **n8n sin cambios de flujo**: el workflow vivo se deja tal cual; el fix es server-side desde Odoo (prompt + sanitizador determinista). El anuncio determinista de n8n (SPEC 32/58) no se toca.
4. **Tests nuevos** para prompt + sanitizador + regresión de suites existentes.

**Out of scope (para futuras specs):**

- Audit del nodo Postgres PGVector Store del subflow (otra spec si las pruebas lo requieren).
- Cambio del prompt del "Vendedor IA" del carrito (SPEC 50/51).
- Regenerar los 12 docs del RAG (workspace SPEC 43).
- Cambios en `chatbot_cart` (SPEC 58 queda intacto).

## Modelo de datos

Sin cambios de estructuras. Cambios de contrato en el `system_prompt` generado y en el sanitizador de entrada:

```python
# Sección de prioridades inyectada al system_prompt del negocio (modo conversacional):
_PRIORIDADES_RAG_FIRST = (
    "PRIORIDAD DE RESPUESTA (modo conversacional):\n"
    "1. Responde SIEMPRE con la información disponible del negocio (RAG).\n"
    "2. NUNCA uses la intención FALLBACK si la pregunta guarda relación con el negocio.\n"
    "3. FALLBACK solo ante mensajes que no traten del negocio.\n"
    "4. Ante saludos y preguntas generales, presenta las capacidades del negocio.\n"
)

# Sanitizador de saludo: 'ghola' contiene 'hola' → SALUDO
if 'hola' in texto_normalizado:
    # intención SALUDO / bienvenida determinista
```

## Plan de implementación

1. `ai_chatbot_1_portal` (`chatbot_config.py`): añadir la sección de PRIORIDADES al `system_prompt` del negocio (antes del bloque del carrito), con fallback sin IA (patrón SPEC 14/45).
2. Sanitizador determinista del saludo: si el texto normalizado contiene `hola` como subcadena → intent SALUDO/Bienvenida, sin pasar por la IA.
3. Tests nuevos (prompt con prioridades RAG-first; 'ghola' → SALUDO) + regresión suites.
4. Upgrade módulo en lead + E2E WhatsApp real (Teresa/Simon): "ghola" → bienvenida del negocio; "que hacen" → respuesta del negocio desde el RAG; carrito sigue funcionando.

## Criterios de aceptación

- [ ] "ghola" → bienvenida del negocio (sin "Disculpa, no entendí").
- [ ] "que hacen" → respuesta del negocio desde el RAG (sin FALLBACK).
- [ ] El prompt del negocio incluye la sección de PRIORIDADES RAG-first.
- [ ] FALLBACK solo cuando el mensaje no trata del negocio.
- [ ] El anuncio de tienda (SPEC 58) sigue llegando tras la respuesta.
- [ ] Suites `ai_chatbot_1_portal` verdes.

## Decisiones tomadas y descartadas

- **Tomado:** instrucción RAG-first en el prompt server-side (Odoo) — **descartado** tocar el subflujo n8n (la tool del RAG es probabilística; reforzar el prompt es el cambio de menor riesgo y reversible).
- **Tomado:** sanitizador de saludo por subcadena `hola` — **descartado** fuzzy matching / edición Levenshtein (ambiguo y caro para un saludo).
- **Tomado:** n8n sin cambios — **descartado** modificar `Unificar_salida` (SPEC 32/58 intactos).
- **Tomado:** modo conversacional (SPEC 18) se mantiene — **descartado** volver a menú determinista (el usuario eligió RAG-first conversacional).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| La IA ignora la instrucción RAG-first (sigue siendo probabilística) | La instrucción es explícita y se probará E2E; si falla, plan B = clasificación determinista por keywords del config (futura spec) |
| `hola` como subcadena puede colisionar con otras palabras (ej. "colación" no contiene `hola`) | Verificar en tests: solo se activa en la ruta de saludo/entrada; sin impacto en otras intenciones |
| El RAG está en lead (`n8n_vectors`) pero en prod puede diferir | El fix es de prompt/sanitizador, no del contenido RAG |

## What is **not** in this spec

- Audit del nodo Postgres PGVector Store del subflow.
- Cambio del prompt del Vendedor IA del carrito (SPEC 50/51).
- Regenerar los documentos RAG.
- Cambios en `chatbot_cart` (SPEC 58 intacto).

Cada uno de esos, si llega, va en su propia spec.