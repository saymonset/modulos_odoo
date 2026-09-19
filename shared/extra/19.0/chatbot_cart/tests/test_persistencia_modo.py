from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestPersistenciaModo(BaseChatbotCartTestCase):
    """SPEC 48: la entrada búsqueda-first persiste el modo carrito."""

    def setUp(self):
        super().setUp()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        self.controller = ChatbotCartController()
        self.session = self.env['chatbot.session'].sudo()

    def _respuestas_buscador(self):
        return self.controller._respuesta_buscador(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')

    def test_01_buscador_activa_modo_carrito(self):
        self.controller._respuesta_buscador(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertTrue(self.session._esta_en_modo_carrito(self.session_id))

    def test_02_buscador_conserva_items(self):
        self.env['chatbot.session'].sudo()._guardar_carrito(
            self.session_id,
            {'items': [{'product_id': self.product_a.id, 'qty': 2}],
             'ultima_busqueda': []})
        self.controller._respuesta_buscador(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        carrito = self.session._get_carrito(self.session_id)
        self.assertEqual(len(carrito['items']), 1)
        self.assertEqual(carrito['items'][0]['product_id'], self.product_a.id)
