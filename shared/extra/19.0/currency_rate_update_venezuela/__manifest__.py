{
    'name': 'Currency Rate Update - Venezuela (BCV)',
    'summary': 'Scraping of BCV official rates for Venezuela',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'author': 'Simon Alberto Rodriguez Pacheco',
    'license': 'LGPL-3',
    'depends': ['currency_rate_update_base'],
    'external_dependencies': {
        'python': ['requests', 'beautifulsoup4'],
    },
    'data': [
        'data/provider_data.xml',
    ],
    'installable': True,
    'auto_install': False,
}
