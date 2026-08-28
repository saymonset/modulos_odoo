from odoo import fields
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BaseBcvTestCase


@tagged("-at_install", "post_install")
class TestPurchaseReportCop(BaseBcvTestCase):
    """Verifica que los reportes de compra (y análisis) reflejan el COP
    cuando ``cop_show_fields`` está activo, y que USD sigue visible.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            'bcv_manual_rate_active': True,
            'bcv_manual_rate': 100.0,
            'cop_show_fields': True,
            'cop_manual_rate_active': True,
            'cop_manual_rate': 4000.0,
        })
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Vendor COP Test',
            'supplier_rank': 1,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Product COP Test',
            'list_price': 1000.0,
            'standard_price': 1000.0,
            'type': 'consu',
            'taxes_id': False,
            'supplier_taxes_id': False,
        })

    @mute_logger("odoo.models.unlink")
    def _create_confirmed_po(self, qty=2.0, price=500.0):
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': qty,
                'price_unit': price,
            })],
        })
        po.button_confirm()
        po.invalidate_recordset()
        return po

    def test_01_purchase_order_line_cop_fields(self):
        """Las líneas de OC deben calcular price_cop y price_subtotal_cop."""
        po = self._create_confirmed_po(qty=3.0, price=500.0)
        line = po.order_line[0]
        self.assertAlmostEqual(line.rate_value, 100.0)
        self.assertAlmostEqual(line.rate_value_cop, 4000.0)
        # price_usd = 500 / 100 = 5.00
        self.assertAlmostEqual(line.price_usd_bcv, 5.0, places=2)
        # price_cop = 5 * 4000 = 20000
        self.assertAlmostEqual(line.price_cop, 20000.0, places=2)
        # subtotal_cop = 20000 * 3 = 60000
        self.assertAlmostEqual(line.price_subtotal_cop, 60000.0, places=2)

    def test_02_purchase_order_totals_cop(self):
        """La OC debe tener amount_total_usd y amount_total_cop calculados."""
        po = self._create_confirmed_po(qty=2.0, price=500.0)
        # total_usd = (500/100) * 2 = 10
        self.assertAlmostEqual(po.amount_total_usd, 10.0, places=2)
        # total_cop = 10 * 4000 = 40000
        self.assertAlmostEqual(po.amount_total_cop, 40000.0, places=2)

    def test_03_purchase_report_has_cop_fields(self):
        """purchase.report debe tener los campos COP definidos."""
        pr = self.env['purchase.report']
        self.assertIn('untaxed_total_cop', pr._fields)
        self.assertIn('price_total_cop', pr._fields)
        self.assertIn('currency_cop_id', pr._fields)
        self.assertIn('cop_show_fields', pr._fields)

    def test_04_purchase_report_cop_values(self):
        """El SQL de purchase.report debe devolver valores COP coherentes."""
        self._create_confirmed_po(qty=2.0, price=500.0)
        pr = self.env['purchase.report'].search([
            ('product_id', '=', self.product.id),
        ], limit=1)
        self.assertTrue(pr)
        # untaxed_total_usd = 10, cop_rate = 4000 → cop = 40000
        if pr.untaxed_total_usd:
            expected_cop = round(pr.untaxed_total_usd * 4000.0, 2)
            self.assertAlmostEqual(
                pr.untaxed_total_cop, expected_cop, places=0,
            )
        self.assertTrue(pr.cop_show_fields)
        cop_curr = self.env.ref('base.COP', raise_if_not_found=False)
        if not cop_curr:
            cop_curr = self.env['res.currency'].sudo().search(
                [('name', '=', 'COP')], limit=1)
        if cop_curr:
            self.assertEqual(pr.currency_cop_id, cop_curr)

    def test_05_cop_disabled_hides_fields(self):
        """Cuando cop_show_fields=False, el campo cop_show_fields del report
        debe ser False."""
        self.company.cop_show_fields = False
        self.company.flush_recordset()
        self._create_confirmed_po(qty=1.0, price=200.0)
        pr = self.env['purchase.report'].search([
            ('product_id', '=', self.product.id),
        ], limit=1)
        self.assertTrue(pr)
        self.assertFalse(pr.cop_show_fields)
        self.company.cop_show_fields = True
        self.company.flush_recordset()

    def test_06_sale_report_has_cop_fields(self):
        """sale.report debe tener los campos COP definidos."""
        sr = self.env['sale.report']
        self.assertIn('price_subtotal_cop', sr._fields)
        self.assertIn('price_total_cop', sr._fields)
        self.assertIn('currency_cop_id', sr._fields)
        self.assertIn('cop_show_fields', sr._fields)

    def test_07_invoice_report_has_cop_fields(self):
        """account.invoice.report debe tener los campos COP definidos."""
        ar = self.env['account.invoice.report']
        self.assertIn('price_subtotal_cop', ar._fields)
        self.assertIn('price_total_cop', ar._fields)
        self.assertIn('currency_cop_id', ar._fields)
        self.assertIn('cop_show_fields', ar._fields)

    def test_08_purchase_report_view_exists(self):
        """Las vistas heredadas de análisis deben existir en el registry."""
        views = self.env['ir.ui.view'].search([
            ('model', '=', 'purchase.report'),
        ])
        arch_fields = views.mapped('arch')
        combined = '\n'.join(arch_fields)
        self.assertIn('untaxed_total_cop', combined)
        self.assertIn('price_total_cop', combined)
        self.assertIn('cop_show_fields', combined)

    def test_09_sale_report_query_runs(self):
        """El SQL de sale.report debe ejecutarse sin error (regresión max(boolean)/GROUP BY)."""
        sr = self.env['sale.report']
        self.assertIn('cop_show_fields', sr._fields)
        sr.search([], limit=1)

    def test_10_invoice_report_query_runs(self):
        """El SQL de account.invoice.report debe ejecutarse sin error (no agrupa por line.id)."""
        ar = self.env['account.invoice.report']
        self.assertIn('cop_show_fields', ar._fields)
        ar.search([], limit=1)
