# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestSpec57CarritoSimple(BaseChatbotCartTestCase):
    """SPEC 57: carrito simple para usuarios no técnicos — "del N solo X",
    captions sin total duplicado, respuestas deterministas y List Message."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        cls.controller = ChatbotCartController()

    # --- "del N solo X" → MODIFICAR ---

    def _clasificar(self, texto):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        return ClasificarAccionCarritoUseCase._clasificar_fallback(texto)[0]

    def test_01_del_n_solo_x_es_modificar(self):
        r = self._clasificar('del 5 solo 4')
        self.assertEqual(r['accion'], 'MODIFICAR')
        self.assertEqual(r['producto'], '5')
        self.assertEqual(r['cantidad'], 4)

    def test_02_quiero_del_n_solo_x_es_modificar(self):
        r = self._clasificar('quiero del 5 solo 4')
        self.assertEqual(r['accion'], 'MODIFICAR')
        self.assertEqual(r['producto'], '5')
        self.assertEqual(r['cantidad'], 4)

    def test_03_agregar_normal_sigue_siendo_agregar(self):
        r = self._clasificar('quiero 2 camisas rojas')
        self.assertEqual(r['accion'], 'AGREGAR')

    # --- preguntas naturales → BUSCAR producto ---

    def test_09_preguntas_naturales_buscan_producto(self):
        for frase, prod in (('tienen pizzas', 'pizzas'),
                            ('tienen pizzas?', 'pizzas'),
                            ('venden pizzas?', 'pizzas'),
                            ('hay pizzas', 'pizzas'),
                            ('tienes camisas rojas?', 'camisas rojas'),
                            ('busco aros de hamburguesa', 'aros de hamburguesa')):
            r = self._clasificar(frase)
            self.assertEqual(r['accion'], 'BUSCAR', f'"{frase}" debe ser BUSCAR')
            self.assertEqual(r['producto'].strip(), prod, f'"{frase}" producto={prod}')

    def test_10_catalogo_general_sigue_siendo_catalogo(self):
        for frase in ('qué tienen', 'que tienen', 'tienen catalogo',
                      'qué venden', 'que venden'):
            r = self._clasificar(frase)
            self.assertEqual(r['accion'], 'CATALOGO', f'"{frase}" debe ser CATALOGO')

    def test_11_comandos_no_se_secuestran(self):
        for frase, accion in (('tienen carrito', 'CONSULTAR'),
                              ('tienes ayuda', 'AYUDA'),
                              ('hay más', 'CATALOGO')):
            r = self._clasificar(frase)
            self.assertEqual(r['accion'], accion, f'"{frase}" debe ser {accion}')

    # --- FALLBACK con botones fijos (sin ➕/➖/Pagar) ---

    def test_12_fallback_botones_fijos_aunque_carrito_con_items(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self.controller._atender_fallback_ia(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'tienen pizzas?')
        # Nunca ➕/➖/Pagar de items que el usuario no ve en este turno
        self.assertEqual(resp['botones'],
                         ['catálogo', 'ayuda', '🏪 Volver al negocio'])
        self.assertNotIn('➕ Sumar', resp['botones'])

    # --- captions sin total duplicado ---

    def test_04_caption_sin_total_duplicado(self):
        self._agregar_producto(self.product_a.id, qty=2)
        productos = [
            {'product_id': self.product_a.id, 'name': 'Camisa Roja',
             'price_ves': 5508.39, 'price_usd': 6.50, 'price_cop': 0.0,
             'show_cop': False, 'has_image': True, 'image_url': 'https://x/img'},
            {'product_id': self.product_b.id, 'name': 'Camisa Azul',
             'price_ves': 5932.11, 'price_usd': 7.00, 'price_cop': 0.0,
             'show_cop': False, 'has_image': True, 'image_url': 'https://x/2'},
        ]
        caps = [c['caption'] for c in self.controller._imagenes_de_productos(
            productos, con_numeros=True, items_carrito=[
                {'product_id': self.product_a.id, 'qty': 2}])]
        # solo el estado individual; jamás el total del carrito en cada caption
        self.assertTrue(any('🛒 en tu carrito: 2 unid.' in c for c in caps))
        self.assertFalse(any('🛒 Tu carrito: ' in c for c in caps))

    # --- respuesta AGREGAR determinista y minimalista ---

    def test_05_agregar_sin_ia_minimalista(self):
        resp = self.controller._ejecutar_item(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'AGREGAR', 'CAM-R', 2, [])
        texto = resp['texto_para_usuario']
        self.assertNotIn('¡Hola!', texto)
        self.assertNotIn('He agregado', texto)
        self.assertNotIn('Aquí tienes un resumen', texto)
        self.assertIn('agregado', texto)
        self.assertIn('Toca *💳 Pagar*', texto)

    # --- List Message del carrito (CONSULTAR) ---

    def test_06_consultar_devuelve_lista_interactiva(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        lista = resp['lista_carrito']
        self.assertEqual(lista['button'], 'Ver carrito')
        filas = lista['sections'][0]['rows']
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['id'], 'modificar_1')
        self.assertIn('2 unid.', filas[0]['description'])
        # texto mínimo con total, sin imágenes por item
        self.assertIn('$', resp['texto_para_usuario'])
        self.assertEqual(resp['imagenes'], [])
        # botones con pago (SPEC 56)
        self.assertEqual(resp['botones'], ['➕ Sumar', '➖ Quitar', '💳 Pagar'])

    def test_07_lista_pagina_con_mas(self):
        productos = [self.product_a, self.product_b]
        for i in range(12):
            p = productos[i % 2]
            # crear líneas distintas agregando productos variados
            otro = self.env['product.product'].create({
                'name': f'Prod {i}', 'default_code': f'PR-{i}',
                'list_price': 10.0 + i, 'list_price_usd': 1.0 + i / 10,
                'type': 'consu', 'sale_ok': True, 'taxes_id': False,
                'supplier_taxes_id': False,
            })
            self._agregar_producto(otro.id, qty=1)
        resumen = self.controller.CART_SERVICE.resumen(
            self.env, self.session_id)
        self.assertGreater(resumen['count'], 10)
        lista = self.controller._lista_interactiva_carrito(resumen, offset=0)
        filas = lista['sections'][0]['rows']
        # máx. 10 filas + fila "mas" para el resto
        self.assertLessEqual(len(filas), 11)
        self.assertTrue(any(f['id'] == 'mas' for f in filas))
        lista2 = self.controller._lista_interactiva_carrito(resumen, offset=10)
        self.assertFalse(any(f['id'] == 'mas' for f in lista2['sections'][0]['rows']))

    def test_08_tap_fila_modificar_resuelve(self):
        self._agregar_producto(self.product_a.id, qty=2)
        decision = self.controller._decision_fila_lista('modificar_1')
        self.assertEqual(decision, ('MODIFICAR', '1'))
        decision_mas = self.controller._decision_fila_lista('mas')
        self.assertEqual(decision_mas, ('MAS', None))
        self.assertIsNone(self.controller._decision_fila_lista('hola'))