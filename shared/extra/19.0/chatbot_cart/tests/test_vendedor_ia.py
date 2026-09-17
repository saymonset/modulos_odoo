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
        """SPEC 57: AGREGAR ya NO pasa por `_redactar` (IA) — texto determinista."""
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
        # El texto es el del motor, NO el del servicio IA
        self.assertFalse(resp['texto_para_usuario'].startswith('IA['))
        self.assertIn('Agregué *Camisa Roja (1 unid.)*', resp['texto_para_usuario'])

    # --- cierre ¿quieres pagar ya? + botones ---

    def test_05_agregar_cierra_con_guia_y_marca_pendiente(self):
        with self._patch_sin_ia():
            resp = self._controller()._ejecutar_item(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'AGREGAR', 'CAM-R', 2, [])
        texto = resp['texto_para_usuario']
        self.assertIn('Agregué', texto)
        # Extensión SPEC 55: guía universal, sin presión de pago
        self.assertIn('¿Quieres algo más?', texto)
        self.assertNotIn('¿Quieres pagar ya?', texto)
        # SPEC 56: con items el 3er botón es Pagar (catálogo por texto)
        self.assertEqual(resp['botones'], ['➕ Sumar', '➖ Quitar', '💳 Pagar'])
        self.assertTrue(self._carrito_flags().get('pendiente_pago'))

    def test_06_ver_carrito_con_items_cierra_con_guia(self):
        self._agregar_producto(self.product_a.id, qty=1)
        with self._patch_sin_ia():
            resp = self._controller()._ejecutar(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'CONSULTAR', '', 0, [])
        texto = resp['texto_para_usuario']
        # SPEC 57: texto mínimo con total; el detalle va en la List Message
        self.assertIn('unid. en', texto)
        self.assertIn('$', texto)
        self.assertIn('lista_carrito', resp)
        self.assertNotIn('¿Quieres pagar ya?', texto)
        # SPEC 56: con items el 3er botón es Pagar (catálogo por texto)
        self.assertEqual(resp['botones'], ['➕ Sumar', '➖ Quitar', '💳 Pagar'])
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

    def test_09_declinacion_pedir_telefono(self):
        with self._patch_sin_ia():
            resp = self._controller()._pedir_email_cotizacion(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        self.assertIn('teléfono', resp['texto_para_usuario'].lower())
        estado = self._carrito_flags().get('pendiente_cotizacion')
        self.assertEqual(estado.get('paso'), 'telefono')

    # --- rama teléfono → email → cotización (SPEC 47) ---

    def test_10_telefono_partner_con_email_confirma_y_crea(self):
        """SPEC 53: partner con email → '¿eres tú?' → sí crea la cotización."""
        self._agregar_producto(self.product_a.id, qty=1)
        self.partner.write({'phone': '+58 414 5551122', 'email': 'partner@test.com'})
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp_conf = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '04145551122')
        self.assertIn('¿Eres tú?', resp_conf['texto_para_usuario'])
        estado = self._carrito_flags().get('pendiente_cotizacion')
        self.assertEqual(estado.get('paso'), 'confirmar_partner')
        capture = {}

        def fake_crear(env, telefono, email, nombre, session_id, resumen):
            capture.update(telefono=telefono, email=email, nombre=nombre)
            return 'COT-0001'

        with patch(
                'odoo.addons.chatbot_cart.controllers.chatbot_cart_controller.'
                'crear_y_enviar_desde_carrito', side_effect=fake_crear):
            resp = controller._cotizacion_turno(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'sí')
        self.assertIn('COT-0001', resp['texto_para_usuario'])
        self.assertEqual(capture['telefono'], '04145551122')
        self.assertEqual(capture['email'], 'partner@test.com')
        self.assertEqual(capture['nombre'], 'Test Partner')
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    def test_10b_telefono_partner_negado_pide_nombre(self):
        """SPEC 53: 'no soy yo' → sigue como cliente nuevo pidiendo el nombre."""
        self._agregar_producto(self.product_a.id, qty=1)
        self.partner.write({'phone': '+58 414 5551122', 'email': 'partner@test.com'})
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '04145551122')
        resp = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'no')
        self.assertIn('llamas', resp['texto_para_usuario'].lower())
        estado = self._carrito_flags().get('pendiente_cotizacion')
        self.assertEqual(estado.get('paso'), 'nombre')

    def test_11_telefono_sin_partner_pide_nombre(self):
        """SPEC 53: cliente nuevo paso a paso — nombre antes del correo."""
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '0499999999')
        self.assertIn('llamas', resp['texto_para_usuario'].lower())
        estado = self._carrito_flags().get('pendiente_cotizacion')
        self.assertEqual(estado.get('paso'), 'nombre')

    def test_12_email_invalido_reformula(self):
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '0499999999')
        controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'Cliente de Prueba')
        resp = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'no-es-correo')
        self.assertIn('nombre@dominio.com', resp['texto_para_usuario'])
        estado = self._carrito_flags().get('pendiente_cotizacion')
        self.assertEqual(estado.get('intentos'), 1)

    def test_12b_email_invalido_dos_intentos_cancela_amable(self):
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        controller._cotizacion_turno(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '0499999999')
        controller._cotizacion_turno(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'Cliente de Prueba')
        controller._cotizacion_turno(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'mal1')
        resp = controller._cotizacion_turno(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'mal2')
        self.assertIn('Dejo la cotización pendiente', resp['texto_para_usuario'])
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    def test_13_cliente_nuevo_telefono_nombre_email(self):
        """SPEC 53: nuevo cliente — teléfono → nombre → correo, un dato por turno."""
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp_tel = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', '0499999999')
        self.assertIn('llamas', resp_tel['texto_para_usuario'].lower())
        capture = {}

        def fake_crear(env, telefono, email, nombre, session_id, resumen):
            capture.update(telefono=telefono, email=email, nombre=nombre)
            return 'COT-0002'

        with patch(
                'odoo.addons.chatbot_cart.controllers.chatbot_cart_controller.'
                'crear_y_enviar_desde_carrito', side_effect=fake_crear):
            resp_nombre = controller._cotizacion_turno(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'María Pérez')
            self.assertIn('correo', resp_nombre['texto_para_usuario'].lower())
            controller._cotizacion_turno(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'nuevo@dominio.com')
        self.assertEqual(capture['telefono'], '0499999999')
        self.assertEqual(capture['email'], 'nuevo@dominio.com')
        self.assertEqual(capture['nombre'], 'María Pérez')
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    def test_13b_cancelar_mantiene_carrito(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        resp = controller._cotizacion_turno(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp', 'cancelar')
        self.assertFalse(resp['finalizado'])
        self.assertEqual(self._carrito_flags()['items'][0]['product_id'], self.product_a.id)
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())

    # --- SPEC 51: sanitizador + listado intangible ---

    def test_15_sanitizador_elimina_fuga_router(self):
        from odoo.addons.chatbot_cart.services.redactar import _sanitizar
        sucio = ('🛒 Tu carrito listo.\n'
                 'flow_name="flujo_carrito_compra"\n'
                 'equipo_asignado="flujo_carrito_compra"\n'
                 'Texto limpio que queda para el cliente.')
        limpio = _sanitizar(sucio)
        self.assertIsNotNone(limpio)
        self.assertNotIn('flow_name', limpio)
        self.assertNotIn('equipo_asignado', limpio)
        self.assertIn('carrito listo', limpio)

    def test_16_redactar_falla_con_solo_fugas(self):
        """Respuesta IA con solo router: fallback a plantilla (no vacío)."""
        with self._patch_ia(contenido='flow_name="flujo_carrito_compra"'):
            from odoo.addons.chatbot_cart.services.redactar import redactar
            texto = redactar(self.env, '🛒 Tu carrito de compras.', {})
        self.assertEqual(texto, '🛒 Tu carrito de compras.')

    def test_17_bienvenida_buscador_generica(self):
        with self._patch_sin_ia():
            resp = self._controller()._respuesta_buscador(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        texto = resp['texto_para_usuario']
        self.assertNotIn('pizza', texto.lower())
        self.assertNotIn('Quieres pagar ya', texto)
        self.assertIn('necesites', texto)

    def test_18_que_haces_clasifica_fallback(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        res = ClasificarAccionCarritoUseCase._clasificar_fallback('que haces')
        self.assertEqual(res[0]['accion'], 'FALLBACK')

    def test_19_que_venden_sigue_catalogo(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        res = ClasificarAccionCarritoUseCase._clasificar_fallback('qué venden')
        self.assertEqual(res[0]['accion'], 'CATALOGO')

    def test_20_buscar_frase_con_busca(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        res = ClasificarAccionCarritoUseCase._clasificar_fallback('busca perfumes')
        self.assertEqual(res[0]['accion'], 'BUSCAR')

    # --- SPEC 52: descubrimiento ---

    def test_21_decision_con_cantidad_en_la_frase(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController as C,
        )
        lista = [{'product_id': 1}, {'product_id': 2}]
        self.assertEqual(
            C._decision_seleccion_numerica('1, quiero 3', lista),
            ('AGREGAR', '1', 3))
        self.assertEqual(
            C._decision_seleccion_numerica('del 2 quiero 5', lista),
            ('AGREGAR', '2', 5))
        self.assertEqual(
            C._decision_seleccion_numerica('1 y quiero 5', lista), ('AGREGAR', '1', 5))
        self.assertEqual(
            C._decision_seleccion_numerica('2', lista),
            ('AGREGAR', '2', 1))
        self.assertEqual(
            C._decision_seleccion_numerica('que haces', lista), None)

    def test_22_captions_con_numero(self):
        controller = self._controller()
        productos = [
            {'has_image': True, 'image_url': 'https://x/1.png', 'name': 'Item A',
             'price_ves': 100.0, 'price_usd': 5.0},
            {'has_image': False, 'image_url': '', 'name': 'Item B',
             'price_ves': 200.0, 'price_usd': 10.0},
            {'has_image': True, 'image_url': 'https://x/c.png', 'name': 'Item C',
             'price_ves': 300.0, 'price_usd': 15.0},
        ]
        caps = [im['caption'] for im in controller._imagenes_de_productos(
            productos, con_numeros=True)]
        self.assertTrue(caps[0].startswith('1. Item A'))
        self.assertTrue(caps[1].startswith('3. Item C'))

    def test_23_hint_acciones_en_agregar(self):
        with self._patch_sin_ia():
            resp = self._controller()._ejecutar_item(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'AGREGAR', 'CAM-R', 1, [])
        # Ext. SPEC 55: guía universal (mantiene la pista ➕/➖ y las salidas)
        texto = resp['texto_para_usuario']
        self.assertIn('Ajustar:', texto)
        self.assertIn('➕', texto)
        self.assertIn('catálogo', texto)

    def test_24_hint_en_consultar_con_items(self):
        self._agregar_producto(self.product_a.id, qty=1)
        with self._patch_sin_ia():
            resp = self._controller()._ejecutar(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'CONSULTAR', '', 0, [])
        # SPEC 57: el detalle y la guía van en la List Message / botones
        self.assertIn('lista_carrito', resp)
        self.assertIn('💳 Pagar', resp['botones'])

    def test_14_cotizacion_sin_servicio_responde_amable_y_sale(self):
        self._agregar_producto(self.product_a.id, qty=1)
        controller = self._controller()
        controller._pedir_email_cotizacion(self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')

        from odoo.addons.chatbot_cart.services.cotizacion_service import (
            CotizacionNoDisponible,
        )

        def sin_modulo(env, telefono, email, nombre, session_id, resumen):
            raise CotizacionNoDisponible('chatbot_cotizacion sin módulo')

        with patch(
                'odoo.addons.chatbot_cart.controllers.chatbot_cart_controller.'
                'crear_y_enviar_desde_carrito', side_effect=sin_modulo):
            controller._cotizacion_turno(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                '04145551122')
            controller._cotizacion_turno(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'Nueva Cliente')
            resp = controller._cotizacion_turno(
                self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
                'nuevo@dominio.com')
        self.assertIn('IA', resp['texto_para_usuario'])
        self.assertTrue(resp['finalizado'])
        self.assertNotIn('pendiente_cotizacion', self._carrito_flags())
