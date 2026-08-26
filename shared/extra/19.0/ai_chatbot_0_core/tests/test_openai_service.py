from unittest.mock import patch, MagicMock

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "openai_service")
class TestOpenAIService(TransactionCase):

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
        cls.config = cls.env['openai.config'].create({
            'name': 'Test Config',
            'api_key': 'sk-test-key-12345',
            'active': True,
        })

    def test_01_get_openai_client_no_api_key(self):
        self.config.write({'active': False})
        with self.assertRaises(ValidationError):
            self.env['openai.service']._get_openai_client()

    def test_02_get_openai_client_package_missing(self):
        with patch('odoo.addons.ai_chatbot_0_core.services.openai_service.OpenAI', None):
            with self.assertRaises(ValidationError):
                self.env['openai.service']._get_openai_client()

    def test_03_get_openai_client_success(self):
        mock_client = MagicMock()
        mock_openai_class = MagicMock(return_value=mock_client)
        with patch(
            'odoo.addons.ai_chatbot_0_core.services.openai_service.OpenAI',
            mock_openai_class,
        ):
            client = self.env['openai.service']._get_openai_client()
            self.assertIsNotNone(client)
            mock_openai_class.assert_called_once_with(api_key='sk-test-key-12345')

    def test_04_generate_text_success(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Test response  "
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class = MagicMock(return_value=mock_client)
        with patch(
            'odoo.addons.ai_chatbot_0_core.services.openai_service.OpenAI',
            mock_openai_class,
        ):
            result = self.env['openai.service'].generate_text("Hello", model="gpt-4o-mini")
        self.assertEqual(result, "Test response")
        mock_client.chat.completions.create.assert_called_once()

    def test_05_generate_text_custom_params(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Custom"
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class = MagicMock(return_value=mock_client)
        with patch(
            'odoo.addons.ai_chatbot_0_core.services.openai_service.OpenAI',
            mock_openai_class,
        ):
            self.env['openai.service'].generate_text(
                "Prompt", model="gpt-4o", max_tokens=500, temperature=0.5
            )
        call_kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs['model'], 'gpt-4o')
        self.assertEqual(call_kwargs.kwargs['max_tokens'], 500)
        self.assertEqual(call_kwargs.kwargs['temperature'], 0.5)

    def test_06_config_create_minimal(self):
        config = self.env['openai.config'].create({
            'name': 'Minimal',
            'api_key': 'sk-minimal',
        })
        self.assertTrue(config.active)
        self.assertEqual(config.default_model, 'gpt-4o-mini')