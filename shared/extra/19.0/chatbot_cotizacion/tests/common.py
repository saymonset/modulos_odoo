from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class BaseCotizacionTestCase(TransactionCase):
    """Base para tests de chatbot_cotizacion (SPEC 47)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            no_reset_password=True,
            tracking_disable=True,
        ))
        cls.product_a = cls.env['product.product'].create({
            'name': 'Item prueba cotización',
            'list_price': 100.0,
            'list_price_usd': 5.0,
            'type': 'consu',
            'sale_ok': True,
            'taxes_id': False,
            'supplier_taxes_id': False,
        })
        cls.partner_con_email = cls.env['res.partner'].create({
            'name': 'Cliente Con Email', 'phone': '+58 414 9990001',
            'email': 'conemail@test.com'})

    def _items(self):
        return [{
            'product_id': self.product_a.id, 'name': self.product_a.name,
            'qty': 1, 'price_usd': 5.0,
        }]

    def _patch_email(self):
        """Simula el envío de correo para tests sin SMTP real."""
        from unittest.mock import patch
        return patch.object(
            type(self.env['chatbot.quote.session']),
            '_enviar_pdf', return_value=True)
