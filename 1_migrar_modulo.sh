#!/bin/bash
# Script para migrar módulos Odoo (sin Git, asume monorepo padre)
# Uso: ./migrar_modulo.sh <ruta_origen> <nombre_modulo> <version>

ORIGEN=$1
MODULO=$2
VERSION=$3

if [ -z "$ORIGEN" ] || [ -z "$MODULO" ] || [ -z "$VERSION" ]; then
    echo "Uso: ./migrar_modulo.sh /ruta/del/modulo nombre_modulo 19.0"
    echo "Ejemplo: ./migrar_modulo.sh /home/odoo/.../chat_bot_n8n_ia chat_bot_n8n_ia 19.0"
    exit 1
fi

DESTINO="/home/odoo/modulos_odoo/shared/${MODULO}/${VERSION}"

echo "Migrando $MODULO a $DESTINO (versión $VERSION)"

# Crear directorio destino si no existe
mkdir -p "$DESTINO"

# Copiar módulo (sobrescribe archivos existentes)
cp -rf "$ORIGEN"/* "$DESTINO/"

echo "✅ Módulo migrado a: $DESTINO"
echo "✅ Recuerda que el control de versiones lo gestionas manualmente en tu monorepo padre"