# SPEC 69 — Pausar/levantar servicios secundarios bajo demanda

> **Estado:** Approved
> **Depende de:** — (complementa la SPEC 68: reducción de carga del host)
> **Fecha:** 2026-09-23
> **Objetivo:** Un script `10_pausar_levantar_secundarios.sh` en el skeleton prod que pare y levante bajo demanda Postiz+Temporal+Elasticsearch+pgAdmin (y el stack leads con un flag), con pausa duradera y sin poder tocar nunca el camino del chatbot.

## Por qué existe esta spec

El 22-sep el VPS de 8 GB llegó a load average 42: Temporal consumía 77–161 % de CPU y Elasticsearch ~530 MB de RAM para un Postiz que ni siquiera está corriendo (`state=created`). El host se reinició y `restart: unless-stopped` hizo resucitar todo solo. La causa raíz del incidente (SPEC 68) incluye sobrecarga; esta spec da el utilitario para bajarla sin recrear stacks.

## Scope

**In:**

1. Script `10_pausar_levantar_secundarios.sh` en `/home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/` con subcomandos `parar | prender | estado`.
2. Grupos: `postiz` (postiz, temporal, temporal-elasticsearch, temporal-ui), `pgadmin` (pgadmin-container), `todos`; y `--inclui-leads` (odoo-19-web-leads, odoo-db19-leads).
3. Pausa duradera: `docker update --restart=no` antes de `docker stop`; `prender` restaura `unless-stopped` y arranca en orden de dependencias.
4. Lista `FORBIDDEN` dura (chatwoot-app, chatwoot-sidekiq, chatwoot-db, n8n-container, odoo-19-web, odoo-db19-n8n, odoo_redis): el script aborta si alguno aparece en el objetivo.
5. Salida estilo repo (`print_message/print_error/print_header`, colores) y medición de RAM liberada.

**Out of scope (para futuras specs):**

- `mem_limit`/`cpus` en los composes y migración de servicios a otra máquina.
- Queue mode de n8n, PG por servicio.
- Cron que pause/levante automáticamente por horario.

## Modelo de datos

Sin estructuras nuevas. Solo nombres de contenedor agrupados en variables del script: `POSTIZ_CONTAINERS`, `PGADMIN_CONTAINERS`, `LEADS_CONTAINERS`, `FORBIDDEN`.

## Implementation plan

1. Crear `10_pausar_levantar_secundarios.sh` y `chmod 755`.
2. `bash -n` para validar sintaxis.
3. Ejecutar `estado` (solo lectura) y confirmar que reporta los 7 contenedores + restart policy.
4. Con usuario al lado: `parar todos` → verificar en `free -h`/`uptime` la RAM liberada.
5. `prender todos` → verificar `docker ps` con los 4 de Postiz arriba y abrir la UI de Postiz.
6. Commit del script en `main` del skeleton prod + push.

## Acceptance criteria

- [ ] `bash -n` pasa sin errores.
- [ ] `estado` muestra ESTADO y RESTART de los 7 contenedores y el `free -h` actual.
- [ ] Tras `parar todos`, `docker inspect` reporta `Status=exited` y `RestartPolicy=no` para los 5 servicios.
- [ ] Tras un `prender todos`, Postiz responde en su URL y Temporal/Elasticsearch quedan `healthy`/corriendo.
- [ ] `parar todos --inclui-leads` también pausa el stack leads; sin el flag, no lo toca.
- [ ] El script aborta (exit ≠ 0) si se le pide parar un contenedor de `FORBIDDEN`.
- [ ] Script commiteado en `main` del skeleton prod.

## Decisiones

- **Sí:** `docker stop`/`docker start` por nombre + `docker update --restart` — la pausa sobrevive reboots sin depender del proyecto compose (que convive con un archivo combinado y varios `-f`).
- **No:** `profiles:` en compose — exige recrear contenedores (ventana de riesgo mayor para un utilitario).
- **No:** parar el stack leads por default — se usa en horario de trabajo; queda tras `--inclui-leads`.
- **Sí:** orden explícito de arranque (ES → Temporal → postiz → UI; BD leads antes que web leads).

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Un `docker compose up -d` general recrea y revive lo pausado | El script lo advierte en la salida de `prender`; documentación en el header |
| Pérdida de datos de Postiz/Temporal | No aplica: todo es bind-mount en `./v19/...` y la BD de Postiz vive en `odoo-db19-n8n` (intocable) |
| Alguien agrega un contenedor del bot al objetivo | Lista `FORBIDDEN` aborta el script antes de tocar nada |

## What is **not** in this spec

- Límites de recursos en compose, migración de servicios, automatización por cron, queue mode de n8n.

Cada uno de esos, si se aprueba, va en su propia spec.
