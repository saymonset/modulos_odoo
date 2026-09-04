from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "brand_settings")
class TestBrandSettings(BaseChatbotTestCase):

    def test_01_helper_usa_marca_de_config_activa(self):
        self.env['chatbot.config'].create({
            'name': 'Clínica Marca',
            'brand_name': 'Clínica Los Andes',
            'attribution_enabled': True,
            'attribution_text': '@clinica_la',
        })

        brand, enabled, text = self.env['chatbot.config']._get_brand_settings()

        self.assertEqual(brand, 'Clínica Los Andes')
        self.assertTrue(enabled)
        self.assertEqual(text, '@clinica_la')

    def test_02_helper_sin_config_devuelve_params_legacy(self):
        self.env['chatbot.config'].with_context(active_test=False).search([]).write(
            {'active': False})
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('ai_chatbot_1_portal.brand_name', 'Legacy Marca')
        params.set_param('ai_chatbot_1_portal.platform_promotion_enabled', 'True')
        params.set_param('ai_chatbot_1_portal.platform_promotion_text', '@legacy')

        brand, enabled, text = self.env['chatbot.config']._get_brand_settings()

        self.assertEqual(brand, 'Legacy Marca')
        self.assertTrue(enabled)
        self.assertEqual(text, '@legacy')

    def test_03_helper_sin_config_y_sin_params_devuelve_defaults(self):
        self.env['chatbot.config'].with_context(active_test=False).search([]).write(
            {'active': False})
        self.env['ir.config_parameter'].sudo().search([
            ('key', 'in', [
                'ai_chatbot_1_portal.brand_name',
                'ai_chatbot_1_portal.platform_promotion_enabled',
                'ai_chatbot_1_portal.platform_promotion_text',
            ]),
        ]).unlink()

        brand, enabled, text = self.env['chatbot.config']._get_brand_settings()

        self.assertEqual(brand, '')
        self.assertFalse(enabled)
        self.assertEqual(text, '@integraiaconodoo')