from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestReciboPago(BaseChatbotCartTestCase):
    """SPEC 41: recibo fiel al pagar (totales reales) + datos de depósito."""

    def setUp(self):
        super().setUp()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        self.controller = ChatbotCartController()
        self.cart = CartService()
        self.cart.agregar(self.env, self.session_id, self.product_a.id, 1)
        # Tests deterministas: sin datos de pago pre-existentes en la config
        # activa (el DB de test puede traer la config real del negocio).
        active = self.env['chatbot.config'].sudo()._get_active_config()
        if active:
            active.write({'payment_instructions': ''})

    # --- recibo con items ---

    def test_01_recibo_con_totales_reales(self):
        resp = self.controller._pagar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        texto = resp['texto_para_usuario']
        self.assertIn('recibido', texto)
        self.assertIn('1 item(s)', texto)
        self.assertNotIn('0 item(s)', texto)
        self.assertIn('130.00', texto)  # total VES del item (130 x 1)
        self.assertIn('6.50', texto)    # total USD del item
        self.assertEqual(resp['finalizado'], True)
        self.assertTrue(resp.get('order_id'))
        self.assertTrue(resp.get('order_name'))

    def test_02_orden_creada_y_confirmada(self):
        self.controller._pagar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        order = self.env['sale.order'].sudo().search(
            [('client_order_ref', '=', self.session_id)], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.state, 'sale')
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_id, self.product_a)

    def test_03_carrito_queda_vacio_y_sesion_en_carrito(self):
        self.controller._pagar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resumen = self.cart.resumen(self.env, self.session_id)
        self.assertEqual(resumen['count'], 0)
        session = self.env['chatbot.session'].sudo().search(
            [('session_id', '=', self.session_id)], limit=1)
        self.assertEqual((session.estado or {}).get('modo'), 'CARRITO')

    # --- datos para el pago ---

    def test_04_pago_sin_datos_fallback(self):
        resp = self.controller._pagar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertIn(
            'Te escribiremos aquí mismo para coordinar el pago',
            resp['texto_para_usuario'])
        self.assertNotIn('datos bancarios que te indicamos', resp['texto_para_usuario'])

    def test_05_pago_con_datos_configurados(self):
        self.env['chatbot.config'].sudo().create({
            'name': 'Negocio Test',
            'payment_instructions': 'Banco Test - 0123456789 - Pago Móvil 0414...',
        })
        resp = self.controller._pagar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        texto = resp['texto_para_usuario']
        self.assertIn('Realiza la transferencia a', texto)
        self.assertIn('Banco Test - 0123456789', texto)
        self.assertNotIn('Te escribiremos aquí mismo', texto)

    def test_06_seccion_pago_directa(self):
        seccion = self.controller._seccion_pago(self.env)
        self.assertIn('Te escribiremos aquí mismo', seccion)
        self.env['chatbot.config'].sudo().create({
            'name': 'Negocio Seccion',
            'payment_instructions': 'Datos X',
        })
        seccion = self.controller._seccion_pago(self.env)
        self.assertIn('Datos X', seccion)
        self.assertIn('vaucher', seccion)

    # --- regresión: carrito vacío ---

    def test_07_pagar_carrito_vacio_no_crea_orden(self):
        session = self.env['chatbot.session'].sudo()
        session._limpiar_carrito(self.session_id)
        ordenes_antes = self.env['sale.order'].sudo().search_count([])
        resp = self.controller._pagar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertIn('carrito está vacío', resp['texto_para_usuario'])
        self.assertEqual(
            self.env['sale.order'].sudo().search_count([]), ordenes_antes)
