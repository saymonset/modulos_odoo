#!/bin/bash
# actualizar_modulos.sh — Despliegue de módulos de la central en el VPS local
#
# Para VPS cliente que NO corren el runner de GitHub Actions (el pipeline CI/CD
# solo corre en el VPS central). Trae los últimos cambios del repo y actualiza
# los módulos en el contenedor Odoo de producción.
#
# Uso (desde la raíz del repo):
#   ./actualizar_modulos.sh                       # actualiza todos los extra/19.0
#   ./actualizar_modulos.sh mod1 mod2             # solo los indicados
#
# Valores por convención del kit installer_vps (ajustables por variables de entorno):
#   PROD_WEB=odoo-19-web  PROD_DB=dbodoo19  PROD_HEALTH=http://localhost:18069/web/health

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
print_ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
print_err(){ echo -e "${RED}[ERROR]${NC} $1"; }

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")" && pwd)")"
cd "$ROOT"

PROD_WEB="${PROD_WEB:-odoo-19-web}"
PROD_DB="${PROD_DB:-dbodoo19}"
PROD_HEALTH="${PROD_HEALTH:-http://localhost:18069/web/health}"
EXTRA_DIR="$ROOT/shared/extra/19.0"

if ! command -v docker > /dev/null 2>&1; then
    print_err "docker no disponible en este host."
    exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -qx "$PROD_WEB"; then
    print_err "No hay contenedor $PROD_WEB corriendo (¿está el stack desplegado?)."
    exit 1
fi

# ------------------------------------------------------------
# 1) Traer últimos cambios
# ------------------------------------------------------------
echo "=== [1/3] git pull en $ROOT ==="
git pull --ff-only
print_ok "repo actualizado"

# ------------------------------------------------------------
# 2) Determinar módulos a actualizar
# ------------------------------------------------------------
if [ "$#" -gt 0 ]; then
    MODULES="$*"
else
    MODULES="$(ls -1 "$EXTRA_DIR" 2>/dev/null | tr '\n' ',' | sed 's/,$//')"
    if [ -z "$MODULES" ]; then
        print_warn "No hay módulos en $EXTRA_DIR; nada que actualizar."
        exit 0
    fi
fi
echo "=== [2/3] Módulos: $MODULES ==="

# Limpiar __pycache__ de los módulos afectados dentro del contenedor
IFS=',' read -ra MODS <<< "$MODULES"
for m in "${MODS[@]}"; do
    docker exec -u root "$PROD_WEB" \
        find "/opt/odoo/custom-addons/extra/${m}" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
done

# ------------------------------------------------------------
# 3) Upgrade + restart + health check
# ------------------------------------------------------------
echo "=== [3/3] Upgrade + restart + health ==="
docker exec "$PROD_WEB" python3 /opt/odoo/odoo-core/odoo-bin \
    -d "$PROD_DB" -u "$MODULES" --stop-after-init --no-http
docker restart "$PROD_WEB"

for i in $(seq 1 90); do
    if curl -sf "$PROD_HEALTH" > /dev/null 2>&1; then
        print_ok "odoo healthy en $PROD_HEALTH"
        exit 0
    fi
    sleep 2
done
print_err "odoo no respondió en $PROD_HEALTH tras el restart."
exit 1