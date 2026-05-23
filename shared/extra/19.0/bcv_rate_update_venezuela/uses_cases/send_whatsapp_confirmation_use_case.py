import logging
import re  # ← Importación necesaria
from odoo import _

_logger = logging.getLogger(__name__)

class SendWhatsappConfirmationUseCase:
    def __init__(self, env):
        self.env = env

    def execute(self, options):
        order = options.get('order')
        success, message = self._send_whatsapp_confirmation(order)
        return {'success': success, 'message': message}

    def _send_whatsapp_confirmation(self, order):
        template = self.env['whatsapp.template'].sudo().search([
            ('name', '=', 'pedido_confirmado_ubicacion'),
            ('active', '=', True)
        ], limit=1)

        if not template:
            msg = f"No se encontró la plantilla 'pedido_confirmado_ubicacion' para la orden {order.name}"
            _logger.error(msg)
            return False, msg

        existing = self.env['whatsapp.history'].sudo().search([
            ('sale_order_id', '=', order.id),
            ('template_name', '=', template.name),
            ('direction', '=', 'outgoing'),
        ], limit=1)

        if existing:
            msg = f"El mensaje para la orden {order.name} ya fue enviado el {existing.timestamp}"
            _logger.warning(msg)
            return True, msg

        # Dirección de la empresa
        company_address = f"{order.company_id.street or ''} {order.company_id.city or ''} {order.company_id.zip or ''}".strip()
        if not company_address:
            company_address = "CC El Mercado, Av. Llano Adentro, Porlamar"
        
        # Dirección del partner (cliente)
        persona_address = order.partner_id.street or ''
        if persona_address:
            persona_address += ", "
        persona_address += f"{order.partner_id.city or ''} {order.partner_id.zip or ''}".strip()

        # Teléfono: limpiar y normalizar
        clean_phone = re.sub(r'\D', '', order.company_id.phone or '')
        if len(clean_phone) == 12 and clean_phone.startswith('58'):
            clean_phone = '0' + clean_phone[2:]   # 582954142087 -> 0414...
        elif len(clean_phone) == 10:
            clean_phone = '0' + clean_phone

        # Horario: eliminar tabuladores y espacios múltiples
        horario_raw = order.company_id.schedule_info or "Abierto - Cierra a las 7:00 p.m."
        horario_limpio = ' '.join(horario_raw.split())

        parameter_values = [
            order.partner_id.name,          # 1
            order.name,                     # 2
            company_address,                # 3
            horario_limpio,                 # 4 (limpio)
            clean_phone,                    # 5 (limpio)
            order.company_id.name,          # 6
        ]

        try:
            template.send_to_partner(order.partner_id, parameter_values)
            order.write({'whatsapp_sent': True})

            last_history = self.env['whatsapp.history'].sudo().search([
                ('partner_id', '=', order.partner_id.id),
                ('template_name', '=', template.name),
                ('direction', '=', 'outgoing'),
                ('sale_order_id', '=', False)
            ], order='create_date desc', limit=1)
            if last_history:
                last_history.sudo().write({'sale_order_id': order.id})
                _logger.info(f"Asociada orden {order.name} al historial ID {last_history.id}")

            _logger.info(f"WhatsApp enviado correctamente para orden {order.name}")
            return True, f"WhatsApp enviado correctamente para orden {order.name}"
        except Exception as e:
            _logger.exception(f"Error al enviar WhatsApp para orden {order.name}: {e}")
            return False, f"Error: {e}"