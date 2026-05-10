#!/bin/bash
# Script para listar todos los módulos migrados

echo "=== ESTRUCTURA SHARED ==="
ls -F /home/odoo/modulos_odoo/shared/

echo ""
echo "=== MODULOS POR CATEGORIA Y VERSION ==="
for cat in oca extra; do
    echo ">>>> CATEGORIA: $cat <<<<"
    for ver in 18.0 19.0; do
        PATH_VER="/home/odoo/modulos_odoo/shared/$cat/$ver"
        if [ -d "$PATH_VER" ]; then
            COUNT=$(ls -1 "$PATH_VER" | wc -l)
            echo "  [$ver] ($COUNT módulos)"
            ls -F "$PATH_VER"
            echo ""
        fi
    done
done