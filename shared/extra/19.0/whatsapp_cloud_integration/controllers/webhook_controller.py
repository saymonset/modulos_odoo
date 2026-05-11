from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class WhatsappWebhook(http.Controller):

    @http.route('/whatsapp/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def webhook_handler(self):
        # Verificación para GET (cuando Meta valida el webhook)
        if request.httprequest.method == 'GET':
            mode = request.params.get('hub.mode')
            challenge = request.params.get('hub.challenge')
            verify_token = request.params.get('hub.verify_token')

            if mode and verify_token:
                # Buscar la cuenta WABA que tenga este verify_token
                waba = request.env['waba.account'].sudo().search([('verify_token', '=', verify_token)], limit=1)
                if waba and mode == 'subscribe':
                    _logger.info(f"Webhook verificado exitosamente para cuenta {waba.name}")
                    return challenge
                else:
                    return "Verification token mismatch", 403
            return "OK", 200

        # Procesamiento de POST (mensajes entrantes)
        elif request.httprequest.method == 'POST':
            try:
                data = json.loads(request.httprequest.data)
                _logger.info("Webhook recibido: %s", json.dumps(data, indent=2))

                # Extraer información de mensajes
                entries = data.get('entry', [])
                for entry in entries:
                    changes = entry.get('changes', [])
                    for change in changes:
                        value = change.get('value', {})
                        messages = value.get('messages', [])
                        for message in messages:
                            # Determinar el número de teléfono del remitente (from)
                            from_number = message.get('from')
                            # Obtener el texto si es un mensaje de texto
                            msg_type = message.get('type')
                            text_body = ''
                            if msg_type == 'text':
                                text_body = message.get('text', {}).get('body', '')

                            # Buscar el partner por teléfono (debes manejar el formato)
                            partner = request.env['res.partner'].sudo().search([
                                '|', ('mobile', 'ilike', from_number),
                                ('phone', 'ilike', from_number)
                            ], limit=1)

                            if not partner:
                                # Si no existe, podrías crearlo automáticamente (opcional)
                                partner = request.env['res.partner'].sudo().create({
                                    'name': from_number,
                                    'mobile': from_number,
                                    'phone': from_number,
                                })

                            # Obtener la cuenta WABA (podrías buscarla por el número destino)
                            # Aquí asumo que la primera cuenta activa sirve; puedes mejorarlo
                            waba_account = request.env['waba.account'].sudo().search([('active', '=', True)], limit=1)

                            # Registrar en historial
                            history_vals = {
                                'partner_id': partner.id,
                                'waba_account_id': waba_account.id if waba_account else False,
                                'direction': 'incoming',
                                'recipient_number': from_number,
                                'message_body': text_body,
                                'response_data': json.dumps(message, indent=2),
                                'status': 'received',
                                'message_id': message.get('id'),
                            }
                            request.env['whatsapp.history'].sudo().create(history_vals)

                return "OK", 200
            except Exception as e:
                _logger.error("Error procesando webhook: %s", e, exc_info=True)
                return "Error", 500