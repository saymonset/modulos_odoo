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

    # Campos básicos
    name = fields.Char(string='Nombre interno', help='Nombre descriptivo de la campaña')
    subject = fields.Char(string='Asunto', required=True, help='Asunto interno (no se envía)')
    mailing_type = fields.Selection([
        ('whatsapp', 'WhatsApp')
    ], default='whatsapp', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_queue', 'En cola'),
        ('sending', 'Enviando'),
        ('sent', 'Enviado'),
        ('canceled', 'Cancelado')
    ], default='draft', string='Estado', tracking=True)
    schedule_type = fields.Selection([
        ('now', 'Enviar ahora'),
        ('later', 'Programar para más tarde')
    ], default='now', string='Programación')
    scheduled_date = fields.Datetime(string='Fecha programada')

    # ----- CAMBIO: Selección directa de contactos con consentimiento -----
    partner_ids = fields.Many2many(
        'res.partner',
        'whatsapp_mailing_partner_rel',
        'whatsapp_mailing_id',
        'partner_id',
        string='Contactos con consentimiento',
        domain=[('consentimiento_whatsapp', '=', True)],
        help='Selecciona uno o varios contactos que hayan aceptado recibir WhatsApp.'
    )
    # --------------------------------------------------------------------

    # Campos específicos de WhatsApp
    whatsapp_text = fields.Html(
        string='Texto del Mensaje',
        help='Cuerpo del mensaje de WhatsApp. Puedes usar placeholders como {{ partner.name }}'
    )
    whatsapp_media_url = fields.Char(
        string='URL del Video o Imagen',
        help='Enlace público al video/imagen que se enviará como multimedia. Si está vacío, solo texto.'
    )
    campaign_whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='Plantilla WhatsApp (aprobada)',
        help='Si usas plantilla aprobada por Meta, selecciona aquí. Sobrescribe el texto libre.'
    )
    use_template = fields.Boolean(
        string='Usar plantilla aprobada',
        help='Marca para usar plantilla (obligatorio para marketing masivo). Si no, se envía texto libre (solo permitido en ventana de 24h).'
    )

    # Adjuntos (opcional)
    whatsapp_attachment_ids = fields.Many2many(
        'ir.attachment',
        'whatsapp_mailing_whatsapp_attachment_rel',
        'whatsapp_mailing_id',
        'attachment_id',
        string='Adjuntos de WhatsApp'
    )

    # -------------------------------------------------------------------------
    # Métodos principales
    # -------------------------------------------------------------------------
    def action_send_mailing(self):
        """Envía la campaña por WhatsApp"""
        for campaign in self:
            if campaign.state != 'draft':
                raise UserError(_('La campaña ya fue enviada o está en proceso.'))

            # Obtener partners seleccionados directamente
            partners = campaign._get_recipient_partners()
            if not partners:
                raise UserError(_('No hay destinatarios seleccionados.'))

            waba = self.env['waba.account'].search([('active', '=', True)], limit=1)
            if not waba:
                raise UserError(_('No hay cuenta WABA activa. Configúrala en WhatsApp > Cuentas WABA.'))

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

    # -------------------------------------------------------------------------
    # Métodos auxiliares
    # -------------------------------------------------------------------------
    def _get_recipient_partners(self):
        """Devuelve los partners seleccionados directamente en la campaña."""
        return self.partner_ids

    def _render_whatsapp_text(self, partner):
        """Renderiza el html del mensaje, convierte a texto plano y reemplaza placeholders"""
        if not self.whatsapp_text:
            return ''
        plain = html2plaintext(self.whatsapp_text)
        rendered = self.env['mail.render.mixin']._render_template(
            plain, 'res.partner', partner.ids
        ).get(partner.id, plain)
        return rendered

    def _extract_template_params(self, partner):
        """Devuelve una lista de parámetros según la cantidad esperada por la plantilla."""
        template = self.campaign_whatsapp_template_id
        expected_count = template.parameter_count if template else 0
        
        if expected_count == 0:
            return []
        elif expected_count == 1:
            return [partner.name or '']
        elif expected_count == 2:
            return [partner.name or '', partner.phone or '']
        else:
            # Si espera más, puedes personalizar
            return [partner.name or ''] + [''] * (expected_count - 1)

    def _send_free_text_message(self, partner, message_body, media_url, waba):
        """Envía mensaje de texto (opcionalmente con multimedia) vía API de Meta."""
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