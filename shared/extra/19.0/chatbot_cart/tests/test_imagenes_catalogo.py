import base64

from odoo.tests import tagged

from .common import BaseChatbotCartTestCase

_PNG_1PX = (
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAC'
    'hwGA60e6kgAAAABJRU5ErkJggg=='
)


@tagged("-at_install", "post_install")
class TestImagenesCatalogo(BaseChatbotCartTestCase):
    """SPEC 39: URLs absolutas y captions de imagen para catálogo/búsqueda."""

    def setUp(self):
        super().setUp()
        from odoo.addons.chatbot_cart.services.product_buscar import (
            ProductBuscarService,
        )
        self.search = ProductBuscarService()
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://lead.test.example')
        self.product_a.product_tmpl_id.write(
            {'image_1920': base64.b64decode(_PNG_1PX)})

    # --- URL absoluta ---

    def test_01_url_imagen_absoluta(self):
        url = self.search._url_imagen(self.env, self.product_a.id)
        self.assertEqual(
            url,
            f"https://lead.test.example/web/image/product.product/"
            f"{self.product_a.id}/image_128")

    def test_02_url_imagen_sin_base_vacia(self):
        self.env['ir.config_parameter'].sudo().set_param('web.base.url', '')
        self.assertEqual(self.search._url_imagen(self.env, self.product_a.id), '')

    def test_03_producto_dict_url_absoluta(self):
        rates = {
            'bcv_rate': 20.0,
            'cop_rate': 0.0,
            'cop_show_fields': False,
        }
        d = self.search._producto_dict(self.env, self.product_a.product_tmpl_id, rates)
        self.assertTrue(d['has_image'])
        self.assertTrue(d['image_url'].startswith('https://lead.test.example/'))

    # --- _imagenes_de_productos ---

    def test_04_imagenes_con_caption_y_exclusion(self):
        productos = [
            {'name': 'Pizza', 'price_ves': 10106.48, 'price_usd': 12.0,
             'price_cop': 0.0, 'show_cop': False, 'has_image': True,
             'image_url': 'https://lead.test.example/web/image/product.product/1/image_128'},
            {'name': 'Tips', 'price_ves': 842.21, 'price_usd': 1.0,
             'price_cop': 0.0, 'show_cop': False, 'has_image': False,
             'image_url': ''},
        ]
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        imagenes = ChatbotCartController._imagenes_de_productos(productos)
        self.assertEqual(len(imagenes), 1)
        self.assertEqual(imagenes[0]['link'], productos[0]['image_url'])
        # SPEC 55: sin carrito los items no aparecen; caption base igual
        self.assertEqual(imagenes[0]['caption'],
                         'Pizza — Bs. 10,106.48 / $12.00')

    def test_04b_caption_con_total_carrito(self):
        # SPEC 55: caption agrega total de items y valor del carrito.
        productos = [
            {'name': 'Pizza', 'price_ves': 10106.48, 'price_usd': 12.0,
             'price_cop': 0.0, 'show_cop': False, 'has_image': True,
             'image_url': 'https://x/img'},
        ]
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        imagenes = ChatbotCartController._imagenes_de_productos(
            productos, items_carrito=[
                {'product_id': 99, 'qty': 2, 'price_usd': 5.0}])
        self.assertIn('\n🛒 Tu carrito: 2 unid. en 1 producto(s) — $10.00',
                      imagenes[0]['caption'])

    def test_05_caption_con_cop(self):
        productos = [
            {'name': 'Pizza', 'price_ves': 10106.48, 'price_usd': 12.0,
             'price_cop': 45000.0, 'show_cop': True, 'has_image': True,
             'image_url': 'https://x/img'},
        ]
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        imagenes = ChatbotCartController._imagenes_de_productos(productos)
        self.assertIn('/ COP $45,000.00', imagenes[0]['caption'])

    # --- regresión: catalogo/buscar no explotan ---

    def test_06_catalogo_devuelve_urls_absolutas(self):
        result = self.search.catalogo(self.env, offset=0)
        self.assertTrue(result['success'])
        for p in result['productos']:
            if p['has_image']:
                self.assertTrue(p['image_url'].startswith('https://lead.test.example/'))
            else:
                self.assertTrue(p['image_url'].endswith('image_128') or p['image_url'] == '')
