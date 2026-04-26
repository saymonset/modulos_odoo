#!/bin/bash
# ============================================================================
# script: init_modulos_structure.sh
# uso: ./init_modulos_structure.sh
# propósito: Inicializa la estructura centralizada de módulos Odoo con Git
# ============================================================================

set -e  # Detener si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Inicializando estructura de módulos Odoo${NC}"
echo -e "${BLUE}========================================${NC}"

# Directorio actual (debe ser /home/odoo/modulos_odoo)
BASE_DIR=$(pwd)
echo -e "${GREEN}✓ Directorio base: ${BASE_DIR}${NC}"

# Crear estructura de directorios
echo -e "${YELLOW}Creando estructura de directorios...${NC}"
mkdir -p shared
mkdir -p clientes
mkdir -p .scripts
mkdir -p logs

echo -e "${GREEN}✓ Estructura creada${NC}"

# Crear .gitignore global
echo -e "${YELLOW}Creando .gitignore...${NC}"
cat > .gitignore << 'EOF'
# ===========================================
# .gitignore para repositorios de módulos Odoo
# ===========================================

# Python
*.py[cod]
*.so
*.egg
*.egg-info
dist
build
__pycache__/
*.pyc

# Odoo
*.odb
*.pid
*.log
*.o
*.rej
*.orig
*.swp
*.swo
*~
.DS_Store
.idea/
.vscode/
*.swp
.session
.bak

# Archivos de base de datos
*.sql
*.dump

# Archivos temporales
temp/
tmp/
*.tmp
*.bak
*.backup

# Entornos virtuales
venv/
env/
ENV/
.env
.venv

# IDs de prueba
*.db
*.sqlite

# Backup de módulos
*.zip
*.tar
*.tar.gz

# Archivos de configuración local
config.local
*.conf.local
odoo.conf

# Logs y reportes
*.log
*.report

# Docker
.docker/
docker-compose.override.yml

# Archivos generados por Odoo
*.filestore
*.sessions
*.db

# Secrets
secrets/
*.pem
*.key
*.crt
secret.txt
*_password.txt 
*_password
*.secret

# Archivos de editor
.cursor/
*.swp
*.swo
*~
.project
.classpath
.settings/

# Archivos de sistema
Thumbs.db
ehthumbs.db
Desktop.ini

# NOTA: Cada módulo tendrá su propio .gitignore
# Este es solo para la estructura padre
EOF

echo -e "${GREEN}✓ .gitignore creado${NC}"

# Crear archivo README.md principal
echo -e "${YELLOW}Creando README.md...${NC}"
cat > README.md << 'EOF'
# Repositorio Central de Módulos Odoo

## Estructura