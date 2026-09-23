# SPEC 68 — Resiliencia del bot Chatwoot→n8n en prod

> **Estado:** Approved
> **Depende de:** —
> **Fecha:** 2026-09-23
> **Objetivo:** Eliminar las tres causas de la falla del 22-sep en prod (DNS intermitente + timeout de 5 s de Chatwoot + cero alertas) con cambios de configuración reversibles y verificados.

## Por qué existe esta spec

Conversación 173 (pedrovillarreal, inbox Instagram 5): entre 19:51 y 20:26 UTC del 22-sep-2026, 5 mensajes del cliente nunca llegaron a n8n (cero ejecuciones registradas). Evidencia: ejecución 44995 de n8n falló con `EAI_AGAIN` (DNS del host caído), la 44999 con `timeout exceeded when trying to connect` (pool de Postgres agotado), y el VPS de 8 GB con ~12 contenedores registró load average pico de 42. Chatwoot 4.17 (`lib/webhooks/trigger.rb`) hace POST al agentbot con `WEBHOOK_TIMEOUT` de **5 s** y los errores de conexión **no se reintentan** → declaró "bot muerto", reabrió la conversación con la actividad *"Conversation was marked open by system due to an error with the agent bot."* y no hubo alerta a humanos. Se perdió un lead caliente. El arreglo de la carga del host (pausar Postiz/Temporal) vive en la SPEC 69.

## Scope

**In:**

1. `outgoing_url` del agentbot `botIntegraIA` (id 1, account 1) → `http://n8n:5678/webhook/chatwoot_integraia` (misma red `odoo_network_19`; elimina DNS público, nginx y Cloudflare del camino). Requiere `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true` en chatwoot-app/sidekiq (ver Implementation plan paso 2).
2. `WEBHOOK_TIMEOUT=15` como env en `chatwoot-app` y `chatwoot-sidekiq` (`docker-compose.chatwoot.yml`).
3. `dns: [1.1.1.1, 8.8.8.8]` en `n8n-container`, `chatwoot-app` y `chatwoot-sidekiq` (composes respectivos) → mata el `EAI_AGAIN` del resolver del host.
4. Prueba E2E con mensaje real al inbox 3 (WhatsApp IntegraIA) y commit de los composes en `main` del skeleton prod.

**Out of scope (para futuras specs):**

- ~~Alerta "Bot caído"~~ — Retirado en implementación: Chatwoot 4.17 ignora mensajes tipo activity en automatizaciones (`AutomationRuleListener#ignore_message_created_event?`), por lo que el disparador literal es imposible; el fallback propuesto (regla 30 min abierto sin respuesta → email a equipo) fue descartado por el usuario el 23-sep. Un mecanismo de alerta (p. ej. webhook de cuenta → n8n → email/Telegram) va en una spec futura.
- Cambiar el endpoint con el que n8n **responde** (el workflow `chatbot_create_lead_0_con_menu_whatsapp` sigue usando `https://chatwoot.integraia.lat/api/v1/...`) — toca el n8n vivo + promoción SPEC 43.
- n8n en queue mode, Postgres dedicado por servicio, mover Postiz/Temporal/Elasticsearch, más RAM.
- Rotación persistente de logs docker.
- `botUnisa` (sin inbox vinculado).

## Modelo de datos

No introduce estructuras nuevas. Cambia 2 cosas existentes:

- Registro `agent_bots` id 1 (`botIntegraIA`): `outgoing_url` → URL interna.
- Envs/dns en `docker-compose.chatwoot.yml` y `docker-compose.n8n.yml` (`WEBHOOK_TIMEOUT`, `SAFE_FETCH_ALLOW_PRIVATE_NETWORK`, `dns`).

## Implementation plan

1. Backup de los 2 composes (`.bak-20260923`) antes de tocar nada.
2. **Pre-test de viabilidad** (sin cambios): `curl http://n8n:5678/webhook/chatwoot_integraia` desde `chatwoot-app` (404 esperado = conectado) y prueba del `SafeFetch` de Chatwoot contra URL privada vía `bundle exec rails runner`. Resultado del 23-sep: SafeFetch bloquea por defecto (`UnsafeUrlError: no public ip`) pero el env `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true` (soportado en `/app/lib/safe_fetch.rb`) habilita el fetcher privado → se incluye en el paso 3.
3. Editar composes (timeout + safe-fetch + dns) y recrear `chatwoot-app`, `chatwoot-sidekiq`, `n8n` (ventana de 30–60 s, horario valle).
4. Actualizar `outgoing_url` de botIntegraIA (rails runner con validación de modelo; rollback: `https://n8n.integraia.lat/webhook/chatwoot_integraia`).
5. ~~Crear automatización "Bot caído"~~ — RETIRADO (ver Out of scope): imposible por diseño en Chatwoot 4.17; el fallback fue descartado por el usuario.
6. Verificación E2E: mensaje de prueba al inbox 3 → el bot responde, n8n registra ejecución, sin `Exception: Invalid webhook URL` en logs.
7. Commit de los composes en `main` del skeleton prod + push (bajo pedido explícito del usuario).

## Acceptance criteria

- [ ] `outgoing_url` de botIntegraIA es la URL interna y una prueba real hace que el bot responda con ejecución registrada en n8n.
- [ ] `WEBHOOK_TIMEOUT=15` y `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true` visibles en `docker inspect` de chatwoot-app y chatwoot-sidekiq.
- [ ] Los 3 servicios resuelven nombres internos y externos (`getent hosts chatwoot-postgres` y `getent hosts n8n.integraia.lat` OK).
- [ ] Cero `EAI_AGAIN` nuevos en logs de n8n tras 24 h.
- [ ] Composes commiteados en `main` de prod.
- ~~[ ] Una actividad "error with the agent bot" (simulada) dispara email a los agentes.~~ — Retirada junto con el paso 5.

## Decisiones

- **Sí:** endpoint interno — la causa del incidente es el salto público con reloj de 5 s.
- **Sí:** 15 s (no 20): 3× de margen sin saturar Sidekiq; Chatwoot desaconseja valores muy altos.
- **Sí:** paquete liviano elegido por el usuario; los cambios fuertes quedan fuera.
- **No:** `keep_pending_on_bot_failure` — ocultar la falla deja al cliente esperando; mejor alerta + humano.
- **No:** automatización "Bot caído" — Chatwoot 4.17 ignora mensajes activity (`ignore_message_created_event?`); el fallback (30 min abierto → email a equipo creado) fue descartado por el usuario el 23-sep. La alerta a humanos queda para una spec futura.
- **No (diferido):** cambio del endpoint de respuesta del workflow, queue mode, PG separado, mover Postiz/ES.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| SafeFetch de Chatwoot bloquea URLs privadas (protección SSRF) | Pre-test paso 2 con `rails runner` antes de recrear contenedores; fallback = quedarse solo con dns fijo + timeout 15 (sigue cubriendo la causa raíz y sigue siendo liviano) |
| Recrear chatwoot-sidekiq descarta jobs en cola | Detener con `stop_graceful` y ejecutar en valle |
| Recrear n8n interrumpe webhooks en vuelo | Ventana de valle + verificación E2E inmediata |

## What is **not** in this spec

- Endpoint interno de respuesta n8n→Chatwoot.
- Queue mode de n8n, separación de Postgres, migración de Postiz/Temporal/ES, logs persistentes.

Cada uno de esos, si se aprueba, va en su propia spec.
