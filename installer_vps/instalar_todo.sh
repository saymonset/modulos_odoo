#!/bin/bash
# ============================================================================
# instalar_todo.sh  —  Orquestador (corre como usuario odoo)
#
# Encadena los pasos 1..5 de installer_vps/. Requiere que antes se haya
# ejecutado como root el bootstrap (0_crear_usuario_odoo.sh) y que odoo
# tenga password (para sudo).
#
# Idempotente: se re-ejecuta y solo completa lo que falta.
#
# Uso (como odoo):
#   cd ~/installer_vps
#   ./instalar_todo.sh                 # todo, preguntando por nginx
#   ./instalar_todo.sh --skip-nginx    # sin nginx (DNS aún no listo)
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
print_ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
print_err(){ echo -e "${RED}[ERROR]${NC} $1"; }

SKIP_NGINX=0
for arg in "$@"; do
    [ "$arg" = "--skip-nginx" ] && SKIP_NGINX=1
done

if [ "$(id -un)" != "odoo" ]; then
    print_err "Ejecuta como usuario odoo:  su - odoo  &&  cd ~/installer_vps && ./instalar_todo.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config_instalacion.env"
if [ ! -f "$CONFIG" ]; then
    print_err "Falta $CONFIG (el bootstrap copia el kit completo a tu home)."
    exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

# ------------------------------------------------------------
# 0) Precheck: sudo con password funcionando
# ------------------------------------------------------------
echo "=== Precheck ==="
echo "  Cliente: ${CLIENTE_SLUG:?Falta CLIENTE_SLUG} (${DOMINIO_BASE:?Falta DOMINIO_BASE})"
echo "  Verificando sudo (pide tu password una vez, se cachea ~15 min)..."
if ! sudo -v; then
    print_err "sudo no funciona. Ponle password a odoo como root:  sudo passwd odoo"
    exit 1
fi
print_ok "sudo disponible"

# SMTP_PASSWORD vacío -> pedir y persistir en config
if [ -z "${SMTP_PASSWORD:-}" ]; then
    read -r -s -p "  SMTP_PASSWORD del cliente (vacío = omitir SMTP): " SMTP_PASSWORD
    echo ""
    if [ -n "$SMTP_PASSWORD" ]; then
        sed -i "s|^SMTP_PASSWORD=.*|SMTP_PASSWORD=\"$SMTP_PASSWORD\"|" "$CONFIG"
        print_ok "SMTP_PASSWORD guardado en $CONFIG"
    fi
fi

# ------------------------------------------------------------
# Ejecución de pasos
# ------------------------------------------------------------
run_step() {
    local step="$1" name="$2"
    echo ""
    echo "########################################################"
    echo "# $name"
    echo "########################################################"
    bash "$SCRIPT_DIR/$step"
}

run_step "1_preparar_ssh_git.sh"      "PASO 1 — SSH + Git (pausa para agregar la llave a GitHub)"
run_step "2_clonar_repos.sh"          "PASO 2 — Clonado de repos desde GitHub"
run_step "3_instalar_docker.sh"       "PASO 3 — Docker + red odoo_network_19"

if [ "$SKIP_NGINX" -eq 0 ]; then
    echo ""
    read -r -p "¿Ejecutar nginx + certbot ahora (requiere DNS apuntando a este VPS)? (s/n): " DO_NGINX
    if [ "${DO_NGINX,,}" = "s" ]; then
        run_step "3.5_instalar_nginx_certbot.sh" "PASO 3.5 — nginx + certbot"
    else
        print_warn "nginx omitido. Cuando el DNS esté listo:  ./3.5_instalar_nginx_certbot.sh"
    fi
else
    print_warn "nginx omitido por --skip-nginx. Cuando el DNS esté listo:  ./3.5_instalar_nginx_certbot.sh"
fi

run_step "4_desplegar_stack.sh"       "PASO 4 — Preparación del stack odoo19-skeleton"
run_step "5_post_instalacion.sh"      "PASO 5 — Post-instalación (crontab, rclone, checklist)"

echo ""
echo "================================================================"
print_ok "instalar_todo.sh finalizado."
echo "  Pendiente manual: DNS si omitiste nginx; R2; onboarding (README_AGENTE.md)."
echo "  Despliegue del stack:"
echo "    cd ~/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19"
echo "    ./1_despliegue_reconstruye_imagen_servicios_adicionales.sh"
echo "    ./2_despliegue_servicios_adicionales.sh"
echo "    ./4_start-all.sh"
echo "================================================================"