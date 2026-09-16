from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestMundoCarrito(BaseChatbotCartTestCase):
    """SPEC 49: mundo carrito separado — FALLBACK, IA solo-carrito,
    salida directa y catálogo clásico."""

    def _controller(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        return ChatbotCartController()

    # --- clasificador ---

    def test_01_texto_extra_clasifica_fallback(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        res = ClasificarAccionCarritoUseCase._clasificar_fallback(
            '¿dime el precio de una reparación?')
        self.assertEqual(res[0]['accion'], 'FALLBACK')

    # --- IA solo-carrito ---

    def _patch_ia(self, respuesta=None):
        if respuesta is None:
            respuesta = '🛒 En el carrito solo gestiono compras: escribe *catálogo* o *salir*.'
        from unittest.mock import patch
        gpt = self.env['gpt.service'].sudo()
        fake_config = type('Cfg', (), {
            'api_key': 'test-key', 'default_model': 'gpt-test'})()
        fake_resp = type('Resp', (), {'choices': [
            type('C', (), {'message': type('M', (), {'content': respuesta})()})()]
        })()
        fake_client = type('Client', (), {})()
        fake_client.chat = type('Chat', (), {})()
        fake_client.chat.completions = type('Compl', (), {})()
        fake_client.chat.completions.create = staticmethod(
            lambda **kw: fake_resp)
        return patch.multiple(
            type(gpt),
            _get_openai_config=lambda self: fake_config,
            _get_openai_client=lambda self, cfg: fake_client,
        )

    def test_02_fallback_con_ia_responde_mundo_carrito(self):
        controller = self._controller()
        with self._patch_ia():
            resp = controller._atender_fallback_ia(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                '¿dime el precio de una reparación?')
        self.assertIn('carrito', resp['texto_para_usuario'].lower())
        self.assertEqual(resp['botones'], ['catálogo', 'ayuda', '🏪 Volver al negocio'])

    def test_03_fallback_sin_ia_responde_generico(self):
        controller = self._controller()
        from unittest.mock import patch
        with patch.object(
                type(self.env['gpt.service'].sudo()), '_get_openai_config',
                side_effect=Exception('sin config')):
            resp = controller._atender_fallback_ia(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'hola')
        self.assertIn('Estás de compras', resp['texto_para_usuario'])
        self.assertIn('salir', resp['texto_para_usuario'])

    # --- salida directa ---

    def test_04_salir_con_items_directo_y_intactos(self):
        self._agregar_producto(self.product_a.id, qty=2)
        session = self.env['chatbot.session'].sudo()
        resp = self._controller()._salir_carrito(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertTrue(resp['finalizado'])
        self.assertIn('Volvemos al negocio', resp['texto_para_usuario'])
        self.assertIn('1 item(s)', resp['texto_para_usuario'])
        self.assertFalse(session._esta_en_modo_carrito(self.session_id))
        carrito = session._get_carrito(self.session_id)
        self.assertEqual(carrito['items'][0]['product_id'], self.product_a.id)
        self.assertNotIn('pendiente_salida', carrito)

    # --- catálogo clásico vs buscador en activación ---

    def _crear_productos(self, n):
        Product = self.env['product.product']
        for i in range(n):
            Product.create({
                'name': f'Refresco Test {i:02d}', 'list_price': 5.0,
                'type': 'consu', 'sale_ok': True,
                'taxes_id': False, 'supplier_taxes_id': False,
            })

    def test_05_catalogo_explicito_es_lista_clasica(self):
        self._crear_productos(11)
        resp = self._controller()._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        self.assertIn('Catálogo', resp['texto_para_usuario'])
        self.assertIn('1.', resp['texto_para_usuario'])
        self.assertNotIn('Tenemos', resp['texto_para_usuario'])

    def test_06_activacion_consultar_vacio_usa_buscador(self):
        self._crear_productos(11)
        resp = self._controller()._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        self.assertIn('Tenemos', resp['texto_para_usuario'])
        self.assertTrue(self.env['chatbot.session'].sudo()._esta_en_modo_carrito(
            self.session_id))
