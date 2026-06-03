import logging
from odoo import models

_logger = logging.getLogger(__name__)


class ChatbotSessionInherit(models.Model):
    _inherit = 'chatbot.session'

    def capturar_lead(self, datos):
        res = super(ChatbotSessionInherit, self).capturar_lead(datos)
        try:
            account_id = datos.get('account_id') or datos.get('account_id')
            conversation_id = datos.get('conversation_id') or datos.get('conversation_id')
            equipo = datos.get('equipo_asignado') or (self and getattr(self, 'equipo_asignado', None))
            mapping_rec = None
            if equipo:
                mapping_rec = self.env['chatwoot.mapping'].sudo().search([('equipo_asignado', '=', equipo), ('active', '=', True)], limit=1)
            if mapping_rec and account_id and conversation_id:
                mapping = {
                    'agent_id': mapping_rec.chatwoot_agent_id or None,
                    'inbox_id': mapping_rec.chatwoot_inbox_id or None,
                    'tags': [t.strip() for t in (mapping_rec.chatwoot_tags or '').split(',') if t.strip()],
                    'notify_message': f"Nuevo lead: {res.get('lead_info', {}).get('lead_id', '')} - {datos.get('solicitar_name') or datos.get('name','Sin nombre')} - {datos.get('solicitar_phone') or datos.get('phone','')}"
                }
                # call client
                try:
                    self.env['chatwoot.client'].assign_conversation(account_id, conversation_id, mapping)
                except Exception:
                    _logger.exception('Error al notificar/assign a Chatwoot')
        except Exception:
            _logger.exception('Error en hook capturar_lead -> Chatwoot')
        return res
