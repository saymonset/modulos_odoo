import logging
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
            ('name', '=', 'pedido_confirmado_ubicacion'),   # Nombre de la nueva plantilla
            ('active', '=', True)
        ], limit=1)

        if not template:
            msg = f"No se encontró la plantilla 'pedido_confirmado_ubicacion' para la orden {order.name}"
            _logger.error(msg)
            return False, msg

        # Parámetros según la nueva plantilla:
        # {{1}} = nombre_cliente
        # {{2}} = numero_pedido
        # {{3}} = direccion (campo del partner o valor por defecto)
        # {{4}} = horario (puedes ajustarlo según tu lógica)
        # {{5}} = telefono del cliente
        # {{6}} = la empresa
        parameter_values = [
            order.partner_id.name,                                   # 1
            order.name,                                              # 2
            order.partner_id.street or "CC El Mercado, Av. Llano Adentro, Porlamar",  # 3 (dirección)
            "Abierto - Cierra a las 7:00 p.m.",                      # 4 (horario fijo o dinámico)
            order.partner_id.phone,                                  # 5
            order.company_id.name,                                   # 6
        ]

        try:
            #template.send_to_partner(order.partner_id, parameter_values)
            order.write({'whatsapp_sent': True})
            _logger.info(f"WhatsApp enviado correctamente para orden {order.name} con plantilla 'pedido_confirmado_ubicacion'")
            return True, f"WhatsApp enviado correctamente para orden {order.name}"
        except Exception as e:
            _logger.exception(f"Error al enviar WhatsApp para orden {order.name}: {e}")
            return False, f"Error: {e}"