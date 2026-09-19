# SPEC 65 — Prompt RAG + config: el bot usa rol/objetivo, contacto y conocimiento junto al RAG

> **Estado:** Approved
> **Depende de:** SPEC 18 (modo conversacional), SPEC 59 (RAG-first fiable), SPEC 03 (una sola fuente de configuración)
> **Fecha:** 2026-09-19
> **Objetivo:** Que en modo conversacional el bot presente el negocio usando el rol/objetivo, el enlace de la tienda, el contacto y los temas de la base de conocimiento configurados manualmente, manteniendo el RAG como fuente primaria para datos fácticos — sin tocar n8n.

## Por qué existe esta spec

La config de INTEGRAIA tiene `role`, `contacto`, `bloque_conocimiento` y `cta_url` completados **manualmente** porque el RAG (`n8n_vectors`) no trajo esas secciones por defecto. Esos campos sí se renderizan en el system_prompt (`render_prompt`, secciones `TÚ ERES`, `CONTACTO`, `CONOCIMIENTO DEL NEGOCIO`, `LLAMADA A LA ACCIÓN`), pero el agente no los usa porque las **reglas 13 y 14** del esqueleto universal prohíben usar el texto de las secciones del prompt como respuesta ("NUNCA uses el texto de las secciones de este prompt como si fuera la respuesta"). Resultado: el bot nunca menciona el objetivo ni el enlace `https://lead.integraia.lat/shop`, y su presentación queda 100% a merced de lo que el LLM recupere del RAG.

El diseño deseado (validado con el usuario): el RAG sigue siendo primario para **datos** (precios, medidas, horarios, políticas), pero el **rol/objetivo, el contacto, los temas y el enlace de tienda** de la config son contenido autorizado que el agente debe usar para **presentar la empresa**, ofrecer el siguiente paso y cerrar con una CTA discreta. La presentación se entrega determinista (texto generado en Odoo e inyectado al prompt), sin depender de la decisión probabilística del LLM.

## Scope

**In:**

1. Nuevo campo `chatbot.config.presentacion_texto` (Text) — presentación autoritativa del negocio, editable por el humano. Ubicado en la ficha **debajo de "Rol / objetivo"**.
2. Método determinista `_generar_presentacion_conversacional()` que arma la presentación desde `brand_name` + **`role` (texto completo)** + temas del `bloque_conocimiento` + `cta_url` (tienda) + `contacto`.
3. **Auto-generación al guardar** (override de `write`/`create` en `chatbot.config`): si `presentacion_texto` está vacío y hay datos fuente, se llena automáticamente. **No se sobreescribe** si el humano ya lo editó.
4. **Auto-generación en "Sincronizar todo desde RAG"** (`_refrescar_desde_rag`): misma guardia — solo si `presentacion_texto` está vacío; la sync nunca pisa la edición manual.
5. En `render_prompt`, **solo modo conversacional** (`menu_enabled=False`), tras `_PRIORIDADES_RAG_FIRST`:
   - Nueva sección fija `=== PRESENTACIÓN DEL NEGOCIO ===` con `presentacion_texto`.
   - Regla de "contenido autorizado": las secciones `TÚ ERES`, `PRESENTACIÓN`, `CONTACTO`, `LLAMADA A LA ACCIÓN` y `CONOCIMIENTO DEL NEGOCIO` son contenido del negocio que el agente **puede y debe** usar para presentar la empresa, dar contacto y cerrar con la tienda — con el RAG siempre primario para datos.
   - Regla de saludo/presentación: ante "hola", "qué hacen", "quién eres", "qué ofrecen", responder presentando la empresa con la PRESENTACIÓN (adaptable con palabras propias), mencionando la tienda online y los temas en los que puede ayudar.
   - Regla de CTA discreto: al cerrar respuestas informativas relevantes (catálogo, compra, planes), ofrecer discretamente la tienda online; no en cada mensaje.
6. `_refrescar_desde_rag`: **no** tocar `presentacion_texto` si está editado; conservar `role`/`contacto` manuales cuando el RAG no traiga esas secciones (comportamiento actual reforzado) y avisarlo en el resumen.
7. Tests nuevos + regresión de `ai_chatbot_1_portal`. Bump del módulo a `1.0.44`.
8. E2E WhatsApp en lead: saludo menciona objetivo + tienda; pregunta de precios responde desde RAG y cierra con CTA.

**Out of scope (para futuras specs):**

- Cambios en workflows n8n (SPEC 43): el fix es 100% Odoo; n8n solo recibe el `system_prompt`.
- Cambios en modo menú (`menu_enabled=True`): su prompt queda exactamente como está (sin sección PRESENTACIÓN ni reglas nuevas).
- Sincronización inversa config → RAG (inyectar la config como documento en `n8n_vectors`).
- Cambiar el prompt del Vendedor IA del carrito (SPEC 50/51).
- Generar el "objetivo" con IA: el texto sale determinista de los campos de la config.

## Modelo de datos

Un campo nuevo en `chatbot.config`:

```python
presentacion_texto = fields.Text(
    string="Presentación del negocio",
    help="Texto autoritativo que el bot usa al saludar/presentarse "
         "(modo conversacional). Se genera automáticamente desde el rol, "
         "los temas RAG, la tienda y el contacto; editable manualmente "
         "(no se sobreescribe si ya tiene contenido).",
)
```

Plantilla determinista de `_generar_presentacion_conversacional()` (role completo):

```
¡Hola! Te saluda *{brand_name}*.

{role (texto completo, tal cual está configurado)}

Puedo ayudarte con: {temas del bloque_conocimiento, lista limpia}

Visita nuestra tienda online: {cta_url}

{contacto}
¿En qué puedo ayudarte? 😊
```

Reglas del generador: omite cada bloque vacío (sin role, sin cta_url, sin contacto, sin temas). No altera `role` ni `contacto` originales. El role completo garantiza que el objetivo (aunque esté en bullets) y el enlace de la tienda queden dentro de la presentación.

Guardia de auto-generación (al guardar y en sync):

```python
if not config.presentacion_texto.strip():
    config.presentacion_texto = config._generar_presentacion_conversacional()
```

## Plan de implementación

1. Campo `presentacion_texto` en `chatbot.config` + vista (debajo de "Rol / objetivo"). Commit verificable (upgrade sin error).
2. Método `_generar_presentacion_conversacional()` en `chatbot_config.py` (brand + role completo + temas del `bloque_conocimiento` + `cta_url` + `contacto`, omitiendo bloques vacíos). Test manual: llamarlo con la config de INTEGRAIA → devuelve el texto esperado con objetivo y tienda.
3. Auto-generación al guardar: override `create`/`write` en `chatbot.config` — si el campo queda vacío y hay datos fuente, llenarlo. Test: crear config sin presentación → se llena; editar manualmente → no se sobreescribe.
4. `_refrescar_desde_rag`: misma guardia de auto-generación al final (si quedó vacío) + conservación reforzada de `role`/`contacto` manuales + aviso en el resumen. Test: sync con RAG sin sección TÚ ERES conserva role manual y, si la presentación está vacía, la llena.
5. `render_prompt` (modo conversacional): inyectar `=== PRESENTACIÓN DEL NEGOCIO ===` con `presentacion_texto` y las reglas de "contenido autorizado", "saludo/presentación" y "CTA discreto" tras `_PRIORIDADES_RAG_FIRST`. Test: el prompt conversacional incluye la sección y las reglas; el prompt en modo menú no las incluye.
6. Tests nuevos en `tests/` (sección PRESENTACIÓN + reglas; generador determinista con y sin campos; auto-generación al guardar y en sync; sync conserva manual) + regresión de las suites `ai_chatbot_1_portal`.
7. Bump `ai_chatbot_1_portal` a `1.0.44`, upgrade en lead + E2E WhatsApp real: saludo → objetivo + tienda + temas; "precios" → respuesta RAG + CTA tienda; "horario" → dato del config/RAG sin "no sé".

## Criterios de aceptación

- [ ] El prompt conversacional incluye `=== PRESENTACIÓN DEL NEGOCIO ===` con el `presentacion_texto` de la config activa.
- [ ] El prompt conversacional incluye las reglas de "contenido autorizado", "saludo/presentación" y "CTA discreto".
- [ ] El prompt en modo menú (`menu_enabled=True`) NO incluye la sección PRESENTACIÓN ni las reglas nuevas (sin regresión de SPEC 13/17).
- [ ] Al crear/guardar una config con `presentacion_texto` vacío y datos fuente, el campo se llena automáticamente con marca, role, temas, tienda y contacto.
- [ ] Editar `presentacion_texto` manualmente NO se sobreescribe al volver a guardar ni al "Sincronizar todo desde RAG".
- [ ] "Sincronizar todo desde RAG" con RAG sin sección TÚ ERES conserva el `role` manual, no pisa la presentación editada y lo avisa en el resumen.
- [ ] "hola"/"qué hacen" → el bot se presenta mencionando el objetivo y el enlace de la tienda (E2E WhatsApp en lead).
- [ ] "precios"/"catálogo" → respuesta con datos del RAG (no inventados) y cierre con CTA discreto a la tienda.
- [ ] "horario"/"contacto" → responde con el dato del `contacto` o del RAG, sin "no tengo esa información" cuando existe en la config.
- [ ] Suites `ai_chatbot_1_portal` verdes en lead. Módulo versionado `1.0.44`.
- [ ] Ningún JSON n8n cambia en esta spec.

## Decisiones tomadas y descartadas

- **Tomado:** fijar el fix 100% en Odoo (prompt + presentación determinista) — **descartado** tocar n8n (SPEC 43): menor riesgo, reversible, sin coordinar exports.
- **Tomado:** la presentación se inyecta como sección fija del `system_prompt` con instrucción de usarla al saludar — **descartado** un campo "bienvenida" servido por endpoint nuevo que n8n no lee hoy (exigiría cambio n8n).
- **Tomado:** excepción de "contenido autorizado" solo en modo conversacional — **descartado** tocar el esqueleto universal para ambos modos (el modo menú ya sirve contenido determinista; evitar regresión).
- **Tomado:** presentación generada **determinista** desde los campos de la config — **descartado** resumir el objetivo con IA (impredecible; el role ya trae el texto del usuario).
- **Tomado:** usar el **role completo** en la plantilla — **descartado** solo el primer párrafo (el objetivo de INTEGRAIA está en los bullets del role, no en el primero; truncar repetiría el bug).
- **Tomado:** auto-generación al guardar y en la sync, con guardia "solo si vacío" — **descartado** botón explícito y **descartado** regenerar siempre (pisaría ajustes manuales).
- **Tomado:** campo ubicado debajo de "Rol / objetivo" en la ficha — queda junto a su fuente.
- **Tomado:** RAG sigue primario para datos — **descartado** inyectar la config como documento RAG (contradice la guardia anti-prompt y mezcla fuentes de verdad).

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| La regla "presentación al saludar" sigue siendo probabilística (el LLM puede ignorarla) | La sección PRESENTACIÓN es determinista y está al final del prompt, cerca de las prioridades RAG-first (SPEC 59); se valida E2E. Plan B si falla: servirlo como bienvenida en un futuro spec con soporte n8n |
| El role completo puede ser largo para una bienvenida de WhatsApp | El campo es editable; el humano lo acorta una vez. El agente adapta con palabras propias (no lo vuelca tal cual) |
| CTA de tienda repetitivo en cada respuesta | La regla limita el CTA a respuestas informativas relevantes (catálogo/compra/planes), no en cada mensaje |
| Regresión en modo menú por tocar el esqueleto universal | Las reglas nuevas se inyectan gated por `menu_enabled=False`; tests de modo menú existentes deben pasar sin cambios |
| El contacto manual se pierde si el RAG trae una sección CONTACTO incompleta | `_refrescar_desde_rag` solo sobreescribe si el RAG trae la sección; se avisa en el resumen del sync |
| Auto-generación pisa una edición manual | Guardia estricta: solo si `presentacion_texto` está vacío; cubierto por test |

## What is **not** in this spec

- Cambios en workflows n8n (exports en `/home/odoo/lead/odoo19-skeleton/n8n_json/`).
- Cambios en el modo menú (`menu_enabled=True`).
- Sincronización inversa config → RAG.
- Resumen del objetivo con IA.
- Cambios en el prompt del carrito (SPEC 50/51) ni en `chatbot_cart`.

Cada uno de esos, si llega, va en su propia spec.