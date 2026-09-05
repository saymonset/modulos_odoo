# SPEC 10 — Visibilidad del estado de generación del menú (IA vs genérico vs obsoleto)

> **Status:** Aopproved
> **Depends on:** SPEC 09 (menú redactado según el rol del negocio)
> **Date:** 2026-09-05
> **Objective:** Hacer observable el estado del menú del bot — notificación y ficha que distingan si el menú se generó con IA o fallback, cuándo, y si quedó desactualizado — eliminando la confusión "menú genérico sin saber por qué".

## Por qué existe esta spec

Post-mortem real (2026-09-05): SPEC 09 desplegado y upgradeado en prod, pero el bot seguía mostrando el menú genérico. Dos causas de silencio:

1. El bot sirve el texto **guardado** en la intención MENU; el upgrade no regenera nada. El texto era del 2026-09-03 (pre-SPEC 09) y nada en la UI indicaba que estaba obsoleto.
2. Al regenerar, un fallo de IA solo va a `_logger.warning` (chatbot_config.py:564) y el botón notifica success **"Menú regenerado según el rol del negocio"** aun usando el fallback genérico (chatbot_config.py:990) — mensaje engañoso.

El operador no puede distinguir menú IA / genérico / obsoleto sin abrir la BD.

## Scope

**In:**

- `_generar_menu_desde_flujos` pasa a devolver `{'texto': str, 'modo': 'ia'|'fallback'}` — `'ia'` si la IA aportó etiquetas o encabezado, `'fallback'` si no. Ambos callers (sync + botón) actualizados al nuevo contrato.
- Campos nuevos en `chatbot.config`: `menu_generated_mode` (selection ia/fallback), `menu_generated_at` (datetime), escritos por botón y sync (misma ruta).
- Botón "Regenerar menú según rol": success si IA; **warning accionable** si fallback ("IA no disponible: menú genérico. Revisa la API key de OpenAI (openai.config) e reintenta").
- "Sincronizar todo desde RAG": escribe los campos y su resumen reporta el modo del menú.
- Ficha: indicador junto al botón (modo + fecha) y badge "posiblemente desactualizado" (compute `menu_stale`: `write_date > menu_generated_at`).
- Tests de ambos caminos + update de tests existentes al nuevo contrato. Bump `ai_chatbot_1_portal` 1.0.25 → 1.0.26.

**Out of scope:**

- Regeneración automática del menú tras deploy/upgrade (sigue explícita: botón o sync).
- Tracking por campo del `role` (se usa `write_date` de la config, no auditoría).
- Notificación al editar la config (el stale es badge pasivo).
- Historial/versionado del menú (solo última generación).
- Cambios en n8n, variante corta, plantillas por sector (heredados de SPEC 09).

## Data model

```python
# ai_chatbot_1_portal/models/chatbot_config.py
menu_generated_mode = fields.Selection(
    [('ia', 'IA (rol del negocio)'),
     ('fallback', 'Genérico (IA no disponible)')],
    string='Último menú generado con', copy=False)
menu_generated_at = fields.Datetime(string='Último menú generado el', copy=False)
menu_stale = fields.Boolean(
    string='Menú posiblemente desactualizado', compute='_compute_menu_stale')

def _compute_menu_stale(self):
    # True si la config fue editada después de la última generación
    self.menu_stale = bool(
        self.menu_generated_at and self.write_date > self.menu_generated_at)

# _generar_menu_desde_flujos — nuevo contrato de retorno:
# {'texto': str, 'modo': 'ia' | 'fallback'}   (texto '' si no hay flujos)
```

## Implementation plan

1. `_generar_menu_desde_flujos`: retorno dict con modo + actualización de los 2 callers y tests al nuevo contrato. Sistema funcional, sin campos nuevos aún.
2. Campos `menu_generated_mode/at` + compute `menu_stale`; botón y sync los escriben junto al `output_largo`.
3. Notificaciones por modo (botón: success/warning accionable; sync: resumen menciona el modo).
4. Vista: indicador modo+fecha + badge stale junto al botón; estado "sin generar" si los campos van vacíos.
5. Tests nuevos (modo por camino, stale True/False, notificaciones) + bump manifest 1.0.26 + upgrade `--test-enable` en `odoo-19-web-leads` (0 FAIL) + verificación manual en staging.

## Acceptance criteria

- [ ] Regenerar con IA activa → notificación success que menciona IA y `menu_generated_mode = 'ia'`.
- [ ] Regenerar con IA caída/sin key (mock de excepción) → notificación **warning** que menciona la API key, y `menu_generated_mode = 'fallback'`.
- [ ] El sync escribe `menu_generated_mode/at` y su resumen reporta el modo.
- [ ] La ficha muestra modo + fecha; badge "posiblemente desactualizado" al editar la config después de generar (test: editar → True; regenerar → False).
- [ ] Sin generación previa, el indicador muestra estado "sin generar" (no modo/fecha erróneos).
- [ ] El texto del menú (IA y fallback) es idéntico al de SPEC 09 — este spec no cambia el generador, solo lo hace observable.
- [ ] `--test-enable` con la cadena `ai_chatbot_1_portal,ai_chatbot_0_core` en staging: 0 FAIL / 0 ERROR.

## Decisions

- **Yes:** estado en `chatbot.config` (no en `chatbot.intencion`) — la intención MENU se borra/recrea en el sync RAG; la config es el ancla estable.
- **Yes:** fallback → warning accionable — el success actual notifica "según el rol" aun en fallback: engañoso.
- **Yes:** stale por `write_date > menu_generated_at` — barato, sin tracking nuevo; falso positivo aceptable (casi cualquier edición de la config puede afectar el menú).
- **Yes:** modo `'ia'` con contribución parcial (algunas labels IA) — el criterio es "la IA participó".
- **No:** regeneración automática post-deploy — sorpresiva y con costo IA en cada upgrade.
- **No:** tracking por campo / historial del menú — complejidad sin caso de uso.
- **No:** notificación al editar la config — ruido; el badge pasivo basta.

## Risks

| Risk | Mitigation |
| --- | --- |
| `write_date` y `menu_generated_at` en la misma transacción → stale espurio | Comparación estricta `>`; la generación escribe ambos → iguales → False |
| Cambio de contrato del retorno rompe llamadores | Método privado; 2 callers internos + tests, actualizados en el paso 1 |
| Falso positivo del stale (edición irrelevante) | Aceptado; el badge dice "posiblemente" |
| Modo 'ia' con menú parcialmente IA | Aceptado por simplicidad: "la IA participó", no "100% IA" |
