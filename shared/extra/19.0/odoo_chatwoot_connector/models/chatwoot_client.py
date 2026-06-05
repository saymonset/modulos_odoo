import logging
import requests
from odoo import api, models

_logger = logging.getLogger(__name__)


class ChatwootClient(models.AbstractModel):
    _name = 'chatwoot.client'
    _description = 'Helpers Chatwoot'

    DEFAULT_CONVERSATION_LABELS = ['#agente_desactivado']

    @staticmethod
    def _headers(api_token):
        return {'Content-Type': 'application/json', 'api_access_token': api_token}

    @api.model
    def get_agent_details(self, account_id, agent_id=None, agent_email=None):
        """Return agent details dict or None.

        Tries agent_id first, then agent_email list lookup.
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id:
            return None

        headers = self._headers(api_token)

        try:
            if agent_id:
                url = f"{base_url}/api/v1/accounts/{account_id}/agents/{agent_id}"
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    return r.json()
            if agent_email:
                url = f"{base_url}/api/v1/accounts/{account_id}/agents"
                r = requests.get(url, headers=headers, timeout=timeout)
                if r.status_code == 200:
                    data = r.json()
                    agents = data if isinstance(data, list) else data.get('payload') or data.get('data') or []
                    for a in agents:
                        if a.get('email') == agent_email or (a.get('agent') and a.get('agent', {}).get('email') == agent_email):
                            return a
        except Exception as e:
            _logger.warning('Error obteniendo detalles del agente: %s', e)
        return None

    @staticmethod
    def _extract_payload_list(data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('payload') or data.get('data') or []
        return []

    @staticmethod
    def _normalize_label(label):
        return (label or '').strip()

    def _get_account_labels(self, account_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id:
            return []

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/labels"
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code != 200:
                return []
            return self._extract_payload_list(r.json())
        except Exception as e:
            _logger.warning('Error obteniendo labels del account %s: %s', account_id, e)
            return []

    def _ensure_account_labels(self, account_id, labels):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id:
            return []

        headers = self._headers(api_token)
        existing = {}
        for item in self._get_account_labels(account_id):
            if isinstance(item, dict):
                title = self._normalize_label(item.get('title'))
                if title:
                    existing[title.lower()] = title

        ensured = []
        for raw_label in labels or []:
            label = self._normalize_label(raw_label)
            if not label:
                continue
            key = label.lower()
            if key in existing:
                ensured.append(existing[key])
                continue
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/labels"
                payload = {
                    'title': label,
                    'show_on_sidebar': True,
                }
                r = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if r.status_code in (200, 201):
                    ensured.append(label)
                    existing[key] = label
                else:
                    text = r.text or ''
                    if r.status_code in (409, 422) or 'already exists' in text.lower():
                        ensured.append(label)
                        existing[key] = label
                    else:
                        _logger.warning('No se pudo crear label %s en account %s: %s %s', label, account_id, r.status_code, text)
            except Exception as e:
                _logger.warning('Error creando label %s en account %s: %s', label, account_id, e)
        return ensured

    def _get_conversation_labels(self, account_id, conversation_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id or not conversation_id:
            return []

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/labels"
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code != 200:
                return None
            payload = self._extract_payload_list(r.json())
            labels = []
            for item in payload:
                if isinstance(item, dict):
                    title = self._normalize_label(item.get('title'))
                    if title:
                        labels.append(title)
                else:
                    title = self._normalize_label(item)
                    if title:
                        labels.append(title)
            return labels
        except Exception as e:
            _logger.warning('Error obteniendo labels de conversación %s: %s', conversation_id, e)
            return None

    def _apply_conversation_labels(self, account_id, conversation_id, labels):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id or not conversation_id:
            return {'ok': False, 'errors': ['missing_configuration_or_ids']}

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/labels"
            r = requests.post(url, json={"labels": labels}, headers=headers, timeout=timeout)
            if r.status_code in (200, 201):
                return {'ok': True, 'errors': [], 'warnings': []}
            return {'ok': False, 'errors': [f'apply_labels_failed:{r.status_code}:{r.text}'], 'warnings': []}
        except Exception as e:
            return {'ok': False, 'errors': [f'exception_apply_labels:{e}'], 'warnings': []}

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

        # Resolve agent id: prefer mapping.agent_id, else mapping.agent_email
        agent_id = mapping.get('agent_id')
        if not agent_id and mapping.get('agent_email'):
            agent_id = _get_agent_id_by_email(mapping.get('agent_email'))

        # Try assign to agent if present.
        if agent_id and mapping.get('prefer_assign_to_agent', True):
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

        # Fallback to inbox: the conversation remains in its inbox.
        # We do not call an API here because Chatwoot assigns conversations to inboxes at creation time.
        if not assigned and mapping.get('inbox_id'):
            assigned = 'inbox'
            if errors:
                warnings.extend(errors)
                warnings.append('agent_assignment_failed_fallback_to_inbox')
                errors = []

        # Labels: keep current labels and add the configured ones.
        configured_labels = [self._normalize_label(label) for label in (mapping.get('tags') or [])]
        labels_to_apply = []
        seen = set()
        for label in self.DEFAULT_CONVERSATION_LABELS + configured_labels:
            if label and label.lower() not in seen:
                labels_to_apply.append(label)
                seen.add(label.lower())

        if labels_to_apply:
            try:
                ensured = self._ensure_account_labels(account_id, labels_to_apply)
                current_labels = self._get_conversation_labels(account_id, conversation_id)
                if current_labels is None:
                    warnings.append('conversation_labels_unavailable_skip_apply')
                else:
                    merged = []
                    seen_labels = set()
                    for label in current_labels + ensured:
                        label = self._normalize_label(label)
                        if label and label.lower() not in seen_labels:
                            merged.append(label)
                            seen_labels.add(label.lower())

                    if merged:
                        label_result = self._apply_conversation_labels(account_id, conversation_id, merged)
                        if not label_result['ok']:
                            warnings.extend(label_result.get('warnings', []))
                            errors.extend(label_result.get('errors', []))
            except Exception as e:
                errors.append(f'exception_apply_labels:{e}')

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
