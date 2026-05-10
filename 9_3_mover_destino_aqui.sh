# 1. Asegurar que el destino existe
mkdir -p /home/odoo/modulos_odoo/shared/oca/19.0

# 2. Mover solo directorios que contengan manifiesto de módulo Odoo
origen="/home/odoo/develop/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca"
destino="/home/odoo/modulos_odoo/shared/oca/19.0"

for dir in "$origen"/*/ ; do
    # Eliminar la barra final para tener el nombre del directorio
    dir=${dir%/}
    # Verificar si es un módulo Odoo (__manifest__.py o __openerp__.py)
    if [[ -f "$dir/__manifest__.py" || -f "$dir/__openerp__.py" ]]; then
        echo "Moviendo módulo: $(basename "$dir")"
        mv "$dir" "$destino/"
    else
        echo "Ignorando (no es módulo): $(basename "$dir")"
    fi
done