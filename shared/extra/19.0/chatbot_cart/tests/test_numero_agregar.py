from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestSeleccionNumerica(BaseChatbotCartTestCase):
    """SPEC 38: responder el número de la lista mostrada agrega el producto."""

    def setUp(self):
        super().setUp()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        self.controller = ChatbotCartController()
        self.ultima_busqueda = [
            {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'default_code': self.product_a.default_code or '',
                'price_usd': 6.50,
                'image_url': '',
            },
            {
                'product_id': self.product_b.id,
                'name': self.product_b.name,
                'default_code': self.product_b.default_code or '',
                'price_usd': 7.00,
                'image_url': '',
            },
        ]

    # --- _es_seleccion_numerica ---

    def test_01_helper_reconoce_numeros(self):
        self.assertEqual(self.controller._es_seleccion_numerica('2'), '2')
        self.assertEqual(self.controller._es_seleccion_numerica('el 2'), '2')
        self.assertEqual(self.controller._es_seleccion_numerica('EL 2'), '2')
        self.assertEqual(self.controller._es_seleccion_numerica('12'), '12')
        self.assertEqual(self.controller._es_seleccion_numerica(' El 1 '), '1')

    def test_02_helper_rechaza_no_numericos(self):
        for texto in ('quiero 2 pizzas', 'catálogo', '', '2 pizzas', 'pizzas 2', '123', 'el dos'):
            self.assertIsNone(self.controller._es_seleccion_numerica(texto), texto)

    # --- _decision_seleccion_numerica ---

    def test_03_decision_agregar(self):
        self.assertEqual(
            self.controller._decision_seleccion_numerica('2', self.ultima_busqueda),
            ('AGREGAR', '2', 1))

    def test_04_decision_sin_lista(self):
        self.assertEqual(
            self.controller._decision_seleccion_numerica('2', []),
            ('SIN_LISTA', None, 1))

    def test_05_decision_fuera_de_rango(self):
        self.assertEqual(
            self.controller._decision_seleccion_numerica('7', self.ultima_busqueda),
            ('FUERA_RANGO', 2, 1))

    def test_06_decision_no_numero(self):
        self.assertIsNone(
            self.controller._decision_seleccion_numerica('pagar', self.ultima_busqueda))

    # --- resolución y flujo AGREGAR ---

    def test_07_resuelve_item_por_numero(self):
        pid, mensaje = self.controller._resolver_producto(
            self.env, self.session_id, '1', self.ultima_busqueda)
        self.assertEqual(pid, self.product_a.id)
        self.assertEqual(mensaje, "")
        pid, _ = self.controller._resolver_producto(
            self.env, self.session_id, '2', self.ultima_busqueda)
        self.assertEqual(pid, self.product_b.id)

    def test_08_agregar_por_numero(self):
        """El flujo del pre-check: AGREGAR el item 2 con cantidad 1."""
        resp = self.controller._ejecutar_item(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'AGREGAR', '2', 1, self.ultima_busqueda)
        self.assertTrue(resp['success'])
        self.assertIn('Agregué', resp['texto_para_usuario'])
        # SPEC 56: con items el 3er botón es Pagar (catálogo por texto)
        self.assertEqual(resp['botones'],
                         ['➕ Sumar', '➖ Quitar', '💳 Pagar'])

        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        self.assertEqual(resumen['count'], 1)
        self.assertEqual(resumen['items'][0]['product_id'], self.product_b.id)
        self.assertEqual(resumen['items'][0]['qty'], 1)

    # --- regresiones ---

    def test_09_salida_pendiente_prevalece(self):
        """SPEC 34: con salida pendiente, "2" resuelve la salida — el pre-check
        numérico no debe agregar (va después de pendiente_salida)."""
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        session = self.env['chatbot.session'].sudo()
        carrito = session._get_carrito(self.session_id)
        carrito['pendiente_salida'] = True
        session._guardar_carrito(self.session_id, carrito)

        resp = self.controller._resolver_salida_pendiente(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '2')
        self.assertTrue(resp)
        self.assertTrue(resp['finalizado'])
        self.assertEqual(CartService().resumen(self.env, self.session_id)['count'], 0)

    def test_10_regresion_comandos_deterministas(self):
        """El clasificador sigue intacto para los comandos conocidos."""
        use_case = self.env['clasificar.accion.carrito.use.case']

        def clasificar(texto):
            return use_case.execute({'texto_usuario': texto})

        self.assertEqual(clasificar('ver carrito')['accion'], 'CONSULTAR')
        self.assertEqual(clasificar('pagar')['accion'], 'PAGAR')
        self.assertEqual(clasificar('catálogo')['accion'], 'CATALOGO')
        self.assertEqual(clasificar('agrega 2 camisas')['accion'], 'AGREGAR')
        self.assertEqual(clasificar('salir')['accion'], 'SALIR')
