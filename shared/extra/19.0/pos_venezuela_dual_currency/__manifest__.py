{
    'name': 'POS Venezuela Dual Currency + IGTF',
    'summary': 'Referencias USD en POS, conversión Bs/USD e IGTF usando tasa BCV',
    'description': """
        Módulo POS para empresas venezolanas que trabajan con bolívares y dólares.
        Reúsa la tasa BCV de bcv_rate_update_venezuela para:
        - Mostrar referencia USD en cada línea del pedido
        - Mostrar total en USD en el resumen del pedido
        - Convertir montos Bs → USD en pantalla de pago
        - Aplicar automáticamente el IGTF en métodos de pago marcados
    """,
    'version': '19.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': 'https://github.com/simonrodriguezpacheco',
    'license': 'LGPL-3',
    'depends': [
        'point_of_sale',
        'bcv_rate_update_venezuela',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_venezuela_dual_currency/static/src/**/*.js',
            'pos_venezuela_dual_currency/static/src/**/*.xml',
        ],
    },
    'application': False,
    'installable': True,
    'auto_install': False,
}
