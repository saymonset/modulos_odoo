# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestSpec56CarritoVisualMulticanal(BaseChatbotCartTestCase):
    """SPEC 56: botón Pagar con items, resumen con total destacado y botones
    adaptados por plataforma (WhatsApp/Messenger/Instagram)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        cls.controller = ChatbotCartController()

    # --- botón Pagar con items ---

    def test_01_pagar_es_boton_con_items(self):
        self._agregar_producto(self.product_a.id, qty=1)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        self.assertEqual(resp['botones'], ['➕ Sumar', '➖ Quitar', '💳 Pagar'])
        self.assertIn('💳 Pagar', resp['botones_por_plataforma']['whatsapp'])

    def test_02_sin_items_no_se_puede_pagar(self):
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        self.assertNotIn('💳 Pagar', resp['botones'])
        self.assertEqual(resp['botones'], ['catálogo', 'ayuda', '🏪 Volver al negocio'])

    # --- resumen con total destacado y CTA de pago ---

    def test_03_resumen_tiene_total_negrita_y_cta_pagar(self):
        self._agregar_producto(self.product_a.id, qty=2)
        texto = self.controller.CART_SERVICE.formato_resumen_amigable(
            self.env, self.session_id)
        self.assertIn('Σ *Total:', texto)
        self.assertIn('Toca *💳 Pagar* para confirmar tu pedido.', texto)
        # separador visual
        self.assertIn('───', texto)

    def test_04_resumen_carrito_en_consultar(self):
        self._agregar_producto(self.product_a.id, qty=2)
        resp = self.controller._ejecutar(
            self.env, self.session_id, 'c1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        rc = resp['resumen_carrito']
        self.assertEqual(rc['count'], 1)
        self.assertEqual(rc['total_unidades'], 2)
        self.assertEqual(rc['total_usd'], 13.00)

    # --- botones por plataforma ---

    def test_05_botones_por_plataforma_tres_claves(self):
        resp = self.controller._respuesta(
            self.session_id, 'c1', '+58414000000', 'whatsapp',
            'hola', extra={'botones': ['➕ Sumar', '➖ Quitar', '💳 Pagar']})
        self.assertEqual(
            sorted(resp['botones_por_plataforma'].keys()),
            ['instagram', 'messenger', 'whatsapp'])
        for plat, botones in resp['botones_por_plataforma'].items():
            self.assertEqual(botones, ['➕ Sumar', '➖ Quitar', '💳 Pagar'])

    def test_06_sin_botones_listas_vacias(self):
        resp = self.controller._respuesta(
            self.session_id, 'c1', '+58414000000', 'whatsapp', 'hola')
        for plat, botones in resp['botones_por_plataforma'].items():
            self.assertEqual(botones, [])

    def test_07_instagram_recibe_hint_de_texto(self):
        resp = self.controller._respuesta(
            self.session_id, 'c1', '+58414000000', 'instagram',
            'ver carrito', extra={'botones': ['💳 Pagar']})
        self.assertIn('Escribe *pagar* para confirmar', resp['texto_para_usuario'])
        # WhatsApp no lo recibe (usa botones)
        resp_wa = self.controller._respuesta(
            self.session_id, 'c1', '+58414000000', 'whatsapp',
            'ver carrito', extra={'botones': ['💳 Pagar']})
        self.assertNotIn('Escribe *pagar* para confirmar', resp_wa['texto_para_usuario'])