from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BaseBcvTestCase


@tagged("-at_install", "post_install")
class TestSecurityPayment(BaseBcvTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
            'type': 'consu',
            'taxes_id': False,
            'supplier_taxes_id': False,
        })

    @mute_logger("odoo.models.unlink")
    def test_01_malicious_payment_data_injection(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
                'price_unit': 100.0,
            })],
        })
        self.assertEqual(order.amount_total, 200.0)
        malicious_payment_data = {
            'amount_vef': 5.0,
            'amount_usd': 1.0,
            'exchange_rate': 5.0,
        }
        order.sudo().write({
            'payment_date': '2026-05-05',
            'payment_method': 'transfer',
            'amount_vef': malicious_payment_data['amount_vef'],
            'amount_usd': malicious_payment_data['amount_usd'],
            'exchange_rate': malicious_payment_data['exchange_rate'],
        })
        self.assertEqual(order.amount_total, 200.0)
        order.action_confirm()
        self.assertEqual(order.amount_total, 200.0)
        invoice = order._create_invoices()
        self.assertEqual(invoice.amount_total, 200.0)
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, 100.0)

    @mute_logger("odoo.models.unlink")
    def test_02_purchase_order_ves_from_usd_regression(self):
        """Regression test: amount_total_ves_from_usd must exist on purchase.order."""
        vendor = self.env['res.partner'].create({
            'name': 'Test Vendor',
            'supplier_rank': 1,
        })
        po = self.env['purchase.order'].create({
            'partner_id': vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 1.0,
                'price_unit': 100.0,
            })],
        })
        self.assertTrue(
            'amount_total_ves_from_usd' in po._fields,
            "amount_total_ves_from_usd debe existir como campo en purchase.order",
        )
        po.button_confirm()
        po.invalidate_recordset()
        self.assertGreaterEqual(po.amount_total_ves_from_usd, 0.0)