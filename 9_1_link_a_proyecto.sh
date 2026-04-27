# 1. Crear enlace
         
#ORIGEN="/home/odoo/modulos_odoo/shared/oca/chat_bot_integra/19.0"
ORIGEN="/home/odoo/modulos_odoo/shared/chat_bot_integra/19.0"
DESTINO="/home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/v19/data/addons/extra/chat_bot_integra"
mkdir -p "$(dirname "$DESTINO")"
[ -e "$DESTINO" ] && mv "$DESTINO" "$DESTINO.bak"
ln -s "$ORIGEN" "$DESTINO"

# 2. Registrar módulo
./4_registrar_modulo.sh chat_bot_integra 19.0 integraia production