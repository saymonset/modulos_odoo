from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestPromptCarrito(BaseChatbotCartTestCase):

    def test_01_append_agrega_instrucciones(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import (
            append_cart_instructions,
            render_instrucciones_carrito,
        )
        bloque = render_instrucciones_carrito()
        self.assertIn('flujo_carrito_compra', bloque)
        self.assertIn('/chatbot_cart/procesar', bloque)
        self.assertNotIn('flujo_carrito\n', bloque)

        prompt = '=== ESQUELETO ==='
        nuevo = append_cart_instructions(prompt)
        self.assertIn('CARRITO DE COMPRAS', nuevo)
        self.assertIn('flujo_carrito_compra', nuevo)

    def test_02_append_no_duplica(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import append_cart_instructions
        prompt = 'x' * 10
        nuevo = append_cart_instructions(prompt)
        nuevo2 = append_cart_instructions(nuevo)
        self.assertEqual(nuevo, nuevo2)

    def test_03_append_prompt_vacio(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import append_cart_instructions
        self.assertEqual(append_cart_instructions(''), '')
        self.assertEqual(append_cart_instructions(None), None)