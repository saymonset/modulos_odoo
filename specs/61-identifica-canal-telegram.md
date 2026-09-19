# SPEC 61 — `Indentifica_canal` tolera Telegram (y canales futuros) sin crash

> **Estado:** Approved
> **Depende de:** SPEC 43 (workspace n8n_json en lead)
> **Fecha:** 2026-09-19
> **Objetivo:** Que el switch `Indentifica_canal` del workflow chatwoot enrute al subflow cualquier canal no vacío (hoy Telegram, y futuros) sin lanzar el error "Wrong type … expecting a number", reemplazando la regla rota `error_no_existe_channel`.

## Por qué existe esta spec

La regla final del switch `Indentifica_canal` (`error_no_existe_channel`) está malformada en el export: `leftValue` es un objeto vacío `{}` con operador `number/exists`. Cuando llega un `channel` que no matchea las reglas 0-3 (WhatsApp/Instagram/facebook/FacebookPage), n8n evalúa esa regla y lanza `Wrong type: '[object Object]' is an object but was expecting a number [condition 0, item 0]`. El input de prueba con `channel: "Channel::Telegram"` dispara el crash. El mismo bug existe en el workflow ycloud, pero queda fuera de alcance. El subflow `chatbot-simple_1_subflow` y el envío de respuesta vía Chatwoot API son agnósticos de canal, así que Telegram puede fluir por el mismo camino.

## Scope

**In:**

1. **Regla catch-all** en el nodo `Indentifica_canal` (`/home/odoo/lead/odoo19-skeleton/n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json`): la regla 4 pasa de `leftValue: {}` + `number/exists` a `leftValue: "={{ $json.channel }}"` + `string/isNotEmpty`, con `outputKey: "otro"`. Canal no vacío no listado (Telegram y futuros) → subflow.
2. **Conexión nueva**: `connections.Indentifica_canal.main[4]` → `Call 'chatbot-simple_1_subflow'` main[0].
3. **Aplicación en vivo**: el usuario importa el JSON corregido en el n8n vivo, prueba con el input Telegram y re-exporta.

**Out of scope (para futuras specs):**

- Workflow ycloud (`ycloud_create_lead_0_con_menu_whatsapp.json`) — tiene la regla rota idéntica.
- Promoción a prod (`/home/odoo/prod/odoo19-skeleton/n8n_json/`): solo tras E2E verde (SPEC 43).
- `Seteamos_variables` (hardcode `channel`/`platform` a `Channel::Whatsapp`).
- Otros nodos del workflow que asuman WhatsApp.

## Modelo de datos

Sin estructuras nuevas. Cambio puntual en el JSON del nodo y su conexión:

```jsonc
// Regla 4 (última) del switch Indentifica_canal — ANTES (rota, crash)
{ "leftValue": {}, "rightValue": "", "operator": { "type": "number", "operation": "exists", "singleValue": true }, "outputKey": "error_no_existe_channel" }

// DESPUÉS (catch-all)
{ "leftValue": "={{ $json.channel }}", "rightValue": "", "operator": { "type": "string", "operation": "isNotEmpty" }, "outputKey": "otro" }

// Conexión nueva en connections.Indentifica_canal.main[4] -> Call 'chatbot-simple_1_subflow'.main[0]
```

Las reglas 0-3 y sus outputs (Whatsapp, Instagram, facebook) quedan intactas.

## Plan de implementación

1. Editar `n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json`: regla 4 de `Indentifica_canal` → catch-all `isNotEmpty` con `outputKey: "otro"` + agregar `connections.Indentifica_canal.main[4]` → `Call 'chatbot-simple_1_subflow'`.
2. Validar: `python3 -m json.tool` y diff enfocado (solo el nodo y la conexión).
3. Usuario: importar el JSON en el n8n vivo (UI Import), reemplazando el workflow.
4. Usuario: probar ejecutando `Indentifica_canal` con el input Telegram (`channel: "Channel::Telegram"`) → enruta al subflow sin error; regresión con `Channel::Whatsapp` → salida 0.
5. Usuario: re-exportar el workflow a `n8n_json/chatwoot/` (actualiza `versionId`) + commit en la rama `lead` de odoo19-skeleton.

## Criterios de aceptación

- [ ] Importar el JSON corregido en el n8n vivo carga sin error de schema.
- [ ] Ejecutar `Indentifica_canal` con `channel: "Channel::Telegram"` enruta a `Call 'chatbot-simple_1_subflow'` sin lanzar "Wrong type … expecting a number".
- [ ] Regresión: `Channel::Whatsapp`, `Channel::Instagram`, `Channel::facebook` y `Channel::FacebookPage` enrutan igual que antes.
- [ ] Con `channel` vacío o ausente, el item se descarta en silencio (sin crash, sin salida).
- [ ] Las reglas 0-3 y sus nombres de salida quedan intactos.
- [ ] `ycloud_create_lead_0_con_menu_whatsapp.json` no se modifica.
- [ ] Export re-hecho en `n8n_json/chatwoot/chatbot_create_lead_0_con_menu_whatsapp.json` + commit en la rama `lead`.

## Decisiones tomadas y descartadas

- **Tomado:** catch-all `channel isNotEmpty → subflow` reemplaza la regla rota — **descartado** regla explícita solo Telegram (canales futuros como SMS seguirían muriendo en silencio).
- **Tomado:** reutilizar la regla 4 existente cambiando `leftValue`/operador/`outputKey` — **descartado** borrarla y crear una nueva (misma semántica de outputs del switch).
- **Tomado:** solo workflow chatwoot — **descartado** tocar ycloud (mismo bug; queda en otra spec).
- **Tomado:** edición del JSON + import del usuario en el n8n vivo — patrón SPEC 43/48 (el export se re-hace tras tocar la nube).
- **Descartado:** borrar la regla rota sin reemplazo — con Fallback Output = None, Telegram se descartaría en silencio (sin responder).
- **Descartado:** `fallbackOutput: extra` del switch — todas las rutas van al mismo subflow; no aporta.

## Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Import en el n8n vivo pisa cambios no exportados | Re-export inmediato a lead tras tocar la nube (patrón SPEC 48); backup del JSON actual |
| `channel` ausente (webhook malformado) → `isNotEmpty` false → descarte | Comportamiento deseado = guardián original; sin crash |
| Canal desconocido futuro (ej. SMS) enruta al subflow con `platform='otro'` | Subflow y envío Chatwoot son agnósticos de canal; verificar en E2E si llega |

## What is **not** in this spec

- Workflow ycloud (misma regla rota; propia spec).
- Promoción a prod (solo tras E2E verde).
- `Seteamos_variables` y demás nodos que asumen WhatsApp.

Cada uno de esos, si llega, va en su propia spec.