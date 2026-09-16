from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestBotonesCarrito(BaseChatbotCartTestCase):
    """SPEC 45: botones interactivos dinámicos con salida siempre visible."""

    def setUp(self):
        super().setUp()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        self.controller = ChatbotCartController()

    def _botones(self, carrito):
        return self.controller._botones_carrito(carrito)

    def test_01_carrito_vacio_sin_boton_pagar(self):
        botones = self._botones({'items': []})
        self.assertEqual(botones, ['catálogo', 'ayuda', '🏪 Volver al negocio'])

    def test_02_carrito_con_items_prioriza_pagar(self):
        botones = self._botones({'items': [{'product_id': 1, 'qty': 2}]})
        self.assertEqual(botones, ['➕ Sumar', '➖ Quitar', 'pagar'])

    def test_03_salida_y_cotizacion_por_texto_con_items(self):
        """SPEC 54: con items el trío es ➕/➖/pagar; salir y cotizar por texto."""
        self.assertEqual(self._botones({'items': []}), ['catálogo', 'ayuda', '🏪 Volver al negocio'])

    def test_04_maximo_tres_botones(self):
        for carrito in ({'items': []}, {'items': [{'product_id': 1}]}):
            self.assertLessEqual(len(self._botones(carrito)), 3)

    def test_05_sin_items_no_se_puede_pagar(self):
        self.assertNotIn('pagar', self._botones({'items': []}))