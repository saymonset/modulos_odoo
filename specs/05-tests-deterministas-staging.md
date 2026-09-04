# SPEC 05 — Tests deterministas: eliminar los 3 fallos preexistentes en staging

> **Status:** Implemented
> **Depends on:** SPEC 04 (cierra su criterio 8 pendiente), SPEC 03 (params legacy de marca)
> **Date:** 2026-09-04
> **Objective:** Hacer deterministas los 3 tests preexistentes que fallan en staging por depender del estado del DB, dejando la cadena completa `--test-enable` en verde.

## Por qué existe esta spec

Corriendo la cadena `-u ai_chatbot_1_portal,ai_chatbot_0_core --test-enable` en staging (`odoo-19-web-leads`, DB `dbodoo19`) fallan 3 tests por dependencia del estado del DB, no por bugs de código:

1. `test_openai_service.test_03_get_openai_client_success` — Odoo 19 usa `_order = 'id'` ASC por default (odoo/orm/models.py:434); `search([('active','=',True)], limit=1)` en `_get_openai_client` devuelve la config **más antigua**: la preexistente id=1 del DB (clave 'GOCSPX...'), no la creada en `setUpClass`. Además el paquete `openai` no está instalado en el contenedor, así que `test_01` pasa de casualidad (la `ValidationError` viene de "paquete no instalado", no de "sin api key"; `assertRaises` solo verifica el tipo). Mismo bug latente.
2. `test_brand_settings.test_03_helper_sin_config_y_sin_params_devuelve_defaults` — el DB tiene el param legacy `ai_chatbot_1_portal.brand_name='IntegraIA'`; el test desactiva configs pero no neutraliza los params.
3. `test_recargar_desde_rag.test_10_diagnostico_y_guardrail_flujos` — el assert busca `'solo se activan cuando el usuario CONFIRMA'` en minúscula; `prompt_renderer.py:123` tiene `'SOLO se activan cuando el usuario CONFIRMA'` en mayúscula.

## Scope

**In:**

- `ai_chatbot_0_core/tests/test_openai_service.py`: en `setUpClass`, archivar (`active=False`) las `openai.config` preexistentes antes de crear la config del test (rollback tras la clase las restaura). Cura `test_03` y el caso latente de `test_01`.
- `ai_chatbot_1_portal/tests/test_brand_settings.py`: en `test_03`, neutralizar los 3 params legacy (`ai_chatbot_1_portal.brand_name`, `platform_promotion_enabled`, `platform_promotion_text`) antes de assertear los defaults (el rollback del test los restaura).
- `ai_chatbot_1_portal/tests/test_recargar_desde_rag.py`: corregir el assert de `test_10` al texto exacto `'SOLO se activan cuando el usuario CONFIRMA'`.
- Re-correr la cadena completa en staging exigiendo 0 fallos.
- Al quedar verde: marcar SPEC 04 como `Implemented` (criterio 8 cumplido) y SPEC 05 como `Implemented`.

**Out of scope (specs futuros / ops):**

- Cambios de runtime (orden explícito en el search de `_get_openai_client`, constraint de única config activa).
- Instalar el paquete `openai` en el contenedor.
- Limpiar/reemplazar la clave 'GOCSPX...' de la config id=1 del DB de staging.
- Tests nuevos de comportamiento de runtime.

## Data model

Esta feature no introduce estructuras de datos nuevas. Solo se modifican archivos de tests.

## Implementation plan

1. `test_openai_service.py` `setUpClass`: buscar todas las configs (`active_test=False`), `write({'active': False})`, luego crear la config del test. Funcional por sí solo.
2. `test_brand_settings.py` `test_03`: tras desactivar configs, buscar y borrar los 3 params legacy (`ir.config_parameter`) antes de los asserts.
3. `test_recargar_desde_rag.py` `test_10`: cambiar el assert a `'SOLO se activan cuando el usuario CONFIRMA'`.
4. Sincronizar ambos módulos al clon lead (rsync, patrón CI) y correr `-u ai_chatbot_1_portal,ai_chatbot_0_core --test-enable --stop-after-init` en `odoo-19-web-leads` → 0 FAIL/ERROR.
5. Actualizar estados: SPEC 04 → `Implemented`, SPEC 05 → `Implemented`.

## Acceptance criteria

- [ ] La cadena `-u ai_chatbot_1_portal,ai_chatbot_0_core --test-enable` en staging termina con 0 FAIL/0 ERROR.
- [ ] `test_03_get_openai_client_success` pasa (el mock se llama con `'sk-test-key-12345'`).
- [ ] `test_01_get_openai_client_no_api_key` pasa por la razón correcta (sin api key), independiente de si el paquete `openai` está instalado.
- [ ] `test_03_helper_sin_config_y_sin_params_devuelve_defaults` pasa con `brand == ''`.
- [ ] `test_10_diagnostico_y_guardrail_flujos` pasa con el assert exacto.
- [ ] Los 3 tests pasan aun con el DB de staging conteniendo la `openai.config` preexistente y los params de marca.
- [ ] El diff no toca `services/`, `models/` ni `controllers/` (solo `tests/`).

## Decisions

- **Yes:** solo tests, sin cambios de runtime — los flujos reales del chatbot no se tocan; riesgo cero de comportamiento.
- **Yes:** archivar configs preexistentes en `setUpClass` (no en cada test) — cubre `test_01` latente y `test_03`; mismo patrón que ya usa `test_brand_settings` con `chatbot.config`.
- **Yes:** assert exacto al texto del renderer — estricto: detecta cambios futuros del prompt.
- **Yes:** cadena verde en staging como criterio de cierre — con eso se cumple el criterio 8 de SPEC 04.
- **No:** bump de manifests — cambios solo de tests; no hay artefacto desplegable que versionar.
- **No:** instalar el paquete `openai` ni limpiar la clave 'GOCSPX...' del DB — decisiones de ops, no de esta spec.
- **No:** assert case-insensitive — laxo, no detectaría cambios de énfasis en el prompt.

## Risks

| Risk | Mitigation |
| --- | --- |
| DB sin configs preexistentes (dev) | El archivo en `setUpClass` es no-op; sin efecto |
| Crash a mitad de la clase de tests | El rollback de clase de `TransactionCase` restaura las configs archivadas |
| Alguien cambia el texto del guardrail en el renderer | El assert exacto de `test_10` fallará a propósito: es su función |

## What is **not** in this spec

- Cambios de runtime, instalación del paquete `openai`, limpieza de la clave del DB, tests nuevos de runtime. Cada uno, si llega, va en su propio spec u operación de ops.