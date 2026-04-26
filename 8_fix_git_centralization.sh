#!/bin/bash

# =================================================================s
# Script para centralizar módulos de Odoo (convertir gitlinks a archivos reales)
# =================================================================

REPO_DIR="/home/odoo/modulos_odoo"
cd "$REPO_DIR" || exit

echo "--- Iniciando proceso de centralización ---"

# 1. Identificar carpetas que son gitlinks (modo 160000)
GITLINKS=$(git ls-files --stage | grep "^160000" | awk '{print $4}')

if [ -z "$GITLINKS" ]; then
    echo "No se encontraron gitlinks (modo 160000). Verificando carpetas .git huérfanas..."
else
    echo "Se encontraron los siguientes gitlinks:"
    echo "$GITLINKS"
    
    for link in $GITLINKS; do
        echo "Procesando: $link"
        
        # Eliminar el .git interno si existe
        if [ -d "$link/.git" ]; then
            echo "  - Eliminando .git interno en $link"
            rm -rf "$link/.git"
        fi
        
        # Quitar del índice de git como enlace
        echo "  - Quitando del índice (cached)..."
        git rm --cached -r "$link" 2>/dev/null
        
        # Añadir como archivos normales
        echo "  - Añadiendo archivos reales..."
        git add "$link"
    done
fi

# 2. Buscar cualquier otro .git que no esté necesariamente en el índice como gitlink
echo "Buscando otros directorios .git residuales..."
find . -mindepth 2 -name ".git" -type d -exec echo "Eliminando .git residual en: {}" \; -exec rm -rf {} +

# 3. Añadir todo por si acaso
echo "Sincronizando índice..."
git add .

echo "--- Proceso completado ---"
echo "Estado actual de Git:"
git status

echo ""
echo "CONSEJO: Ahora puedes hacer commit y push:"
echo "git commit -m 'feat: centralizar modulos (convertir gitlinks a archivos reales)'"
echo "git push"
