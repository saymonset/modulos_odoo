from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestCatalogoEscalable(BaseChatbotCartTestCase):
    """SPEC 40: búsqueda-first con umbral + categorías + búsqueda multi-término."""

    def setUp(self):
        super().setUp()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        from odoo.addons.chatbot_cart.services.product_buscar import (
            ProductBuscarService,
        )
        self.controller = ChatbotCartController()
        self.search = ProductBuscarService()
        self.categ_bebidas = self.env['product.category'].create({'name': 'Bebidas Test'})
        self.env['product.product'].create({
            'name': 'Café Frío', 'categ_id': self.categ_bebidas.id,
            'list_price': 5.0, 'list_price_usd': 0.5, 'type': 'consu',
            'sale_ok': True, 'taxes_id': False, 'supplier_taxes_id': False,
        })

    def _crear_productos(self, n, prefijo='Producto'):
        Product = self.env['product.product']
        for i in range(n):
            Product.create({
                'name': f'{prefijo} {i:02d}', 'list_price': 10.0 + i,
                'type': 'consu', 'sale_ok': True, 'taxes_id': False,
                'supplier_taxes_id': False,
            })

    # --- umbral de escalabilidad ---

    def test_01_umbral_pequeno_catalogo_clasico(self):
        resp = self.controller._mostrar_catalogo(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', offset=0)
        self.assertIn('Catálogo', resp['texto_para_usuario'])
        self.assertNotIn('lista_categorias', resp)

    def test_02_umbral_grande_buscador_con_categorias(self):
        self._crear_productos(11)
        resp = self.controller._mostrar_catalogo(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', offset=0)
        self.assertIn('Tenemos', resp['texto_para_usuario'])
        self.assertIn('lista_categorias', resp)
        lista = resp['lista_categorias']
        self.assertEqual(lista['button'], 'Ver categorías')
        self.assertTrue(lista['sections'][0]['rows'])
        self.assertEqual(resp['botones'], self.controller.BOTONES_CARRITO)

    def test_03_umbral_grande_paginacion_respaldo(self):
        self._crear_productos(11)
        resp = self.controller._mostrar_catalogo(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', offset=5)
        self.assertIn('Catálogo', resp['texto_para_usuario'])

    # --- categorías ---

    def test_04_categorias_con_conteo(self):
        filas = self.search.categorias_con_conteo(self.env)
        self.assertTrue(filas)
        self.assertTrue(all(len(f['title']) <= 24 for f in filas))
        self.assertEqual(fila_bebidas := next(
            f for f in filas if f['id'] == str(self.categ_bebidas.id)
        )['description'], '1 productos')

    def test_05_precheck_categoria_por_nombre(self):
        self.assertEqual(
            self.controller._categoria_por_nombre(self.env, 'Bebidas Test'),
            self.categ_bebidas.id)
        self.assertIsNone(self.controller._categoria_por_nombre(self.env, 'pagar'))
        self.assertIsNone(self.controller._categoria_por_nombre(self.env, '2'))
        self.assertIsNone(self.controller._categoria_por_nombre(self.env, 'ver carrito'))
        self.assertIsNone(self.controller._categoria_por_nombre(self.env, 'agrega'))
        self.assertIsNone(self.controller._categoria_por_nombre(self.env, 'producto inexistente'))

    def test_06_precheck_titulo_recortado_roundtrip(self):
        categ_larga = self.env['product.category'].create(
            {'name': 'Categoría Muy Larga Que Supera Veinticuatro'})
        self.env['product.product'].create({
            'name': 'Producto Largo', 'categ_id': categ_larga.id,
            'list_price': 1.0, 'type': 'consu', 'sale_ok': True,
            'taxes_id': False, 'supplier_taxes_id': False,
        })
        filas = self.search.categorias_con_conteo(self.env)
        fila = next(f for f in filas if f['id'] == str(categ_larga.id))
        # el título que ve el usuario en la lista roundtrip contra el pre-check
        self.assertEqual(
            self.controller._categoria_por_nombre(self.env, fila['title']),
            categ_larga.id)

    def test_07_catalogo_por_categoria(self):
        result = self.search.catalogo_por_categoria(
            self.env, self.categ_bebidas.id, offset=0)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['productos'][0]['name'], 'Café Frío')

    def test_08_seleccion_categoria_flujo_completo(self):
        self._crear_productos(11)
        resp = self.controller._mostrar_catalogo_categoria(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            self.categ_bebidas.id, offset=0)
        self.assertIn('Catálogo', resp['texto_para_usuario'])
        self.assertIn('Café Frío', resp['texto_para_usuario'])
        session = self.env['chatbot.session'].sudo().search(
            [('session_id', '=', self.session_id)], limit=1)
        ultima = (session.estado or {}).get('carrito', {}).get('ultima_busqueda', [])
        self.assertEqual(len(ultima), 1)
        self.assertEqual(ultima[0]['name'], 'Café Frío')

    # --- búsqueda multi-término ---

    def test_09_busqueda_multi_palabra(self):
        result = self.search.buscar(self.env, 'camisa roja')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['productos'][0]['name'], 'Camisa Roja')
        self.assertEqual(result['total_coincidencias'], 1)

    def test_10_busqueda_sin_acentos(self):
        self.env['product.product'].create({
            'name': 'Café Mozzarella Andino', 'list_price': 3.0,
            'type': 'consu', 'sale_ok': True, 'taxes_id': False,
            'supplier_taxes_id': False,
        })
        result = self.search.buscar(self.env, 'cafe mozzarella')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['productos'][0]['name'], 'Café Mozzarella Andino')

    def test_11_busqueda_mas_resultados_que_limite(self):
        self._crear_productos(8, prefijo='Refresco Test')
        result = self.search.buscar(self.env, 'refresco test', limit=5)
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['total_coincidencias'], 8)
        texto = self.search.formato_lista_productos(result)
        self.assertIn('mostrando 5', texto)

    # --- regresión SPEC 38 (el número sigue agregando tras ver lista) ---

    def test_12_regresion_numero_con_ultima_busqueda(self):
        self.controller._mostrar_catalogo(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', offset=0)
        decision = self.controller._decision_seleccion_numerica(
            '1', [{'product_id': self.product_a.id}])
        self.assertEqual(decision, ('AGREGAR', '1'))
