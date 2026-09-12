# -*- coding: utf-8 -*-
from odoo.tests import tagged

from .common import BaseChatbotCartTestCase


@tagged("-at_install", "post_install")
class TestCatalogo(BaseChatbotCartTestCase):
    """SPEC 33: comando catálogo, paginación, descripción y CONSULTAR vacío."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['product.product'].create({
            'name': 'Servicio Mantenimiento VPS',
            'default_code': 'VPS-MANT',
            'list_price': 50.0,
            'list_price_usd': 25.0,
            'type': 'consu',
            'sale_ok': True,
            'description_sale': 'Mantenimiento mensual del servidor.',
            'taxes_id': False,
            'supplier_taxes_id': False,
        })
        # Producto vendible SIN descripción (descripción vacía no debe romper).
        cls.env['product.product'].create({
            'name': 'Refresco',
            'default_code': 'REF',
            'list_price': 2.0,
            'list_price_usd': 1.0,
            'type': 'consu',
            'sale_ok': True,
            'description_sale': False,
            'taxes_id': False,
            'supplier_taxes_id': False,
        })

    def _catalogo(self, offset=0):
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        return ProductBuscarService().catalogo(self.env, offset=offset)

    def test_01_catalogo_muestra_productos_vendibles(self):
        result = self._catalogo()
        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['count'], 1)
        nombres = [p['name'] for p in result['productos']]
        self.assertIn('Camisa Roja', nombres)

    def test_02_catalogo_incluye_descripcion(self):
        result = self._catalogo()
        vps = next(p for p in result['productos'] if p['name'] == 'Servicio Mantenimiento VPS')
        self.assertEqual(vps['description'], 'Mantenimiento mensual del servidor.')

    def test_03_catalogo_descripcion_vacia_no_rompe(self):
        result = self._catalogo()
        refresco = next(p for p in result['productos'] if p['name'] == 'Refresco')
        self.assertEqual(refresco['description'], '')
        texto = ProductBuscarService().formato_lista_catalogo(result)
        self.assertIn('Refresco', texto)

    def test_03b_descripcion_con_lang_de_company(self):
        # En Odoo 19 description_sale es JSON de traducciones; _descripcion_producto
        # fuerza el lang de la compañía para leer el texto correcto.
        from odoo.addons.chatbot_cart.services.product_buscar import ProductBuscarService
        vps = self.env['product.product'].search(
            [('name', '=', 'Servicio Mantenimiento VPS')], limit=1)
        tmpl = vps.product_tmpl_id
        desc = ProductBuscarService._descripcion_producto(tmpl)
        self.assertIn('Mantenimiento', desc)

    def test_04_catalogo_paginacion_offset(self):
        result = self._catalogo(offset=1)
        self.assertEqual(result['offset'], 1)
        self.assertGreaterEqual(result['count'], 1)
        texto = ProductBuscarService().formato_lista_catalogo(result)
        self.assertIn('Catálogo', texto)

    def test_05_formato_incluye_guia_persistente(self):
        result = self._catalogo()
        texto = ProductBuscarService().formato_lista_catalogo(result)
        self.assertIn('Responde el número para agregarlo', texto)
        self.assertIn('ver carrito', texto)

    def test_06_formato_con_has_more_sugiere_mas(self):
        result = self._catalogo(offset=0)
        result['has_more'] = True
        texto = ProductBuscarService().formato_lista_catalogo(result)
        self.assertIn('*más*', texto)

    def test_07_consultar_con_carrito_vacio_devuelve_catalogo(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        controller = ChatbotCartController()
        resp = controller._ejecutar(
            self.env, self.session_id, 'conv-1', '+58414000000', 'whatsapp',
            'CONSULTAR', '', 0, [])
        self.assertIn('texto_para_usuario', resp)
        self.assertIn('Catálogo', resp['texto_para_usuario'])

    def test_08_accion_catalogo_desde_controller(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        controller = ChatbotCartController()
        resp = controller._ejecutar(
            self.env, self.session_id, 'conv-1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        self.assertIn('texto_para_usuario', resp)
        self.assertIn('Catálogo', resp['texto_para_usuario'])
        # Los botones interactivos se marcan para n8n.
        self.assertEqual(resp.get('botones'), controller.BOTONES_CARRITO)

    def test_09_paginacion_mas_avanza_offset(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        controller = ChatbotCartController()
        # Sin catálogo previo, "más" no avanza (offset 0).
        offset = controller._offset_catalogo(self.env, self.session_id, 'MAS')
        self.assertEqual(offset, 0)
        # Tras mostrar la página 0, "más" avanza CATALOG_LIMIT.
        controller._ejecutar(
            self.env, self.session_id, 'conv-1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        offset = controller._offset_catalogo(self.env, self.session_id, 'MAS')
        self.assertEqual(offset, controller.SEARCH_SERVICE.CATALOG_LIMIT)

    def test_10_guardado_de_pagina_y_ultima_busqueda(self):
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        controller = ChatbotCartController()
        controller._ejecutar(
            self.env, self.session_id, 'conv-1', '+58414000000', 'whatsapp',
            'CATALOGO', '', 0, [])
        session = self.env['chatbot.session'].sudo()
        carrito = session._get_carrito(self.session_id)
        self.assertEqual(carrito['pagina_catalogo'], 0)
        self.assertTrue(carrito['ultima_busqueda'])