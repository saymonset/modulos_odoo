import base64
import io

from odoo import fields
from odoo.tests import TransactionCase


class TestProductXlsxImport(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Import = self.env['product.xlsx.import']

    def _create_test_xlsx(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl no instalado")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Producto', 'Tipo', 'Referencia', 'Precio ($)', 'Atributo', 'Valor Atributo', 'Imagen (nombre archivo)'])
        ws.append(['Producto Simple', 'Simple', 'SIMP-001', 25.99, '', '', ''])
        ws.append(['Producto Simple 2', 'Simple', 'SIMP-002', 35.50, '', '', ''])
        ws.append(['Producto Padre', 'Padre', 'PADRE-001', 100.00, 'Tamaño', '', ''])
        ws.append(['Producto Padre', 'Variante', 'PADRE-001-S', 90.00, 'Tamaño', 'S', ''])
        ws.append(['Producto Padre', 'Variante', 'PADRE-001-M', 100.00, 'Tamaño', 'M', ''])
        ws.append(['Producto Padre', 'Variante', 'PADRE-001-L', 110.00, 'Tamaño', 'L', ''])
        buf = io.BytesIO()
        wb.save(buf)
        return base64.b64encode(buf.getvalue())

    def test_import_simple_products(self):
        xlsx_data = self._create_test_xlsx()
        import_record = self.Import.create({
            'name': 'Test Simple',
            'xlsx_file': xlsx_data,
            'xlsx_filename': 'test.xlsx',
        })
        import_record.action_import()
        self.assertEqual(import_record.state, 'done')
        self.assertEqual(import_record.created_products, 3)
        self.assertEqual(import_record.created_variants, 3)
        self.assertEqual(import_record.error_count, 0)

    def test_import_duplicate_skip(self):
        uom = self.env['uom.uom'].search([('name', '=', 'Unit(s)')], limit=1) or self.env['uom.uom'].search([], limit=1)
        self.env['product.template'].create({
            'name': 'Existente',
            'default_code': 'SIMP-001',
            'type': 'consu',
            'list_price': 10.0,
            'uom_id': uom.id or 1,
            'service_tracking': 'no',
            'tracking': 'none',
        })
        xlsx_data = self._create_test_xlsx()
        import_record = self.Import.create({
            'name': 'Test Duplicados',
            'xlsx_file': xlsx_data,
            'xlsx_filename': 'test.xlsx',
        })
        import_record.action_import()
        self.assertEqual(import_record.state, 'done')
        self.assertEqual(import_record.skipped_count, 1)

    def test_import_with_category(self):
        category = self.env['product.category'].create({'name': 'Test Cat'})
        xlsx_data = self._create_test_xlsx()
        import_record = self.Import.create({
            'name': 'Test Categoría',
            'xlsx_file': xlsx_data,
            'xlsx_filename': 'test.xlsx',
            'categ_id': category.id,
        })
        import_record.action_import()
        product = self.env['product.template'].search([('default_code', '=', 'SIMP-001')], limit=1)
        self.assertTrue(product)
        self.assertEqual(product.categ_id.id, category.id)
