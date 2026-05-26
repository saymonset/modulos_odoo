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

    whatsapp_text = fields.Html(
        string='Texto del Mensaje',
        help='Cuerpo del mensaje de WhatsApp. Puedes usar placeholders como {{ partner.name }}'
    )
    whatsapp_media_url = fields.Char(
        string='URL del Video o Imagen',
        help='Enlace público al video/imagen que se enviará como multimedia.'
    )
    campaign_whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='Plantilla WhatsApp (aprobada)'
    )
    use_template = fields.Boolean(string='Usar plantilla aprobada')
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
        """Devuelve una lista de parámetros según la plantilla seleccionada.
        Si la plantilla tiene encabezado de video, el primer parámetro es la URL del video (campo whatsapp_media_url).
        Los siguientes parámetros (si los hay) se extraen del texto o de otros campos.
        """
        template = self.campaign_whatsapp_template_id
        expected_count = template.parameter_count if template else 0
        if expected_count == 0:
            return []
        params = []
        # Si la plantilla tiene video header, el primer parámetro es la URL del video
        if template.has_video_header:
            if self.whatsapp_media_url:
                params.append(self.whatsapp_media_url)
            else:
                raise UserError(_('La plantilla seleccionada requiere una URL de video. Por favor, completa el campo "URL del Video o Imagen".'))
            remaining = expected_count - 1
        else:
            remaining = expected_count

        # Completar con valores de partner según los parámetros restantes
        if remaining >= 1:
            params.append(partner.name or '')
        if remaining >= 2:
            params.append(partner.phone or '')
        # Si se necesitan más, puedes añadir lógica adicional
        while len(params) < expected_count:
            params.append('')
        return params

    def _send_free_text_message(self, partner, message_body, media_url, waba):
        to_number = partner.phone.strip().replace(' ', '').replace('+', '')

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