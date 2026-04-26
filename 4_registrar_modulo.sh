#!/bin/bash
# Script para registrar módulo en inventario
# Uso: ./registrar_modulo.sh <nombre_modulo> <version> <cliente> <entorno>

MODULO=$1
VERSION=$2
CLIENTE=$3
ENTORNO=$4

if [ -z "$MODULO" ] || [ -z "$VERSION" ] || [ -z "$CLIENTE" ] || [ -z "$ENTORNO" ]; then
    echo "Uso: ./registrar_modulo.sh nombre_modulo 19.0 cliente1 development"
    exit 1
fi

FECHA=$(date +%Y-%m-%d)
INVENTARIO="/home/odoo/modulos_odoo/INVENTARIO.csv"

# Crear inventario si no existe
if [ ! -f "$INVENTARIO" ]; then
    echo "MODULO,VERSION_ODOO,CLIENTE,ENTORNO,VERSION_MODULO,FECHA,ULTIMO_UPDATE,ESTADO,RUTA" > "$INVENTARIO"
fi

echo "$MODULO,$VERSION,$CLIENTE,$ENTORNO,${VERSION}.1.0.0,$FECHA,,migrado,shared/$MODULO/$VERSION" >> "$INVENTARIO"

echo "Modulo registrado en inventario"