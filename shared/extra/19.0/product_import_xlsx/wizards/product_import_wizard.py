from odoo import _, api, fields, models


class ProductImportXlsxWizard(models.TransientModel):
    _name = 'product.import.xlsx.wizard'
    _description = 'Asistente de importación de productos desde XLSX'

    xlsx_file = fields.Binary(
        string='Archivo XLSX',
        required=True,
        attachment=True,
        help='Archivo Excel (.xlsx) con las columnas: Producto, Tipo, Referencia, Precio ($), Atributo, Valor Atributo, Imagen (nombre archivo)',
    )
    xlsx_filename = fields.Char(string='Nombre del archivo')
    imagenes_zip = fields.Binary(
        string='ZIP de imágenes (opcional)',
        attachment=True,
        help='Archivo ZIP con las imágenes referenciadas en la columna "Imagen (nombre archivo)". Las imágenes deben estar en la raíz del ZIP.',
    )
    imagenes_zip_filename = fields.Char(string='Nombre del ZIP')
    categ_id = fields.Many2one(
        'product.category',
        string='Categoría de producto',
        help='Categoría que se asignará a todos los productos. Si se deja vacío, se usará la categoría raíz.',
    )
    state = fields.Selection([
        ('confirm', 'Confirmar'),
        ('done', 'Finalizado'),
    ], string='Estado', default='confirm')
    import_id = fields.Many2one('product.xlsx.import', string='Importación')
    log = fields.Text(string='Log', readonly=True)
    created_products = fields.Integer(string='Productos creados', readonly=True)
    created_variants = fields.Integer(string='Variantes creadas', readonly=True)
    skipped_count = fields.Integer(string='Omitidos', readonly=True)
    error_count = fields.Integer(string='Errores', readonly=True)

    def action_import(self):
        self.ensure_one()
        import_record = self.env['product.xlsx.import'].create({
            'name': _('Importación %s') % fields.Datetime.now(),
            'xlsx_file': self.xlsx_file,
            'xlsx_filename': self.xlsx_filename,
            'imagenes_zip': self.imagenes_zip,
            'imagenes_zip_filename': self.imagenes_zip_filename,
            'categ_id': self.categ_id.id if self.categ_id else False,
        })
        try:
            import_record.action_import()
            self.write({
                'state': 'done',
                'import_id': import_record.id,
                'log': import_record.log,
                'created_products': import_record.created_products,
                'created_variants': import_record.created_variants,
                'skipped_count': import_record.skipped_count,
                'error_count': import_record.error_count,
            })
        except Exception:
            self.write({
                'state': 'done',
                'import_id': import_record.id,
                'log': import_record.log or 'Error crítico durante la importación',
            })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.import.xlsx.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
