from unittest import SkipTest

from odoo.tests import HttpCase, tagged

from .common import BaseChatbotTestCase


@tagged("-at_install", "post_install", "ai_chatbot_1_portal", "modo_carrito")
class TestConfiguracionAgenteModoCarrito(HttpCase):
    """SPEC 34: configuracion_agente aísla el modo carrito del negocio.

    En modo CARRITO devuelve modo_carrito=true y un prompt de solo carrito
    (sin contenido de negocio ni menú). En modo negocio devuelve el prompt
    del negocio con modo_carrito=false.
    """

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

    def _get_config(self, session_id):
        return self.url_open(
            '/ai_chatbot_1_portal/configuracion_agente',
            method='POST',
            json={'session_id': session_id},
            headers={'x-chatbot-token': self.token},
        )

    def test_01_modo_negocio_prompt_de_negocio(self):
        response = self._get_config('session-negocio-001')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIs(data['modo_carrito'], False)
        prompt = data['system_prompt']
        self.assertNotIn('=== CARRITO DE COMPRA (modo aislado) ===', prompt)

    def test_02_modo_carrito_prompt_aislado_y_flag(self):
        session = self.env['chatbot.session'].sudo().create({
            'session_id': 'session-carrito-001',
            'estado': {'modo': 'CARRITO', 'carrito': {'items': []}},
        })
        response = self._get_config('session-carrito-001')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIs(data['modo_carrito'], True)
        prompt = data['system_prompt']
        self.assertIn('=== CARRITO DE COMPRA (modo aislado) ===', prompt)
        # Aislamiento: no debe mezclar el prompt del negocio
        self.assertNotIn('=== MENÚ DE OPCIONES ===', prompt)

    def test_03_modo_carrito_sin_session_id_no_activa(self):
        # Sin session_id no hay sesión en carrito → no activa aislamiento.
        response = self._get_config('')
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.json()['modo_carrito'], False)

    def _post_paso(self, session_id, valor='catálogo'):
        return self.url_open(
            '/ai_chatbot_1_portal/procesar_paso',
            method='POST',
            json={'session_id': session_id, 'valor': valor,
                  'conversation_id': session_id, 'account_id': '1',
                  'platform': 'whatsapp'},
            headers={'x-chatbot-token': self.token},
        )

    def test_04_paso_sesion_carrito_delega_al_carrito(self):
        # SPEC 48: sesión en modo carrito sin paso activo -> responde carrito.
        self.env['chatbot.session'].sudo().create({
            'session_id': 'session-paso-carrito',
            'estado': {'modo': 'CARRITO', 'carrito': {'items': []}},
        })
        response = self._post_paso('session-paso-carrito')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('modo'), 'CARRITO')
        self.assertTrue(data.get('texto_para_usuario'))
        self.assertNotIn('No hay un flujo activo', data.get('texto_para_usuario', ''))

    def test_05_paso_sesion_negocio_mantiene_genericas(self):
        # SPEC 48: sesión en negocio sin paso conserva el mensaje genérico.
        self.env['chatbot.session'].sudo().create({
            'session_id': 'session-paso-negocio',
            'estado': {'modo': 'NEGOCIO'},
        })
        response = self._post_paso('session-paso-negocio', valor='hola')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('modo'), 'MENU_PRINCIPAL')
        self.assertIn('No hay un flujo activo', data.get('texto_para_usuario', ''))