# SPEC 71 — Confirmación única por intención explícita y teléfono capturado del mensaje de disparo

> **Estado:** Approved
> **Depende de:** SPEC 06 (protocolo "no sé" y reglas 16/17), SPEC 01 (motor de flujos), SPEC 43 (workspace n8n_json en lead), SPEC 64 (risgo documentado: n8n nunca envía teléfono a /inicioagendar)
> **Fecha:** 2026-09-24
> **Objetivo:** Que el flujo de contacto se dispare con la primera afirmación explícita de intención del cliente y arranque con el teléfono ya extraído de su mensaje, eliminando el doble "Responde Sí" y la re-pregunta del teléfono.

## Por qué existe esta spec

Transcript real de prod (24-sep, INTEGRAIA):

1. El cliente escribe *"Me gustaría poder contactarlos y plantearles mi idea y así me puedan ayudar a crear un plan adecuado y si respectivo costo"* — una intención explícita de ser contactado. El bot, aun así, responde *"Responde Sí si te gustaría que coordine una reunión"*: un segundo gate "Sí o No" que **arrincona** al usuario sin necesidad.
2. El cliente obedece y escribe *"Si mi numero de teléfono es 04143160999"*. El flujo se dispara, pero n8n llama `/inicioagendar` **sin el mensaje del usuario** (jsonBody verificado en `chatbot_create_lead_0_con_menu_whatsapp.json`: solo session/conversation/account/flow/equipo/plataforma — riesgo ya documentado en SPEC 64), así que el teléfono se pierde y el primer paso del flujo lo vuelve a pedir: *"Para empezar, ¿me compartes tu número de teléfono?"*. El cliente que ya dio todo queda atrapado repitiéndose.

En el mismo hilo, un tercer síntoma: ante la instalación de WhatsApp Cloud API, el bot reprodujo el documento del RAG que instruye *"facilitarme tu usuario y contraseña de Facebook"*. El contenido del RAG lo gestiona el usuario (fuera de esta spec); lo que sí toca aquí es una regla universal que impida al bot pedir credenciales aunque el RAG las mencione.

La solución usa machinery que ya existe: `iniciar_flujo` filtra los pasos cuyo `campo_destino` ya tiene valor en `datos_precargados` (chatbot_session.py:207-221) — nunca recibe datos porque n8n no los manda.

## Scope

**In:**

1. `ai_chatbot_1_portal/services/prompt_renderer.py` — extender la **regla 16** del `_UNIVERSAL_SKELETON`: una **afirmación explícita** de querer ser contactado / asesoría / cotización / cita ("me gustaría contactarlos", "quiero una asesoría", "contáctenme", "quiero plantearles mi idea") **es en sí la confirmación**: dispara el flujo en ese mismo mensaje, sin segunda pregunta "Sí o No". La regla 17 (una pregunta nunca es confirmación) y el gate "no sé → ¿quiere un asesor? Responde Sí o No" de SPEC 06 quedan **intactos**.
2. `ai_chatbot_1_portal/services/prompt_renderer.py` — nueva **regla 19 anti-credenciales**: jamás pedir ni aceptar contraseñas, PINs, códigos de verificación ni datos de acceso de cuentas del cliente, aunque un documento del RAG describa procedimientos que lo impliquen; ofrecer en su lugar coordinación con un humano (flujo de asesor).
3. `ai_chatbot_1_portal/controllers/chatbot_utils.py` — helper `ChatBotUtils._extraer_telefono(texto)`: candidatea secuencias de dígitos con regex y valida/normaliza con `_normalizar_telefono` existente (móvil venezolano: 04XX…, 414…, +58…, 58…; 10 dígitos). Sin candidato válido → `None`.
4. `ai_chatbot_1_portal/controllers/chatbot_0_inicio_agendar_procesar_paso_conroller.py` — `/inicioagendar` acepta campo opcional `mensaje_usuario` (string). Si no vino `telefono` explícito, se extrae el teléfono de `mensaje_usuario` y: (a) alimenta `telefono_busqueda` para `_precargar_datos_cliente` (cliente existente: precarga nombre/email/etc. como hoy), y (b) si no hay partner, se inyecta en `datos_precargados` con las claves canónicas `telefono`, `phone`, `solicitar_phone` (las que usan `iniciar_flujo`/`capturar_lead`) → el paso teléfono se salta.
5. n8n (`/home/odoo/lead/odoo19-skeleton/n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json`, nodo `paso_0_inicio_agendar`) — añadir al `jsonBody`:
   `"mensaje_usuario": {{ JSON.stringify($('Obtener_configuracion_agente').item.json.text || '') }}`
   (JSON.stringify escapa comillas/saltos del texto crudo del cliente; el trigger siempre lleva `text`). Commit en rama `lead` del skeleton.
6. Tests nuevos: reglas exactas del prompt (regla 16 extendida + regla 19), `_extraer_telefono` (formatos VZ, texto rodeado, sin teléfono, no confundir "$25" u otros números con móvil), e `inicioagendar` con `mensaje_usuario` → flujo arranca con `telefono` en `datos_paciente` y el primer paso pendiente es el **nombre**, no el teléfono. Regresión de las suites de `ai_chatbot_1_portal`.
7. Bump `ai_chatbot_1_portal` 1.0.44 → 1.0.45, upgrade en lead + E2E WhatsApp con replay del transcript.
8. Promoción a prod: solo manual tras E2E verde (SPEC 43/63): copiar el JSON exportado a `/home/odoo/prod/odoo19-skeleton/n8n_json/` + commit `main` + push + upgrade del módulo en prod (lo ejecuta el usuario).

**Out of scope (para futuras specs):**

- Editar o regenerar el contenido del RAG (documento de instalación de WhatsApp Cloud API con la petición de contraseña, precio de "Shared post"): lo gestiona el humano, por su advertencia expresa.
- El caso "¿Cuánto cuesta?" sobre un posteo compartido: la respuesta honesta "no tengo esa información" + derivación a asesor (SPEC 06) se acepta como comportamiento correcto.
- Extraer email o nombre del mensaje de disparo (solo teléfono: es el paso 1 de los flujos de contacto y donde se atasca; el nombre es ambiguo).
- Cambiar la heurística `detectarSiNo`/`esPreguntaSiNo` del nodo `Separar_variables_en_json` ni el resto del workflow n8n.
- El prompt del Vendedor IA del carrito (SPEC 50/51).
- Guardrail determinista que rechace `/inicioagendar` sin confirmación previa (SPEC 06 lo dejó como spec futura).

## Modelo de datos

Sin modelos ni campos nuevos en Odoo. Cambia el contrato HTTP de `/ai_chatbot_1_portal/inicioagendar`: una clave opcional nueva.

```python
# Body de /inicioagendar (nuevo campo opcional)
{
  "session_id": "...", "conversation_id": "...", "account_id": "...",
  "name_flow": "flujo_agendamiento_otra_consulta",
  "equipo_asignado": "...", "plataforma": "whatsapp",
  "mensaje_usuario": "Si mi numero de teléfono es 04143160999"  # opcional
}

# ChatBotUtils._extraer_telefono(texto) -> str | None
#   entrada libre → normaliza a +58XXXXXXXXXX solo si es móvil venezolano válido
#   "Si mi numero es 04143160999" → "+584143160999"
#   "te quiero mucho"             → None
#   "cuesta $25 x 2"              → None   (no es secuencia de 10 dígitos 04XX)

# Semilla en datos_precargados cuando no hay partner (claves que ya consumen
# iniciar_flujo por campo_destino y capturar_lead):
{'telefono': '+584143160999', 'phone': '+584143160999', 'solicitar_phone': '+584143160999'}
```

Reglas del flujo de datos:

- `telefono` explícito en el body (si algún día llega) tiene prioridad sobre el extraído.
- Con partner encontrado por teléfono, la precarga de `_precargar_datos_cliente` gana (ya cubre las tres claves); el teléfono extraído solo se usa como término de búsqueda.
- El seed del teléfono extraído **nunca pisa** una clave ya presente en `datos_precargados`.

## Plan de implementación

1. `chatbot_utils.py`: `RE_TELEFONO_CANDIDATO` + `_extraer_telefono()` apoyándose en `_normalizar_telefono` (rechaza candidatos que no queden en el patrón +58 + 10 dígitos empezando en 4). Tests unitarios de formatos y no-falsos-positivos. Funcional por sí solo.
2. `prompt_renderer.py`: texto nuevo de la regla 16 (intención afirmativa = confirmación, con ejemplos literales del transcript) y regla 19 anti-credenciales. Tests exactos al estilo SPEC 06 (`test_prompt_renderer.py`) + asserts de que la regla 17 y el protocolo "NO SÉ" no cambiaron.
3. `inicio_agendar`: leer `mensaje_usuario`; si no hay `telefono_busqueda`, `telefono_busqueda = _extraer_telefono(mensaje_usuario)`; tras `_precargar_datos_cliente`, si sigue sin `telefono` en `datos_precargados`, inyectar el extraído con las tres claves. Test de controller: POST con `mensaje_usuario` conteniendo teléfono → respuesta con `primer_paso` = paso nombre y `datos_paciente.telefono` poblado.
4. Editar el export n8n `paso_0_inicio_agendar` (jsonBody + `mensaje_usuario` con `JSON.stringify`), importar el JSON en el n8n de **lead**, y commitear en la rama `lead` de `odoo19-skeleton` (SPEC 43). Ningún otro nodo toca.
5. Bump manifest 1.0.45; `-u ai_chatbot_1_portal --test-enable` en `odoo-19-web-leads` (0 FAIL) con las suites completas.
6. E2E WhatsApp en lead (replay del transcript): "Me gustaría contactarlos y plantearles mi idea" → el flujo arranca **de una** (aviso + primera pregunta, sin gate "Responde Sí"); "Si mi numero de teléfono es 04143160999" → el flujo no re-pide el teléfono; "¿me haces un descuento?" → sigue exigiendo confirmación (regla 17); "necesito instalar WhatsApp, ¿qué necesito?" → el bot NO pide contraseñas (regla 19).
7. Promoción manual a prod (usuario, tras E2E verde): `cp` del JSON al skeleton prod + commit `main` + push + upgrade 1.0.45 en la DB de prod.

## Criterios de aceptación

- [ ] El prompt renderizado contiene la extensión de la regla 16 ("afirmación explícita de contacto/asesoría/cotización/cita es la confirmación; no se vuelve a preguntar") y la regla 19 anti-credenciales, y conserva textualmente la regla 17 y el protocolo "NO SÉ" (tests exactos).
- [ ] `ChatBotUtils._extraer_telefono` devuelve el móvil normalizado a `+58…` para los formatos 04143160999 / +58 414 3160999 / 584143160999 embebidos en prosa, y `None` para texto sin móvil o con solo precios/cantidades.
- [ ] POST `/inicioagendar` con `mensaje_usuario="Si mi numero de teléfono es 04143160999"` y flujo de contacto: `datos_paciente.telefono='+584143160999'` y `primer_paso.nombre_interno != 'telefono'` (el paso teléfono se saltó).
- [ ] POST `/inicioagendar` sin `mensaje_usuario` o sin teléfono en él: comportamiento idéntico al actual (step teléfono se pregunta) — cero regresión.
- [ ] El nodo `paso_0_inicio_agendar` del export de lead envía `mensaje_usuario` con el texto crudo escapado (JSON válido aunque el mensaje contenga comillas o saltos).
- [ ] E2E lead: "me gustaría contactarlos…" dispara el flujo en ese mismo mensaje (sin segundo "Responde Sí o No").
- [ ] E2E lead: confirmación que trae teléfono → el flujo pregunta el siguiente dato, no el teléfono.
- [ ] E2E lead: preguntas de negociación ("¿cómo pago?", "¿me haces un descuento?") siguen respondándose primero y pidiendo confirmación (regla 17 sin regresión).
- [ ] E2E lead: ante un trámite que el RAG describe pidiendo contraseñas, el bot no solicita credenciales y ofrece coordinación humana.
- [ ] Suites `ai_chatbot_1_portal` verdes en lead; módulo versionado 1.0.45.
- [ ] Commits: `modulos_odoo` (código+tests) y `odoo19-skeleton` rama `lead` (JSON n8n). La promoción a prod queda constada como acción manual del usuario.

## Decisiones tomadas y descartadas

- **Tomado:** intención afirmativa explícita = confirmación válida — **descartado:** mantener el doble gate "Sí o No" (arrincona al cliente y el transcript muestra que ya consintió; las reglas 16/17 solo pedían confirma para *preguntas*).
- **Tomado:** n8n pasa el `mensaje_usuario` crudo y Odoo extrae el teléfono — **descartado:** extraer en un Code node de n8n (duplica la normalización VZ fuera de Odoo, no testeable con la suite) y **descartado:** que Odoo consulte el último mensaje a Chatwoot (acoplamiento y latencia extra por un dato que n8n ya tiene en mano).
- **Tomado:** solo teléfono en la extracción — **descartado:** email y nombre (ningún flujo de contacto pide email primero; el nombre embebido en prosa es ambiguo y generaría falsos positivos que saltarían el paso).
- **Tomado:** regla universal anti-credenciales en el esqueleto — **descartado:** editar el documento del RAG como fix (el usuario gestiona su contenido; la regla protege además ante cualquier doc futuro, y el RAG sigue siendo primario para datos).
- **Tomado:** reutilizar el mecanismo `datos_precargados` de `iniciar_flujo` (ya salta pasos con valor) — **descartado:** un parámetro `salta_paso` nuevo (duplica un mecanismo existente).
- **Tomado:** `JSON.stringify` en el jsonBody de n8n para el texto crudo — el interpolation simple rompería el JSON con comillas/saltos del mensaje del cliente.
- **No:** tocar la heurística `detectarSiNo`/menú de `Separar_variables_en_json`, el caso "Shared post" y el contenido del RAG (fuera, arriba).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Falso positivo de teléfono (un número de 10 dígitos que no es móvil, p. ej. cédula/RIF) y el flujo salta el paso con dato erróneo | `_extraer_telefono` solo acepta secuencias que normalizan a móvil venezolano (`04XX…`/+58+`4`+9 dígitos); si queda malo, el humano corrige al llamar y el lead muestra el teléfono tal cual; tests con no-falsos-positivos |
| El LLM sigue confirmando de más pese a la regla (prompt ≠ determinismo) | Ejemplos literales del transcript en la regla 16; el paso 6 del plan es un replay E2E obligatorio; plan B (future spec): guardarrail determinista en `/inicioagendar` |
| El texto crudo del cliente rompe el JSON del body de n8n | `JSON.stringify` en la expresión; test manual con mensaje conteniendo `"` y salto de línea |
| `mensaje_usuario` con PII se loguea | El controller ya loguea payloads (`_logger.debug("JSON recibido")`); el teléfono se loguea igual que en `/procesar_paso` hoy — sin exposición nueva; sin cambios de log en esta spec |
| Drift lead↔prod del workflow (SPEC 43) | Prod solo recibe el JSON por promoción manual documentada (paso 7), igual que SPEC 63 |

## What is **not** in this spec

- Edición del contenido del RAG (doc de instalación de WhatsApp, precios de "Shared post").
- Extracción de email/nombre del mensaje de disparo.
- Cambios en el resto del workflow n8n, en `Separar_variables_en_json` ni en el subflujo RAG.
- Respuesta de dudas de negocio dentro del túnel, guardrail determinista en `/inicioagendar`, textos configurables por cliente (línea SPEC 04/06).
- Prompt del Vendedor IA del carrito.

Cada uno de esos, si llega, va en su propia spec.
