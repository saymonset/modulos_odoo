cd /home/odoo/modulos_odoo

# Módulo 1: bcv_rate_update_venezuela
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/bcv_rate_update_venezuela" bcv_rate_update_venezuela 19.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/bcv_rate_update_venezuela" bcv_rate_update_venezuela 19.0
./4_registrar_modulo.sh bcv_rate_update_venezuela 19.0 integraiadev_19 development

# Módulo 2: chat_bot_integra
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_integra" chat_bot_integra 19.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_integra" chat_bot_integra 19.0
./4_registrar_modulo.sh chat_bot_integra 19.0 integraiadev_19 development

# Módulo 3: chat_bot_n8n_ia
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia" chat_bot_n8n_ia 19.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia" chat_bot_n8n_ia 19.0
./4_registrar_modulo.sh chat_bot_n8n_ia 19.0 integraiadev_19 development

# Verificar
./3_ver_modulos.sh
echo ""
echo "=== ENLACES CREADOS ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/ | grep "^l"