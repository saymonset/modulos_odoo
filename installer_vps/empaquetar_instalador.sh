#!/bin/bash
# ============================================================================
# empaquetar_instalador.sh
#
# Genera un tarball autocontenido del kit installer_vps/ listo para llevar
# a un VPS nuevo con scp/rsync. No empaqueta los repos (se clonan de GitHub).
#
# Uso:  ./empaquetar_instalador.sh
# Salida: installer_vps_<CLIENTE_SLUG>.tar.gz
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
print_ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG="config_instalacion.env"
[ -f "$CONFIG" ] && { # shellcheck source=/dev/null
    source "$CONFIG"
}
CLIENTE_SLUG="${CLIENTE_SLUG:-cliente}"

OUT_NAME="installer_vps_$CLIENTE_SLUG.tar.gz"
OUT_PATH="../$OUT_NAME"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Copia todo el kit a un staging (para no empaquetar basura de builds previos)
cp -r . "$TMP_DIR/"
rm -f "$TMP_DIR/$OUT_NAME"

# Permisos de ejecución
chmod +x "$TMP_DIR"/[0-9]*.sh "$TMP_DIR"/empaquetar_instalador.sh

tar -czf "$OUT_PATH" -C "$TMP_DIR" .
print_ok "Tarball generado: $OUT_PATH"

print_warn "Para llevarlo a otro VPS:"
echo "  scp $OUT_PATH root@<IP_VPS>:/tmp/"
echo "  ssh root@<IP_VPS> \"mkdir -p /root/installer && tar -xzf /tmp/$OUT_NAME -C /root/installer\""