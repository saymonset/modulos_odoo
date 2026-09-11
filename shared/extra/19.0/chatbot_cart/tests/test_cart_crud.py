from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestCartCrud(BaseChatbotCartTestCase):

    def test_01_agregar_producto_nuevo(self):
        self._configurar_tasas(bcv_rate=20.0)
        result = self._agregar_producto(self.product_a.id, qty=2)
        self.assertTrue(result['success'])
        carrito = result['carrito']
        self.assertEqual(len(carrito['items']), 1)
        item = carrito['items'][0]
        self.assertEqual(item['product_id'], self.product_a.id)
        self.assertEqual(item['qty'], 2)
        self.assertEqual(item['price_usd'], 6.50)
        self.assertEqual(item['price_ves'], 130.0)

    def test_02_agregar_producto_ya_existente_suma_cantidad(self):
        self._agregar_producto(self.product_a.id, qty=1)
        result = self._agregar_producto(self.product_a.id, qty=3)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['carrito']['items']), 1)
        self.assertEqual(result['carrito']['items'][0]['qty'], 4)

    def test_03_agregar_producto_inexistente_falla(self):
        self._configurar_tasas(bcv_rate=20.0)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        result = CartService().agregar(self.env, self.session_id, 999999, 1)
        self.assertFalse(result['success'])

    def test_04_quitar_producto(self):
        self._agregar_producto(self.product_a.id, qty=2)
        self._agregar_producto(self.product_b.id, qty=1)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        result = CartService().quitar(self.env, self.session_id, self.product_a.id)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['carrito']['items']), 1)
        self.assertEqual(result['carrito']['items'][0]['product_id'], self.product_b.id)

    def test_05_quitar_producto_no_en_carrito_falla(self):
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        result = CartService().quitar(self.env, self.session_id, self.product_a.id)
        self.assertFalse(result['success'])

    def test_06_modificar_cantidad(self):
        self._agregar_producto(self.product_a.id, qty=2)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        result = CartService().modificar(self.env, self.session_id, self.product_a.id, 5)
        self.assertTrue(result['success'])
        self.assertEqual(result['carrito']['items'][0]['qty'], 5)

    def test_07_modificar_cantidad_cero_elimina(self):
        self._agregar_producto(self.product_a.id, qty=2)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        result = CartService().modificar(self.env, self.session_id, self.product_a.id, 0)
        self.assertTrue(result['success'])
        self.assertEqual(len(result['carrito']['items']), 0)

    def test_08_consultar_carrito_vacio(self):
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        carrito = CartService().consultar(self.env, self.session_id)
        self.assertEqual(carrito['items'], [])


@tagged("-at_install", "post_install")
class TestCartResumen(BaseChatbotCartTestCase):

    def test_09_resumen_totales_ves_usd(self):
        self._configurar_tasas(bcv_rate=20.0, cop_show=False)
        self._agregar_producto(self.product_a.id, qty=2)  # 130 Bs / 6.50 USD
        self._agregar_producto(self.product_b.id, qty=1)  # 140 Bs / 7.00 USD
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        self.assertEqual(resumen['total_ves'], 400.0)
        self.assertEqual(resumen['total_usd'], 20.0)
        self.assertEqual(resumen['count'], 2)
        self.assertFalse(resumen['show_cop'])

    def test_10_resumen_sin_cop_no_incluye_totales(self):
        self._configurar_tasas(bcv_rate=20.0, cop_show=False)
        self._agregar_producto(self.product_a.id, qty=1)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        self.assertFalse(resumen['show_cop'])
        self.assertEqual(resumen['total_cop'], 0.0)
        texto = CartService().formato_resumen_amigable(self.env, self.session_id)
        self.assertNotIn('COP', texto)

    def test_11_resumen_con_cop_incluye_totales(self):
        self._configurar_tasas(bcv_rate=20.0, cop_rate=1000.0, cop_show=True)
        self._agregar_producto(self.product_a.id, qty=1)  # 6.50 USD * 1000 = 6500 COP
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        self.assertTrue(resumen['show_cop'])
        self.assertEqual(resumen['total_cop'], 6500.0)
        texto = CartService().formato_resumen_amigable(self.env, self.session_id)
        self.assertIn('COP', texto)

    def test_12_resumen_carrito_vacio(self):
        self._configurar_tasas(bcv_rate=20.0, cop_show=False)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        self.assertEqual(resumen['count'], 0)
        self.assertEqual(resumen['total_usd'], 0.0)


@tagged("-at_install", "post_install")
class TestBuscarProductos(BaseChatbotCartTestCase):

    def test_13_buscar_por_nombre(self):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        result = ProductBuscarService().buscar(self.env, 'camisa')
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['count'], 1)
        nombres = [p['name'] for p in result['productos']]
        self.assertIn('Camisa Roja', nombres)

    def test_14_buscar_por_codigo(self):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        result = ProductBuscarService().buscar(self.env, 'CAM-R')
        self.assertTrue(result['success'])
        self.assertEqual(result['productos'][0]['default_code'], 'CAM-R')

    def test_15_buscar_sin_resultados(self):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        result = ProductBuscarService().buscar(self.env, 'zzznoexiste')
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 0)

    def test_16_buscar_consulta_vacia(self):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        result = ProductBuscarService().buscar(self.env, '   ')
        self.assertFalse(result['success'])


@tagged("-at_install", "post_install")
class TestMaterializarOrden(BaseChatbotCartTestCase):

    def test_17_materializar_orden_desde_carrito(self):
        self._configurar_tasas(bcv_rate=20.0, cop_show=False)
        self._agregar_producto(self.product_a.id, qty=2)
        self._agregar_producto(self.product_b.id, qty=1)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        order = self.env['sale.order'].sudo()._materializar_desde_carrito(
            self.session_id, phone='+584121234567', platform='whatsapp')
        self.assertTrue(order)
        self.assertEqual(order.state, 'sale')
        self.assertEqual(len(order.order_line), 2)
        # El carrito se limpia tras materializar
        carrito = CartService().consultar(self.env, self.session_id)
        self.assertEqual(carrito['items'], [])

    def test_18_materializar_carrito_vacio_devuelve_false(self):
        order = self.env['sale.order'].sudo()._materializar_desde_carrito(
            self.session_id, phone='+584121234567')
        self.assertFalse(order)

    def test_19_partner_resuelto_por_telefono(self):
        self._configurar_tasas(bcv_rate=20.0, cop_show=False)
        self._agregar_producto(self.product_a.id, qty=1)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        order = self.env['sale.order'].sudo()._materializar_desde_carrito(
            self.session_id, phone='+584121234567')
        self.assertTrue(order)
        self.assertEqual(order.partner_id.phone, '+584121234567')