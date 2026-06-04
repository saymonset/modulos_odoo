import logging
from odoo import models

_logger = logging.getLogger(__name__)


class ChatbotSessionInherit(models.Model):
    _inherit = 'chatbot.session'

    def capturar_lead(self, datos):
        res = super(ChatbotSessionInherit, self).capturar_lead(datos)
        try:
            account_id = datos.get('account_id')
            conversation_id = datos.get('conversation_id')
            mapping_rec = None
            lead = None

            # Try to find lead id from the result and get its team
            lead_id = None
            try:
                lead_id = res.get('lead_info', {}).get('lead_id') or res.get('lead_id')
            except Exception:
                lead_id = None

            team = None
            if lead_id:
                lead = self.env['crm.lead'].sudo().browse(int(lead_id))
                if lead and lead.exists():
                    team = lead.team_id

            equipo = datos.get('equipo_asignado') or (self and getattr(self, 'equipo_asignado', None))
            flow_name = datos.get('flow_name') or datos.get('name_flow')

            # Select mapping with round-robin across mappings that share the same flow/team
            mapping_rec = self.env['chatwoot.mapping'].sudo().select_round_robin_mapping(
                team=team,
                equipo_asignado=equipo,
                flow_name=flow_name,
            )

            if mapping_rec and account_id and conversation_id:
                agent_details = self.env['chatwoot.client'].get_agent_details(
                    account_id,
                    agent_id=mapping_rec.chatwoot_agent_id or None,
                    agent_email=mapping_rec.chatwoot_agent_email or None,
                )
                assigned_agent_name = None
                assigned_agent_email = None
                if agent_details:
                    assigned_agent_name = agent_details.get('available_name') or agent_details.get('name') or agent_details.get('email')
                    assigned_agent_email = agent_details.get('email')

                mapping = {
                    'agent_id': mapping_rec.chatwoot_agent_id or None,
                    'agent_email': mapping_rec.chatwoot_agent_email or None,
                    'inbox_id': mapping_rec.chatwoot_inbox_id or None,
                    'prefer_assign_to_agent': mapping_rec.prefer_assign_to_agent,
                    'tags': [t.strip() for t in (mapping_rec.chatwoot_tags or '').split(',') if t.strip()],
                    'notify_message': (
                        f"Nuevo lead: {res.get('lead_info', {}).get('lead_id', '')}"
                        f" - {datos.get('solicitar_name') or datos.get('name','Sin nombre')}"
                        f" - {datos.get('solicitar_phone') or datos.get('phone','')}"
                        + (f"\n👤 Ejecutivo asignado: {assigned_agent_name} ({assigned_agent_email})" if assigned_agent_name else '')
                    )
                }
                # call client
                try:
                    result = self.env['chatwoot.client'].assign_conversation(account_id, conversation_id, mapping)
                    # log result in lead chatter or a field
                    if lead and lead.exists():
                        note = f"Chatwoot assign result: {result}"
                        if assigned_agent_name:
                            note += f"\nEjecutivo esperado: {assigned_agent_name} ({assigned_agent_email or 'sin email'})"
                        lead.message_post(body=note)
                except Exception:
                    _logger.exception('Error al notificar/assign a Chatwoot')
        except Exception:
            _logger.exception('Error en hook capturar_lead -> Chatwoot')
        return res
