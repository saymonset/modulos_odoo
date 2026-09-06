# SPEC 17 — Menú e intenciones desde los temas reales del RAG

> **Status:** Approved
> **Depends on:** SPEC 13, SPEC 14, SPEC 16
> **Date:** 2026-09-06
> **Objective:** Que el menú generado por "Sincronizar todo desde RAG" liste un ítem por tema real del RAG (inmobiliaria, panadería, etc.) más solo las acciones de flujo que apliquen al negocio — eliminando el menú genérico (agendar/cotizar/confirmar compra) y la mala vinculación intención→flujo del contenido RAG.

## Por qué existe esta spec

Bug real (2026-09-05, bot KARLA CAMPOVERDE): el menú mostró 6 opciones genéricas ("Agendar cita o reserva", "Consulta con un asesor", "Confirmar compra o pedido"...) cuando el RAG solo tiene un tema ("Edificio de Oficinas 350 m²"). Además la intención auto-RAG `EDIFICIO DE OFICINAS` quedó vinculada al flujo PRECIOS y con keywords genéricas (`tiene,qué,capacidad`) que matchean cualquier mensaje. Causa: `_generar_menu_desde_flujos` arma el menú desde el catálogo genérico de flujos (`_MENU_LABELS`) sin usar los temas de `n8n_vectors`, y `_vincular_flow_id_en_intenciones` vincula contenido a flujos por score.

## Scope

**In:**

- **Menú por temas RAG:** `_generar_menu_desde_flujos` (o función nueva) recibe además los temas `es_auto_rag` de la config; el menú lista un ítem numerado por tema del RAG + las acciones de los flujos detectados para ese negocio (excluyendo `flujo_agendamiento_default`).
- **Contenido nunca dispara flujo:** en `_refrescar_desde_rag` / `_vincular_flow_id_en_intenciones`, las intenciones `es_auto_rag` de contenido quedan SIEMPRE con `flow_id = False`. Solo las intenciones de acción (MENU, IMAGEN, CANCELAR, SALIR y sus confirmaciones) llevan flujo.
- **Keywords por tema con IA:** al crear intenciones de contenido desde el RAG, la IA genera keywords específicas del tema (ej. `edificio,oficinas,350,galpón,m²,piso,planta`) en vez de tokens genéricos; fallback determinista: tokens del nombre del tema (stopwords fuera, mínimo 4 caracteres).
- **Un solo paso:** `action_recargar_todo_desde_rag` ya regenera el menú (se mantiene); el menú ahora se arma con temas RAG + acciones.
- **RAG sin temas:** si `n8n_vectors` no rinde temas útiles, menú mínimo con marca + invitación a preguntar (sin opciones de contenido inventadas).
- Bump de versión + tests deterministas.

**Out of scope:**

- Cambios en n8n (workflow `ycloud_create_lead_0_con_menu_whatsapp.json` y "Sistema RAG standar" intactos; SPEC 13 sigue garantizando el menú determinista).
- Cambiar el catálogo de flujos base (`_ensure_catalogo_flujos`).
- Branding/marca (SPEC 16 cerrado).

## Data model

Sin modelos ni campos nuevos. Cambios de comportamiento sobre datos existentes:

```
chatbot.intencion (es_auto_rag de contenido):
  flow_id: antes podía apuntar a flujo (PRECIOS...) → SIEMPRE False
  keywords: tokens genéricos ('tiene','qué') → keywords del tema (IA o tokens del título)

Menú MENU.output_largo:
  antes: 6 acciones genéricas del catálogo de flujos
  después: [bienvenida con marca] + 1 ítem por tema RAG + ítems de acciones detectadas
```

## Implementation plan

1. `chatbot_config.py`: regla dura — en `_refrescar_desde_rag` y `_vincular_flow_id_en_intenciones`, intenciones `es_auto_rag` de contenido con `flow_id = False` (y desvincular las existentes en cada sync). Commit 1 verificable.
2. Keywords por tema: llamada IA (mockeable vía `gpt.service`) con fallback determinista (tokens del título del tema, stopwords filtradas). Integrado en la creación de intenciones de contenido.
3. Menú por temas: `_generar_menu_desde_flujos` recibe los temas RAG y los antepone a las acciones detectadas; caso sin temas → menú mínimo con marca. Actualiza el mensaje de resumen del botón.
4. Tests: menú contiene el tema del RAG y NO contiene "Confirmar compra" cuando el negocio no lo detecta; intención de contenido con `flow_id=False` tras sync; keywords IA (mock) y fallback determinista; caso RAG vacío.
5. Verificación staging: sync en bot Karla (lead) → "hola" muestra "Edificio de Oficinas 350 m²" como opción, sin opciones genéricas; pregunta "¿qué capacidad tiene el edificio?" la responde el RAG sin saltar a flujo PRECIOS.

## Acceptance criteria

- [ ] Tras sync, el menú del bot lista un ítem por tema del RAG (verificado con inmobiliaria: "Edificio de Oficinas 350 m²").
- [ ] El menú no muestra acciones de flujos no detectados para el negocio.
- [ ] Toda intención `es_auto_rag` de contenido tiene `flow_id = False` después de cada sync.
- [ ] Las keywords de contenido no incluyen stopwords genéricas solas ("qué", "tiene"); las genera la IA o el fallback de tokens del tema.
- [ ] RAG vacío → menú mínimo con marca, sin opciones de contenido inventadas.
- [ ] SPEC 13 intacto: el menú se sigue sirviendo determinista desde el system_prompt en n8n.
- [ ] Tests deterministas de staging pasan (suite actual + nuevos).

## Decisions

- **Yes:** el menú se arma en Odoo desde temas RAG + flujos detectados (no en n8n; la plantilla genérica vive en `_generar_menu_desde_flujos` + `_MENU_LABELS`).
- **Yes:** temas RAG primero, acciones después (el menú refleja primero lo que el negocio vende/ofrece).
- **Yes:** regla dura contenido→sin flujo (elimina el matching por score, que produjo el bug EDIFICIO→PRECIOS).
- **Yes:** keywords por tema con IA + fallback determinista (mismo patrón que la marca de SPEC 16).
- **No:** reescribir el prompt de n8n "Sistema RAG standar" — la ingestión del RAG no es la causa del menú genérico.
- **No:** tocar el catálogo de flujos — la detección IA de "Flujos de este cliente" ya filtra acciones por negocio.

## Risks

| Risk | Mitigation |
| --- | --- |
| La IA genera keywords pobres o fuera de contexto | Fallback determinista: tokens del título del tema; keywords nunca vacías |
| Menú muy largo con muchos temas RAG | Límite de ítems (8, numeración existente); temas priorizados por orden de sección |
| Quitar flujo de contenido cambia respuestas existentes | Es el comportamiento correcto (RAG responde contenido); replay de test de intención informativa en staging |
| Flujos detectados = 0 y RAG sin temas → menú sin ítems | Menú mínimo con marca + invitación (nunca menú vacío) |

## What is **not** in this spec

- Cambios en n8n o en la ingestión del RAG.
- Nuevo catálogo de flujos o wizards de flujos.
- Menú editable a mano por el operador (otra spec si aterriza).
