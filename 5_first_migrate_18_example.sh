cd /home/odoo/modulos_odoo

# ============================================
# PREPARAR ESTRUCTURA PARA OCA
# ============================================
mkdir -p shared/oca/18.0

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
# Módulo 4: chat-bot-n8n-ia (mantener nombre original)
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
# Módulo 13: website_whatsapp (OCA - estructura separada)
# ============================================
# Migrar a la carpeta especial de OCA
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/website_whatsapp" website_whatsapp 18.0

# Mover a la estructura de OCA
mv /home/odoo/modulos_odoo/shared/website_whatsapp/18.0 /home/odoo/modulos_odoo/shared/oca/18.0/website_whatsapp
rmdir /home/odoo/modulos_odoo/shared/website_whatsapp 2>/dev/null

# Crear enlace simbólico
rm -f "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/website_whatsapp"
ln -s /home/odoo/modulos_odoo/shared/oca/18.0/website_whatsapp "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/website_whatsapp"

# Registrar como OCA
./4_registrar_modulo.sh website_whatsapp 18.0 oca development

# ============================================
# Módulo 14: web_responsive (OCA - estructura separada)
# ============================================
# Migrar a la carpeta especial de OCA
./1_migrar_modulo.sh "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/web_responsive" web_responsive 18.0

# Mover a la estructura de OCA
mv /home/odoo/modulos_odoo/shared/web_responsive/18.0 /home/odoo/modulos_odoo/shared/oca/18.0/web_responsive
rmdir /home/odoo/modulos_odoo/shared/web_responsive 2>/dev/null

# Crear enlace simbólico
rm -f "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/web_responsive"
ln -s /home/odoo/modulos_odoo/shared/oca/18.0/web_responsive "/home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/web_responsive"

# Registrar como OCA
./4_registrar_modulo.sh web_responsive 18.0 oca development

# ============================================
# VERIFICAR RESULTADOS
# ============================================
echo ""
echo "=========================================="
echo "VERIFICACIÓN DE MIGRACIÓN"
echo "=========================================="

echo ""
echo "=== MÓDULOS MIGRADOS (shared) ==="
./3_ver_modulos.sh

echo ""
echo "=== ESTRUCTURA OCA ==="
ls -la /home/odoo/modulos_odoo/shared/oca/18.0/

echo ""
echo "=== ENLACES EN EXTRA (cliente1) ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/extra/ | grep "^l" | head -12

echo ""
echo "=== ENLACES EN OCA ==="
ls -la /home/odoo/odoo-from-13-to-18/arquitectura/odoo18/clientes/cliente1/extra-addons/oca/ | grep "^l"

echo ""
echo "=== INVENTARIO COMPLETO ==="
cat INVENTARIO.csv

echo ""
echo "=========================================="
echo "MIGRACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Resumen:"
echo "  - Cliente 'cliente1': 12 módulos en extra/"
echo "  - Cliente 'oca': 2 módulos en oca/"
echo "  - Todos los módulos están en /home/odoo/modulos_odoo/shared/"
echo "  - Los originales fueron respaldados como .bak"
echo "  - Los enlaces simbólicos apuntan a la nueva ubicación"