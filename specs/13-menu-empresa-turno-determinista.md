# SPEC 13 — Menú determinista por empresa de turno y salida IA sin JSON anidado

> **Status:** Implemented
> **Depends on:** SPEC 09, SPEC 10, SPEC 11, SPEC 12
> **Date:** 2026-09-05
> **Objective:** Que el saludo/menú del bot se sirva siempre determinista desde la intención MENU de la config activa (con marca, SPEC 11) — sin depender de la IA ni de RAG — y que la salida de la IA nunca llegue anidada (JSON dentro de `output`) ni con `isMenu=false` en intención MENU, para que el menú represente a la empresa de turno en cada VPS.

## Por qué existe esta spec

Transcript real (2026-09-05, 15:19, bot KARLA CAMPOVERDE): a un "hola", el agente devolvió
`output` **como string JSON escapado** (JSON dentro de JSON) con `isMenu: false`, y el menú
servido en el system_prompt era el genérico pre-SPEC 11 (sin marca). Dos causas:

1. La intención MENU pasó por la IA, que puede desobedecer formato (doble escape,
   `isMenu` incorrecto) — el texto del menú ya está guardado con marca; la IA solo
   lo degrada.
2. El gap de marca ya quedó cerrado operativamente (SPEC 12: regeneración con
   `brand_name`), pero no hay mecanismo que **garantice** el menú con marca por
   defecto en cada VPS nuevo sin depender de la IA.

## Scope

**In:**

- **Menú determinista sin IA:** en n8n (`Separar_variables_en_json` o nodo previo), si
  el system_prompt contiene la sección `=== MENÚ DE OPCIONES ===` y la intención
  detectada es MENU (palabra clave o `tipoPregunta=MENU`), se usa **directamente el
  texto del menú del system_prompt** como `output`, se fuerza `isMenu=true` y
  `tipoPregunta="MENU"`, ignorando lo que la IA haya devuelto. La IA no participa
  en saludos/menú → sin RAG, sin doble escape.
- **Des-nidificación defensiva:** al procesar la salida del agente, si `output` es
  un string que empieza por `{` y parsea como JSON con clave `output`, extraer el
  objeto interno (merge de campos) antes de continuar. Cubre desobediencia de la IA
  en cualquier intención.
- **Checklist operativa de alta de cliente/VPS** (doc en `specs/` o README del
  módulo): crear config → setear `brand_name` → sincronizar RAG → regenerar menú
  con IA → verificar "hola" muestra `*MARCA*` + tagline.
- Bump `ai_chatbot_1_portal` (solo si toca código Odoo; los fixes de n8n son del
  JSON del workflow).

**Out of scope:**

- Routing multicliente por `account_id` en una sola BD (cada VPS = una BD = una
  config activa; decisión cerrada).
- Cambios en el generador de menú IA de Odoo (SPEC 09/11 intactos).
- Regeneración automática post-deploy (sigue manual: botón/sync).

## Data model

Sin modelos ni campos nuevos. Todo es lógica de parsing/ruteo en el workflow n8n
(`ycloud_create_lead_0_con_menu_whatsapp.json`):

```
Entrada al nodo de parseo:
  agent_output.output        → string (posible JSON anidado)
  agent_output.tipoPregunta  → string
  config.system_prompt       → contiene '=== MENÚ DE OPCIONES ===\n<texto>'

Reglas:
  1. Si output parsea como JSON con 'output' → des-nificar (merge de campos).
  2. Si intención MENU → output = texto de MENÚ DE OPCIONES del system_prompt,
     isMenu = true, tipoPregunta = 'MENU'.
```

## Implementation plan

1. En el nodo de parseo del workflow n8n: des-nidificar `output` si es string JSON
   con clave `output` (merge de campos internos). Sistema funcional.
2. Añadir ruteo determinista MENU: si `tipoPregunta === 'MENU'` o el texto del
   usuario matchea las keywords del menú → `output` = sección MENÚ DE OPCIONES del
   system_prompt, `isMenu = true`, `equipo_asignado/flow_name = ''`. La salida de
   la IA se ignora para este caso.
3. Ajustar el prompt (`Agente_Informacion_basica`): regla explícita de que en
   intención MENU debe devolver el menú EXACTO de la sección MENÚ DE OPCIONES con
   `isMenu=true` (defensa en profundidad; el paso 2 es la garantía).
4. Checklist operativa de alta de cliente (doc markdown) con los 5 pasos.
5. Pruebas: replay "hola" → menú con marca, `isMenu=true`, JSON plano; replay de
   intención informativa → sin regresión (RAG y flujos intactos).

## Acceptance criteria

- [ ] "hola" / "menu" → el bot envía el menú de la config activa con `*MARCA*` en
      línea 1 y `isMenu=true`, aunque la IA devuelva JSON anidado o `isMenu=false`.
- [ ] Si la IA anida JSON en `output`, el workflow lo des-nifica y el flujo
      continúa (test: output anidado → output plano).
- [ ] El menú nunca consulta RAG ni depende de la IA: es el texto guardado.
- [ ] Intenciones informativas y de flujo sin regresión (RAG, confirmaciones,
      derivación intactas).
- [ ] Checklist de alta de cliente documentada (config → brand_name → RAG → menú
      → verificación "hola").
- [ ] Cada VPS nuevo reproduce el menú de su empresa sin tocar n8n.

## Decisions

- **Yes:** menú determinista desde el system_prompt (Odoo es la única fuente, SPEC
  03) — la IA no debe reformatear texto ya guardado; elimina doble escape y
  `isMenu` falso en la vía crítica.
- **Yes:** des-nidificación defensiva en n8n — la desobediencia de formato de la IA
  no debe romper el ruteo.
- **Yes:** un VPS = una BD = una config activa — la "empresa de turno" ya está
  resuelta por despliegue; sin routing nuevo.
- **No:** mover el menú a n8n hardcoded — rompería multicliente y SPEC 03.
- **No:** regeneración automática del menú — criterio SPEC 10/12 (costo IA, manual
  por cliente).

## Risks

| Risk | Mitigation |
| --- | --- |
| Regex de MENÚ DE OPCIONES frágil si cambia el formato de `render_prompt` | El marcador `=== MENÚ DE OPCIONES ===` es estable (SPEC 01); test contra el render real |
| La IA ignora la regla MENU del prompt | El paso 2 (n8n) no depende de la IA: garantía determinista |
| Keyword de menú en otro idioma/variante | Reusar las mismas keywords de la intención MENU del system_prompt |
