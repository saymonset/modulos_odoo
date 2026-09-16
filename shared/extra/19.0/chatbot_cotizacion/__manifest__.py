# -*- coding: utf-8 -*-
{
    'name': 'Chatbot Cotización',
    'version': '19.0.1.0.0',
    'category': 'Sales/WhatsApp',
    'summary': 'Cotizaciones por WhatsApp con IA, partner por teléfono',
    'description': """Cotización asistida por IA (SPEC 47): la IA pide el teléfono,
resuelve el partner con el matcher existente, arma la cotización con el módulo
BCV (USD/VES con tasa congelada) y envía el PDF por correo. Endpoints HTTP por
token para el agente de n8n y contrato cotizar_desde_carrito para el carrito.""",
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': 'https://integraia.lat',
    'depends': [
        'ai_chatbot_1_portal',
        'bcv_rate_update_venezuela',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
