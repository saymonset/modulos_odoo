import logging
import requests
from odoo import api, models

_logger = logging.getLogger(__name__)


class ChatwootClient(models.AbstractModel):
    _name = 'chatwoot.client'
    _description = 'Helpers Chatwoot'

    DEFAULT_ACCOUNT_LABELS = ['#agente_desactivado']

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

    def _ensure_default_account_labels(self, account_id):
        return self._ensure_account_labels(account_id, self.DEFAULT_ACCOUNT_LABELS)

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

    def _get_conversation_details(self, account_id, conversation_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id or not conversation_id:
            _logger.warning('_get_conversation_details skipped: missing config/ids (base_url=%s, token=%s, account=%s, conv=%s)',
                            bool(base_url), bool(api_token), account_id, conversation_id)
            return None

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}"
            _logger.info('_get_conversation_details calling GET %s', url)
            r = requests.get(url, headers=headers, timeout=timeout)
            _logger.info('_get_conversation_details response status=%s', r.status_code)
            if r.status_code != 200:
                _logger.warning('_get_conversation_details non-200: %s %s', r.status_code, r.text[:500])
                return None
            data = r.json() or {}
            meta = data.get('meta', {})
            assignee = meta.get('assignee')
            _logger.info('_get_conversation_details success. meta.assignee=%s', assignee)
            return data
        except Exception as e:
            _logger.warning('Error obteniendo conversación %s: %s', conversation_id, e, exc_info=True)
            return None

    def _set_conversation_status(self, account_id, conversation_id, status):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id or not conversation_id:
            return {'ok': False, 'errors': ['missing_configuration_or_ids'], 'warnings': []}

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_status"
            r = requests.post(url, json={'status': status}, headers=headers, timeout=timeout)
            if r.status_code in (200, 201):
                return {'ok': True, 'errors': [], 'warnings': []}
            return {'ok': False, 'errors': [f'set_status_failed:{r.status_code}:{r.text}'], 'warnings': []}
        except Exception as e:
            return {'ok': False, 'errors': [f'exception_set_status:{e}'], 'warnings': []}

    def _get_inbox_members(self, account_id, inbox_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id or not inbox_id:
            return None

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/inbox_members/{inbox_id}"
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code != 200:
                return None
            members = self._extract_payload_list(r.json())
            ids = []
            for item in members:
                if isinstance(item, dict) and item.get('id'):
                    ids.append(int(item['id']))
            return ids
        except Exception as e:
            _logger.warning('Error obteniendo miembros del inbox %s: %s', inbox_id, e)
            return None

    def _ensure_inbox_member(self, account_id, inbox_id, agent_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('chatwoot.base_url') or ''
        api_token = self.env['ir.config_parameter'].sudo().get_param('chatwoot.api_access_token') or ''
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('chatwoot.timeout', 3))
        if not base_url or not api_token or not account_id or not inbox_id or not agent_id:
            return {'ok': False, 'warnings': [], 'errors': []}

        current_ids = self._get_inbox_members(account_id, inbox_id)
        if current_ids is None:
            return {'ok': False, 'warnings': ['inbox_members_unavailable_skip_sync'], 'errors': []}
        if int(agent_id) in current_ids:
            return {'ok': True, 'warnings': [], 'errors': []}

        headers = self._headers(api_token)
        try:
            url = f"{base_url}/api/v1/accounts/{account_id}/inbox_members"
            user_ids = sorted(set(current_ids + [int(agent_id)]))
            payload = {'inbox_id': int(inbox_id), 'user_ids': user_ids}
            r = requests.patch(url, json=payload, headers=headers, timeout=timeout)
            if r.status_code in (200, 201):
                return {'ok': True, 'warnings': [], 'errors': []}
            return {'ok': False, 'warnings': [], 'errors': [f'ensure_inbox_member_failed:{r.status_code}:{r.text}']}
        except Exception as e:
            return {'ok': False, 'warnings': [], 'errors': [f'exception_ensure_inbox_member:{e}']}

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
        # We always reassign according to the selected round-robin mapping.
        # This prevents a previous assignee from blocking the next lead.

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
                            found_id = a.get('id') or a.get('agent', {}).get('id')
                            _logger.info('assign_conversation[conv=%s]: resolved agent email=%s -> id=%s',
                                         conversation_id, email, found_id)
                            return found_id
                    _logger.warning('assign_conversation[conv=%s]: email=%s no encontrado en lista de agents',
                                    conversation_id, email)
            except Exception as e:
                _logger.warning('Error listing agents by email: %s', e)
            return None

        # Resolve agent id: prefer mapping.agent_id, else mapping.agent_email
        agent_id = mapping.get('agent_id')
        if not agent_id and mapping.get('agent_email'):
            _logger.info('assign_conversation[conv=%s]: agent_id no proporcionado, buscando por email=%s',
                         conversation_id, mapping.get('agent_email'))
            agent_id = _get_agent_id_by_email(mapping.get('agent_email'))

        _logger.info('assign_conversation[conv=%s]: resolved agent_id=%s, prefer_assign=%s, inbox_id=%s',
                     conversation_id, agent_id, mapping.get('prefer_assign_to_agent', True), mapping.get('inbox_id'))

        if agent_id and mapping.get('inbox_id'):
            try:
                inbox_result = self._ensure_inbox_member(account_id, mapping.get('inbox_id'), agent_id)
                if inbox_result.get('warnings'):
                    warnings.extend(inbox_result.get('warnings', []))
                if not inbox_result.get('ok'):
                    _logger.warning(
                        'assign_conversation[conv=%s]: unable to ensure inbox member for agent %s inbox %s: %s',
                        conversation_id, agent_id, mapping.get('inbox_id'), inbox_result.get('errors', []),
                    )
            except Exception as e:
                warnings.append(f'exception_ensure_inbox_member:{e}')

        # Always try to assign to the selected agent.
        if agent_id and mapping.get('prefer_assign_to_agent', True):
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/assignments"
                payload = {"assignee_id": agent_id}
                _logger.info('assign_conversation[conv=%s]: assigning to agent_id=%s', conversation_id, agent_id)
                r = requests.post(url, json=payload, headers=headers, timeout=timeout)
                if r.status_code in (200, 201):
                    assigned = 'agent'
                    _logger.info('assign_conversation[conv=%s]: assign to agent %s OK', conversation_id, agent_id)
                else:
                    errors.append(f'assign_agent_failed:{r.status_code}:{r.text}')
                    _logger.warning('assign_conversation[conv=%s]: assign to agent %s FAILED: %s %s',
                                    conversation_id, agent_id, r.status_code, r.text[:500])
            except Exception as e:
                errors.append(f'exception_assign_agent:{e}')
                _logger.warning('assign_conversation[conv=%s]: assign exception: %s', conversation_id, e, exc_info=True)

        # Fallback to inbox: the conversation remains in its inbox.
        # We do not call an API here because Chatwoot assigns conversations to inboxes at creation time.
        if not assigned and mapping.get('inbox_id'):
            assigned = 'inbox'
            if errors:
                warnings.extend(errors)
                warnings.append('agent_assignment_failed_fallback_to_inbox')
                errors = []

        # Ensure account-level labels exist, but do not force them on the conversation.
        self._ensure_default_account_labels(account_id)

        # Labels on the conversation: only the ones configured for this mapping.
        configured_labels = [self._normalize_label(label) for label in (mapping.get('tags') or [])]
        labels_to_apply = []
        seen = set()
        for label in configured_labels:
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

                    current_set = {self._normalize_label(label).lower() for label in current_labels if self._normalize_label(label)}
                    desired_set = {self._normalize_label(label).lower() for label in merged if self._normalize_label(label)}

                    if desired_set and desired_set != current_set:
                        label_result = self._apply_conversation_labels(account_id, conversation_id, merged)
                        if not label_result['ok']:
                            warnings.extend(label_result.get('warnings', []))
                            errors.extend(label_result.get('errors', []))
            except Exception as e:
                errors.append(f'exception_apply_labels:{e}')

        # Notify message whenever assignment is attempted successfully.
        if mapping.get('notify_message'):
            try:
                url = f"{base_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
                r = requests.post(url, json={"content": mapping['notify_message']}, headers=headers, timeout=timeout)
                if r.status_code not in (200, 201):
                    errors.append(f'notify_failed:{r.status_code}:{r.text}')
            except Exception as e:
                errors.append(f'exception_notify:{e}')

        ok = assigned is not None and len(errors) == 0
        _logger.info('assign_conversation[conv=%s]: FINAL assigned=%s assignee_id=%s ok=%s errors=%s warnings=%s',
                     conversation_id, assigned, agent_id if assigned == 'agent' else None,
                     ok, errors, warnings)
        return {
            'ok': ok,
            'assigned_to': assigned,
            'errors': errors,
            'warnings': warnings,
            'assignee_id': agent_id if assigned == 'agent' else None,
        }
