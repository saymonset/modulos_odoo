# SPEC 70 — Composes resilientes al reboot (restart policies + arranque ordenado)

> **Estado:** Approved
> **Depende de:** — (complementa SPEC 68/69: misma clase de incidente del 24-sep)
> **Fecha:** 2026-09-24
> **Objetivo:** Que tras un reboot del host todos los servicios del camino crítico arranquen solos y en orden, eliminando el crash-loop de n8n (224 % de CPU, load 35) observado el 24-sep.

## Por qué existe esta spec

El 24-sep el host se reinició y `odoo-db19-n8n`, `odoo-19-web` y `odoo-db19-leads` quedaron **muertos** porque sus servicios no declaran `restart:` (política efectiva `no`). `n8n-container` (`unless-stopped`) sobrevivió pero su `depends_on: [db, redis]` es sintaxis corta sin `condition`, así que entró en crash-loop `getaddrinfo ENOTFOUND db` cada pocos segundos consumiendo ~2 de 3 cores, con redis/pgadmin/backup reintentando contra BDs inexistentes y el disco al 82 % de utilización. El `restart=no` de Postiz/Temporal es intencional (pausa duradera SPEC 69) y no se toca.

## Scope

**In:**

1. `docker-compose.odoo.yml` (prod): `restart: unless-stopped` en `db` y `web`.
2. `docker-compose.n8n.yml` (prod): `depends_on` a forma larga con `condition: service_healthy` para `db` y `redis` (ambos ya tienen healthcheck), y healthcheck de n8n (`GET /healthz`, `start_period: 30s`) para acotar el crash-loop y hacerlo visible.
3. `docker-compose.leads.yml` (lead): `restart: unless-stopped` en `db-leads` (`web-leads` ya la tiene).
4. Alineación inmediata sin recrear: `docker update --restart=unless-stopped odoo-db19-n8n odoo-19-web odoo-db19-leads`.
5. Recreación del stack prod en horario valle para materializar healthcheck/depends_on: `docker compose -f docker-compose.yaml up -d` (en lead/ solo `up -d` de leads).
6. Verificación con simulacro real: `systemctl restart docker` en ventana de valle.
7. Commits: skeleton prod → rama `main`; skeleton lead → rama `lead`; ambos con push.

**Out of scope (para futuras specs):**

- Cambiar políticas de Postiz/Temporal/Elasticsearch/pgadmin (pausa gestionada por `10_pausar_levantar_secundarios.sh`, SPEC 69).
- `mem_limit`/`cpus`, queue mode de n8n, Postgres dedicado por servicio, rotación de logs docker.
- Unificar redis `always` → `unless-stopped` (funciona bien, no es causa del incidente).
- systemd `After=docker.service` ni healthchecks externos de monitoreo.

## Modelo de datos

No introduce estructuras nuevas. Cambian 3 archivos compose (fragmentos):

```yaml
# docker-compose.odoo.yml — en db: y web:
restart: unless-stopped

# docker-compose.n8n.yml — n8n:
depends_on:
  db: { condition: service_healthy }
  redis: { condition: service_healthy }
healthcheck:
  test: ["CMD", "wget", "--spider", "-q", "http://127.0.0.1:5678/healthz"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s

# docker-compose.leads.yml — db-leads:
restart: unless-stopped
```

## Implementation plan

1. Backup de los 3 composes (`.bak-20260924`) y rama/commit inicial de los backups según convención de cada skeleton.
2. Aplicar los 3 edits de YAML. Validar: `docker compose -f docker-compose.yaml config` (prod) y `-f docker-compose.leads.yml config` (lead) sin errores ni warnings de fusión.
3. `docker update --restart=unless-stopped` sobre los 3 contenedores vivos (fix de política sin recrear → blindaje inmediato ante reboot aunque la recreación se tarde).
4. Recrear en valle: en prod `docker compose -f docker-compose.yaml up -d`; en lead `docker compose -f docker-compose.yaml up -d`. Confirmar `docker ps` con db/web/n8n/leads `healthy`/`Up` y cero `ENOTFOUND` nuevos en `docker logs n8n-container`.
5. Simulacro de reboot: `systemctl restart docker` (ventana 1–2 min avisada) → verificar que TODOS los de política propia vuelven solos, Postiz/pgadmin pausados siguen abajo, y n8n arranca a la primera (sin más de 1–2 reinicios).
6. E2E: mensaje de prueba al inbox 3 (WhatsApp IntegraIA) → respuesta del bot + ejecución registrada en n8n; `uptime` < 5 tras 10 min.
7. Commit + push: prod skeleton rama `main`, lead skeleton rama `lead`.

## Acceptance criteria

- [ ] `docker inspect -f '{{.HostConfig.RestartPolicy.Name}}'` reporta `unless-stopped` en odoo-db19-n8n, odoo-19-web, odoo-db19-leads y n8n-container.
- [ ] `docker compose config` valida los dos proyectos sin errores.
- [ ] Tras `systemctl restart docker`: los 10 servicios del camino crítico quedan `Up` sin intervención manual y postiz/temporal/temporal-ui/temporal-elasticsearch siguen `Exited`.
- [ ] `docker logs n8n-container` desde el simulacro: cero `ENOTFOUND`, ≤2 inicios de proceso.
- [ ] E2E WhatsApp (inbox 3): el bot responde y hay ejecución nueva en n8n.
- [ ] `load average` < 5 a los 10 min del simulacro.
- [ ] Commits hechos: `main` en prod skeleton, `lead` en lead skeleton, ambos pusheados.

## Decisiones

- **Sí:** fixes en los hijos (`docker-compose.odoo.yml`, `.n8n.yml`), no como override en el combinado — los hijos son la fuente de verdad que usan los scripts de despliegue vía `extends`.
- **Sí:** `unless-stopped` uniforme en db/web/db-leads — sobrevive reboots y respeta paradas manuales (`docker stop` / script SPEC 69); `always` pelearía con mantenimientos.
- **Sí:** incluir el stack lead — mismo bug (db sin política, web con política = web huérfana tras reboot).
- **Sí:** `condition: service_healthy` + healthcheck de n8n — el orden solo funciona si las dependencias tienen puerta de salud; db/redis ya la tenían, a n8n le faltaba la propia.
- **No:** `depends_on` en el chatwoot/postiz compose — ya están correctos (forma larga con conditions).
- **No:** perfilar CPU/RAM ahora — va con la spec de migración de servicios si nunca llega.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| `0_install_docker_and_setup.sh` ejecuta `-f docker-compose.n8n.yml down` suelto y `depends_on` referenciaría servicios no definidos ahí | el script ya usa `|| true`; el arranque real es por el combinado. Verificado: ningún script de arranque usa n8n.yml suelto |
| `systemctl restart docker` cae todo el stack 1–2 min | ventana de valle avisada; el paso 3 deja la política arreglada antes, para que un reboot imprevisto entre pasos ya no duerma el servicio |
| `docker compose up -d` recrea db y corta conexiones activas | paso 4 en valle; `stop_grace_period: 60s` ya declarados |
| Drift runtime-vs-archivo: SPEC 69 cambia políticas con `docker update` sin tocar YAML | aceptado: el YAML describe el estado deseado del camino crítico; los pausados quedan fuera del scope de políticas |

## What is **not** in this spec

- Límites de CPU/RAM por contenedor, queue mode de n8n, BDs dedicadas.
- Alertas externas por caída de servicio (especulación de la SPEC 68, aún sin spec propia).
- Cambios a las políticas de los servicios pausables (Postiz, Temporal, ES, pgAdmin).
- Automatización tipo cron de verificación post-reboot.
