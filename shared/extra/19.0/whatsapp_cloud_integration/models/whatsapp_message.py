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
    template_name = fields.Char(string='Nombre de la Plantilla', required=True,
                                help='Ej: hello_world, pedido_confirmado_con_ubicacion')
    language_code = fields.Selection([
        ('en_US', 'Inglés (US)'),
        ('es', 'Español'),
    ], string='Idioma de la plantilla', required=True, default='es',
        help='Selecciona el idioma en que está creada la plantilla en Meta.')
    parameter_values = fields.Text(string='Valores de Parámetros (JSON)',
                                   help='Ej: ["Simón", "s0003", "+58414271652", "Mi Tienda"]')

    def action_send_whatsapp_message(self):
        self.ensure_one()
        # Validar que el partner tenga teléfono
        recipient = self.partner_id.phone
        if not recipient:
            raise UserError(_('El cliente no tiene número de teléfono.'))

        # Limpiar formato
        recipient = recipient.strip().replace(' ', '').replace('+', '')

        url = f"https://graph.facebook.com/v25.0/{self.waba_account_id.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.waba_account_id.access_token}',
            'Content-Type': 'application/json'
        }

        payload = {
            'messaging_product': 'whatsapp',
            'to': recipient,
            'type': 'template',
            'template': {
                'name': self.template_name,
                'language': {'code': self.language_code}   # ← usa el idioma seleccionado
            }
        }

        # Incorporar parámetros si existen
        if self.parameter_values:
            try:
                params = json.loads(self.parameter_values)
                if isinstance(params, list):
                    components = [{
                        'type': 'body',
                        'parameters': [{'type': 'text', 'text': str(p)} for p in params]
                    }]
                    payload['template']['components'] = components
                else:
                    raise UserError(_('Los parámetros deben ser un array JSON.'))
            except json.JSONDecodeError:
                raise UserError(_('El campo de parámetros no es un JSON válido.'))

        # Enviar petición
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            # Registrar historial
            history_vals = {
                'partner_id': self.partner_id.id,
                'waba_account_id': self.waba_account_id.id,
                'direction': 'outgoing',
                'template_name': self.template_name,
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
                'template_name': self.template_name,
                'recipient_number': recipient,
                'message_body': json.dumps(payload, indent=2),
                'response_data': error_detail,
                'status': 'error',
            })
            raise UserError(_(f'Error al enviar: {error_detail}'))