from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "flujos_no_autodetectados")
class TestFlujosNoAutodetectados(BaseChatbotTestCase):
    """SPEC 29: flujo_carrito_compra solo se activa manualmente, nunca por detección."""

    def _flujo_carrito(self):
        return self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search(
            [('name', '=', 'flujo_carrito_compra')], limit=1)

    def _archivar_configs_activas(self):
        self.env['chatbot.config'].sudo().search(
            [('active', '=', True)]).write({'active': False})

    def test_01_deteccion_excluye_carrito_con_keywords(self):
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito, 'flujo_carrito_compra debe existir')
        texto = "Venta y alquiler de inmuebles, locales, productos y pedidos"
        flujos = self.env['chatbot.flujo'].sudo().with_context(
            active_test=False).search([])
        resultado = self.env['chatbot.config']._detectar_flujos_desde_rag(
            texto, flujos)
        self.assertNotIn(flujo_carrito, resultado['flujos'])

    def test_02_deteccion_automatica_no_activa_carrito(self):
        self._archivar_configs_activas()
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        flujo_carrito.write({'active': False})
        self.env['chatbot.flujo'].sudo().aplicar_deteccion_automatica(
            "Venta de productos y pedidos por carrito")
        self.assertFalse(flujo_carrito.active)

    def test_03_manual_marcado_en_config_activa_carrito(self):
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Con Carrito',
            'flujo_ids': [(6, 0, flujo_carrito.ids)],
        })
        self.env['chatbot.flujo'].sudo()._aplicar_deteccion_desde_config(config)
        self.assertTrue(flujo_carrito.active)

    def test_04_sin_marca_la_cascada_archiva_carrito(self):
        flujo_carrito = self._flujo_carrito()
        self.assertTrue(flujo_carrito)
        flujo_carrito.write({'active': True})
        config = self.env['chatbot.config'].sudo().create({
            'name': 'Cliente Test Sin Carrito',
        })
        self.env['chatbot.flujo'].sudo()._aplicar_deteccion_desde_config(config)
        self.assertFalse(flujo_carrito.active)