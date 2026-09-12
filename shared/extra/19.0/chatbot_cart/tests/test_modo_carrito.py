from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestAislamientoModos(BaseChatbotCartTestCase):
    """SPEC 34: aislamiento total entre modo carrito y modo negocio.

    - `_salir_modo_carrito` vuelve a NEGOCIO (conservando o vaciando items).
    - `_guardar_carrito` pone modo CARRITO; la salida pendiente 1/2/3 se resuelve.
    - Las preguntas de negocio en carrito devuelven la respuesta determinista
      que sugiere *salir* (sin RAG ni LLM).
    """

    def _session(self):
        return self.env['chatbot.session'].sudo()

    def test_01_guardar_carrito_pone_modo_carrito(self):
        self._agregar_producto(self.product_a.id, qty=1)
        self.assertTrue(self._session()._esta_en_modo_carrito(self.session_id))

    def test_02_salir_vacio_cambia_a_negocio(self):
        self._session()._guardar_carrito(self.session_id, {'items': [], 'ultima_busqueda': []})
        self.assertTrue(self._session()._esta_en_modo_carrito(self.session_id))
        self._session()._salir_modo_carrito(self.session_id, vaciar=False)
        self.assertFalse(self._session()._esta_en_modo_carrito(self.session_id))
        registro = self._session().search([('session_id', '=', self.session_id)], limit=1)
        self.assertEqual((registro.estado or {}).get('modo'), 'NEGOCIO')

    def test_03_salir_conservando_items(self):
        self._agregar_producto(self.product_a.id, qty=2)
        self._session()._salir_modo_carrito(self.session_id, vaciar=False)
        carrito = self._session()._get_carrito(self.session_id)
        self.assertEqual(len(carrito['items']), 1)
        self.assertFalse(self._session()._esta_en_modo_carrito(self.session_id))

    def test_04_salir_vaciando_quita_items(self):
        self._agregar_producto(self.product_a.id, qty=2)
        self._session()._salir_modo_carrito(self.session_id, vaciar=True)
        carrito = self._session()._get_carrito(self.session_id)
        self.assertEqual(len(carrito['items']), 0)
        self.assertFalse(self._session()._esta_en_modo_carrito(self.session_id))

    def test_05_salir_con_carrito_vacio_sale_directo(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        resp = ChatbotCartController()._salir_carrito(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertTrue(resp['finalizado'])
        self.assertIn('Saliste del carrito', resp['texto_para_usuario'])
        self.assertFalse(self._session()._esta_en_modo_carrito(self.session_id))

    def test_06_salir_con_items_pide_decision_y_guarda(self):
        self._agregar_producto(self.product_a.id, qty=1)
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        resp = ChatbotCartController()._salir_carrito(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertFalse(resp['finalizado'])
        self.assertIn('1', resp['texto_para_usuario'])
        carrito = self._session()._get_carrito(self.session_id)
        self.assertTrue(carrito.get('pendiente_salida'))

        # Resolver opción 1: guardar y salir
        resp2 = ChatbotCartController()._resolver_salida_pendiente(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '1')
        self.assertTrue(resp2['finalizado'])
        self.assertFalse(self._session()._esta_en_modo_carrito(self.session_id))
        carrito = self._session()._get_carrito(self.session_id)
        self.assertEqual(len(carrito['items']), 1)

    def test_07_opcion_2_vacia_y_sale(self):
        self._agregar_producto(self.product_a.id, qty=1)
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        ChatbotCartController()._salir_carrito(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp = ChatbotCartController()._resolver_salida_pendiente(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '2')
        self.assertTrue(resp['finalizado'])
        self.assertFalse(self._session()._esta_en_modo_carrito(self.session_id))
        carrito = self._session()._get_carrito(self.session_id)
        self.assertEqual(len(carrito['items']), 0)

    def test_08_opcion_3_sigue_comprando(self):
        self._agregar_producto(self.product_a.id, qty=1)
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        ChatbotCartController()._salir_carrito(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp = ChatbotCartController()._resolver_salida_pendiente(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '3')
        self.assertFalse(resp['finalizado'])
        self.assertTrue(self._session()._esta_en_modo_carrito(self.session_id))
        carrito = self._session()._get_carrito(self.session_id)
        self.assertNotIn('pendiente_salida', carrito)

    def test_09_negocio_responde_determinista_sin_llm(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        resp = ChatbotCartController()._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'DESCONOCIDA', '', 0, [])
        self.assertIn('Estás de compras', resp['texto_para_usuario'])
        self.assertIn('salir', resp['texto_para_usuario'])

    def test_10_salir_reconocido_por_clasificador(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        for texto in ('salir', 'cancelar', 'menú principal', 'volver', 'dejar carrito'):
            res = ClasificarAccionCarritoUseCase._clasificar_fallback(texto)
            self.assertEqual(res[0]['accion'], 'SALIR', f'falla con: {texto}')