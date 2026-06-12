import json
import logging
from odoo import models, fields

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

            _logger.info('RR[session] INICIO: lead_id=%s account=%s conv=%s',
                         lead_id, account_id, conversation_id)

            team = None
            if lead_id:
                lead = self.env['crm.lead'].sudo().browse(int(lead_id))
                if lead and lead.exists():
                    team = lead.team_id
                    _logger.info('RR[session] lead encontrado: id=%s team=%s(%s)',
                                 lead.id, team.name if team else None, team.id if team else None)
                else:
                    _logger.warning('RR[session] lead_id=%s no existe en BD', lead_id)
            else:
                _logger.warning('RR[session] no se pudo extraer lead_id de res=%s', res)

            equipo = datos.get('equipo_asignado') or (self and getattr(self, 'equipo_asignado', None))
            flow_name = datos.get('flow_name') or datos.get('name_flow')
            _logger.info('RR[session] datos: equipo=%s flow_name=%s team=%s', equipo, flow_name, team.name if team else None)

            # Select mapping with round-robin across mappings that share the same flow/team
            _logger.info('RR[session] llamando select_round_robin_mapping team=%s equipo=%s flow=%s',
                         team.name if team else None, equipo, flow_name)
            mapping_rec = self.env['chatwoot.mapping'].sudo().select_round_robin_mapping(
                team=team,
                equipo_asignado=equipo,
                flow_name=flow_name,
            )

            if mapping_rec:
                _logger.info('RR[session] mapping SELECCIONADO: id=%s name=%s agent_id=%s agent_email=%s inbox_id=%s',
                             mapping_rec.id, mapping_rec.name,
                             mapping_rec.chatwoot_agent_id, mapping_rec.chatwoot_agent_email,
                             mapping_rec.chatwoot_inbox_id)
            else:
                _logger.warning('RR[session] NO SE ENCONTRÓ MAPPING - team=%s equipo=%s flow=%s',
                                team.name if team else None, equipo, flow_name)

            if mapping_rec and account_id and conversation_id:
                # Asignar usuario Odoo por email del mapping Chatwoot
                user = self.env['res.users'].sudo().search([
                    ('login', '=', mapping_rec.chatwoot_agent_email)
                ], limit=1)
                if user and lead and lead.exists():
                    lead.write({'user_id': user.id})
                    _logger.info('RR[session] lead user_id asignado: user=%s(%s) email=%s',
                                 user.name, user.id, user.login)
                    # Enviar email de notificación
                    if user.partner_id.email:
                        try:
                            subject = f"Nuevo lead asignado: {lead.name}"
                            servicio = lead.name.split(' - ')[0] if ' - ' in lead.name else lead.name
                            body = (
                                f"<p>Hola {user.name},</p>"
                                f"<p>Se te ha asignado un nuevo lead generado desde el chatbot de UNISA.</p>"
                                f"<br/>"
                                f"<p><strong>Datos del paciente:</strong></p>"
                                f"<ul>"
                                f"<li><strong>Nombre:</strong> {lead.contact_name or ''}</li>"
                                f"<li><strong>Teléfono:</strong> {lead.phone or ''}</li>"
                                f"<li><strong>Email:</strong> {lead.email_from or ''}</li>"
                                f"<li><strong>Servicio:</strong> {servicio}</li>"
                                f"<li><strong>Equipo:</strong> {lead.team_id.name or 'Sin equipo'}</li>"
                                f"</ul>"
                                f"<p>Por favor, contacta al paciente a la brevedad para dar seguimiento a su solicitud.</p>"
                                f"<p>Saludos,<br/><strong>Sistema UNISA Salud</strong></p>"
                            )
                            email_from = self.env['ir.config_parameter'].sudo().get_param('mail.default.from', 'admin@unisasalud.com')
                            self.env['mail.mail'].sudo().create({
                                'subject': subject,
                                'body_html': body,
                                'email_to': user.partner_id.email,
                                'email_from': email_from,
                                'model': 'crm.lead',
                                'res_id': lead.id,
                            })
                            _logger.info('RR[session] email de notificación creado para %s (%s)',
                                         user.name, user.partner_id.email)
                        except Exception as e:
                            _logger.warning('RR[session] error creando email: %s', e)
                else:
                    _logger.warning('RR[session] no se encontró user Odoo para email=%s',
                                    mapping_rec.chatwoot_agent_email)

                _logger.info('RR[session] consultando get_agent_details account=%s agent_id=%s agent_email=%s',
                             account_id, mapping_rec.chatwoot_agent_id, mapping_rec.chatwoot_agent_email)
                agent_details = self.env['chatwoot.client'].get_agent_details(
                    account_id,
                    agent_id=mapping_rec.chatwoot_agent_id or None,
                    agent_email=mapping_rec.chatwoot_agent_email or None,
                )
                _logger.info('RR[session] agent_details RESULTADO: %s', agent_details)
                assigned_agent_name = None
                assigned_agent_email = None
                if agent_details:
                    assigned_agent_name = agent_details.get('available_name') or agent_details.get('name') or agent_details.get('email')
                    assigned_agent_email = agent_details.get('email')
                    _logger.info('RR[session] agente resuelto: name=%s email=%s', assigned_agent_name, assigned_agent_email)
                else:
                    _logger.warning('RR[session] NO se obtuvieron agent_details - agent_id=%s agent_email=%s',
                                    mapping_rec.chatwoot_agent_id, mapping_rec.chatwoot_agent_email)

                equipo_legible = (mapping_rec.equipo_asignado or '').replace('_', ' ')
                if assigned_agent_email:
                    notify_msg = f"Tu consulta sobre {equipo_legible} ha sido registrada.\n👤 Ejecutivo asignado: {assigned_agent_email}"
                else:
                    notify_msg = f"Tu consulta sobre {equipo_legible} ha sido registrada."

                mapping = {
                    'agent_id': mapping_rec.chatwoot_agent_id or None,
                    'agent_email': mapping_rec.chatwoot_agent_email or None,
                    'inbox_id': mapping_rec.chatwoot_inbox_id or None,
                    'prefer_assign_to_agent': mapping_rec.prefer_assign_to_agent,
                    'tags': [t.strip() for t in (mapping_rec.chatwoot_tags or '').split(',') if t.strip()],
                    'notify_message': notify_msg,
                    'equipo_asignado': mapping_rec.equipo_asignado or '',
                }
                _logger.info('RR[session] asignando conversación conv=%s account=%s mapping=%s',
                             conversation_id, account_id, {
                                 'agent_id': mapping['agent_id'],
                                 'agent_email': mapping['agent_email'],
                                 'inbox_id': mapping['inbox_id'],
                                 'prefer_assign_to_agent': mapping['prefer_assign_to_agent'],
                                 'tags': mapping['tags'],
                                 'notify_message_len': len(mapping.get('notify_message', '')),
                             })
                # call client
                try:
                    result = self.env['chatwoot.client'].assign_conversation(account_id, conversation_id, mapping)
                    _logger.info('RR[session] assign_conversation RESULTADO: %s', result)
                    if lead and lead.exists():
                        ejecutivo = assigned_agent_name or mapping_rec.chatwoot_agent_email or 'sin datos'
                        if result.get('assigned_to') in ('agent', 'preserved'):
                            lead.message_post(body=f"Solicitud recibida. Ejecutivo asignado: {ejecutivo}")
                            _logger.info('RR[session] chatter message posted: ejecutivo=%s', ejecutivo)
                        elif result.get('assigned_to') != 'existing':
                            lead.message_post(body=f"Solicitud recibida. Ejecutivo asignado: {ejecutivo}")
                            _logger.info('RR[session] chatter message posted: ejecutivo=%s', ejecutivo)
                        else:
                            _logger.info('RR[session][conv=%s]: assignee skipped, no chatter',
                                         conversation_id)
                            ejecutivo = 'preservado'
                        # Store chatwoot ids on the lead for backup lookups
                        try:
                            lead.sudo().write({
                                'chatwoot_conversation_id': str(conversation_id),
                                'chatwoot_account_id': str(account_id),
                                'chatwoot_processing_status': 'assigned' if result.get('ok', False) else 'error',
                                'chatwoot_processed_at': fields.Datetime.now(),
                                'chatwoot_assigned_agent_name': ejecutivo if result.get('ok', False) else False,
                                'chatwoot_assign_log': json.dumps({
                                    'assigned_to': result.get('assigned_to'),
                                    'assignee_id': result.get('assignee_id'),
                                    'mapping_id': mapping_rec.id,
                                    'agent_name': ejecutivo,
                                    'errors': result.get('errors', []),
                                    'warnings': result.get('warnings', []),
                                }),
                                'chatwoot_assign_failed': not result.get('ok', False),
                            })
                            _logger.info('RR[session] lead %s escrito con estado=%s asignado_a=%s',
                                         lead.id, result.get('ok', False), result.get('assigned_to'))
                        except Exception as e_write:
                            _logger.warning('RR[session] Error guardando chatwoot ids en lead %s: %s', lead.id, e_write)
                except Exception:
                    _logger.exception('RR[session] Error al notificar/assign a Chatwoot')
            else:
                _logger.warning('RR[session] SKIP: mapping=%s account=%s conv=%s',
                                bool(mapping_rec), account_id, conversation_id)
            _logger.info('RR[session] FIN')
        except Exception:
            _logger.exception('RR[session] Error en hook capturar_lead -> Chatwoot')
        return res
