from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

class WhatsAppMailing(models.Model):
    _name = 'whatsapp.mailing'
    _description = 'Campaña de WhatsApp Marketing'
    _rec_name = 'subject'
    _order = 'create_date desc'

    name = fields.Char(string='Nombre interno')
    subject = fields.Char(string='Asunto', required=True)
    mailing_type = fields.Selection([
        ('whatsapp', 'WhatsApp')
    ], default='whatsapp', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_queue', 'En cola'),
        ('sending', 'Enviando'),
        ('sent', 'Enviado'),
        ('canceled', 'Cancelado')
    ], default='draft', string='Estado')
    schedule_type = fields.Selection([
        ('now', 'Enviar ahora'),
        ('later', 'Programar para más tarde')
    ], default='now', string='Programación')
    scheduled_date = fields.Datetime(string='Fecha programada')

    partner_ids = fields.Many2many(
        'res.partner',
        'whatsapp_mailing_partner_rel',
        'whatsapp_mailing_id',
        'partner_id',
        string='Contactos con consentimiento',
        domain=[('consentimiento_whatsapp', '=', True)],
        help='Selecciona uno o varios contactos que hayan aceptado recibir WhatsApp.'
    )

    # Campos para envío sin plantilla (texto libre)
    whatsapp_text = fields.Html(
        string='Texto del Mensaje',
        help='Cuerpo del mensaje de WhatsApp. Puedes usar placeholders como {{ partner.name }}'
    )
    whatsapp_media_url = fields.Char(
        string='URL del Video o Imagen',
        help='Enlace público al video/imagen que se enviará como multimedia.'
    )

    # Campos para plantilla aprobada
    use_template = fields.Boolean(string='Usar plantilla aprobada')
    campaign_whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='Plantilla WhatsApp (aprobada)'
    )
    # Almacena los valores de los parámetros en formato JSON
    parameter_values = fields.Text(
        string='Valores de parámetros',
        default='[]', 
        help='Almacena los valores de los parámetros en formato JSON según el esquema de la plantilla. '
             'Ejemplo: ["https://.../video.mp4", "Texto del mensaje"]'
    )

    whatsapp_attachment_ids = fields.Many2many(
        'ir.attachment',
        'whatsapp_mailing_whatsapp_attachment_rel',
        'whatsapp_mailing_id',
        'attachment_id',
        string='Adjuntos de WhatsApp'
    )

    def action_send_mailing(self):
        for campaign in self:
            if campaign.state != 'draft':
                raise UserError(_('La campaña ya fue enviada o está en proceso.'))

            partners = campaign._get_recipient_partners()
            if not partners:
                raise UserError(_('No hay destinatarios seleccionados.'))

            waba = self.env['waba.account'].search([('active', '=', True)], limit=1)
            if not waba:
                raise UserError(_('No hay cuenta WABA activa.'))

            if campaign.use_template and not campaign.campaign_whatsapp_template_id:
                raise UserError(_('Debes seleccionar una plantilla aprobada.'))

            campaign.write({'state': 'sending'})
            for partner in partners:
                if not partner.phone:
                    _logger.warning(f'WhatsApp: Contacto {partner.name} sin teléfono, omitido')
                    continue

                if campaign.use_template:
                    params = campaign._extract_template_params(partner)
                    campaign.campaign_whatsapp_template_id.send_to_partner(partner, params, waba.id)
                else:
                    message_body = campaign._render_whatsapp_text(partner)
                    media_url = campaign.whatsapp_media_url
                    campaign._send_free_text_message(partner, message_body, media_url, waba)

            campaign.write({'state': 'sent'})
        return True

    def _get_recipient_partners(self):
        return self.partner_ids

    def _render_whatsapp_text(self, partner):
        if not self.whatsapp_text:
            return ''
        plain = html2plaintext(self.whatsapp_text)
        rendered = self.env['mail.render.mixin']._render_template(
            plain, 'res.partner', partner.ids
        ).get(partner.id, plain)
        return rendered

    def _extract_template_params(self, partner):
        template = self.campaign_whatsapp_template_id
        expected_count = template.parameter_count if template else 0
        if expected_count == 0:
            return []

        try:
            params = json.loads(self.parameter_values or '[]')
            if not isinstance(params, list):
                params = []
        except json.JSONDecodeError:
            params = []

        if len(params) != expected_count:
            raise UserError(_(
                'La plantilla "%s" espera %s parámetros, pero se proporcionaron %s.',
                template.name, expected_count, len(params)
            ))

        rendered_params = []
        for idx, val in enumerate(params, start=1):
            if template.has_video_header and idx == 1:
                rendered_params.append(val)
            else:
                rendered = self.env['mail.render.mixin']._render_template(
                    str(val), 'res.partner', partner.ids
                ).get(partner.id, val)
                rendered_params.append(rendered)
        return rendered_params

    def _send_free_text_message(self, partner, message_body, media_url, waba):
        # (el mismo código que ya tenías, sin cambios)
        to_number = partner.phone.strip().replace(' ', '').replace('+', '').replace('-', '')
        # Formatear números de Venezuela si vienen sin código de país (ej: 0412... -> 58412...)
        if to_number.startswith('04') and len(to_number) == 11:
            to_number = '58' + to_number[1:]
        elif to_number.startswith('4') and len(to_number) == 10:
            to_number = '58' + to_number
        url = f"https://graph.facebook.com/v25.0/{waba.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {waba.access_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': 'text',
            'text': {'body': message_body[:1024]}
        }
        if media_url:
            ext = media_url.split('.')[-1].lower()
            if ext in ['mp4', 'mov', 'avi', 'mpeg']:
                payload['type'] = 'video'
                payload['video'] = {'link': media_url}
            else:
                payload['type'] = 'image'
                payload['image'] = {'link': media_url}
            del payload['text']
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            self.env['whatsapp.history'].create({
                'partner_id': partner.id,
                'waba_account_id': waba.id,
                'direction': 'outgoing',
                'recipient_number': to_number,
                'message_body': message_body,
                'response_data': json.dumps(result),
                'status': 'sent',
                'message_id': result.get('messages', [{}])[0].get('id', '')
            })
            _logger.info(f'WhatsApp enviado a {to_number}')
        except Exception as e:
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_msg = e.response.json().get('error', {}).get('message', error_msg)
                except:
                    pass
            self.env['whatsapp.history'].create({
                'partner_id': partner.id,
                'waba_account_id': waba.id,
                'direction': 'outgoing',
                'recipient_number': to_number,
                'message_body': message_body,
                'response_data': error_msg,
                'status': 'error',
            })
            _logger.error(f'Error enviando a {to_number}: {error_msg}')