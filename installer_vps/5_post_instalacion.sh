#!/bin/bash
# ============================================================================
# 5_post_instalacion.sh
#
# Cierra la instalación: crontab del monitor 6_5, rclone opcional y checklist
# final de verificación. NO instala 6_6_monitor_cliente_testusuario.sh (es
# específico del cliente de referencia).
# Corre COMO odoo; no necesita sudo.
#
# Uso:  su - odoo  &&  cd ~/installer_vps && ./5_post_instalacion.sh
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
print_ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
print_err(){ echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$(id -un)" != "odoo" ]; then
    print_err "Ejecuta como usuario odoo:  su - odoo  (y luego este script)"
    exit 1
fi

STACK_DIR="$HOME/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19"

echo "=== [1/3] Crontab del monitor ==="
MONITOR="$STACK_DIR/6_5_monitor_bd_salud.sh"
if [ -f "$MONITOR" ]; then
    CRON_LINE="15 * * * * $MONITOR"
    if crontab -l 2>/dev/null | grep -Fq "$MONITOR"; then
        print_ok "Monitor 6_5 ya en crontab"
    else
        ( crontab -l 2>/dev/null; echo "$CRON_LINE" ) | crontab -
        print_ok "Monitor 6_5 agregado al crontab de odoo"
    fi
else
    print_warn "No se encontró $MONITOR (¿ya clonaste el skeleton?)"
fi

echo "[2/3] rclone opcional (backups R2)..."
if command -v rclone > /dev/null 2>&1 || [ -x "$HOME/bin/rclone" ]; then
    print_ok "rclone ya disponible"
else
    read -r -p "¿Instalar rclone en ~/bin? (s/n): " INSTALL_RCLONE
    if [ "${INSTALL_RCLONE,,}" = "s" ]; then
        # rclone se baja con curl y se descomprime con unzip (no garantizados en VPS fresco)
        for tool in curl unzip; do
            if ! command -v "$tool" > /dev/null 2>&1; then
                sudo apt-get update -y
                sudo apt-get install -y "$tool"
            fi
        done
        ARCH="$(uname -m)"
        case "$ARCH" in
            x86_64|amd64) RCLONE_ARCH="amd64" ;;
            aarch64|arm64) RCLONE_ARCH="arm64" ;;
            *) print_err "Arquitectura no soportada: $ARCH"; RCLONE_ARCH="" ;;
        esac
        if [ -n "${RCLONE_ARCH:-}" ]; then
            RCLONE_URL="https://downloads.rclone.org/rclone-current-linux-$RCLONE_ARCH.zip"
            TMP_ZIP="$(mktemp)"
            curl -fsSL "$RCLONE_URL" -o "$TMP_ZIP"
            TMP_DIR="$(mktemp -d)"
            unzip -q "$TMP_ZIP" -d "$TMP_DIR"
            mkdir -p "$HOME/bin"
            cp "$TMP_DIR"/rclone-*/rclone "$HOME/bin/rclone"
            chmod +x "$HOME/bin/rclone"
            rm -rf "$TMP_DIR" "$TMP_ZIP"
            print_ok "rclone instalado en $HOME/bin/rclone"
        fi
    else
        print_warn "rclone omitido (los backups remotos R2 quedan pendientes)"
    fi
fi

echo "[3/3] Checklist final..."
echo "================================================================"
echo "  Usuario  : $(id -un) / grupos: $(groups)"
echo "  Docker   : $(docker --version 2>/dev/null || echo 'pendiente de login')"
echo "  Red      : $(docker network ls --format '{{.Name}}' 2>/dev/null | grep odoo_network_19 || echo 'odoo_network_19 pendiente')"
echo "  nginx    : $(ls /etc/nginx/sites-enabled/*.conf 2>/dev/null | tr '\n' ' ')"
echo "  Stack    : $STACK_DIR"
echo "  Crontab  :"
crontab -l 2>/dev/null | grep -v '^#' || echo "    (vacío)"
echo "================================================================"
echo ""
print_ok "Instalación completada."
print_warn "Pendientes manuales: DNS ya verificado (paso 3.5), credenciales R2 en .env,"
echo "                        onboarding del cliente (tools/TUTORIAL_NUEVO_CLIENTE.md)."
echo ""
print_ok "Despliegue del stack:"
echo "  cd $STACK_DIR"
echo "  ./1_despliegue_reconstruye_imagen_servicios_adicionales.sh"
echo "  ./2_despliegue_servicios_adicionales.sh"
echo "  ./4_start-all.sh"