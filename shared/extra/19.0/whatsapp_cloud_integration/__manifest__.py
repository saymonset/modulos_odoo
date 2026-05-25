# -*- coding: utf-8 -*-
{
    'name': 'WhatsApp Cloud API Integration',
    'version': '19.0.1.0.0',
    'category': 'Sales/WhatsApp',
    'summary': 'Integrate Odoo with Meta WhatsApp Cloud API',
    'description': """
        This module integrates Odoo 19 with the Meta WhatsApp Cloud API.
        It allows sending and receiving messages using official Meta templates.
    """,
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': 'https://integraia.lat',
    'maintainer': 'Simon Alberto Rodriguez Pacheco',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/waba_account_views.xml',
        'views/whatsapp_history_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_template_views.xml',   # ← nuevo
        'views/menu_views.xml',
        'views/server_actions_cron_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
     'images': [
        'whatsapp_cloud_integration/static/description/icon.png'
    ],
}