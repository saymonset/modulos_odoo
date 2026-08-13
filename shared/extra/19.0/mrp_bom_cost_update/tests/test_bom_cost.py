from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestBomCost(TransactionCase):

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
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'standard_price': 50.0,
        })
        cls.component_1 = cls.env['product.product'].create({
            'name': 'Component 1',
            'type': 'consu',
            'standard_price': 10.0,
        })
        cls.component_2 = cls.env['product.product'].create({
            'name': 'Component 2',
            'type': 'consu',
            'standard_price': 5.0,
        })
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Test Workcenter',
            'costs_hour': 60.0,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.component_1.id,
                    'product_qty': 2.0,
                }),
                (0, 0, {
                    'product_id': cls.component_2.id,
                    'product_qty': 3.0,
                }),
            ],
            'operation_ids': [
                (0, 0, {
                    'name': 'Op 1',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle': 30.0,
                }),
                (0, 0, {
                    'name': 'Op 2',
                    'workcenter_id': cls.workcenter.id,
                    'time_cycle': 60.0,
                }),
            ],
        })

    def test_01_compute_bom_cost_material(self):
        cost = self.bom.bom_cost
        total = (2.0 * 10.0) + (3.0 * 5.0)
        self.assertGreaterEqual(cost, total)

    def test_02_compute_bom_cost_includes_operations(self):
        cost = self.bom.bom_cost
        material = (2.0 * 10.0) + (3.0 * 5.0)
        ops = (30.0 / 60.0 * 60.0) + (60.0 / 60.0 * 60.0)
        self.assertAlmostEqual(cost, material + ops, places=2)

    def test_03_compute_bom_cost_no_operations(self):
        bom_simple = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.component_1.id,
                    'product_qty': 1.0,
                }),
            ],
        })
        self.assertAlmostEqual(bom_simple.bom_cost, 10.0, places=2)

    def test_04_action_update_bom_cost(self):
        self.bom.action_update_bom_cost()
        self.product.invalidate_recordset()
        self.assertGreater(self.product.product_tmpl_id.standard_price, 0.0)

    def test_05_compute_bom_cost_empty_bom(self):
        empty_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product.product_tmpl_id.id,
            'product_qty': 1.0,
        })
        self.assertEqual(empty_bom.bom_cost, 0.0)