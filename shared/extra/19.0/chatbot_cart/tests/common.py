from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class BaseChatbotCartTestCase(TransactionCase):
    """Base class for chatbot_cart tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            no_reset_password=True,
            tracking_disable=True,
        ))
        # SPEC 50: los tests del módulo validan las plantillas del motor;
        # la redacción IA del vendedor se simula con passthrough aquí y se
        # prueba a fondo (con mock) en test_vendedor_ia.
        from unittest.mock import patch
        from odoo.addons.chatbot_cart.controllers.chatbot_cart_controller import (
            ChatbotCartController,
        )
        cls._redactar_original = ChatbotCartController._redactar
        patcher = patch.object(
            ChatbotCartController, '_redactar',
            lambda self, env, texto, contexto=None: texto)
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.product_a = cls.env['product.product'].create({
            'name': 'Camisa Roja',
            'default_code': 'CAM-R',
            'list_price': 130.0,
            'list_price_usd': 6.50,
            'type': 'consu',
            'sale_ok': True,
            'taxes_id': False,
            'supplier_taxes_id': False,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Camisa Azul',
            'default_code': 'CAM-A',
            'list_price': 140.0,
            'list_price_usd': 7.00,
            'type': 'consu',
            'sale_ok': True,
            'taxes_id': False,
            'supplier_taxes_id': False,
        })
        cls.session_id = 'test-session-001'

    def _configurar_tasas(self, bcv_rate=20.0, cop_rate=0.0, cop_show=False):
        company = self.env.company
        company.write({
            'bcv_manual_rate_active': True,
            'bcv_manual_rate': bcv_rate,
            'cop_manual_rate_active': bool(cop_rate),
            'cop_manual_rate': cop_rate or 0.0,
            'cop_show_fields': cop_show,
        })

    def _agregar_producto(self, product_id, qty=1):
        from odoo.addons.chatbot_cart.services.cart_service import CartService
        return CartService().agregar(self.env, self.session_id, product_id, qty)