#!/bin/bash
# ============================================================================
# 3_instalar_docker.sh
#
# Instala Docker Engine + Docker Compose plugin, agrega el usuario odoo al
# grupo docker y crea la red externa odoo_network_19. NO destructivo:
# no borra volúmenes ni hace pruning. Idempotente.
# Corre COMO odoo; usa sudo para lo privilegiado.
#
# Uso:  su - odoo  &&  cd ~/installer_vps && ./3_instalar_docker.sh
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

echo "=== [1/4] Instalación de Docker ==="

# ------------------------------------------------------------
# 1) Instalar Docker si falta
# ------------------------------------------------------------
echo "[1/4] Docker engine..."
if command -v docker > /dev/null 2>&1; then
    print_ok "Docker ya instalado: $(docker --version)"
else
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.gpg > /dev/null
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    print_ok "Docker instalado"
fi

# ------------------------------------------------------------
# 2) Compose plugin
# ------------------------------------------------------------
echo "[2/4] Docker Compose plugin..."
if docker compose version > /dev/null 2>&1; then
    print_ok "Compose plugin disponible: $(docker compose version --short)"
else
    print_err "Falta el plugin docker compose. Instálalo:  sudo apt install docker-compose-plugin"
    exit 1
fi

# ------------------------------------------------------------
# 3) Usuario en grupo docker
# ------------------------------------------------------------
echo "[3/4] Usuario odoo en grupo docker..."
sudo usermod -aG docker odoo
print_ok "odoo en grupo docker (ya activo en esta sesión si nació con el grupo)"

# ------------------------------------------------------------
# 4) Red externa odoo_network_19
# ------------------------------------------------------------
echo "[4/4] Red odoo_network_19..."
if docker network ls --format '{{.Name}}' | grep -qx 'odoo_network_19'; then
    print_ok "La red odoo_network_19 ya existe"
else
    docker network create odoo_network_19
    print_ok "Red odoo_network_19 creada"
fi

# ------------------------------------------------------------
echo "=== Verificación ==="
docker --version
docker compose version
docker network ls | grep odoo_network_19

print_ok "Docker listo. Siguiente: ./3.5_instalar_nginx_certbot.sh (opcional, o ./4_desplegar_stack.sh)"