import logging
import requests
from odoo import api, models

_logger = logging.getLogger(__name__)


class ChatwootClient(models.AbstractModel):
    _name = 'chatwoot.client'
    _description = 'Helpers Chatwoot'

    @staticmethod
    def _headers(api_token):
        return {'Content-Type': 'application/json', 'api_access_token': api_token}

    @api.model
    def assign_conversation(self, account_id, conversation_id, mapping):
        """mapping: dict with optional keys: agent_id, inbox_id, tags (list), notify_message"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        headers = self._headers(api_token)

        if not base_url or not api_token or not account_id or not conversation_id:
            _logger.warning('Chatwoot assign skipped: falta configuración o ids.')
            return False

        # 1) Try assign to agent
        try:
            if mapping.get('agent_id'):
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}"
                payload = {"assignee_id": mapping['agent_id'], "assignee_type": "User"}
                r = requests.put(url, json=payload, headers=headers, timeout=timeout)
                if r.status_code not in (200, 201):
                    _logger.warning('Chatwoot assign agent failed: %s - %s', r.status_code, r.text)
        except Exception as e:
            _logger.exception('Error assigning agent in Chatwoot: %s', e)

        # 2) fallback: inbox
        try:
            if not mapping.get('agent_id') and mapping.get('inbox_id'):
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}"
                payload = {"inbox_id": mapping['inbox_id']}
                r = requests.put(url, json=payload, headers=headers, timeout=timeout)
                if r.status_code not in (200,201):
                    _logger.warning('Chatwoot set inbox failed: %s - %s', r.status_code, r.text)
        except Exception as e:
            _logger.exception('Error setting inbox in Chatwoot: %s', e)

        # 3) tags
        try:
            if mapping.get('tags'):
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/tags"
                r = requests.post(url, json={"tags": mapping['tags']}, headers=headers, timeout=timeout)
                if r.status_code not in (200,201):
                    _logger.warning('Chatwoot add tags failed: %s - %s', r.status_code, r.text)
        except Exception as e:
            _logger.exception('Error adding tags in Chatwoot: %s', e)

        # 4) notify message
        try:
            if mapping.get('notify_message'):
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
                r = requests.post(url, json={"content": mapping['notify_message']}, headers=headers, timeout=timeout)
                if r.status_code not in (200,201):
                    _logger.warning('Chatwoot notify message failed: %s - %s', r.status_code, r.text)
        except Exception as e:
            _logger.exception('Error sending notify message: %s', e)

        return True
