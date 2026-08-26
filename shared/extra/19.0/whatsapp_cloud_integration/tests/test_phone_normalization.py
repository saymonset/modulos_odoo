from unittest.mock import patch, MagicMock

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BaseWhatsappTestCase


@tagged("-at_install", "post_install", "whatsapp_phone")
class TestPhoneNormalization(BaseWhatsappTestCase):

    def _create_wizard(self, phone):
        partner = self.env['res.partner'].create({
            'name': 'Phone Test Partner',
            'phone': phone,
        })
        template = self.env['whatsapp.template'].create({
            'name': 'test_template',
            'friendly_name': 'Plantilla de prueba',
            'language_code': 'es',
            'has_video_header': False,
        })
        return self.env['whatsapp.message.wizard'].create({
            'partner_id': partner.id,
            'waba_account_id': self.waba_account.id,
            'template_id': template.id,
        })

    def _get_normalized_recipient(self, wizard):
        """Extract the normalized recipient from the payload by mocking requests.post."""
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured['json'] = json
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = {'messages': [{'id': 'wamid.test123'}]}
            return resp

        with patch('requests.post', side_effect=fake_post):
            wizard.action_send_whatsapp_message()

        return captured.get('json', {}).get('to', '')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_01_0412_prefix_normalized(self):
        wizard = self._create_wizard('04121234567')
        recipient = self._get_normalized_recipient(wizard)
        self.assertEqual(recipient, '584121234567')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_02_412_prefix_normalized(self):
        wizard = self._create_wizard('4121234567')
        recipient = self._get_normalized_recipient(wizard)
        self.assertEqual(recipient, '584121234567')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_03_plus_stripped(self):
        wizard = self._create_wizard('+58 412-123-4567')
        recipient = self._get_normalized_recipient(wizard)
        self.assertEqual(recipient, '584121234567')

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_04_international_kept(self):
        wizard = self._create_wizard('+15551234567')
        recipient = self._get_normalized_recipient(wizard)
        self.assertEqual(recipient, '15551234567')

    def test_05_no_phone_raises(self):
        partner = self.env['res.partner'].create({
            'name': 'No Phone Partner',
            'phone': False,
        })
        template = self.env['whatsapp.template'].create({
            'name': 'test_tpl',
            'friendly_name': 'Plantilla de prueba',
            'language_code': 'es',
            'has_video_header': False,
        })
        wizard = self.env['whatsapp.message.wizard'].create({
            'partner_id': partner.id,
            'waba_account_id': self.waba_account.id,
            'template_id': template.id,
        })
        with self.assertRaises(UserError):
            wizard.action_send_whatsapp_message()

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_06_invalid_json_params_raises(self):
        wizard = self._create_wizard('04121234567')
        wizard.write({'parameter_values': 'not_valid_json{'})
        with self.assertRaises(UserError):
            wizard.action_send_whatsapp_message()

    @mute_logger("odoo.addons.whatsapp_cloud_integration.models.whatsapp_message")
    def test_07_non_list_params_raises(self):
        wizard = self._create_wizard('04121234567')
        wizard.write({'parameter_values': '{"key": "value"}'})
        with self.assertRaises(UserError):
            wizard.action_send_whatsapp_message()