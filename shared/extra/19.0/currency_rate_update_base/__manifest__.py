{
    'name': 'Currency Rate Update Base',
    'summary': 'Base engine for multi-bank currency rate updates',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'Simon Alberto Rodriguez Pacheco',
    'license': 'LGPL-3',
    'depends': ['base', 'account', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_data.xml',
        'views/currency_rate_provider_views.xml',
    ],
    'installable': True,
    'application': False,
}
