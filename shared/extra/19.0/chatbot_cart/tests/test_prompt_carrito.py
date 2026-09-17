from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestPromptCarrito(BaseChatbotCartTestCase):

    def test_01_append_agrega_instrucciones(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import (
            _FLOW_CARTO,
            append_cart_instructions,
            render_instrucciones_carrito,
        )
        bloque = render_instrucciones_carrito()
        self.assertIn('=== CARRITO DE COMPRA ===', bloque)
        self.assertIn(f'flow_name="{_FLOW_CARTO}"', bloque)
        self.assertIn(f'equipo_asignado="{_FLOW_CARTO}"', bloque)
        self.assertIn('/chatbot_cart/procesar', bloque)
        self.assertIn('PRIORIDAD sobre la REGLA 3', bloque)

        prompt = '=== ESQUELETO ==='
        nuevo = append_cart_instructions(prompt)
        self.assertTrue(nuevo.startswith('=== CARRITO DE COMPRA ==='))
        self.assertIn('=== ESQUELETO ===', nuevo)

    def test_02_append_no_duplica(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import append_cart_instructions
        prompt = 'x' * 10
        nuevo = append_cart_instructions(prompt)
        nuevo2 = append_cart_instructions(nuevo)
        self.assertEqual(nuevo, nuevo2)
        self.assertEqual(nuevo.count('=== CARRITO DE COMPRA ==='), 1)

    def test_03_append_prompt_vacio(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import append_cart_instructions
        self.assertEqual(append_cart_instructions(''), '')
        self.assertEqual(append_cart_instructions(None), None)

    def test_04_sin_url_no_hay_anuncio(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import render_instrucciones_carrito
        bloque = render_instrucciones_carrito()
        self.assertNotIn('Escribe «carrito»', bloque)
        self.assertNotIn('Visita nuestra tienda online', bloque)
        self.assertNotIn('termina SIEMPRE con esta línea exacta', bloque)

    def test_05_con_url_anuncio_tienda(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import render_instrucciones_carrito
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('chatbot_cart.tienda_url', 'https://tienda.integraia.lat')
        bloque = render_instrucciones_carrito(self.env)
        self.assertIn('termina SIEMPRE con esta línea exacta', bloque)
        self.assertIn('❗ Visita nuestra tienda online: https://tienda.integraia.lat', bloque)
        self.assertNotIn('Escribe «carrito»', bloque)
        param.set_param('chatbot_cart.tienda_url', '')

    def test_06_disparo_por_palabra_clave(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import (
            _FLOW_CARTO,
            render_instrucciones_carrito,
        )
        bloque = render_instrucciones_carrito()
        self.assertIn('INMEDIATAMENTE', bloque)
        self.assertIn(f'flow_name="{_FLOW_CARTO}"', bloque)
        self.assertIn(f'equipo_asignado="{_FLOW_CARTO}"', bloque)
        self.assertIn('en cualquier turno', bloque)

    def test_07_prioridad_sobre_regla_3(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import render_instrucciones_carrito
        bloque = render_instrucciones_carrito()
        self.assertIn('PRIORIDAD sobre la REGLA 3', bloque)
        self.assertIn('sin Base_Conocimiento_RAG', bloque)