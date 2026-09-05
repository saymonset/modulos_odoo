from unittest.mock import MagicMock

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "extraer_marca")
class TestExtraerMarcaDelRol(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            tracking_disable=True,
        ))

    def test_01_fallback_determinista_bot_x(self):
        use_case = self.env['extraer.marca.del.rol.use.case']
        brand = use_case._extraer_marca_determinista(
            'TÚ ERES:\nBOT INTEGRAIA. Asistente virtual y vendedor oficial.')
        self.assertEqual(brand, 'INTEGRAIA')

    def test_02_fallback_sin_patron_vacio(self):
        use_case = self.env['extraer.marca.del.rol.use.case']
        brand = use_case._extraer_marca_determinista(
            'Eres una asistente de ventas para el negocio.')
        self.assertEqual(brand, '')

    def test_03_ia_extrae_marca(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = \
            '{"brand": "Ventas Sillas Paper"}'
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        use_case = self.env['extraer.marca.del.rol.use.case']
        res = use_case.execute({
            'role_text': 'TÚ ERES:\nBOT VENTAS SILLAS PAPER. Vendemos sillas.',
            'openai_client': mock_client,
            'model': 'gpt-4o-mini',
            'max_tokens': 100,
        })
        self.assertEqual(res['brand'], 'Ventas Sillas Paper')

    def test_04_ia_falla_cae_al_fallback(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception('boom')
        use_case = self.env['extraer.marca.del.rol.use.case']
        res = use_case.execute({
            'role_text': 'TÚ ERES:\nBOT INTEGRAIA. Asistente.',
            'openai_client': mock_client,
            'model': 'gpt-4o-mini',
            'max_tokens': 100,
        })
        self.assertEqual(res['brand'], 'INTEGRAIA')
