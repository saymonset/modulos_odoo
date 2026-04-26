cd /home/odoo/modulos_odoo

# Eliminar los .git de cada módulo (para que sean parte del padre)
rm -rf shared/bcv_rate_update_venezuela/19.0/.git
rm -rf shared/chat_bot_integra/19.0/.git
rm -rf shared/chat_bot_n8n_ia/19.0/.git

# Si hay más módulos, eliminar todos
find shared -name ".git" -type d -exec rm -rf {} + 2>/dev/null