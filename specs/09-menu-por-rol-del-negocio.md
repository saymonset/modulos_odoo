# SPEC 09 — Menú del bot redactado según el rol del negocio

> **Status:** Implemented
> **Depends on:** SPEC 01 (config/intenciones y menú dinámico), SPEC 03 (única fuente de configuración / vista ficha)
> **Date:** 2026-09-05
> **Objective:** Que el menú que el bot muestra por WhatsApp se redacte en el lenguaje del negocio (IA desde el rol: etiquetas por flujo + encabezado con marca), dejando de ser el menú genérico "Precios y cotizaciones / Servicios del negocio / ...", con la misma estructura una-opción-por-flujo para no romper el ruteo de números en n8n.

## Por qué existe esta spec

Transcript real (2026-09-04, bot de INMOBILIARIA KARLA CAMPOVERDE C.A): ante "menu" el bot muestra el menú genérico con las 4 opciones enlatadas idénticas para cualquier vertical. El cliente no se siente identificado con el negocio. La causa: `_generar_menu_desde_flujos` (chatbot_config.py:521) etiqueta los flujos con `_MENU_LABELS` hardcodeadas (línea 512) y un encabezado fijo — el `role` de la config solo llega al system prompt para respuestas libres del LLM, nunca al menú enlatado que se sirve en `RESPUESTAS POR INTENCIÓN`.

Requisito multicliente: el mismo mecanismo sirve a cualquier vertical (inmobiliaria, impresión y gran formato, ingeniería civil, laboratorio clínico, hospital, ente gubernamental) porque las etiquetas se derivan del rol de cada `chatbot.config` (una instancia/VPS por cliente).

## Scope

**In:**

- Nueva generación de etiquetas del menú por IA (`gpt.service`) desde: `role` + flujos detectados/marcados (name, descripcion_intencion, etiqueta actual) + temas del bloque de conocimiento. Una etiqueta por flujo, mismo orden — la IA solo redacta, nunca estructura.
- Encabezado del menú generado por la misma llamada IA (puede saludar con marca/negocio); pie ("Responde con el número...") se mantiene determinista universal.
- Ensamblado determinista en Odoo: numeración 1️⃣..8️⃣ + orden de flujos (como hoy) — la IA no controla cantidad/posición.
- Fallback determinista: sin IA (sin API key, excepción) → etiquetas actuales de `_MENU_LABELS` (menú idéntico al de hoy). Cero regresión.
- Botón "Regenerar menú según rol" en la ficha `chatbot.config` (usa `flujo_ids` marcados; mismo generador que el sync).
- "Sincronizar todo desde RAG" sigue regenerando el menú (comportamiento pisar-siempre se mantiene).
- Restricciones de etiqueta: ≤ 40 caracteres, sin números ni emojis (numeración la pone Odoo), una línea.
- Tests: generador con gpt mockeado (etiquetas por rol: inmobiliaria ≠ genérica), fallback determinista, botón, sync; update de `test_09`.
- Bump `__manifest__.py` 1.0.24 → 1.0.25 (`ai_chatbot_1_portal`) + bump `ai_chatbot_0_core` si se modifica `gpt_service.py`.

**Out of scope (specs futuros):**

- Fallback ("Disculpa, no entendí...") y textos de CANCELAR/SALIR — universales (decisión).
- Variante corta del menú (`output_corto` / Instagram).
- Cambios en n8n (el menú sigue llegando vía system_prompt; contrato intacto).
- Menú libre/reordenado por IA (rompe ruteo por número).
- Preservar edición manual del menú ante sync (pisar siempre).
- Plantillas por sector.

## Data model

Sin modelos ni campos nuevos. Cambios de comportamiento:

```python
# ai_chatbot_0_core/services/gpt_service.py — método nuevo
# (patrón detectar_flujos_por_prompt, línea 214)
def generar_menu_por_rol(self, role_text, flujos_info):
    """Genera encabezado y etiquetas del menú desde el rol del negocio.

    :param role_text: chatbot.config.role (TÚ ERES / objetivo)
    :param flujos_info: [{'name', 'descripcion_intencion', 'label_actual'}]
    :return: {'header': str, 'labels': {flow_name: label}} — dict vacío si falla
    """

# ai_chatbot_1_portal/models/chatbot_config.py — cambios
_generar_menu_desde_flujos(flujos)
# Ahora: 1) pedir labels por IA (role+temas)
#         2) fallback a _MENU_LABELS / descripcion_intencion
#         3) ensamblar numeración+orden/pie como hoy

action_regenerar_menu()   # botón: flujos = self.flujo_ids; misma ruta
```

## Implementation plan

1. `gpt_service.py`: `generar_menu_por_rol` — prompt con reglas (una etiqueta por flujo, ≤40 chars, sin números/emojis, lenguaje del negocio según role, header de saludo con marca), parseo JSON tolerante (regex de respaldo si JSON incompleto). Funcional por sí solo. Tests unitarios del método (patrón `detectar_flujos_por_prompt`).
2. `chatbot_config.py::_generar_menu_desde_flujos`: llamar al gpt service (try/except + `_logger.warning`, patrón `_detectar_flujos_desde_rag:748-768`); fallback determinista a `_MENU_LABELS`/`descripcion_intencion` ante fallo; ensamblado numeración/orden/pie intacto. Manual: config demo con role inmobiliaria + IA mockeada → menú con etiquetas del rubro.
3. `chatbot_config.py::action_regenerar_menu` + botón en `chatbot_config_views.xml` (junto a los otros botones de la ficha): si no hay `flujo_ids` activos o no existe intención MENU → notificación warning; si ok → escribe `output_largo` y notifica.
4. Tests (`ai_chatbot_1_portal/tests/test_menu_por_rol.py` nuevo + update `test_recargar_desde_rag.py::test_09`): (a) mock gpt → etiquetas del rol en el menú y una línea por flujo en el mismo orden; (b) IA caída/sin configurar → menú idéntico al actual (regresión); (c) botón regenera con `flujo_ids`; (d) sin MENU/flujo_ids → warning; (e) test_09 existente pasa con el fallback determinista (tests sin mock de IA). Ciego: `test_09` se blinda con mock forzando el camino determinista para evitar que un API key en staging rompa el assert.
5. Bump manifests (`ai_chatbot_1_portal` 1.0.24→1.0.25; `ai_chatbot_0_core` si cambia) + upgrade `-u ai_chatbot_1_portal,ai_chatbot_0_core --test-enable` en `odoo-19-web-leads` (0 FAIL) + replay manual WhatsApp: "menu" en el bot de Karla en staging muestra menú inmobiliario con etiquetas del rubro.

## Acceptance criteria

- [ ] Con la config de Karla (rol inmobiliaria) e IA activa, "menu" por WhatsApp muestra etiquetas del rubro inmobiliario (p. ej. "Inmuebles y precios" en vez de "Precios y cotizaciones") y encabezado que referencia el negocio/marca.
- [ ] El menú tiene una opción por flujo, en el mismo orden que hoy; la numeración 1️⃣/2️⃣/... la agrega Odoo (la IA no puede alterar cantidad/posición).
- [ ] Los números del menú siguen rutendo igual en n8n (replay: "1", "3" disparan lo mismo que antes del cambio).
- [ ] Sin IA (sin API key o caída), el menú es idéntico al actual (etiquetas `_MENU_LABELS`) — sin regresión.
- [ ] El botón "Regenerar menú según rol" regenera el menú con los flujos marcados, sin requerir re-sincronizar RAG; notifica el resultado.
- [ ] "Sincronizar todo desde RAG" regenera el menú con etiquetas por rol (mismo generador que el botón).
- [ ] Cada etiqueta: ≤ 40 caracteres, una línea, sin números ni emojis.
- [ ] `--test-enable` pasa con la cadena `ai_chatbot_1_portal,ai_chatbot_0_core` en staging (0 FAIL / 0 ERROR).

## Decisions

- **Yes:** IA desde el rol (`gpt.service`) — un mecanismo para cualquier vertical sin catálogo de plantillas que mantener.
- **Yes:** una opción por flujo, mismo orden, numeración determinista — la IA redacta, no estructura; el ruteo de números de n8n queda intacto.
- **Yes:** pisar siempre en el sync — mismo comportamiento que hoy; simple y predecible.
- **Yes:** botón "Regenerar menú según rol" aparte — refresca el menú sin re-sincronizar RAG (útil tras editar el rol).
- **Yes:** fallback determinista a las etiquetas actuales — cero regresión si la IA no está; los tests sin mock ejercitan ese camino.
- **No:** personalizar fallback/CANCELAR/SALIR — textos de cortesía universales.
- **No:** menú libre/reordenado por IA — rompe heurísticas de número/posición de n8n.
- **No:** plantillas por sector — rígido, catálogo a mantener, vertical nueva vuelve a lo genérico.
- **No:** preservar edición manual del menú — campo extra y lógica de detección; el flujo real es sync → retoques → (si re-sync, se regenera).

## Risks

| Risk | Mitigation |
| --- | --- |
| La IA devuelve etiquetas fuera de formato (largas, con emojis/números) | Prompt con reglas explícitas + saneamiento en Odoo (strip, recorte a 40 chars, quitar emojis/números) + fallback por flujo a `_MENU_LABELS` si la etiqueta viene vacía |
| IA no disponible en la instancia del cliente | Fallback determinista: menú idéntico al actual |
| Respuesta IA mal parseada (JSON inválido) | Parseo tolerante (regex/JSON parcial) → tratar como fallo → fallback; `_logger.warning` |
| Costo/latencia extra en el sync | Una sola llamada IA por sync (una por botón); payload chico (labels cortas) |
| test_09 existente depende de la etiqueta genérica | En tests sin mock, el gpt service no está configurado → camino determinista → label genérica se mantiene. Ciego el test con mock forzando camino determinista para evitar que un API key en staging rompa el assert |

## What is **not** in this spec

- Personalizar fallback y textos de cortesía, variante corta del menú, cambios en n8n, menú libre por IA, preservación de edición manual, plantillas por sector. Cada uno, si llega, va en su propio spec.
