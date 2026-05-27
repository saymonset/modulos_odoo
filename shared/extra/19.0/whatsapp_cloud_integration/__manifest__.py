# -*- coding: utf-8 -*-
{
    'name': 'WhatsApp Cloud API Integration',
    'version': '19.0.1.0.0',
    'category': 'Sales/WhatsApp',
    'summary': 'Integrate Odoo with Meta WhatsApp Cloud API',
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': 'https://integraia.lat',
    'depends': ['base', 'mail', 'mass_mailing'],
    'data': [
        'security/ir.model.access.csv',
        'views/waba_account_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_history_views.xml',
        'views/whatsapp_mailing_views.xml',
        'views/menu_views.xml',
        'views/server_actions_cron_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_cloud_integration/static/src/js/dynamic_parameters_widget.js',
            'whatsapp_cloud_integration/static/src/xml/dynamic_parameters_template.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
}