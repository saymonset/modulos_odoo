{
    'name': 'Importación de Productos desde XLSX',
    'version': '1.0.0',
    'summary': 'Importa productos, variantes y atributos desde archivo XLSX con imágenes ZIP',
    'description': """
Módulo para importar productos en Odoo 19 CE desde un archivo XLSX.
Soporta:

- Productos simples
- Productos con variantes (atributos + valores)
- Asignación de imágenes desde archivo ZIP
- Detección automática de duplicados por referencia interna
- Reutilización de atributos existentes
- Log detallado del proceso
    """,
    'author': 'Simon Alberto Rodriguez Pacheco',
    'website': '',
    'category': 'Sales',
    'depends': ['product', 'sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_import_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
