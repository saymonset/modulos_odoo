# 1. Crear enlace
#ORIGEN="/home/odoo/modulos_odoo/shared/bcv_rate_update_venezuela/19.0"
ORIGEN="/home/odoo/modulos_odoo/shared/chat_bot_integra/19.0"
DESTINO="/home/odoo/develop/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_integra"
mkdir -p "$(dirname "$DESTINO")"
[ -e "$DESTINO" ] && mv "$DESTINO" "$DESTINO.bak"
ln -s "$ORIGEN" "$DESTINO"

# 2. Registrar módulo
./4_registrar_modulo.sh chat_bot_integra 19.0 integraiadev_19 development