from odoo.tests import tagged

from .common import BaseCotizacionTestCase


@tagged("-at_install", "post_install")
class TestCotizacion(BaseCotizacionTestCase):
    """SPEC 47: partner por teléfono, cotización sale.order, PDF/estado."""

    # --- partner ---

    def test_01_partner_por_telefono_existente(self):
        partner = self.env['chatbot.quote.session'].resolver_partner_por_telefono(
            '584149990001')
        self.assertEqual(partner.id, self.partner_con_email.id)

    def test_02_partner_nuevo_con_nombre_y_email(self):
        partner = self.env['chatbot.quote.session'].resolver_partner_por_telefono(
            '04123557788', nombre='Juan Cotizado', email='juan@dominio.com')
        self.assertEqual(partner.phone, '04123557788')
        self.assertEqual(partner.name, 'Juan Cotizado')
        self.assertEqual(partner.email, 'juan@dominio.com')

    def test_03_partner_nuevo_sin_nombre_no_se_crea(self):
        partner = self.env['chatbot.quote.session'].resolver_partner_por_telefono(
            '04123557799')
        self.assertFalse(partner)

    # --- cotizar_desde_carrito (contrato SPEC 50) ---

    def test_05_cotizar_partner_con_email(self):
        with self._patch_email():
            order_id = self.env['chatbot.quote.session'].cotizar_desde_carrito(
                session_id='test-quote-001', telefono='584149990001',
                email=None, nombre=None, items=self._items())
        order = self.env['sale.order'].browse(order_id)
        self.assertEqual(order.partner_id, self.partner_con_email)
        self.assertTrue(order.quotation_chatbot)
        self.assertEqual(len(order.order_line), 1)
        self.assertTrue(self.env['chatbot.quote.session'].search(
            [('sale_order_id', '=', order.id)]))

    def test_06_cotizar_partner_nuevo_lleva_telefono_nombre_email(self):
        with self._patch_email():
            order_id = self.env['chatbot.quote.session'].cotizar_desde_carrito(
                session_id='test-quote-002', telefono='04123557788',
                email='maria@dominio.com', nombre='María Prueba', items=self._items())
        order = self.env['sale.order'].browse(order_id)
        self.assertEqual(order.partner_id.phone, '04123557788')
        self.assertEqual(order.partner_id.name, 'María Prueba')
        self.assertEqual(order.partner_id.email, 'maria@dominio.com')
