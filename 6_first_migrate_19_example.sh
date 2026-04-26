cd /home/odoo/modulos_odoo

# ============================================
# PREPARAR ESTRUCTURA PARA OCA (múltiples versiones)
# ============================================
mkdir -p shared/oca/18.0
mkdir -p shared/oca/19.0

# ============================================
# ============================================
# MIGRACIÓN ODOO 18
# ============================================
# ============================================

# ============================================
# Módulo 1: a_hospital
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/a_hospital" a_hospital 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/a_hospital" a_hospital 18.0
./4_registrar_modulo.sh a_hospital 18.0 cliente1 development

# ============================================
# Módulo 2: backend_theme_explorer
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/backend_theme_explorer" backend_theme_explorer 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/backend_theme_explorer" backend_theme_explorer 18.0
./4_registrar_modulo.sh backend_theme_explorer 18.0 cliente1 development

# ============================================
# Módulo 3: business_intelligence_queries
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/business_intelligence_queries" business_intelligence_queries 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/business_intelligence_queries" business_intelligence_queries 18.0
./4_registrar_modulo.sh business_intelligence_queries 18.0 cliente1 development

# ============================================
# Módulo 4: chat-bot-n8n-ia
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/chat-bot-n8n-ia" chat-bot-n8n-ia 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/chat-bot-n8n-ia" chat-bot-n8n-ia 18.0
./4_registrar_modulo.sh chat-bot-n8n-ia 18.0 cliente1 development

# ============================================
# Módulo 5: chat-bot-unisa
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/chat-bot-unisa" chat-bot-unisa 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/chat-bot-unisa" chat-bot-unisa 18.0
./4_registrar_modulo.sh chat-bot-unisa 18.0 cliente1 development

# ============================================
# Módulo 6: chatter_voice_note
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/chatter_voice_note" chatter_voice_note 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/chatter_voice_note" chatter_voice_note 18.0
./4_registrar_modulo.sh chatter_voice_note 18.0 cliente1 development

# ============================================
# Módulo 7: conversion
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/conversion" conversion 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/conversion" conversion 18.0
./4_registrar_modulo.sh conversion 18.0 cliente1 development

# ============================================
# Módulo 8: delivery_orders_report
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/delivery_orders_report" delivery_orders_report 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/delivery_orders_report" delivery_orders_report 18.0
./4_registrar_modulo.sh delivery_orders_report 18.0 cliente1 development

# ============================================
# Módulo 9: evolution-api
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/evolution-api" evolution-api 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/evolution-api" evolution-api 18.0
./4_registrar_modulo.sh evolution-api 18.0 cliente1 development

# ============================================
# Módulo 10: igftpaymentmethod
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/igtfpaymentmethod" igftpaymentmethod 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/igtfpaymentmethod" igftpaymentmethod 18.0
./4_registrar_modulo.sh igftpaymentmethod 18.0 cliente1 development

# ============================================
# Módulo 11: pdfmake
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/pdfmake" pdfmake 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/pdfmake" pdfmake 18.0
./4_registrar_modulo.sh pdfmake 18.0 cliente1 development

# ============================================
# Módulo 12: pos_my_ticket
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/pos_my_ticket" pos_my_ticket 18.0
./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/pos_my_ticket" pos_my_ticket 18.0
./4_registrar_modulo.sh pos_my_ticket 18.0 cliente1 development

# ============================================
# Módulo 13: website_whatsapp (OCA - Odoo 18)
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/website_whatsapp" website_whatsapp 18.0
mv /home/odoo/modulos_odoo/shared/website_whatsapp/18.0 /home/odoo/modulos_odoo/shared/oca/18.0/website_whatsapp
rmdir /home/odoo/modulos_odoo/shared/website_whatsapp 2>/dev/null
rm -f "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/website_whatsapp"
ln -s /home/odoo/modulos_odoo/shared/oca/18.0/website_whatsapp "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/website_whatsapp"
./4_registrar_modulo.sh website_whatsapp 18.0 oca development

# ============================================
# Módulo 14: web_responsive (OCA - Odoo 18)
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/web_responsive" web_responsive 18.0
mv /home/odoo/modulos_odoo/shared/web_responsive/18.0 /home/odoo/modulos_odoo/shared/oca/18.0/web_responsive
rmdir /home/odoo/modulos_odoo/shared/web_responsive 2>/dev/null
rm -f "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/web_responsive"
ln -s /home/odoo/modulos_odoo/shared/oca/18.0/web_responsive "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/web_responsive"
./4_registrar_modulo.sh web_responsive 18.0 oca development

# ============================================
# ============================================
# MIGRACIÓN ODOO 19
# ============================================
# ============================================

# ============================================
# Módulo 15: bcv_rate_update_venezuela (Odoo 19)
# ============================================
# ./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/bcv_rate_update_venezuela" bcv_rate_update_venezuela 19.0
# ./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/bcv_rate_update_venezuela" bcv_rate_update_venezuela 19.0
# ./4_registrar_modulo.sh bcv_rate_update_venezuela 19.0 integraiadev_19 development

# ============================================
# Módulo 16: chat_bot_integra (Odoo 19)
# ============================================
# ./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_integra" chat_bot_integra 19.0
# ./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_integra" chat_bot_integra 19.0
# ./4_registrar_modulo.sh chat_bot_integra 19.0 integraiadev_19 development

# ============================================
# Módulo 17: chat_bot_n8n_ia (Odoo 19)
# ============================================
# ./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia" chat_bot_n8n_ia 19.0
# ./2_enlazar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/chat_bot_n8n_ia" chat_bot_n8n_ia 19.0
# ./4_registrar_modulo.sh chat_bot_n8n_ia 19.0 integraiadev_19 development

# ============================================
# Módulo 18: website_whatsapp (OCA - Odoo 19)
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/website_whatsapp" website_whatsapp 19.0
mv /home/odoo/modulos_odoo/shared/website_whatsapp/19.0 /home/odoo/modulos_odoo/shared/oca/19.0/website_whatsapp
rmdir /home/odoo/modulos_odoo/shared/website_whatsapp 2>/dev/null
rm -f "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/website_whatsapp"
ln -s /home/odoo/modulos_odoo/shared/oca/19.0/website_whatsapp "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/website_whatsapp"
./4_registrar_modulo.sh website_whatsapp 19.0 oca development

# ============================================
# Módulo 19: web_responsive (OCA - Odoo 19)
# ============================================
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/web_responsive" web_responsive 19.0
mv /home/odoo/modulos_odoo/shared/web_responsive/19.0 /home/odoo/modulos_odoo/shared/oca/19.0/web_responsive
rmdir /home/odoo/modulos_odoo/shared/web_responsive 2>/dev/null
rm -f "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/web_responsive"
ln -s /home/odoo/modulos_odoo/shared/oca/19.0/web_responsive "/home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/web_responsive"
./4_registrar_modulo.sh web_responsive 19.0 oca development

# ============================================
# VERIFICAR RESULTADOS
# ============================================
echo ""
echo "=========================================="
echo "VERIFICACIÓN DE MIGRACIÓN COMPLETA"
echo "=========================================="

echo ""
echo "=== ESTRUCTURA SHARED/OCA ==="
echo "OCA 18.0:"
ls -la /home/odoo/modulos_odoo/shared/oca/18.0/
echo ""
echo "OCA 19.0:"
ls -la /home/odoo/modulos_odoo/shared/oca/19.0/

echo ""
echo "=== TODOS LOS MÓDULOS EN SHARED ==="
./3_ver_modulos.sh

echo ""
echo "=== ENLACES ODOO 18 - EXTRA ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/ | grep "^l" | wc -l
echo "enlaces activos"

echo ""
echo "=== ENLACES ODOO 18 - OCA ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/ | grep "^l"

echo ""
echo "=== ENLACES ODOO 19 - EXTRA ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/extra/ | grep "^l"

echo ""
echo "=== ENLACES ODOO 19 - OCA ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo19/clientes/integraiadev_19/data/addons/oca/ | grep "^l"

echo ""
echo "=== INVENTARIO COMPLETO ==="
cat INVENTARIO.csv

echo ""
echo "=========================================="
echo "RESUMEN FINAL"
echo "=========================================="
echo ""
echo "Odoo 18 - cliente1: 12 módulos en extra/"
echo "Odoo 18 - oca: 2 módulos en oca/"
echo "Odoo 19 - integraiadev_19: 3 módulos en extra/"
echo "Odoo 19 - oca: 2 módulos en oca/"
echo ""
echo "Total módulos migrados: 19"
echo ""
echo "Estructura final:"
echo "  /home/odoo/modulos_odoo/shared/"
echo "    ├── a_hospital/18.0/"
echo "    ├── backend_theme_explorer/18.0/"
echo "    ├── business_intelligence_queries/18.0/"
echo "    ├── chat-bot-n8n-ia/18.0/"
echo "    ├── chat-bot-unisa/18.0/"
echo "    ├── chatter_voice_note/18.0/"
echo "    ├── conversion/18.0/"
echo "    ├── delivery_orders_report/18.0/"
echo "    ├── evolution-api/18.0/"
echo "    ├── igftpaymentmethod/18.0/"
echo "    ├── pdfmake/18.0/"
echo "    ├── pos_my_ticket/18.0/"
echo "    ├── bcv_rate_update_venezuela/19.0/"
echo "    ├── chat_bot_integra/19.0/"
echo "    ├── chat_bot_n8n_ia/19.0/"
echo "    └── oca/"
echo "          ├── 18.0/"
echo "          │    ├── website_whatsapp/"
echo "          │    └── web_responsive/"
echo "          └── 19.0/"
echo "               ├── website_whatsapp/"
echo "               └── web_responsive/"