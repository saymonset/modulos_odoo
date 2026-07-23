{
    'name': 'BCV Rate Update for Venezuela',
    'summary': 'Actualización automática de tasa BCV para Venezuela',
    'description': """
        Obtiene diariamente la tasa de cambio oficial del BCV y actualiza
        la moneda VES en Odoo.
    """,
    'version': '19.0.1.0.4',
    'category': 'Sales/Point of Sale',
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': 'https://github.com/simonrodriguezpacheco',
    'maintainer': 'Simon Alberto Rodriguez Pacheco',
    'license': 'LGPL-3',
    #'website_sale', 'base_address_city', 'contacts'
    'depends': [
        'base',
        'web',
        'sale_management',
        'purchase',
        'account',          # Contabilidad base
        'stock',            # Inventario
        'point_of_sale',
        'website_sale', 
        'contacts',
        'payment',
        'whatsapp_cloud_integration',
        'currency_rate_update_base',
        'currency_rate_update_venezuela',
        'currency_rate_update_colombia',
    ],

    'external_dependencies': {
        'python': ['requests', 'beautifulsoup4'],
    },
    
    'data': [
        'security/ir.model.access.csv',
        'data/res_bank_data.xml',
        'views/res_currency_views.xml',
        'views/sale_order_tree_debug.xml',
        'views/sale_order_views.xml',
        'views/website_cart_usd.xml',
        'views/payment_attachment_templates.xml',
        'views/payment_provider_views.xml',
        'views/res_company_views.xml',
        # 'views/website_sale_templates.xml',
        'views/invoice_report_templates.xml',
        'views/sale_report_templates.xml',
        'views/purchase_report_templates.xml',
        'views/payment_templates_inherit.xml',
        'views/product_views.xml',
        'views/stock_quant_views.xml',
        'views/account_move_views.xml',
        'views/purchase_order_views.xml',
        'data/ir_cron_data.xml',
    ],
    
    'assets': {
        'point_of_sale.assets': [
            'bcv_rate_update_venezuela/static/src/css/payment_proof_component.css',
            'bcv_rate_update_venezuela/static/src/js/payment_proof_component.js',
            'bcv_rate_update_venezuela/static/src/xml/payment_proof_component.xml',
            'bcv_rate_update_venezuela/static/src/css/address_autofill.css',
            'bcv_rate_update_venezuela/static/src/js/address_autofill.js',
            'bcv_rate_update_venezuela/static/src/xml/address_autofill.xml',
        ],
        'web.assets_backend': [
            'bcv_rate_update_venezuela/static/src/css/payment_proof_component.css',
            'bcv_rate_update_venezuela/static/src/js/address_autofill.js',
        ],
         "web.assets_frontend": [
            'bcv_rate_update_venezuela/static/src/css/payment_proof_component.css',
            'bcv_rate_update_venezuela/static/src/js/payment_proof_component.js',
            'bcv_rate_update_venezuela/static/src/xml/payment_proof_component.xml',
            'bcv_rate_update_venezuela/static/src/css/address_autofill.css',
            'bcv_rate_update_venezuela/static/src/js/address_autofill.js',
            'bcv_rate_update_venezuela/static/src/xml/address_autofill.xml',
        ],
    },
    
    'application': False,
    'installable': True,
    'auto_install': False,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_cleanup',
    'images': [
        'bcv_rate_update_venezuela/static/description/icon.png'
    ],
}
