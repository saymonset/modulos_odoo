#!/bin/bash
# ============================================================================
# 1_preparar_ssh_git.sh
#
# Genera/instala la llave SSH ed25519 de GitHub para el usuario odoo,
# configura ~/.ssh/config y ~/.gitconfig, y valida con `ssh -T git@github.com`.
# Incluye pausa para que el usuario agregue la llave pública a GitHub.
# Corre COMO odoo (no como root); no necesita sudo.
#
# Uso:  su - odoo  &&  cd ~/installer_vps && ./1_preparar_ssh_git.sh
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

SSH_DIR="$HOME/.ssh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config_instalacion.env"
[ -f "$CONFIG" ] && { # shellcheck source=/dev/null
    source "$CONFIG"
}
GIT_NAME="${GIT_NAME:-saymonset}"
GIT_EMAIL="${GIT_EMAIL:-saymon_set@hotmail.com}"

echo "=== [1/6] Preparación SSH + Git (usuario odoo) ==="

# ------------------------------------------------------------
# 1) Llave ed25519
# ------------------------------------------------------------
echo "[1/6] Llave SSH..."
if [ -f "$SSH_DIR/id_ed25519" ]; then
    print_ok "Llave ya existe: $SSH_DIR/id_ed25519"
else
    mkdir -p -m 700 "$SSH_DIR"
    ssh-keygen -t ed25519 -C "odoo@$HOSTNAME" -f "$SSH_DIR/id_ed25519" -N "" > /dev/null
    print_ok "Llave ed25519 generada"
fi

# ------------------------------------------------------------
# 2) known_hosts de GitHub (fingerprint verificado contra el oficial)
#    Nota: ssh-keyscan no imprime fingerprints; se calculan con ssh-keygen -lf.
# ------------------------------------------------------------
echo "[2/6] known_hosts de GitHub..."
GITHUB_FP="SHA256:uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s"
touch "$SSH_DIR/known_hosts"
chmod 600 "$SSH_DIR/known_hosts"
if ssh-keygen -F github.com -f "$SSH_DIR/known_hosts" > /dev/null 2>&1; then
    print_ok "github.com ya en known_hosts"
else
    TMP_KEYS="$(mktemp)"
    ssh-keyscan -t ed25519 github.com 2>/dev/null > "$TMP_KEYS" || true
    FP="$(ssh-keygen -lf "$TMP_KEYS" 2>/dev/null | awk '{print $2}' | head -1)"
    if [ "$FP" = "$GITHUB_FP" ]; then
        cat "$TMP_KEYS" >> "$SSH_DIR/known_hosts"
        print_ok "github.com agregado (fingerprint $FP verificado)"
    else
        rm -f "$TMP_KEYS"
        print_err "Fingerprint no coincide (obtenido: ${FP:-vacío}). Revisa la red."
        exit 1
    fi
    rm -f "$TMP_KEYS"
fi

# ------------------------------------------------------------
# 3) ~/.ssh/config
# ------------------------------------------------------------
echo "[3/6] Config SSH..."
cat > "$SSH_DIR/config" << EOF
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
EOF
chmod 600 "$SSH_DIR/config"
print_ok "$SSH_DIR/config escrito"

# ------------------------------------------------------------
# 4) .gitconfig
# ------------------------------------------------------------
echo "[4/6] Git config..."
cat > "$HOME/.gitconfig" << EOF
[user]
    name = $GIT_NAME
    email = $GIT_EMAIL
EOF
print_ok ".gitconfig con $GIT_NAME <$GIT_EMAIL>"

# ------------------------------------------------------------
# 5) Pausa para agregar la llave pública a GitHub
# ------------------------------------------------------------
echo "[5/6] Agregar la llave a GitHub..."
PUB="$(cat "$SSH_DIR/id_ed25519.pub")"
echo ""
echo "  Copia esta llave pública y agrégala a GitHub"
echo "  (Settings -> SSH and GPG keys -> New SSH key):"
echo ""
echo "  $PUB"
echo ""
while true; do
    read -r -p "¿Ya la agregaste? Responde si cuando esté lista (si): " CONFIRM
    case "${CONFIRM,,}" in
        s|si|sí|y|yes) break ;;
        *) echo "  Aún no. Agrega la llave y escribe 'si'." ;;
    esac
done

# ------------------------------------------------------------
# 6) Validación de conexión
# ------------------------------------------------------------
echo "[6/6] Validando conexión con GitHub..."
if ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    print_ok "Conexión SSH a GitHub verificada"
else
    print_err "ssh -T git@github.com falló. Revisa que la llave esté agregada."
    exit 1
fi

print_ok "SSH + Git listos. Siguiente: ./2_clonar_repos.sh"