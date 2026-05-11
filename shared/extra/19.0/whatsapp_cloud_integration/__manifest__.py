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
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/waba_account_views.xml',          # acciones y vistas
        'views/whatsapp_message_views.xml',
        'views/whatsapp_history_views.xml',
        'views/menu_views.xml',                  # menús, después de las acciones
        'data/server_actions_cron.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}