from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)

MAX_CAPTION_LENGTH = 1024


class WhatsappMessageWizard(models.TransientModel):
    _name = 'whatsapp.message.wizard'
    _description = 'Wizard para enviar mensajes de WhatsApp'

    partner_id = fields.Many2one('res.partner', string='Cliente', required=True)
    waba_account_id = fields.Many2one('waba.account', string='Cuenta WhatsApp', required=True,
                                      domain=[('active', '=', True)])
    template_id = fields.Many2one('whatsapp.template', string='Plantilla', required=True)
    parameter_values = fields.Text(
        string='Valores de Parámetros (JSON)',
        help='Ej: ["https://urlvideo.mp4", "Simón"] (primero la URL del video si la plantilla tiene header)'
    )

    @staticmethod
    def _normalizar_telefono(recipient):
        """Normaliza un número de teléfono al formato internacional para Meta."""
        recipient = recipient.strip().replace(' ', '').replace('+', '').replace('-', '')
        # Formatear números de Venezuela si vienen sin código de país (ej: 0412... -> 58412...)
        if recipient.startswith('04') and len(recipient) == 11:
            recipient = '58' + recipient[1:]
        elif recipient.startswith('4') and len(recipient) == 10:
            recipient = '58' + recipient
        return recipient

    def send_image_with_caption(self, partner_id, image_url, caption, waba_account_id=None):
        """Envía una imagen pública con caption en una conversación iniciada.

        Se usa para mostrar productos con su nombre y precio en el carrito del
        chatbot (no requiere plantilla aprobada porque responde a un mensaje
        del usuario dentro de la ventana de conversación de 24h).
        """
        partner = self.env['res.partner'].sudo().browse(partner_id)
        if not partner.phone:
            return {'success': False, 'message': 'El cliente no tiene número de teléfono.'}

        waba = self.env['waba.account'].sudo().browse(waba_account_id) if waba_account_id \
            else self.env['waba.account'].sudo().search([('active', '=', True)], limit=1)
        if not waba:
            return {'success': False, 'message': 'No hay cuenta WABA activa.'}

        to_number = self._normalizar_telefono(partner.phone)
        url = f"https://graph.facebook.com/v25.0/{waba.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {waba.access_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_number,
            'type': 'image',
            'image': {
                'link': image_url,
                'caption': (caption or '')[:MAX_CAPTION_LENGTH],
            },
        }
        try:
            _logger.info("=== PAYLOAD IMAGEN CON CAPTION ===")
            _logger.info(json.dumps(payload, indent=2))
            _logger.info("==================================")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            self.env['whatsapp.history'].create({
                'partner_id': partner.id,
                'waba_account_id': waba.id,
                'direction': 'outgoing',
                'recipient_number': to_number,
                'message_body': caption,
                'response_data': json.dumps(result, indent=2),
                'status': 'sent',
                'message_id': result.get('messages', [{}])[0].get('id', ''),
            })
            return {'success': True, 'message_id': result.get('messages', [{}])[0].get('id', '')}
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if e.response is not None:
                try:
                    error_detail = e.response.json().get('error', {}).get('message', error_detail)
                except Exception:
                    pass
            self.env['whatsapp.history'].create({
                'partner_id': partner.id,
                'waba_account_id': waba.id,
                'direction': 'outgoing',
                'recipient_number': to_number,
                'message_body': caption,
                'response_data': error_detail,
                'status': 'error',
            })
            _logger.error(f"Error enviando imagen a {to_number}: {error_detail}")
            return {'success': False, 'message': error_detail}

    def action_send_whatsapp_message(self):
        self.ensure_one()
        recipient = self.partner_id.phone
        if not recipient:
            raise UserError(_('El cliente no tiene número de teléfono.'))

        recipient = self._normalizar_telefono(recipient)

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
                # Meta prohíbe terminantemente enviar saltos de línea dentro de las variables (como {{1}}).
                # Esto causa el error "132018 There’s an issue with the parameters".
                # Limpiamos los saltos de línea de todos los parámetros de texto.
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