from unittest.mock import patch

from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestVendedorIA(BaseChatbotCartTestCase):
    """SPEC 50: redacción IA del vendedor, gate sin IA y rama cotización."""

    def _controller(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        return ChatbotCartController()

    def _patch_ia(self, contenido='🛒 Tengo lo que buscas, ¿quieres pagar ya?'):
        fake_config = type('Cfg', (), {'api_key': 'k', 'default_model': 'gpt-test'})()
        fake_resp = type('Resp', (), {'choices': [
            type('C', (), {'message': type('M', (), {'content': contenido})()})()]})()
        fake_client = type('Client', (), {})()
        fake_client.chat = type('Chat', (), {})()
        fake_client.chat.completions = type('Compl', (), {})()
        fake_client.chat.completions.create = staticmethod(lambda **kw: fake_resp)
        gpt = self.env['gpt.service'].sudo()
        return patch.multiple(
            type(gpt),
            _get_openai_config=lambda self: fake_config,
            _get_openai_client=lambda self, cfg: fake_client,
        )

    def _patch_sin_ia(self):
        """IA sin config: redactar() y _hay_ia() caen al fallback."""
        gpt = self.env['gpt.service'].sudo()
        return patch.object(
            type(gpt), '_get_openai_config', side_effect=Exception('sin config'))

    def _carrito_flags(self):
        return self.env['chatbot.session'].sudo()._get_carrito(self.session_id)

    # --- redacción IA (servicio) ---

    def test_01_redactar_con_ia_devuelve_texto_vendedor(self):
        with self._patch_ia(contenido='¡Tenemos esa camisa lista! 😊 ¿Seguimos?'):
            from odoo.addons.chatbot_cart.services.redactar import redactar
            texto = redactar(self.env, '✅ Agregué *1 x Camisa Roja*.', {'resumen': {}})
        self.assertEqual(texto, '¡Tenemos esa camisa lista! 😊 ¿Seguimos?')

    def test_02_redactar_sin_ia_devuelve_plantilla(self):
        with self._patch_sin_ia():
            from odoo.addons.chatbot_cart.services.redactar import redactar
            texto = redactar(self.env, '✅ Agregué *1 x Camisa Roja*.', {'resumen': {}})
        self.assertEqual(texto, '✅ Agregué *1 x Camisa Roja*.')

    # --- gate sin IA en el mundo carrito ---

    def test_03_aviso_sin_ia_sale_al_negocio_y_conserva_items(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self._controller()._aviso_sin_ia(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertTrue(resp['finalizado'])
        self.assertIn('IA', resp['texto_para_usuario'])
        self.assertIn('item(s)', resp['texto_para_usuario'])
        session = self.env['chatbot.session'].sudo()
        self.assertFalse(session._esta_en_modo_carrito(self.session_id))
        self.assertEqual(self._carrito_flags()['items'][0]['product_id'], self.product_a.id)

    def test_04_wire_redaccion_ia_en_agregar(self):
        """El controller pasa el texto del motor por el servicio del vendedor."""
        import odoo.addons.chatbot_cart.controllers.chatbot_cart_controller as ctrl
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        with patch.object(ChatbotCartController, '_redactar', self._redactar_original):
            with patch.object(ctrl, '_redactar_service',
                              lambda env, t, ctx: f'IA[{t[:20]}]'):
                resp = self._controller()._ejecutar_item(
                    self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                    'AGREGAR', 'CAM-R', 1, [])
        self.assertTrue(resp['texto_para_usuario'].startswith('IA['))

    # --- cierre ¿quieres pagar ya? + botones ---

    def test_05_agregar_cierra_con_pregunta_y_marca_pendiente(self):
        with self._patch_sin_ia():
            resp = self._controller()._ejecutar_item(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'AGREGAR', 'CAM-R', 2, [])
        texto = resp['texto_para_usuario']
        self.assertIn('Agregué', texto)
        self.assertIn('¿Quieres pagar ya?', texto)
        self.assertEqual(resp['botones'], ['pagar', 'cotización', '🏪 Volver al negocio'])
        self.assertTrue(self._carrito_flags().get('pendiente_pago'))

    def test_06_ver_carrito_con_items_cierra_con_pregunta(self):
        self._agregar_producto(self.product_a.id, qty=1)
        with self._patch_sin_ia():
            resp = self._controller()._ejecutar(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'CONSULTAR', '', 0, [])
        self.assertIn('¿Quieres pagar ya?', resp['texto_para_usuario'])
        self.assertEqual(resp['botones'], ['pagar', 'cotización', '🏪 Volver al negocio'])
        self.assertTrue(self._carrito_flags().get('pendiente_pago'))

    def test_07_pagar_limpia_pendiente_pago(self):
        controller = self._controller()
        controller._marcar_pendiente_pago(self.env, self.session_id)
        with self._patch_sin_ia():
            # Carrito vacío: _pagar limpia el flag antes del early-return.
            controller._pagar(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertNotIn('pendiente_pago', self._carrito_flags())

    # --- clasificador COTIZACION ---

    def test_08_clasificador_cotizacion(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        for texto in ('cotización', 'presupuesto', 'quiero una cotización'):
            res = ClasificarAccionCarritoUseCase._clasificar_fallback(texto)
            self.assertEqual(res[0]['accion'], 'COTIZACION')

    def test_09_declinacion_pedir_email(self):
        with self._patch_sin_ia():
            resp = self._controller()._pedir_email_cotizacion(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertIn('correo', resp['texto_para_usuario'].lower())
        carrito = self._carrito_flags()
        self.assertFalse(carrito.get('pendiente_pago'))
        self.assertEqual(carrito.get('pendiente_cotizacion'), 0)

    # --- rama email ---

    def test_10_email_valido_crea_cotizacion(self):
        self._agregar_producto(self.product_a.id, qty=1)
        with patch(
                'odoo.addons.chatbot_cart.controllers.chatbot_cart_controller.'
                'crear_y_enviar_desde_carrito',
                return_value='COT-0001'):
            resp = self._controller()._cotizacion_email(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'cliente@dominio.com')
        self.assertIn('cliente@dominio.com', resp['texto_para_usuario'])
        self.assertIn('COT-0001', resp['texto_para_usuario'])
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    def test_11_email_invalido_reformula(self):
        resp = self._controller()._cotizacion_email(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'no-es-correo')
        self.assertIn('nombre@dominio.com', resp['texto_para_usuario'])
        self.assertEqual(self._carrito_flags().get('pendiente_cotizacion'), 1)

    def test_12_email_invalido_dos_intentos_cancela_amable(self):
        controller = self._controller()
        controller._cotizacion_email(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'mal1')
        resp = controller._cotizacion_email(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'mal2')
        self.assertIn('Dejo la cotización pendiente', resp['texto_para_usuario'])
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    def test_13_cancelar_email_mantiene_carrito(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp = controller._cotizacion_email(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'cancelar')
        self.assertFalse(resp['finalizado'])
        self.assertEqual(self._carrito_flags()['items'][0]['product_id'], self.product_a.id)
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    def test_14_cotizacion_sin_servicio_responde_amable_y_sale(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')

        from odoo.addons.chatbot_cart.services.cotizacion_service import (
            CotizacionNoDisponible,
        )

        def sin_modulo(env, email, session_id, resumen):
            raise CotizacionNoDisponible('chatbot_cotizacion sin módulo')

        with patch(
                'odoo.addons.chatbot_cart.controllers.chatbot_cart_controller.'
                'crear_y_enviar_desde_carrito', side_effect=sin_modulo):
            resp = controller._cotizacion_email(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'cliente@dominio.com')
        self.assertIn('IA', resp['texto_para_usuario'])
        self.assertTrue(resp['finalizado'])
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())
