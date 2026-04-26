#!/bin/bash
# Script para reemplazar carpeta original con enlace simbólico
# Uso: ./enlazar_modulo.sh <ruta_original> <nombre_modulo> <version>

RUTA_ORIGINAL=$1
MODULO=$2
VERSION=$3

if [ -z "$RUTA_ORIGINAL" ] || [ -z "$MODULO" ] || [ -z "$VERSION" ]; then
    echo "Uso: ./enlazar_modulo.sh /ruta/original/del/modulo nombre_modulo 19.0"
    exit 1
fi

FUENTE="/home/odoo/modulos_odoo/shared/${MODULO}/${VERSION}"

# Verificar que el módulo existe en la central
if [ ! -d "$FUENTE" ]; then
    echo "Error: Modulo no encontrado en $FUENTE"
    echo "Ejecuta primero ./migrar_modulo.sh"
    exit 1
fi

# Respaldar original
echo "Respaldando original en $RUTA_ORIGINAL.bak"
mv "$RUTA_ORIGINAL" "$RUTA_ORIGINAL.bak"

# Crear enlace
echo "Creando enlace simbolico"
ln -s "$FUENTE" "$RUTA_ORIGINAL"

echo "Enlace creado"
echo "Original respaldado en: $RUTA_ORIGINAL.bak"
echo "Nuevo enlace apunta a: $FUENTE"