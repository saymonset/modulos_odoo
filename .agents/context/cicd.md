# CI/CD Context — GitHub Actions

## Workflow principal

- **Archivo**: `.github/workflows/deploy-prod.yml`
- **Trigger**: `push` a `main`
- **Runner**: self-hosted en el servidor (label `odoo-prod`)

## Pipeline serializado (`concurrency: deploy-prod`)

1. `changes` — detecta módulos `extra/19.0` tocados y resuelve cadena de deps custom en orden topológico
2. `lint` — compileall, claves de manifest, anti-patrón `attrs=` en XML
3. `test` — rsync al clon **lead**, restart `odoo-19-web-leads`, `-u <cadena> --test-enable` contra staging `dbodoo19`; log como artifact
4. `deploy` — `git fetch + merge --ff-only` en clon **prod**, `-u <cadena>` sin tests en `odoo-19-web`, restart + health check `:18069`

Push sin cambios en `extra/19.0` → lint/test se skipean y deploy solo hace `git pull`.

## Runner self-hosted

- Servicio systemd: `actions.runner.saymonset-modulos_odoo.vmi2870902.service`
- Ubicación: `/home/odoo/actions-runner`
- Verificar estado: `systemctl status actions.runner.saymonset-modulos_odoo.vmi2870902.service`

## Auth SSH (deploy)

El clon **prod** tiene `core.sshCommand`:
```
git -C /home/odoo/prod/modulos_odoo config core.sshCommand "ssh -o BatchMode=yes -o IdentityAgent=/home/odoo/.ssh/agent.sock"
```
Agente persistente: `ssh-agent -a /home/odoo/.ssh/agent.sock -D` (detached, sobrevive cierre de sesión pero no reinicio). Tras reinicio: `/home/odoo/.local/bin/ssh-agent-recovery.sh`.

Nota: deploy key `~/.ssh/id_ed25519_deploy` ya no se usa (GitHub la rechaza).

## Fallback manual si runner cae

```bash
git pull  # en prod
docker exec odoo-19-web python3 /opt/odoo/odoo-core/odoo-bin -d dbodoo19 -u <cadena> --stop-after-init
docker restart odoo-19-web
curl -s -o /dev/null -w "%{http_code}" http://localhost:18069  # health check
```

## OJO

El deploy exige clon prod limpio (`merge --ff-only`). Cambios locales sin commitear que colisionen harán fallar el job.
