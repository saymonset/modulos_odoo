#!/bin/bash
# ============================================================================
# 3.5_instalar_nginx_certbot.sh
#
# Instala nginx + certbot, despliega snippets, renderiza el conf del cliente
# desde templates/nginx-site.conf.template, verifica DNS y emite el certificado
# Let's Encrypt multi-SAN (un solo cert para todos los subdominios).
#
# Flujo de 2 pasadas para VPS nuevo (los certs aún no existen):
#   1) render con cert autofirmado temporal -> nginx -t + reload (sirve ACME)
#   2) certbot certonly --webroot -> certs reales
#   3) re-render con certs reales -> nginx -t + reload
#
# Corre COMO odoo; usa sudo para lo privilegiado (apt, /etc/nginx, certbot, ufw).
#
# Uso:  su - odoo  &&  cd ~/installer_vps && ./3.5_instalar_nginx_certbot.sh
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config_instalacion.env"
[ -f "$CONFIG" ] && { # shellcheck source=/dev/null
    source "$CONFIG"
}

CLIENTE_SLUG="${CLIENTE_SLUG:?Falta CLIENTE_SLUG en config_instalacion.env}"
DOMINIO_BASE="${DOMINIO_BASE:?Falta DOMINIO_BASE en config_instalacion.env}"
INCLUIR_BLOQUE_LEAD="${INCLUIR_BLOQUE_LEAD:-no}"
CERT_ADMIN="${CERT_ADMIN:-admin@$CLIENTE_SLUG.$DOMINIO_BASE}"

CLIENTE_FQDN="$CLIENTE_SLUG.$DOMINIO_BASE"
CONF_NAME="$CLIENTE_SLUG.conf"
RENDER="/tmp/nginx-render-$CLIENTE_SLUG.conf"

# FQDNs del certificado (multi-SAN)
SERVICIOS="chatwoot n8n postiz pgadmin temporal"
[ "$INCLUIR_BLOQUE_LEAD" = "yes" ] && SERVICIOS="lead $SERVICIOS"

echo "=== [1/8] Instalación nginx + certbot ==="

# Prerrequisitos de utilidades: dig (verificación DNS), curl (IP pública), unzip (rclone).
# En un VPS fresco no están garantizadas; instalar si falta (idempotente).
for tool in dig curl unzip; do
    if ! command -v "$tool" > /dev/null 2>&1; then
        sudo apt-get update -y
        DEBIAN_FRONTEND=noninteractive sudo apt-get install -y "$tool"
    fi
done
print_ok "utilidades listas (dig, curl, unzip)"

# ------------------------------------------------------------
# 1) Paquetes
# ------------------------------------------------------------
if command -v nginx > /dev/null 2>&1; then
    print_ok "nginx ya instalado: $(nginx -v 2>&1)"
else
    sudo apt-get update -y
    DEBIAN_FRONTEND=noninteractive sudo apt-get install -y nginx certbot python3-certbot-nginx
    print_ok "nginx + certbot instalados"
fi
sudo systemctl enable --now nginx > /dev/null 2>&1 || true

# ------------------------------------------------------------
# 2) Snippets + directorio webroot
# ------------------------------------------------------------
echo "[2/8] Snippets y webroot..."
sudo install -d -m 0755 /etc/nginx/snippets /var/www/html
sudo cp "$SCRIPT_DIR/nginx_snippets/ssl.conf"         /etc/nginx/snippets/ssl.conf
sudo cp "$SCRIPT_DIR/nginx_snippets/letsencrypt.conf" /etc/nginx/snippets/letsencrypt.conf
print_ok "snippets/ssl.conf y snippets/letsencrypt.conf instalados"

# ------------------------------------------------------------
# 3) Render del conf (con cert temporal autofirmado)
# ------------------------------------------------------------
echo "[3/8] Render del conf ($CONF_NAME)..."
TMP_CERT_DIR="/tmp/nginx-cert-$CLIENTE_SLUG"
mkdir -p "$TMP_CERT_DIR"
if [ ! -f "$TMP_CERT_DIR/fullchain.pem" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout "$TMP_CERT_DIR/privkey.pem" \
        -out "$TMP_CERT_DIR/fullchain.pem" \
        -days 365 -subj "/CN=$CLIENTE_FQDN" > /dev/null 2>&1
    cp "$TMP_CERT_DIR/fullchain.pem" "$TMP_CERT_DIR/chain.pem"
fi

render_conf() {
    local cert_base="$1" out="$2"
    cp "$SCRIPT_DIR/templates/nginx-site.conf.template" "$out"
    sed -i "s|{{CLIENTE_SLUG}}|$CLIENTE_SLUG|g"   "$out"
    sed -i "s|{{DOMINIO_BASE}}|$DOMINIO_BASE|g"   "$out"
    sed -i "s|{{CERT_BASE}}|$cert_base|g"        "$out"
    if [ "$INCLUIR_BLOQUE_LEAD" != "yes" ]; then
        sed -i '/{{LEAD_BLOQUE_START}}/,/{{LEAD_BLOQUE_END}}/d' "$out"
    fi
    sed -i '/{{LEAD_BLOQUE_START}}/d; /{{LEAD_BLOQUE_END}}/d' "$out"
}

render_conf "$TMP_CERT_DIR" "$RENDER"

# ------------------------------------------------------------
# 4) Desplegar en nginx (primera pasada, cert temporal)
# ------------------------------------------------------------
echo "[4/8] Desplegando conf en nginx..."
sudo cp "$RENDER" "/etc/nginx/sites-available/$CONF_NAME"
sudo ln -sf "/etc/nginx/sites-available/$CONF_NAME" "/etc/nginx/sites-enabled/$CONF_NAME"
sudo rm -f /etc/nginx/sites-enabled/default
if ! sudo nginx -t; then
    print_err "nginx -t falló con el cert temporal. Revisa el conf renderizado: $RENDER"
    exit 1
fi
sudo systemctl reload nginx
print_ok "nginx sirviendo el conf temporal (puerto 80 para ACME)"

# ------------------------------------------------------------
# 5) Verificación de DNS
# ------------------------------------------------------------
echo "[5/8] Verificando DNS..."
SERVER_IP="$(curl -fsS --max-time 10 https://ifconfig.me 2>/dev/null || true)"
FAILED_DNS=0
for svc in "$CLIENTE_SLUG" $SERVICIOS; do
    fqdn="$svc.$CLIENTE_SLUG.$DOMINIO_BASE"
    [ "$svc" = "$CLIENTE_SLUG" ] && fqdn="$CLIENTE_FQDN"
    resolved="$(dig +short "$fqdn" | head -1 || true)"
    if [ -z "$resolved" ]; then
        print_err "  $fqdn -> NXDOMAIN (aún no resuelve). Configura el DNS antes de continuar."
        FAILED_DNS=1
    else
        if [ -n "$SERVER_IP" ] && [ "$resolved" != "$SERVER_IP" ]; then
            print_warn "  $fqdn -> $resolved (la IP pública de este servidor es $SERVER_IP)"
        else
            print_ok "  $fqdn -> $resolved"
        fi
    fi
done
if [ "$FAILED_DNS" -eq 1 ]; then
    print_err "DNS incompleto. Crea los A records en Namecheap y re-ejecuta el script."
    exit 1
fi

# ------------------------------------------------------------
# 6) Emisión del certificado Let's Encrypt (multi-SAN)
# ------------------------------------------------------------
echo "[6/8] Emitiendo certificado Let's Encrypt..."
DOMAINS=""
for svc in "$CLIENTE_SLUG" $SERVICIOS; do
    fqdn="$svc.$CLIENTE_SLUG.$DOMINIO_BASE"
    [ "$svc" = "$CLIENTE_SLUG" ] && fqdn="$CLIENTE_FQDN"
    DOMAINS="$DOMAINS -d $fqdn"
done
# shellcheck disable=SC2086
sudo certbot certonly --webroot -w /var/www/html $DOMAINS \
    --non-interactive --agree-tos -m "$CERT_ADMIN" \
    --keep-until-expiring > /dev/null 2>&1 || {
    print_err "certbot falló. Revisa que el puerto 80 esté abierto y el DNS correcto."
    exit 1
}
print_ok "Certificado en /etc/letsencrypt/live/$CLIENTE_FQDN/"

# ------------------------------------------------------------
# 7) Re-render con certs reales + validación
# ------------------------------------------------------------
echo "[7/8] Re-render con certs reales..."
CERT_BASE="/etc/letsencrypt/live/$CLIENTE_FQDN"
render_conf "$CERT_BASE" "$RENDER"
sudo cp "$RENDER" "/etc/nginx/sites-available/$CONF_NAME"
if ! sudo nginx -t; then
    print_err "nginx -t falló con los certs reales."
    exit 1
fi
sudo systemctl reload nginx
print_ok "Conf final validado y desplegado"

# ------------------------------------------------------------
# 8) Firewall UFW
# ------------------------------------------------------------
echo "[8/8] Firewall UFW..."
if command -v ufw > /dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 22/tcp > /dev/null
    sudo ufw allow 80/tcp > /dev/null
    sudo ufw allow 443/tcp > /dev/null
    print_ok "UFW: permitidos 22, 80 y 443"
else
    print_warn "UFW no activo u ausente; omite si el proveedor filtra los puertos."
fi

echo "================================================"
print_ok "nginx + SSL listos para $CLIENTE_FQDN"
echo "  Conf:         /etc/nginx/sites-available/$CONF_NAME"
echo "  Render local: $RENDER"
echo "  Cert:         /etc/letsencrypt/live/$CLIENTE_FQDN/"
echo "  Siguiente:    ./4_desplegar_stack.sh"
echo "================================================"