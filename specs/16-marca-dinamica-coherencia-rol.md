# SPEC 16 — Marca dinámica y coherencia marca↔rol

> **Status:** Approved
> **Depends on:** SPEC 13, SPEC 14
> **Date:** 2026-09-06
> **Objective:** Que la marca del bot sea siempre la misma empresa en saludo, prompt y respuestas — derivada dinámicamente del rol (nunca hardcodeada) y validada por constrains — eliminando mezclas tipo "saluda *Karla Campoverde* pero responde INTEGRAIA".

## Por qué existe esta spec

Bug real (2026-09-06): testeando prod (bot de IntegraIA, cliente real de la plataforma) el saludo decía `Te saluda *Karla Campoverde*` (marca copiada de staging durante el deploy de SPEC 14) mientras las respuestas informativas hablaban de INTEGRAIA (salían del rol). Causa: `brand_name` se escribió a mano con el valor de otro cliente. Cada empresa debe tener su rol y su marca coherentes; la marca nunca debe venir de otro contexto ni hardcodearse.

## Scope

**In:**
- **Extracción dinámica de marca (Odoo):** si `brand_name` está vacío, al regenerar menú / sincronizar desde RAG la IA extrae el nombre de la empresa del texto del rol (`_extraer_marca_del_rol`, use case nuevo en `ai_chatbot_0_core`) y lo guarda. Si el usuario ya puso marca, se respeta. Fallback determinista si la IA falla (patrón `BOT <NOMBRE>.` / primera entidad del rol).
- **Constrains bloqueante:** `@api.constrains('brand_name', 'role')` en `chatbot.config` — la marca (sin asteriscos, case-insensitive) debe aparecer en el rol. Evita que otro cliente quede incoherente ("Ventas Sillas Paper" con rol de otro negocio).
- **Fix script de deploy:** alinear configs existentes incoherentes (extraer marca del rol) ANTES de que el constrains bloquee writes futuros.
- **Regla de identidad en el prompt universal:** la empresa es siempre `{brand}`; la IA jamás menciona otra empresa ni terceros en sus respuestas.
- **Fix en prod con el mecanismo dinámico:** extraer marca del rol INTEGRAIA + regenerar menú + FALLBACK (sin escribir nada a mano).
- Bump de versiones + tests.

**Out of scope:**
- Marca en respuestas RAG exitosas (spec futura).
- Cambios en n8n (el ruteo determinista de SPEC 13/14 no cambia).
- Migración de datos de otros clientes (solo configs activas existentes).

## Data model

Sin campos nuevos. `brand_name` pasa a ser derivable del rol; el constrains añade la regla de coherencia.

## Implementation plan

1. `ai_chatbot_0_core`: use case `extraer_marca_del_rol` (IA + fallback determinista) y regla de identidad en el skeleton del prompt.
2. `ai_chatbot_1_portal` (`chatbot_config.py`): `_preparar_marca()` (extrae y guarda si vacía) llamada en `action_regenerar_menu` y `action_recargar_todo_desde_rag`; constrains de coherencia; la marca ya no se imprime a mano nunca.
3. Tests: extracción dinámica (IA mockeada + fallback), constrains (error si marca ∉ rol), coherencia del prompt renderizado (contiene la marca y NO contiene marcas de otros configs).
4. Deploy: fix script alinea configs existentes → upgrade módulos → en prod: sincronizar/regenerar (extrae "IntegraIA" del rol) → verificación.
5. Verificación: replay "hola"/"k" → saluda `*IntegraIA*` y "Que hacen" → responde INTEGRAIA (misma empresa); staging tests OK.

## Acceptance criteria

- [ ] Config con `brand_name` vacío + regenerar → la marca se extrae del rol y se guarda (sin hardcode).
- [ ] Guardar config con marca que no aparece en el rol → `ValidationError`.
- [ ] El prompt renderizado contiene la regla "jamás menciones otra empresa".
- [ ] Prod: saludo del menú y respuesta informativa nombran la MISMA empresa.
- [ ] Fix script alineó las configs existentes antes del constrains.
- [ ] 105+ tests de staging pasan.

## Decisions

- **Yes:** extraer del rol solo si `brand_name` está vacío (se respeta la marca manual; dinámico por defecto).
- **Yes:** constrains bloqueante (no warning) — la incoherencia ya costó una queja real de cliente.
- **Yes:** fix script en deploy para no romper writes sobre configs viejas.
- **No:** sobreescribir `brand_name` en cada regeneración (pisaría decisiones del operador).
- **No:** detección heurística de nombres ajenos en runtime (el constrains + prompt bastan; lo "extra" se loguea en el test).

## Risks

| Risk | Mitigation |
| --- | --- |
| La IA extrae un nombre incorrecto del rol | Fallback determinista (patrón `BOT X.` / entidad principal) + constrains valida contra el rol |
| Config comercial cuyo rol usa nombre legal distinto de la marca | El operador puede fijar la marca manualmente antes de regenerar (el constrains exige que aparezca en el rol) |
| El constrains rompe automatizaciones existentes | Fix script se ejecuta antes del upgrade en el deploy |
