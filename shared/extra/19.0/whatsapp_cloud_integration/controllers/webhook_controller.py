from odoo import http
from odoo.http import request
from markupsafe import Markup
import json
import logging
import base64

_logger = logging.getLogger(__name__)

_DESCRIPCION_COMPROBANTE = 'Comprobante de pago - Transferencia / Pago Móvil'


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
                                ('phone', 'ilike', from_number)
                            ], limit=1)

                            if not partner:
                                # Si no existe, podrías crearlo automáticamente (opcional)
                                partner = request.env['res.partner'].sudo().create({
                                    'name': from_number,
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

                            # Procesar imágenes entrantes (vaucher de pago)
                            if msg_type == 'image':
                                self._procesar_imagen_entrante(partner, message, waba_account)

                return "OK", 200
            except Exception as e:
                _logger.error("Error procesando webhook: %s", e, exc_info=True)
                return "Error", 500

    # -------------------------------------------------------------------------
    #  IMÁGENES ENTRANTES: VAUCHER DE PAGO
    # -------------------------------------------------------------------------
    def _procesar_imagen_entrante(self, partner, message, waba_account):
        """Descarga la imagen recibida y la adjunta a la orden de venta pendiente
        del partner como comprobante de pago (patrón de bcv_rate_update_venezuela)."""
        image_info = message.get('image', {})
        media_id = image_info.get('id')
        if not media_id:
            _logger.warning(f"Mensaje de imagen sin media_id para {partner.name}")
            return False
        if not waba_account:
            _logger.warning(f"Sin cuenta WABA activa para procesar imagen de {partner.name}")
            return False

        datos, mimetype, filename = waba_account.download_media(media_id)
        if not datos:
            _logger.error(f"No se pudo descargar la imagen {media_id}")
            return False

        order = self._buscar_orden_pendiente(partner)
        if not order:
            _logger.info(f"Sin orden pendiente para {partner.name}; imagen guardada solo en historial")
            return False

        try:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': datos,
                'res_model': 'sale.order',
                'res_id': order.id,
                'mimetype': mimetype,
                'description': _DESCRIPCION_COMPROBANTE,
            })
            order.sudo().write({
                'payment_proof': datos,
                'payment_proof_filename': filename,
            })
            timestamp = int(attachment.write_date.timestamp()) if attachment.write_date else ''
            attachment_url = f"/web/image/{attachment.id}" + (f"?unique={timestamp}" if timestamp else "")
            img_tag = f'<div><img src="{attachment_url}" style="max-width:100%; max-height:300px;"/></div>'
            body_html = f"""
            <p>🧾 <strong>Comprobante de pago adjunto (WhatsApp)</strong></p>
            <ul>
                <li>📱 Número: {partner.phone or partner.mobile or ''}</li>
                <li>🖼️ Imagen: {filename}</li>
            </ul>
            {img_tag}
            """
            order.sudo().message_post(
                body=Markup(body_html),
                attachment_ids=[attachment.id],
                message_type='comment',
                subtype_id=request.env.ref('mail.mt_comment').id
            )
            _logger.info(f"✅ Vaucher adjuntado a orden {order.name}")
            return True
        except Exception as e:
            _logger.error(f"Error adjuntando vaucher a {order.name}: {e}", exc_info=True)
            return False

    def _buscar_orden_pendiente(self, partner):
        """Busca la orden de venta del partner que aún no tiene comprobante."""
        order = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done']),
            ('payment_proof', '=', False),
        ], order='create_date desc', limit=1)
        return order if order else False