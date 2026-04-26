#!/bin/bash
# Script para listar todos los módulos migrados

echo "=== MODULOS EN SHARED ==="
ls -la /home/odoo/modulos_odoo/shared/

echo ""
echo "=== MODULOS POR VERSION ==="
for mod in /home/odoo/modulos_odoo/shared/*/; do
    if [ -d "$mod" ]; then
        nombre=$(basename "$mod")
        echo "Modulo: $nombre"
        ls "$mod"
        echo ""
    fi
done