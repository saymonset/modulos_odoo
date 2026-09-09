#!/bin/bash
# Script para listar todos los módulos de la central (Odoo 18.0 y 19.0)
# Portable: la raíz del repo se detecta sola (funciona en cualquier ruta/clon).

set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")" && pwd)")"
SHARED="$ROOT/shared"

echo "=== ESTRUCTURA SHARED ==="
ls -F "$SHARED/"

echo ""
echo "=== MODULOS POR CATEGORIA Y VERSION ==="
for cat in oca extra; do
    echo ">>>> CATEGORIA: $cat <<<<"
    for ver in 18.0 19.0; do
        PATH_VER="$SHARED/$cat/$ver"
        if [ -d "$PATH_VER" ]; then
            COUNT=$(ls -1 "$PATH_VER" | wc -l)
            echo "  [$ver] ($COUNT módulos)"
            ls -F "$PATH_VER"
            echo ""
        fi
    done
done