from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.ai_chatbot_0_core.services.gpt_service import GptService

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "marca_dinamica")
class TestMarcaDinamica(BaseChatbotTestCase):

    def _crear_flujo(self, name, palabras_clave=''):
        return self.env['chatbot.flujo'].create({
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
            'palabras_clave': palabras_clave,
        })

    def test_01_constrains_marca_no_en_rol(self):
        config = self.env['chatbot.config'].create({
            'menu_enabled': True,
            'name': 'IntegraIA',
            'role': 'BOT INTEGRAIA. Asistente virtual.',
        })
        with self.assertRaises(ValidationError):
            config.write({'brand_name': 'Karla Campoverde'})

    def test_02_constrains_marca_en_rol_ok(self):
        config = self.env['chatbot.config'].create({
            'menu_enabled': True,
            'name': 'Ventas Sillas Paper',
            'role': 'BOT VENTAS SILLAS PAPER. Vendemos sillas.',
        })
        config.write({'brand_name': 'Ventas Sillas Paper'})
        self.assertEqual(config.brand_name, 'Ventas Sillas Paper')

    def test_03_preparar_marca_extrae_si_vacio(self):
        flujo_p = self._crear_flujo('flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'menu_enabled': True,
            'name': 'Config Sin Marca',
            'role': 'BOT INTEGRAIA. Asistente virtual y vendedor.',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        self.assertFalse(config.brand_name)
        with patch.object(GptService, 'extraer_marca_del_rol',
                          return_value='INTEGRAIA'):
            config._preparar_marca()
        self.assertEqual(config.brand_name, 'INTEGRAIA')

    def test_04_preparar_marca_respeta_marca_manual(self):
        flujo_p = self._crear_flujo('flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'menu_enabled': True,
            'name': 'Config Con Marca',
            'brand_name': 'Mi Marca',
            'role': 'BOT MI MARCA. Vendedor.',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        with patch.object(GptService, 'extraer_marca_del_rol',
                          return_value='OTRA'):
            config._preparar_marca()
        self.assertEqual(config.brand_name, 'Mi Marca')

    def test_05_regenerar_menu_extrae_marca(self):
        flujo_p = self._crear_flujo('flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'menu_enabled': True,
            'name': 'Regen Marca',
            'role': 'BOT INTEGRAIA. Vendedor.',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': 'Menú viejo',
        })
        with patch.object(GptService, 'extraer_marca_del_rol',
                          return_value='INTEGRAIA'):
            result = config.action_regenerar_menu()
        self.assertEqual(config.brand_name, 'INTEGRAIA')
        menu = self.env['chatbot.intencion'].search([
            ('config_id', '=', config.id), ('nombre', '=', 'MENU')
        ], limit=1)
        self.assertTrue(menu.output_largo.startswith(
            '¡Hola! 👋 Te saluda *INTEGRAIA*'))

    def test_06_prompt_identidad_y_no_marca_ajena(self):
        from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import render_prompt
        flujo_p = self._crear_flujo('flujo_agendamiento_precios', 'precio')
        config = self.env['chatbot.config'].create({
            'menu_enabled': True,
            'name': 'IntegraIA',
            'brand_name': 'IntegraIA',
            'role': 'BOT INTEGRAIA. Asistente virtual.',
            'flujo_ids': [(6, 0, [flujo_p.id])],
        })
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': '¡Hola! 👋 Te saluda *IntegraIA*. Encantados 😊\n1️⃣ Opción',
        })
        prompt = render_prompt(config)
        self.assertIn('IDENTIDAD', prompt)
        self.assertIn('la empresa que representas es IntegraIA', prompt)
        self.assertIn('Jamás menciones otra empresa', prompt)
        self.assertNotIn('Karla Campoverde', prompt)
