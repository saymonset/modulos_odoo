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
        """mapping: dict with optional keys: agent_id, agent_email, inbox_id, tags (list), notify_message
        Behavior: try assign to agent_id (or resolve agent_email) using Chatwoot assignments API.
        If assignment to agent fails, keep conversation in its inbox as fallback and continue."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        headers = self._headers(api_token)

        if not base_url or not api_token or not account_id or not conversation_id:
            _logger.warning('Chatwoot assign skipped: falta configuración o ids.')
            return {'ok': False, 'errors': ['missing_configuration_or_ids']}

        errors = []
        warnings = []
        assigned = None

        def _get_agent_id_by_email(email):
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/agents"
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    data = r.json()
                    # data may be list or dict depending on version
                    agents = data if isinstance(data, list) else data.get('payload') or data.get('data') or []
                    for a in agents:
                        if a.get('email') == email or a.get('agent') and a.get('agent').get('email') == email:
                            return a.get('id') or a.get('agent', {}).get('id')
            except Exception as e:
                _logger.warning('Error listing agents by email: %s', e)
            return None

        def _agent_exists(agent_id):
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/agents/{agent_id}"
                r = requests.get(url, headers=headers, timeout=timeout)
                return r.status_code == 200
            except Exception:
                return False

        # Resolve agent id: prefer mapping.agent_id, else mapping.agent_email
        agent_id = mapping.get('agent_id')
        if not agent_id and mapping.get('agent_email'):
            agent_id = _get_agent_id_by_email(mapping.get('agent_email'))

        # Try assign to agent if present and valid
        if agent_id and mapping.get('prefer_assign_to_agent', True):
            if _agent_exists(agent_id):
                try:
                    url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/assignments"
                    payload = {"assignee_id": agent_id}
                    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
                    if r.status_code in (200, 201):
                        assigned = 'agent'
                    else:
                        errors.append(f'assign_agent_failed:{r.status_code}:{r.text}')
                except Exception as e:
                    errors.append(f'exception_assign_agent:{e}')
            else:
                errors.append('agent_not_found_or_inactive')

        # Fallback to inbox: the conversation remains in its inbox.
        # We do not call an API here because Chatwoot assigns conversations to inboxes at creation time.
        if not assigned and mapping.get('inbox_id'):
            assigned = 'inbox'
            if errors:
                warnings.extend(errors)
                warnings.append('agent_assignment_failed_fallback_to_inbox')
                errors = []

        # Tags
        if mapping.get('tags'):
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/tags"
                r = requests.post(url, json={"tags": mapping['tags']}, headers=headers, timeout=timeout)
                if r.status_code not in (200, 201):
                    errors.append(f'add_tags_failed:{r.status_code}:{r.text}')
            except Exception as e:
                errors.append(f'exception_add_tags:{e}')

        # Notify message
        if mapping.get('notify_message'):
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
                r = requests.post(url, json={"content": mapping['notify_message']}, headers=headers, timeout=timeout)
                if r.status_code not in (200, 201):
                    errors.append(f'notify_failed:{r.status_code}:{r.text}')
            except Exception as e:
                errors.append(f'exception_notify:{e}')

        ok = assigned is not None and len(errors) == 0
        _logger.info('Chatwoot assign result: assigned=%s, errors=%s, warnings=%s', assigned, errors, warnings)
        return {'ok': ok, 'assigned_to': assigned, 'errors': errors, 'warnings': warnings}
