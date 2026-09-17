from unittest.mock import patch

from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestAjusteCarrito(BaseChatbotCartTestCase):
    """SPEC 54: ➕/➖ por número y seleccionado, caption con estado del
    carrito, cap de inventario al sumar y ➖ a 0 elimina."""

    def _controller(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        return ChatbotCartController()

    def _carrito_flags(self):
        return self.env['chatbot.session'].sudo()._get_carrito(self.session_id)

    def _lista_ejemplo(self):
        return [
            {'product_id': self.product_a.id, 'name': self.product_a.name,
             'default_code': 'CAM-R', 'price_usd': 6.5, 'price_ves': 130.0,
             'has_image': True, 'image_url': 'https://x/cam-r.png'},
            {'product_id': self.product_b.id, 'name': self.product_b.name,
             'default_code': 'CAM-A', 'price_usd': 7.0, 'price_ves': 140.0,
             'has_image': True, 'image_url': 'https://x/cam-a.png'},
        ]

    # --- parse determinista número + signo ---

    def test_01_parse_mas_menos(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController as C,
        )
        self.assertEqual(C._decision_mas_menos('1 ➕'), ('SUMAR', '1'))
        self.assertEqual(C._decision_mas_menos('➕ 2'), ('SUMAR', '2'))
        self.assertEqual(C._decision_mas_menos('➕'), ('SUMAR', None))
        self.assertEqual(C._decision_mas_menos('Sumar'), ('SUMAR', None))
        self.assertEqual(C._decision_mas_menos('1 ➖'), ('RESTAR', '1'))
        self.assertEqual(C._decision_mas_menos('➖'), ('RESTAR', None))
        self.assertEqual(C._decision_mas_menos('menos'), ('RESTAR', None))
        self.assertEqual(C._decision_mas_menos('➖ Quitar'), ('RESTAR', None))
        self.assertEqual(C._decision_mas_menos('➕ Sumar'), ('SUMAR', None))

    def test_02_sin_regresion_en_comandos(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController as C,
        )
        self.assertIsNone(C._decision_mas_menos('quitar 3'))
        self.assertIsNone(C._decision_mas_menos('ver carrito'))
        self.assertIsNone(C._decision_mas_menos('2'))
        self.assertIsNone(C._decision_mas_menos('quiero un 4'))
        self.assertIsNone(C._decision_mas_menos('Responde *1 ➕* para sumar'))

    def test_02b_eco_del_gateway_con_etiqueta(self):
        """FIX E2E: el gateway antepone el cuerpo del mensaje anterior."""
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController as C,
        )
        self.assertEqual(
            C._decision_mas_menos(
                '¡Hola! Estoy aquí para ayudarte. ¿Ver catálogo? ➕ Sumar'),
            ('SUMAR', None))
        self.assertEqual(
            C._decision_mas_menos(
                'Tu carrito:\n1. Aros x4 — $88.84\n➖ Quitar'),
            ('RESTAR', None))
        self.assertEqual(C._decision_mas_menos('$88.84 2 ➕'), ('SUMAR', '2'))
        self.assertIsNone(C._decision_mas_menos('precio $88.84 sin signo'))

    # --- 1 ➕ / 1 ➖ sobre el listado mostrado y el carrito ---

    def test_03_mas_con_indice_agrega_uno(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['ultima_busqueda'] = self._lista_ejemplo()
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        resp = controller._ajustar_cantidad(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'SUMAR', '1', carrito)
        self.assertIn('Sumé 1', resp['texto_para_usuario'])
        carrito = self._carrito_flags()
        self.assertEqual(carrito['items'][0]['qty'], 2)
        self.assertEqual(carrito['producto_seleccionado'], self.product_a.id)

    def test_04_menos_llega_a_cero_elimina(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['ultima_busqueda'] = self._lista_ejemplo()
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        resp = controller._ajustar_cantidad(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'RESTAR', '1', carrito)
        self.assertIn('Quité', resp['texto_para_usuario'])
        self.assertIn('catálogo', resp['texto_para_usuario'])
        self.assertEqual(self._carrito_flags()['items'], [])

    def test_05_sin_seleccion_y_un_solo_item_operan_directo(self):
        self._agregar_producto(self.product_a.id, qty=2)
        carrito = self._carrito_flags()
        carrito.pop('producto_seleccionado', None)
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        resp = self._controller()._ajustar_cantidad(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'SUMAR', None, self._carrito_flags())
        self.assertIn('Sumé 1', resp['texto_para_usuario'])
        self.assertEqual(
            self._carrito_flags()['items'][0]['qty'], 3)

    def test_06_seleccionado_sin_seleccion_previa(self):
        self._agregar_producto(self.product_a.id, qty=2)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['producto_seleccionado'] = self.product_b.id
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        resp = controller._ajustar_cantidad(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'SUMAR', None, self._carrito_flags())
        carrito = self._carrito_flags()
        # product_b no estaba: se agrega con qty 1 y queda seleccionado
        nuevo = [it for it in carrito['items']
                 if it['product_id'] == self.product_b.id]
        self.assertEqual(len(nuevo), 1)
        self.assertEqual(nuevo[0]['qty'], 1)

    # --- cap de inventario (solo type=='product') ---

    def test_07_cap_inventario_en_stockeable(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['producto_seleccionado'] = self.product_a.id
        with patch.object(type(controller), '_stock_libre', staticmethod(lambda p: 1)):
            resp = controller._ajustar_cantidad(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'SUMAR', None, carrito)
        self.assertIn('Solo quedan 1 de *Camisa Roja*', resp['texto_para_usuario'])
        self.assertEqual(self._carrito_flags()['items'][0]['qty'], 1)

    def test_08_cap_cero_sin_inventario(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['producto_seleccionado'] = self.product_a.id
        with patch.object(type(controller), '_stock_libre', staticmethod(lambda p: 0)):
            resp = controller._ajustar_cantidad(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'SUMAR', None, carrito)
        self.assertIn('Sin inventario', resp['texto_para_usuario'])
        self.assertEqual(self._carrito_flags()['items'][0]['qty'], 1)

    def test_09_stock_libre_none_para_consu(self):
        self.assertIsNone(self._controller()._stock_libre(self.product_a))
        self.assertIsNone(self._controller()._stock_libre(self.product_b))

    # --- caption con estado del carrito ---

    def test_10_caption_con_estado_del_carrito(self):
        self._agregar_producto(self.product_a.id, qty=3)
        controller = self._controller()
        carrito = self._carrito_flags()
        productos = self._lista_ejemplo()
        caps = {c['caption'] for c in controller._imagenes_de_productos(
            productos, con_numeros=True, items_carrito=carrito.get('items'))}
        # producto 1 (Camisa Roja) con qty, producto 2 sin (SPEC 57: el total
        # NO va en cada caption; solo el estado del producto individual)
        self.assertTrue(any('🛒 en tu carrito: 3 unid.' in c for c in caps
                            if c.startswith('1.')))
        self.assertFalse(any('🛒 Tu carrito: ' in c for c in caps))

    def test_11_pista_mas_menos_en_busqueda(self):
        controller = self._controller()
        with patch.object(type(controller), '_redactar',
                          lambda self, env, texto, contexto=None: texto):
            resp = controller._ejecutar(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'BUSCAR', 'camisa', 0, [])
        self.assertIn('1 ➕', resp['texto_para_usuario'])
        self.assertIn('1 ➖', resp['texto_para_usuario'])
        caps = resp.get('imagenes') or []
        self.assertTrue(all(
            any(s in c['caption'] for s in ('🛒', '(no está'))
            for c in caps if isinstance(c, dict) and c.get('caption')))