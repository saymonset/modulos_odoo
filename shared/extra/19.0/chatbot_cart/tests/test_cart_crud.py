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


@tagged("-at_install", "post_install")
class TestUltimaBusqueda(BaseChatbotCartTestCase):
    """Fix: buscar guarda ultima_busqueda para resolver por número."""

    def test_20_buscar_guarda_ultima_busqueda(self):
        self._configurar_tasas(bcv_rate=20.0)
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import ChatbotCartController
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        ChatbotCartController()._ejecutar(
            self.env, self.session_id, None, None, 'whatsapp',
            'BUSCAR', 'CAM-R', 0, [])
        carrito = CartService().consultar(self.env, self.session_id)
        self.assertEqual(len(carrito['ultima_busqueda']), 1)
        self.assertEqual(carrito['ultima_busqueda'][0]['product_id'], self.product_a.id)
        self.assertEqual(carrito['ultima_busqueda'][0]['name'], 'Camisa Roja')

    def test_21_referencia_numerica_resuelve_producto(self):
        ultima_busqueda = [
            {'product_id': self.product_a.id, 'name': 'Camisa Roja', 'price_usd': 6.50},
            {'product_id': self.product_b.id, 'name': 'Camisa Azul', 'price_usd': 7.00},
        ]
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import ChatbotCartController
        product_id, mensaje = ChatbotCartController()._resolver_producto(
            self.env, self.session_id, '2', ultima_busqueda)
        self.assertEqual(product_id, self.product_b.id)
        self.assertEqual(mensaje, '')


@tagged("-at_install", "post_install")
class TestResolverPartner(BaseChatbotCartTestCase):
    """Fix: resolver partner por sesión, nunca por historial global."""

    def test_22_partner_generico_sin_telefono(self):
        partner = self.env['sale.order'].sudo()._resolver_partner(self.session_id)
        self.assertEqual(partner.name, f'Cliente Chatbot {self.session_id}')
        self.assertFalse(partner.phone)

    def test_23_partner_desde_telefono_capturado_en_sesion(self):
        self.env['chatbot.session'].sudo().create({
            'session_id': self.session_id,
            'estado': {'datos_paciente': {'solicitar_phone': '+584121234567'}},
        })
        partner = self.env['sale.order'].sudo()._resolver_partner(self.session_id)
        self.assertEqual(partner.phone, '+584121234567')

    def test_24_telefono_explicito_gana_al_de_sesion(self):
        self.env['chatbot.session'].sudo().create({
            'session_id': self.session_id,
            'estado': {'datos_paciente': {'solicitar_phone': '+584120000000'}},
        })
        partner = self.env['sale.order'].sudo()._resolver_partner(
            self.session_id, phone='+584121234567')
        self.assertEqual(partner.phone, '+584121234567')


@tagged("-at_install", "post_install")
class TestGateCarrito(BaseChatbotCartTestCase):
    """SPEC 29: gate de disponibilidad del carrito (productos + flujo activo)."""

    def test_25_disponible_true_con_productos(self):
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        self.assertTrue(CartService.disponible(self.env))

    def test_26_gate_false_si_flujo_inactivo(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import carrito_disponible
        flujo = self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search(
            [('name', '=', 'flujo_carrito_compra')], limit=1)
        self.assertTrue(flujo, 'flujo_carrito_compra debe existir')
        flujo.sudo().write({'active': False})
        self.assertFalse(carrito_disponible(self.env))

    def test_27_gate_true_si_flujo_activo(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import carrito_disponible
        flujo = self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search(
            [('name', '=', 'flujo_carrito_compra')], limit=1)
        self.assertTrue(flujo, 'flujo_carrito_compra debe existir')
        flujo.sudo().write({'active': True})
        self.assertTrue(carrito_disponible(self.env))


@tagged("-at_install", "post_install")
class TestBottonCarrito(BaseChatbotCartTestCase):
    """SPEC 30: toggle 'Activar/Desactivar carrito' en la ficha del cliente."""

    def _flujo_carrito(self):
        return self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search(
            [('name', '=', 'flujo_carrito_compra')], limit=1)

    def test_28_activa_y_marca_en_flujo_ids(self):
        flujo = self._flujo_carrito()
        self.assertTrue(flujo, 'flujo_carrito_compra debe existir')
        flujo.write({'active': False})
        config = self.env['chatbot.config'].sudo().create(
            {'name': 'Cliente Test Boton'})
        config.action_activar_carrito()
        self.assertTrue(flujo.active)
        self.assertIn(flujo, config.flujo_ids)

    def test_29_desactiva_y_desmarca(self):
        flujo = self._flujo_carrito()
        self.assertTrue(flujo)
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Boton Off',
            'flujo_ids': [(6, 0, flujo.ids)],
        })
        flujo.write({'active': True})
        config.action_activar_carrito()
        self.assertFalse(flujo.active)
        self.assertNotIn(flujo, config.flujo_ids)

    def test_30_gate_sin_productos_aborta(self):
        from unittest.mock import patch
        flujo = self._flujo_carrito()
        self.assertTrue(flujo)
        flujo.write({'active': False})
        config = self.env['chatbot.config'].sudo().create(
            {'name': 'Cliente Test Sin Prod'})
        with patch(
                'odoo.addons.chatbot_cart.services.cart_service.'
                'CartService.disponible',
                return_value=False):
            res = config.action_activar_carrito()
        self.assertFalse(flujo.active)
        self.assertNotIn(flujo, config.flujo_ids)
        self.assertEqual(res['params']['type'], 'warning')

    def test_31_flujo_inexistente_se_recrea(self):
        flujo = self._flujo_carrito()
        if flujo:
            flujo.unlink()
        config = self.env['chatbot.config'].sudo().create(
            {'name': 'Cliente Test Recrea'})
        config.action_activar_carrito()
        flujo = self._flujo_carrito()
        self.assertTrue(flujo)
        self.assertTrue(flujo.active)
        self.assertFalse(flujo.generar_pasos_automatico)
        self.assertEqual(flujo.politica_inicio, 'confirmation')

    def test_32_computed_activo_correcto(self):
        flujo = self._flujo_carrito()
        self.assertTrue(flujo)
        config = self.env['chatbot.config'].sudo().create(
            {'name': 'Cliente Test Computed'})
        flujo.write({'active': False})
        config.invalidate_recordset()
        self.assertFalse(config.carrito_compra_activo)
        flujo.write({'active': True})
        config.invalidate_recordset()
        self.assertTrue(config.carrito_compra_activo)