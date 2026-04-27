#!/bin/bash
ORIGEN="/home/odoo/modulos_odoo/shared/chat_bot_n8n_ia/19.0"
DESTINO="/home/odoo/prod/odoo19-skeleton/postiz-n8n-chatwoot-pgadmin-odoo_19/v19/data/addons/extra/chat_bot_n8n_ia"

# Copiar con sudo
sudo cp -r "$ORIGEN" "$DESTINO"
sudo chown -R 1001:1001 "$DESTINO"
sudo chmod -R 755 "$DESTINO"

# Ajustar dentro del contenedor
docker exec odoo-19-web chown -R 1001:1001 /opt/odoo/custom-addons/extra/chat_bot_n8n_ia
docker exec odoo-19-web chmod -R 755 /opt/odoo/custom-addons/extra/chat_bot_n8n_ia

echo "✅ Módulo copiado y permisos listos"