from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "pos_dual_currency")
class TestPosUsdConversion(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            tracking_disable=True,
        ))
        cls.USD = cls.env.ref('base.USD', raise_if_not_found=False)
        cls.company = cls.env.company

    def test_01_compute_amount_total_usd_happy_path(self):
        order = self.env['pos.order'].new({
            'amount_total': 3650.0,
            'config_id': False,
            'currency_id': self.company.currency_id,
        })
        with patch.object(
            type(self.env['product.template']),
            '_get_bcv_rate',
            return_value=36.5,
        ):
            order._compute_amount_total_usd()
        self.assertAlmostEqual(order.amount_total_usd, 100.0, places=2)

    def test_02_compute_amount_total_usd_zero_rate(self):
        order = self.env['pos.order'].new({
            'amount_total': 3650.0,
            'config_id': False,
            'currency_id': self.company.currency_id,
        })
        with patch.object(
            type(self.env['product.template']),
            '_get_bcv_rate',
            return_value=0.0,
        ):
            order._compute_amount_total_usd()
        self.assertEqual(order.amount_total_usd, 0.0)

    def test_03_compute_amount_total_usd_no_rate(self):
        order = self.env['pos.order'].new({
            'amount_total': 3650.0,
            'config_id': False,
            'currency_id': self.company.currency_id,
        })
        with patch.object(
            type(self.env['product.template']),
            '_get_bcv_rate',
            return_value=False,
        ):
            order._compute_amount_total_usd()
        self.assertEqual(order.bcv_rate_value, 1.0)

    def test_04_compute_currency_aux_finds_usd(self):
        if not self.USD:
            self.skipTest("USD currency not found")
        order = self.env['pos.order'].new({
            'currency_id': self.company.currency_id,
        })
        order._compute_currency_aux()
        self.assertEqual(order.currency_aux_usd, self.USD)