# -*- coding: utf-8 -*-
{
    'name': 'Chatbot Cart',
    'version': '19.0.1.17.0',
    'category': 'Sales/WhatsApp',
    'summary': 'Carrito de compra por WhatsApp con IA',
    'description': """Carrito de compra por WhatsApp: el usuario consulta productos (con imagen),
arma un carrito con operaciones fáciles (ver, agregar, quitar, modificar, volver, cancelar)
y paga enviando el vaucher. Reutiliza ai_chatbot_1_portal, whatsapp_cloud_integration y
bcv_rate_update_venezuela.""",
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': 'https://integraia.lat',
    'depends': [
        'ai_chatbot_1_portal',
        'whatsapp_cloud_integration',
        'bcv_rate_update_venezuela',
    ],
    'data': [
        'data/chatbot_flujo_carrito_data.xml',
        'views/chatbot_cart_views.xml',
        'views/chatbot_config_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}