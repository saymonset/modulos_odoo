# SPEC 02 — Flow map dinámico para n8n (mapeo de flujos sin hardcodeo)

> **Status:** Implemented
> **Depends on:** SPEC 01 (parcial: el endpoint lee `chatbot.flujo` directo; SPEC 01
> luego re-fuentea el flow_map desde `chatbot.config`)
> **Date:** 2026-08-27
> **Objective:** Eliminar el mapeo hardcodeado en el nodo n8n
> `Separar_variables_en_json` para que flujos nuevos creados por el cliente en Odoo
> funcionen sin editar n8n. Cambio aditivo en Odoo, deploy a riesgo cero.

## Scope

**In:**

- `/ai_chatbot_1_portal/configuracion_agente` devuelve además `flow_map`
  (`{routing_key o name: nombre_flujo}`) desde `chatbot.flujo` activos.
- Helper `_get_flow_routing_map()` en `chatbot.flujo`.
- Nodo n8n `Separar_variables_en_json`: consume `flow_map` con **merge** sobre el
  mapeo actual (defaults preservados, Odoo gana en conflictos, fallback si no viene).
- Actualización del JSON exportado del workflow (respaldo/versionado).
- Tests: TransactionCase del helper + HttpCase del endpoint.

**Out of scope:**

- Botones WhatsApp dinámicos (`Construir_botones_WhatsApp`) → SPEC 01.
- Heurísticas de texto del nodo (CITA_DIRECTA/RESULTADOS, isMenu) → SPEC 01.
- Modelos `chatbot.config`/`chatbot.intencion` → SPEC 01.
- Mover tokens del JSON de n8n a credenciales.

## Implementation plan

1. `models/chatbot_flujo.py`: `_get_flow_routing_map()` → dict de activos
   (mismo dominio que `build_agent_system_prompt`, chatbot_utils.py:688).
2. Controller `configuracion_agente` (:418-424): `data['flow_map'] = ...`.
3. `tests/test_flow_routing_map.py` (patrón OCA del repo).
4. JSON exportado n8n: script Python reemplaza solo el bloque `mapeoFlow`
   del jsCode (dump `indent=2, ensure_ascii=False`); resto del nodo intacto.

## Acceptance criteria

- [ ] `flow_map` con routing_key→name, name→name si sin routing_key, sin inactivos.
- [ ] Endpoint retrocompatible (system_prompt/fallback_message intactos; 401 igual).
- [ ] n8n: sin `flow_map` usa defaults; con flow_map enruta flujos nuevos sin editar n8n.
- [ ] `--test-enable` pasa en `ai_chatbot_1_portal`.

## Decisions

- **Yes:** merge (defaults + dyn) en n8n, no replace — claves actuales siguen
  funcionando aunque Odoo no tenga el registro.
- **Yes:** cambio aditivo en endpoint existente, no endpoint nuevo.
- **No:** tocar botones/heurísticas en esta ronda.

## Risks

| Risk | Mitigation |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| JSON exportado diverge del workflow real en n8n UI                    | Se aplica en UI; JSON queda como respaldo |
| flow_map vacío (sin flujos activos)                                   | n8n conserva DEFAULT_FLOW_MAP |
| Agente emite routing_key en flow_name                                 | Prompt ya entrega flow_name exactos; merge cubre fallback |

## Deploy

1. Odoo (additive) → 2. tests staging → 3. update del nodo en n8n UI (sin prisa).