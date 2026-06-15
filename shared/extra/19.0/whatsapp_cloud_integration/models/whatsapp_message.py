from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class WhatsappMessageWizard(models.TransientModel):
    _name = 'whatsapp.message.wizard'
    _description = 'Wizard para enviar mensajes de WhatsApp'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    waba_account_id = fields.Many2one('waba.account', string='Cuenta WhatsApp', required=True,
                                      domain=[('active', '=', True)])
    template_id = fields.Many2one('whatsapp.template', string='Plantilla', required=True)
    parameter_values = fields.Text(
        string='Valores de Parámetros (JSON)',
        help='Ej: ["https://urlvideo.mp4", "Simón"] (primero la URL del video/imagen si la plantilla tiene header)'
    )

    def action_send_whatsapp_message(self):
        self.ensure_one()
        recipient = self.partner_id.phone
        if not recipient:
            raise UserError(_('El cliente no tiene número de teléfono.'))

        recipient = recipient.strip().replace(' ', '').replace('+', '').replace('-', '')
        # Formatear números de Venezuela si vienen sin código de país (ej: 0412... -> 58412...)
        if recipient.startswith('04') and len(recipient) == 11:
            recipient = '58' + recipient[1:]
        elif recipient.startswith('4') and len(recipient) == 10:
            recipient = '58' + recipient

        url = f"https://graph.facebook.com/v25.0/{self.waba_account_id.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.waba_account_id.access_token}',
            'Content-Type': 'application/json'
        }

        template = self.template_id
        payload = {
            'messaging_product': 'whatsapp',
            'to': recipient,
            'type': 'template',
            'template': {
                'name': template.name,
                'language': {'code': template.language_code}
            }
        }

        # Procesar parámetros
        params = []
        if self.parameter_values:
            try:
                params = json.loads(self.parameter_values)
                if not isinstance(params, list):
                    raise UserError(_('Los parámetros deben ser un array JSON.'))
            except json.JSONDecodeError:
                raise UserError(_('El campo de parámetros no es un JSON válido.'))

        # Construir componentes según el tipo de plantilla
        components = []

        # Si tiene video header, el primer parámetro debe ser la URL del video
        if template.has_video_header:
            if not params or len(params) < 1:
                raise UserError(_('La plantilla con video requiere al menos la URL del video como primer parámetro.'))
            video_url = params[0]
            components.append({
                'type': 'header',
                'parameters': [{
                    'type': 'video',
                    'video': {'link': video_url}
                }]
            })
            # El resto de parámetros van al body (si hay)
            body_params = params[1:]
            if body_params:
                cleaned_body_params = [str(p).replace('\n', '  ').replace('\r', '') for p in body_params]
                components.append({
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': p} for p in cleaned_body_params]
                })
        elif template.has_image_header:
            if not params or len(params) < 1:
                raise UserError(_('La plantilla con imagen requiere al menos la URL de la imagen como primer parámetro.'))
            image_url = params[0]
            components.append({
                'type': 'header',
                'parameters': [{
                    'type': 'image',
                    'image': {'link': image_url}
                }]
            })
            body_params = params[1:]
            if body_params:
                cleaned_body_params = [str(p).replace('\n', '  ').replace('\r', '') for p in body_params]
                components.append({
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': p} for p in cleaned_body_params]
                })
        else:
            # Plantilla sin header de video: todos los parámetros van al body
            if params:
                cleaned_params = [str(p).replace('\n', '  ').replace('\r', '') for p in params]
                components.append({
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': p} for p in cleaned_params]
                })

        if components:
            payload['template']['components'] = components

        # Enviar petición
        try:
            _logger.info("=== PAYLOAD A ENVIAR A WHATSAPP ===")
            _logger.info(json.dumps(payload, indent=2))
            _logger.info("===================================")

            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            history_vals = {
                'partner_id': self.partner_id.id,
                'waba_account_id': self.waba_account_id.id,
                'direction': 'outgoing',
                'template_name': template.display_name,
                'recipient_number': recipient,
                'message_body': json.dumps(payload, indent=2),
                'response_data': json.dumps(result, indent=2),
                'status': 'sent',
                'message_id': result.get('messages', [{}])[0].get('id', '')
            }
            self.env['whatsapp.history'].create(history_vals)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mensaje enviado'),
                    'message': _('WhatsApp enviado correctamente. ID: %s') % history_vals['message_id'],
                    'type': 'success',
                    'sticky': False,
                }
            }
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if e.response is not None:
                try:
                    error_detail = e.response.json().get('error', {}).get('message', error_detail)
                except:
                    pass
            self.env['whatsapp.history'].create({
                'partner_id': self.partner_id.id,
                'waba_account_id': self.waba_account_id.id,
                'direction': 'outgoing',
                'template_name': template.display_name,
                'recipient_number': recipient,
                'message_body': json.dumps(payload, indent=2),
                'response_data': error_detail,
                'status': 'error',
            })
            raise UserError(_(f'Error al enviar: {error_detail}'))