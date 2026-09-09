#!/bin/bash
# ============================================================================
# 0_crear_usuario_odoo.sh  —  BOOTSTRAP (primera y única ejecución como root)
#
# Crea el usuario 'odoo' con los grupos del stack (uid 1001,
# adm,sudo,docker,odoogroup) y deja el kit portable en su home. El password
# NO se fija aquí: lo defines tú con `passwd odoo` cuando quieras.
# El grupo 'sudo' da superpoderes CON password (sudo estándar, sin NOPASSWD).
#
# Después de este script: pon password, entra como odoo y corre
# `./instalar_todo.sh` (root ya no hace falta).
#
# Uso:  sudo ./0_crear_usuario_odoo.sh
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
print_ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn(){ echo -e "${YELLOW}[WARN]${NC} $1"; }
print_err(){ echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$(id -u)" -ne 0 ]; then
    print_err "Ejecuta como root (solo esta primera vez)."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config_instalacion.env"
[ -f "$CONFIG" ] && { # shellcheck source=/dev/null
    source "$CONFIG"
}
ODOO_UID="${ODOO_UID:-1001}"

echo "=== Bootstrap: creación del usuario odoo ==="

# ------------------------------------------------------------
# 1) Grupos necesarios
# ------------------------------------------------------------
echo "[1/5] Grupos..."
for group in docker odoo odoogroup; do
    if getent group "$group" > /dev/null 2>&1; then
        print_ok "Grupo $group ya existe"
    else
        groupadd "$group"
        print_ok "Grupo $group creado"
    fi
done

# ------------------------------------------------------------
# 2) Usuario odoo
# ------------------------------------------------------------
echo "[2/5] Usuario..."
if id odoo > /dev/null 2>&1; then
    print_ok "Usuario odoo ya existe: $(id odoo)"
else
    if getent passwd "$ODOO_UID" > /dev/null 2>&1; then
        print_warn "UID $ODOO_UID ocupado; se usará el siguiente UID libre."
        ODOO_UID=""
    fi
    # -U fuerza UID libre si ODOO_UID queda vacío; -G grupos secundarios
    # shellcheck disable=SC2086
    useradd -m -s /bin/bash -g odoo -G adm,sudo,docker,odoogroup -u $ODOO_UID odoo 2>/dev/null \
        || useradd -m -s /bin/bash -g odoo -G adm,sudo,docker,odoogroup odoo
    print_ok "Usuario odoo creado"
fi

# ------------------------------------------------------------
# 3) Grupos garantizados (idempotente)
# ------------------------------------------------------------
echo "[3/5] Grupos secundarios garantizados..."
usermod -aG adm,sudo,docker,odoogroup odoo
print_ok "Grupos de odoo: $(groups odoo)"

# ------------------------------------------------------------
# 4) Password: NO se fija (la defines tú). Instrucción clara.
# ------------------------------------------------------------
echo "[4/5] Password..."
if passwd --status odoo | grep -q '^odoo: L'; then
    print_warn "odoo aún sin password. Pónselo tú (como root):"
    echo "    sudo passwd odoo"
else
    print_ok "odoo ya tiene password configurada"
fi

# ------------------------------------------------------------
# 5) Kit portable en /home/odoo + permisos
# ------------------------------------------------------------
echo "[5/5] Kit en el home de odoo..."
ODOO_HOME="$(getent passwd odoo | cut -d: -f6)"
KIT_DEST="$ODOO_HOME/installer_vps"

if [ -d "$KIT_DEST" ]; then
    print_ok "Kit ya presente en $KIT_DEST"
else
    if [ "$SCRIPT_DIR" = "$KIT_DEST" ]; then
        print_ok "El kit ya se está ejecutando desde $KIT_DEST"
    else
        cp -r "$SCRIPT_DIR" "$KIT_DEST"
        print_ok "Kit copiado a $KIT_DEST"
    fi
fi
chown -R odoo:odoo "$ODOO_HOME"
chmod 750 "$ODOO_HOME"
chmod -R u+rwX "$KIT_DEST"

echo "================================================================"
print_ok "Bootstrap completado."
echo ""
echo "  Siguientes pasos (root ya no hace falta):"
echo "  1) Pon el password de odoo:            sudo passwd odoo"
echo "  2) Entra como odoo:                    su - odoo"
echo "  3) Instala TODO desde su home:         cd ~/installer_vps && ./instalar_todo.sh"
echo ""
echo "  (opcional, si quieres entrar por ssh como odoo: ssh-copy-id odoo@IP)"
echo "================================================================"