# -*- coding: utf-8 -*-
{
    'name': 'ai_chatbot_1_portal',
    'version': '1.0.0',
    'summary': """ ai_chatbot_1_portal Summary """,
    'description': """Módulo de portal para Chatbot de IA. Proporciona la interfaz y componentes de portal para el chatbot de Inteligencia Artificial.""",
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': '',
    'category': '',
    'depends': ['base', 'crm', 'web','website','ai_chatbot_0_core'],
    "data": [
        "security/ir.model.access.csv",
        "data/chatbot_flujos_data.xml",
        "data/chatbot_teams_data.xml",
        "views/res_config_settings_view.xml",  # AÑADIDO: El XML debe ir aquí
        "views/login_templates.xml",  # AÑADIDO: El XML debe ir aquí
        "views/remove_powered_by.xml",  # AÑADIDO: El xml para eliminar el footer debe ir aquí
        'views/chatbot_flujo_views.xml',
        'views/chatbot_paso_views.xml',
        'views/partner_view.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        
#         Tu componente:
            # Se monta usando <owl-component> en website.homepage
            # Está registrado en registry.category("public_components")
            # Solo se usa en el frontend del website
        "web.assets_frontend": [
            'ai_chatbot_1_portal/static/src/css/chat-bot.css',
            'ai_chatbot_1_portal/static/src/js/ChatBotWrapper.js',  
            'ai_chatbot_1_portal/static/src/xml/ChatBotWrapper.xml'
            
        ],
        #Si lo usas en el backend (vista CRM, formulario, kanban, etc.), 
        # así que cargarlo en web.assets_backend 
        'web.assets_backend': [
        ],
        
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
