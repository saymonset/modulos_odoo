from unittest.mock import patch

from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestCapturaGuiada(BaseChatbotCartTestCase):
    """SPEC 53: datos de cotización uno por turno, confirmación de frases
    ambiguas, anuncio de datos y menú post-agregar."""

    def _controller(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        return ChatbotCartController()

    def _carrito_flags(self):
        return self.env['chatbot.session'].sudo()._get_carrito(self.session_id)

    def _lista_ejemplo(self):
        """última búsqueda con ≥4 items simulada (ids reales de sesión)."""
        return [
            {'product_id': self.product_a.id, 'name': self.product_a.name,
             'default_code': 'CAM-R', 'price_usd': 6.5},
            {'product_id': self.product_b.id, 'name': self.product_b.name,
             'default_code': 'CAM-A', 'price_usd': 7.0},
        ]

    # --- clasificador: decisiones AMBIGUO (aún NADA agregado) ---

    def test_01_decision_ambigua_no_agrega(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController as C,
        )
        lista = [{'product_id': 1}, {'product_id': 2}]
        self.assertEqual(
            C._decision_seleccion_numerica('quiero un 4', lista), ('AMBIGUO', '4', None))
        self.assertEqual(
            C._decision_seleccion_numerica('un 4', lista), ('AMBIGUO', '4', None))
        self.assertEqual(
            C._decision_seleccion_numerica('quiero 4', lista), ('AMBIGUO', '4', None))
        # cantidad en palabras: también ambigua
        self.assertEqual(
            C._decision_seleccion_numerica('quiero cuatro', lista), ('AMBIGUO', None, 4))

    def test_02_explicitos_no_rompen_spec_52(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController as C,
        )
        lista = [{'product_id': 1}, {'product_id': 2}]
        self.assertEqual(C._decision_seleccion_numerica('4', lista), ('FUERA_RANGO', 2, 1))
        self.assertEqual(C._decision_seleccion_numerica('1, quiero 3', lista),
                         ('AGREGAR', '1', 3))
        self.assertEqual(C._decision_seleccion_numerica('del 2 quiero 5', lista),
                         ('AGREGAR', '2', 5))

    # --- pregunta ambigua: dos interpretaciones, nada en el carrito ---

    def test_03_ambiguo_muestra_opciones_y_no_agrega(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['ultima_busqueda'] = self._lista_ejemplo()
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        with patch.object(type(controller), '_redactar',
                          lambda self, env, texto, contexto=None: texto):
            resp = controller._preguntar_agregado_ambiguo(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                self._carrito_flags(), '4', None)
        texto = resp['texto_para_usuario']
        # con lista de 2 productos y "4" fuera de rango, solo es válida la
        # interpretación de cantidad sobre el producto único del carrito
        self.assertIn('4 unidades de Camisa Roja', texto)
        estado = self._carrito_flags().get('pendiente_confirmar')
        self.assertIsNotNone(estado)
        self.assertEqual(len(estado['opciones']), 1)
        # el carrito NO cambió: sigue exactamente 1 item con qty 1
        self.assertEqual(self._carrito_flags()['items'][0]['qty'], 1)

    def test_04_responder_1_agrega_cantidad_ambiguada(self):
        """opción '1' (4 unidades del producto único) ejecuta AGREGAR."""
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['ultima_busqueda'] = self._lista_ejemplo()
        carrito['pendiente_confirmar'] = {
            'opciones': [
                {'id': '1', 'tipo': 'AGREGAR', 'producto': 'Camisa Roja',
                 'cantidad': 4, 'etiqueta': '4 unidades de Camisa Roja'},
                {'id': '2', 'tipo': 'AGREGAR', 'producto': '1',
                 'cantidad': 1, 'etiqueta': '1 unidad del producto 1: Camisa Roja'},
            ],
            'pregunta': '¿Qué prefieres?',
        }
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        resp = controller._resolver_pendiente_confirmar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '1')
        self.assertIn('Agregué *Camisa Roja (4 unid.)*', resp['texto_para_usuario'])
        self.assertIn('Tu carrito:', resp['texto_para_usuario'])
        self.assertNotIn('pendiente_confirmar', self._carrito_flags())
        carrito = self._carrito_flags()
        self.assertEqual(carrito['items'][0]['qty'], 5)

    def test_05_cancelar_pendiente_no_agrega_nada(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        carrito = self._carrito_flags()
        carrito['pendiente_confirmar'] = {
            'opciones': [{'id': '1', 'tipo': 'AGREGAR', 'producto': '1',
                          'cantidad': 1, 'etiqueta': 'x'}],
            'pregunta': '¿Qué prefieres?',
        }
        self.env['chatbot.session'].sudo()._guardar_carrito(self.session_id, carrito)
        resp = controller._resolver_pendiente_confirmar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '🚫 Cancelar')
        self.assertIsNotNone(resp)
        self.assertNotIn('pendiente_confirmar', self._carrito_flags())
        self.assertEqual(self._carrito_flags()['items'][0]['qty'], 1)

    # --- anuncio de datos y un dato por turno ---

    def test_06_anuncio_de_datos_pide_solo_telefono(self):
        with patch.object(type(self._controller()), '_redactar',
                          lambda self, env, texto, contexto=None: texto):
            resp = self._controller()._pedir_email_cotizacion(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        texto = resp['texto_para_usuario'].lower()
        self.assertIn('te pediré unos datos', texto)
        self.assertIn('empezamos por tu teléfono', texto)
        # ya NO pide el correo en el mismo mensaje
        self.assertNotIn('nombre y correo del cliente', texto)

    def test_07_cliente_nuevo_un_dato_por_turno(self):
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp_tel = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '0499999999')
        self.assertIn('llamas', resp_tel['texto_para_usuario'].lower())
        self.assertNotIn('correo', resp_tel['texto_para_usuario'].lower())
        resp_nom = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'Ana Pérez')
        self.assertIn('correo', resp_nom['texto_para_usuario'].lower())
        self.assertNotIn('llamas', resp_nom['texto_para_usuario'].lower())

    # --- menú post-agregar ---

    def test_08_menu_post_agregar_lista_y_total(self):
        self._configurar_tasas(bcv_rate=20.0)
        with patch.object(type(self._controller()), '_redactar',
                          lambda self, env, texto, contexto=None: texto):
            resp = self._controller()._ejecutar_item(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'AGREGAR', 'CAM-R', 2, [])
        texto = resp['texto_para_usuario']
        self.assertIn('Tu carrito:', texto)
        self.assertIn('1. Camisa Roja — 2 unid.', texto)
        self.assertIn('Bs. 260.00', texto)
        self.assertIn('➕', texto)
        self.assertIn('➖', texto)

    def test_09_lista_compacta_con_cop(self):
        self._configurar_tasas(bcv_rate=20.0, cop_rate=1200.0, cop_show=True)
        self._agregar_producto(self.product_a.id, qty=2)
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        resumen = CartService().resumen(self.env, self.session_id)
        lista = self._controller()._lista_compacta_carrito(resumen)
        self.assertIn('1. Camisa Roja — 2 unid.', lista)
        self.assertIn('COP', lista)
