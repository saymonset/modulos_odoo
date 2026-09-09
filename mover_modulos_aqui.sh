#!/bin/bash
# Mueve módulos Odoo desde una carpeta de origen hacia la central (shared/extra/19.0).
# 1. Edita la variable ORIGEN con la ruta de tu proyecto/carpeta temporal.
# 2. Ejecuta: ./mover_modulos_aqui.sh
# Portable: el destino se detecta solo desde la raíz del repo.

set -euo pipefail

# Carpeta de origen (editar): se buscan subcarpetas con manifiesto de módulo Odoo
ORIGEN="/ruta/al/origen"

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$(cd "$(dirname "$0")" && pwd)")"
DESTINO="$ROOT/shared/extra/19.0"

if [ ! -d "$ORIGEN" ]; then
    echo "[ERROR] La carpeta de origen no existe: $ORIGEN"
    echo "        Edita la variable ORIGEN en este script."
    exit 1
fi

# Asegurar que el destino existe
mkdir -p "$DESTINO"

# Mover solo directorios que contengan manifiesto de módulo Odoo
for dir in "$ORIGEN"/*/ ; do
    # Eliminar la barra final para tener el nombre del directorio
    dir=${dir%/}
    # Verificar si es un módulo Odoo (__manifest__.py o __openerp__.py)
    if [[ -f "$dir/__manifest__.py" || -f "$dir/__openerp__.py" ]]; then
        echo "Moviendo módulo: $(basename "$dir")"
        mv "$dir" "$DESTINO/"
    else
        echo "Ignorando (no es módulo): $(basename "$dir")"
    fi
done