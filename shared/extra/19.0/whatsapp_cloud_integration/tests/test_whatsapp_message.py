import json
from unittest.mock import patch, MagicMock

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BaseWhatsappTestCase


@tagged("-at_install", "post_install", "whatsapp_message")
class TestWhatsappMessage(BaseWhatsappTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env['whatsapp.template'].create({
            'name': 'test_template',
            'language_code': 'es',
            'has_video_header': False,
        })
        cls.template_video = cls.env['whatsapp.template'].create({
            'name': 'test_video_template',
            'language_code': 'es',
            'has_video_header': True,
        })

    def _mock_response(self, success=True, error_msg="API Error"):
        resp = MagicMock()
        if success:
            resp.raise_for_status.return_value = None
            resp.json.return_value = {'messages': [{'id': 'wamid.test123'}]}
        else:
            resp.raise_for_status.side_effect = Exception(error_msg)
            resp.json.return_value = {'error': {'message': error_msg}}
        return resp

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_01_send_success_creates_history(self):
        wizard = self.env['whatsapp.message.wizard'].create({
            'partner_id': self.partner.id,
            'waba_account_id': self.waba_account.id,
            'template_id': self.template.id,
            'parameter_values': json.dumps(["hello"]),
        })
        with patch('requests.post', return_value=self._mock_response(success=True)):
            wizard.action_send_whatsapp_message()
        history = self.env['whatsapp.history'].search([
            ('partner_id', '=', self.partner.id),
            ('direction', '=', 'outgoing'),
        ], order='id desc', limit=1)
        self.assertTrue(history)
        self.assertEqual(history.status, 'sent')
        self.assertEqual(history.message_id, 'wamid.test123')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_02_send_error_creates_error_history(self):
        wizard = self.env['whatsapp.message.wizard'].create({
            'partner_id': self.partner.id,
            'waba_account_id': self.waba_account.id,
            'template_id': self.template.id,
        })
        import requests
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            response=MagicMock(json=lambda: {'error': {'message': 'API Error'}})
        )
        with patch('requests.post', return_value=error_response):
            with self.assertRaises(UserError):
                wizard.action_send_whatsapp_message()
        history = self.env['whatsapp.history'].search([
            ('partner_id', '=', self.partner.id),
            ('direction', '=', 'outgoing'),
            ('status', '=', 'error'),
        ], order='id desc', limit=1)
        self.assertTrue(history)
        self.assertEqual(history.status, 'error')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_03_video_header_builds_components(self):
        wizard = self.env['whatsapp.message.wizard'].create({
            'partner_id': self.partner.id,
            'waba_account_id': self.waba_account.id,
            'template_id': self.template_video.id,
            'parameter_values': json.dumps(["https://video.url.mp4", "body text"]),
        })
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured['payload'] = json
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {'messages': [{'id': 'wamid.video123'}]}
            return resp

        with patch('requests.post', side_effect=fake_post):
            wizard.action_send_whatsapp_message()

        components = captured['payload']['template']['components']
        types = [c['type'] for c in components]
        self.assertIn('header', types)
        header_params = components[0]['parameters'][0]
        self.assertEqual(header_params['type'], 'video')
        self.assertEqual(header_params['video']['link'], 'https://video.url.mp4')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_04_newlines_cleaned_in_body_params(self):
        wizard = self.env['whatsapp.message.wizard'].create({
            'partner_id': self.partner.id,
            'waba_account_id': self.waba_account.id,
            'template_id': self.template.id,
            'parameter_values': json.dumps(["line1\nline2\r"]),
        })
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured['payload'] = json
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {'messages': [{'id': 'wamid.clean123'}]}
            return resp

        with patch('requests.post', side_effect=fake_post):
            wizard.action_send_whatsapp_message()

        body_component = [c for c in captured['payload']['template']['components'] if c['type'] == 'body'][0]
        text_value = body_component['parameters'][0]['text']
        self.assertNotIn('\n', text_value)
        self.assertNotIn('\r', text_value)