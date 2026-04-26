#!/bin/bash
# Script simple para migrar módulos existentes
# Uso: ./migrar_modulo.sh <ruta_origen> <nombre_modulo> <version>

ORIGEN=$1
MODULO=$2
VERSION=$3

if [ -z "$ORIGEN" ] || [ -z "$MODULO" ] || [ -z "$VERSION" ]; then
    echo "Uso: ./migrar_modulo.sh /ruta/del/modulo nombre_modulo 19.0"
    echo "Ejemplo: ./migrar_modulo.sh /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia chat_bot_n8n_ia 19.0"
    exit 1
fi

DESTINO="/home/odoo/modulos_odoo/shared/${MODULO}/${VERSION}"

echo "Migrando $MODULO a $DESTINO"

# Crear destino
mkdir -p "$DESTINO"

# Copiar módulo
cp -r "$ORIGEN"/* "$DESTINO/"

# Inicializar Git
cd "$DESTINO"
git init
git add .
git commit -m "Migración inicial desde $ORIGEN"

# Crear rama por versión
git branch "$VERSION"
git checkout "$VERSION"

echo "Modulo migrado a: $DESTINO"
echo "Rama actual: $VERSION"