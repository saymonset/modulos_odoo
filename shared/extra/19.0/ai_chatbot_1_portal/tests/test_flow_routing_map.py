from unittest import SkipTest

from odoo.tests import HttpCase, tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "flow_routing_map")
class TestFlowRoutingMap(BaseChatbotTestCase):

    def _create_flujo(self, name, routing_key=False, active=True):
        vals = {
            'name': name,
            'company_id': self.env.ref('base.main_company').id,
            'active': active,
        }
        if routing_key:
            vals['routing_key'] = routing_key
        return self.env['chatbot.flujo'].create(vals)

    def test_01_maps_routing_key_and_name(self):
        self._create_flujo('flujo_test_con_key', routing_key='TEST_KEY')
        self._create_flujo('flujo_test_sin_key')

        flow_map = self.env['chatbot.flujo']._get_flow_routing_map()

        self.assertEqual(flow_map.get('TEST_KEY'), 'flujo_test_con_key')
        self.assertEqual(flow_map.get('flujo_test_sin_key'), 'flujo_test_sin_key')

    def test_02_excludes_inactive_flujos(self):
        self._create_flujo('flujo_test_inactivo', active=False)

        flow_map = self.env['chatbot.flujo']._get_flow_routing_map()

        self.assertNotIn('flujo_test_inactivo', flow_map)


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "flow_routing_map")
class TestConfiguracionAgenteEndpoint(HttpCase):

    @classmethod
    def setUpClass(cls):
        try:
            port = cls.http_port()
        except AttributeError:
            port = None
        if port is None:
            raise SkipTest(
                'Servidor HTTP no disponible (--no-http): se omite el HttpCase del endpoint.')
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            no_reset_password=True,
            tracking_disable=True,
        ))
        cls.token = 'test-token-n8n'
        cls.env['ir.config_parameter'].sudo().set_param(
            'ai_chatbot_1_portal.api_token', cls.token)

    def test_01_returns_flow_map_with_valid_token(self):
        self.env['chatbot.flujo'].create({
            'name': 'flujo_test_endpoint',
            'routing_key': 'EP_KEY',
            'company_id': self.env.ref('base.main_company').id,
        })

        response = self.url_open(
            '/ai_chatbot_1_portal/configuracion_agente',
            method='POST',
            json={},
            headers={'x-chatbot-token': self.token},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('system_prompt', data)
        self.assertIn('fallback_message', data)
        self.assertIn('flow_map', data)
        self.assertEqual(data['flow_map'].get('EP_KEY'), 'flujo_test_endpoint')

    def test_02_returns_401_without_token(self):
        response = self.url_open(
            '/ai_chatbot_1_portal/configuracion_agente',
            method='POST',
            json={},
        )

        self.assertEqual(response.status_code, 401)