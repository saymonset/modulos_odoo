from odoo.tests import tagged

from odoo.addons.ai_chatbot_1_portal.services.prompt_renderer import render_prompt

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "menu_determinista")
class TestMenuDeterminista(BaseChatbotTestCase):

    def _crear_flujo(self, name, routing_key=False):
        vals = {'name': name, 'company_id': self.env.ref('base.main_company').id}
        if routing_key:
            vals['routing_key'] = routing_key
        return self.env['chatbot.flujo'].create(vals)

    def _crear_config(self):
        flujo_precios = self._crear_flujo(
            'flujo_agendamiento_precios', routing_key='Agendamiento_Precios')
        flujo_directo = self._crear_flujo(
            'flujo_agendamiento_directo', routing_key='Agendamiento_Directo')
        config = self.env['chatbot.config'].create({
            'name': 'Cliente Test',
            'brand_name': 'KARLA CAMPOVERDE',
            'role': 'TÚ ERES:\nBOT KARLA CAMPOVERDE. Vendedora oficial.',
            'flujo_ids': [(6, 0, [flujo_precios.id, flujo_directo.id])],
        })
        menu_texto = ('*KARLA CAMPOVERDE*\n'
                      '¡Hola! 👋 ¿Qué necesitas hoy?\n'
                      '1️⃣ Precios\n'
                      '2️⃣ Agendar')
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'MENU',
            'keywords': 'hola,menu,menu_principal,menú,opciones,ayuda',
            'prioridad': 10,
            'es_menu': True,
            'output_largo': menu_texto,
        })
        # Intención informativa (contenido): nunca lleva flujo.
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'PRECIOS',
            'keywords': 'precio,costo,cuánto',
            'prioridad': 20,
            'tipo_pregunta': 'PRECIOS',
        })
        # Intención de acción: sí lleva flujo (captura).
        self.env['chatbot.intencion'].create({
            'config_id': config.id,
            'nombre': 'CITA_DIRECTA',
            'keywords': 'agendar,cita',
            'prioridad': 42,
            'tipo_pregunta': 'CITA_DIRECTA',
            'flow_id': flujo_directo.id,
        })
        return config, menu_texto

    def test_01_render_prompt_incluye_menu_con_marca(self):
        """El system prompt incluye la sección MENÚ DE OPCIONES con *MARCA*."""
        config, menu_texto = self._crear_config()
        prompt = render_prompt(config)

        self.assertIn('=== MENÚ DE OPCIONES ===', prompt)
        self.assertIn(menu_texto, prompt)
        self.assertIn('*KARLA CAMPOVERDE*', prompt)

    def test_02_intencion_menu_keywords_y_marcador(self):
        """La intención MENU expone keywords y el marcador (muestra el menú)."""
        config, _ = self._crear_config()
        prompt = render_prompt(config)

        self.assertIn('hola,menu,menu_principal,menú,opciones,ayuda', prompt)
        self.assertIn('(muestra el menú)', prompt)

    def test_03_menu_no_dispara_flujo(self):
        """La intención MENU y las de contenido no llevan flujo de captura."""
        config, _ = self._crear_config()
        menu = config.intencion_ids.filtered(lambda i: i.nombre == 'MENU')
        precios = config.intencion_ids.filtered(lambda i: i.nombre == 'PRECIOS')
        cita = config.intencion_ids.filtered(lambda i: i.nombre == 'CITA_DIRECTA')

        self.assertFalse(menu.flow_id)
        self.assertFalse(precios.flow_id)
        self.assertTrue(cita.flow_id)
