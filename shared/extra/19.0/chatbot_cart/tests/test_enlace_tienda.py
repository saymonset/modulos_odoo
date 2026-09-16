from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestEnlaceTienda(BaseChatbotCartTestCase):
    """SPEC 46: enlace a la tienda online del negocio en bienvenida y catálogo."""

    def _url_tienda(self):
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        return CartService.obtener_url_tienda_enlace(self.env)

    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(key, value)

    def _clear_tienda_param(self):
        self._set_param('chatbot_cart.tienda_url', '')

    def _limpiar_websites(self):
        """Quita website_id y website_ids (si existen) para probar fallbacks."""
        company = self.env.company
        try:
            company.website_id = False
        except AttributeError:
            pass
        try:
            if company.website_ids:
                company.website_ids = [(5, 0, 0)]
        except AttributeError:
            pass
        try:
            company.website = False
        except AttributeError:
            pass

    def _base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')

    def test_01_sin_nada_devuelve_none(self):
        self._clear_tienda_param()
        self._limpiar_websites()
        # Sin web.base.url no hay auto-detección ni fallback que aplicar.
        self._set_param('web.base.url', '')
        self.assertIsNone(self._url_tienda())

    def test_02_auto_deteccion_website_sale(self):
        """website_sale instalado + web.base.url -> base + /shop."""
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', 'https://lead.integraia.lat')
        self.assertEqual(self._url_tienda(), 'https://lead.integraia.lat/shop')

    def test_03_override_config_gana(self):
        """El override del negocio manda sobre auto-detección y website."""
        self._set_param('chatbot_cart.tienda_url', 'https://tienda.integraia.lat')
        self._limpiar_websites()
        self.assertEqual(self._url_tienda(), 'https://tienda.integraia.lat')
        self._clear_tienda_param()

    def test_04_prompt_sin_url_no_imprime_linea(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import (
            render_instrucciones_carrito,
        )
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', '')
        bloque = render_instrucciones_carrito(self.env)
        self.assertNotIn('Visita nuestra tienda online', bloque)
        self.assertIn('Salida al activar', bloque)

    def test_05_prompt_con_url_imprime_linea(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import (
            render_instrucciones_carrito,
        )
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', 'https://lead.integraia.lat')
        bloque = render_instrucciones_carrito(self.env)
        self.assertIn(
            f'❗ Visita nuestra tienda online: {self._base_url()}/shop', bloque)

    def test_06_append_cart_instructions_recibe_env(self):
        from odoo.addons.chatbot_cart.services.prompt_carrito import (
            append_cart_instructions,
        )
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', 'https://lead.integraia.lat')
        prompt = '=== ESQUELETO ==='
        nuevo = append_cart_instructions(prompt, self.env)
        self.assertIn(f'Visita nuestra tienda online: {self._base_url()}/shop', nuevo)
        self.assertIn('=== ESQUELETO ===', nuevo)

    def test_07_catalogo_sin_url_no_antecede_linea(self):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', '')
        result = ProductBuscarService().catalogo(self.env)
        texto = ProductBuscarService().formato_lista_catalogo(result)
        self.assertNotIn('Visita nuestra tienda online', texto)
        self.assertIn('Catálogo', texto)

    def test_08_catalogo_con_url_antecede_linea(self):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', 'https://lead.integraia.lat')
        url = self._base_url() + '/shop'
        result = ProductBuscarService().catalogo(self.env)
        texto = ProductBuscarService().formato_lista_catalogo(result, url_tienda=url)
        self.assertTrue(texto.startswith(f'❗ Visita nuestra tienda online: {url}'))

    def _buscador(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        return ChatbotCartController()._respuesta_buscador(
            self.env, self.session_id, 'conv-1', '+58414000000', 'whatsapp')

    def test_09_buscador_con_url_incluye_linea(self):
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', 'https://lead.integraia.lat')
        resp = self._buscador()
        self.assertTrue(
            resp['texto_para_usuario'].startswith(
                f'❗ Visita nuestra tienda online: {self._base_url()}/shop'))
        self.assertIn('Tenemos', resp['texto_para_usuario'])

    def test_10_buscador_sin_url_no_incluye_linea(self):
        self._clear_tienda_param()
        self._limpiar_websites()
        self._set_param('web.base.url', '')
        resp = self._buscador()
        self.assertNotIn('Visita nuestra tienda online', resp['texto_para_usuario'])
        self.assertIn('Tenemos', resp['texto_para_usuario'])