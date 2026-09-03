from odoo.tests import tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "flujos_neutros")
class TestFlujosPasosNeutros(BaseChatbotTestCase):
    """Verifica que los flujos no hereden pasos/textos de la demo IntegraIA."""

    def _crear_flujo(self, name, team=False):
        vals = {'name': name, 'company_id': self.env.ref('base.main_company').id}
        if team:
            vals['team_id'] = team.id
        return self.env['chatbot.flujo'].create(vals)

    def test_01_plantilla_precios_sin_paso_demo(self):
        """El template del flujo de precios usa los pasos genéricos (sin
        informar_precios ni 'Conoce nuestros planes')."""
        flujo = self._crear_flujo('flujo_agendamiento_precios')
        pasos = flujo._get_pasos_data_para_flujo()
        nombres = [p['nombre_interno'] for p in pasos]
        self.assertNotIn('informar_precios', nombres,
                         'El paso demo no debe estar en la plantilla')
        self.assertIn('solicitar_phone', nombres)
        self.assertIn('solicitar_name', nombres)
        for p in pasos:
            self.assertNotIn('Conoce nuestros planes', p.get('mensaje_prompt', ''))

    def test_02_mapeo_descripcion_dinamico(self):
        """El mapa de áreas usa el grupo CRM real, no textos de demo."""
        team = self.env['crm.team'].create({'name': 'Grupo Informativo Test'})
        self._crear_flujo('flujo_agendamiento_precios', team=team)
        mapeo = self.env['chatbot.flujo']._get_mapeo_equipo_descripcion()
        self.assertEqual(mapeo.get('flujo_agendamiento_precios'),
                         'Grupo Informativo Test')
        self.assertNotIn('tienda virtual y planes',
                         mapeo.get('flujo_agendamiento_precios', ''))

    def test_03_pie_mensaje_simplificado(self):
        """El pie de finalización es corto y sin líneas demo."""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
            ChatBotUtils)
        self.env['chatbot.config'].create({'name': 'Mi Negocio Test'})
        pie = ChatBotUtils._pie_mensaje(
            123, 'flujo_agendamiento_precios', env=self.env)
        self.assertIn('Referencia: 123', pie)
        self.assertIn('Próximo paso', pie)
        self.assertNotIn('tienda virtual', pie)
        self.assertNotIn('Agradecimiento', pie)
        self.assertNotIn('Proceso:', pie)
        self.assertNotIn('Privacidad:', pie)

    def test_04_brand_fallback_nombre_config(self):
        """Sin brand_name, la marca cae al nombre del negocio de la config
        (no a 'IntegraIA')."""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import (
            ChatBotUtils)
        self.env['chatbot.config'].create(
            {'name': 'Mi Negocio Test', 'active': True})
        brand = ChatBotUtils._get_brand_name(self.env)
        self.assertEqual(brand, 'Mi Negocio Test')