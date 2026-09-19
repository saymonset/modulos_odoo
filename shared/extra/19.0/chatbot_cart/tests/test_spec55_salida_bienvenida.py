# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestSpec55SalidaBienvenida(BaseChatbotCartTestCase):
    """SPEC 55: salida del carrito con bienvenida del negocio y compra
    solo por imágenes (captions con total del carrito, guía de búsqueda)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        cls.controller = ChatbotCartController()
        cls.config = cls.env['chatbot.config'].sudo().create(
            {'name': 'Cliente Spec55', 'brand_name': 'Marca Spec55'})
        cls.env['chatbot.intencion'].sudo().create({
            'config_id': cls.config.id, 'nombre': 'MENU',
            'es_auto_rag': True,
            'output_largo': '¡Hola! 👋 Te saluda *Marca Spec55*. '
                            'Somos un negocio de pruebas 😊\n1️⃣ Catálogo',
        })

    def _salir(self):
        return self.controller._salir_carrito(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')

    # --- salida con bienvenida del negocio ---

    def test_01_salida_con_items_bienvenida_y_aviso(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self._salir()
        self.assertTrue(resp['finalizado'])
        texto = resp['texto_para_usuario']
        self.assertIn('¡Hola! 👋 Te saluda *Marca Spec55*.', texto)
        self.assertIn('1️⃣ Catálogo', texto)
        self.assertIn('🛒 Te quedaron 1 item(s) guardados.', texto)
        self.assertIn('Escribe *carrito* para retomar tu compra.', texto)
        self.assertNotIn('¡Listo!', texto)
        self.assertNotIn('Volvemos al negocio', texto)

    def test_02_salida_sin_items_bienvenida_pura(self):
        resp = self._salir()
        self.assertTrue(resp['finalizado'])
        texto = resp['texto_para_usuario']
        self.assertIn('¡Hola! 👋 Te saluda *Marca Spec55*.', texto)
        self.assertNotIn('item(s) guardados', texto)
        self.assertNotIn('¡Listo!', texto)

    def test_03_salida_sin_menu_intent_fallback_marca(self):
        # Sin texto de MENU en la config: fallback mínimo con la marca.
        for i in self.config.intencion_ids:
            i.unlink()
        resp = self._salir()
        texto = resp['texto_para_usuario']
        self.assertIn('¡Hola! 👋 Te saluda *Marca Spec55*.', texto)

    def test_04_aviso_sin_ia_usa_bienvenida_negocio(self):
        self._agregar_producto(self.product_a.id, qty=1)
        resp = self.controller._aviso_sin_ia(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp')
        texto = resp['texto_para_usuario']
        self.assertIn('no tengo la IA activa', texto)
        self.assertIn('¡Hola! 👋 Te saluda *Marca Spec55*.', texto)
        self.assertIn('Te quedaron 1 item(s) guardados', texto)
        self.assertNotIn('Volvemos al negocio:', texto)
        # sale del modo carrito (SPEC 50)
        self.assertFalse(self.env['chatbot.session'].sudo()._esta_en_modo_carrito(
            self.session_id))

    # --- guía de búsqueda y Hallazgos sin resultados ---

    def test_05_catalogo_guia_con_ejemplo_real_sin_lista_textual(self):
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        texto = resp['texto_para_usuario']
        self.assertIn('¿Buscas algo en particular?', texto)
        self.assertIn('Escríbelo con tus palabras', texto)
        self.assertIn('p. ej. "', texto)
        self.assertNotIn('1. Camisa Roja', texto)
        self.assertNotIn('Ref: ', texto)
        # destacados con número en el caption (imágenes)
        self.assertTrue(resp['imagenes'])

    def test_06_busqueda_resultados_solo_contado(self):
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'BUSCAR', 'camisa', 0, [])
        texto = resp['texto_para_usuario']
        self.assertIn('Encontré', texto)
        self.assertNotIn('1. Camisa Roja', texto)
        self.assertNotIn('Ref: CAM-R', texto)

    def test_07_busqueda_sin_resultados_sugiere_tienda(self):
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'BUSCAR', 'zzzinexistente', 0, [])
        texto = resp['texto_para_usuario']
        self.assertIn('No encontré', texto)
        self.assertIn('zzzinexistente', texto)

    # --- caption con total del carrito ---

    def test_08_captions_destacados_sin_total_duplicado(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        # SPEC 57: el total del carrito ya no se repite en cada caption
        captions = [c['caption'] for c in resp['imagenes']]
        self.assertTrue(captions)
        self.assertFalse(any('🛒 Tu carrito: ' in c for c in captions))
        # el estado por producto (SPEC 54) se prueba directo en
        # test_ajuste_carrito.test_10 y test_imagenes_catalogo.test_04b


@tagged("-at_install", "post_install")
class TestSpec55VerCarritoVisual(BaseChatbotCartTestCase):
    """Extensión SPEC 55 (16/9): typos, ver carrito con imágenes y Σ unidades,
    guía universal y botones con salida a productos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        cls.controller = ChatbotCartController()

    def test_01_typos_con_simbolos_clasifican_consultar(self):
        from odoo.addons.chatbot_cart.uses_cases.clasificar_accion_carrito_use_case import (
            ClasificarAccionCarritoUseCase,
        )
        for typo in ('ver carri`to', 'ver carrito!', 'mi *carrito*'):
            self.assertEqual(
                ClasificarAccionCarritoUseCase._clasificar_fallback(typo)[0]['accion'],
                'CONSULTAR', f'"{typo}" debe ser CONSULTAR')

    def test_02_ver_carrito_con_items_lista_interactiva(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        texto = resp['texto_para_usuario']
        # SPEC 57: texto mínimo con total; el detalle va en la List Message
        self.assertIn('2 unid. en 1 producto(s)', texto)
        self.assertNotIn('¿Quieres pagar ya?', texto)
        self.assertNotIn('¿Quieres algo más?', texto)
        # lista interactiva del carrito (sin imágenes por item)
        lista = resp['lista_carrito']
        filas = lista['sections'][0]['rows']
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['id'], 'modificar_1')
        self.assertIn('2 unid.', filas[0]['description'])
        self.assertEqual(resp['imagenes'], [])

    def test_03_resumen_lleva_total_unidades(self):
        self._agregar_producto(self.product_a.id, qty=2)
        self._agregar_producto(self.product_b.id, qty=3)
        resumen = self.controller.CART_SERVICE.resumen(env=self.env, session_id=self.session_id)
        self.assertEqual(resumen['count'], 2)
        self.assertEqual(resumen['total_unidades'], 5)

    def test_04_sin_productos_inventados_en_templates(self):
        # Guía universal: nunca menciona tipos de producto ("camisas")
        self._agregar_producto(self.product_a.id, qty=1)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        self.assertNotIn('camisas', resp['texto_para_usuario'].lower())
        resumen = self.controller.CART_SERVICE.resumen(env=self.env, session_id=self.session_id)
        self.assertNotIn('camisas', self.controller._lista_compacta_carrito(resumen).lower())

    def test_05_botones_con_items_salen_a_productos(self):
        self._agregar_producto(self.product_a.id, qty=1)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        # SPEC 56: el 3er botón pasa a Pagar (catálogo queda en la guía)
        self.assertEqual(resp['botones'], ['➕ Sumar', '➖ Quitar', '💳 Pagar'])
