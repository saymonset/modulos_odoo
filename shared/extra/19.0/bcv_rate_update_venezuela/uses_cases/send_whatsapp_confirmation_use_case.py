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


        # --- Verificar si ya se envió para esta orden y plantilla ---
        existing = self.env['whatsapp.history'].sudo().search([
            ('sale_order_id', '=', order.id),
            ('template_name', '=', template.name),
            ('direction', '=', 'outgoing'),
        ], limit=1)

        if existing:
            msg = f"El mensaje para la orden {order.name} ya fue enviado el {existing.timestamp}"
            _logger.warning(msg)
            # Consideramos éxito lógico (ya estaba enviado)
            return True, msg

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
            template.send_to_partner(order.partner_id, parameter_values)
            order.write({'whatsapp_sent': True})

            # Buscar el registro de historial recién creado (último para este partner/plantilla)
            last_history = self.env['whatsapp.history'].sudo().search([
                ('partner_id', '=', order.partner_id.id),
                ('template_name', '=', template.name),
                ('direction', '=', 'outgoing'),
                ('sale_order_id', '=', False)   # Aún sin asociar
            ], order='create_date desc', limit=1)
            if last_history:
                last_history.sudo().write({'sale_order_id': order.id})
                _logger.info(f"Asociada orden {order.name} al historial ID {last_history.id}")

            _logger.info(f"WhatsApp enviado correctamente para orden {order.name} con plantilla 'pedido_confirmado_ubicacion'")
            return True, f"WhatsApp enviado correctamente para orden {order.name}"
        except Exception as e:
            _logger.exception(f"Error al enviar WhatsApp para orden {order.name}: {e}")
            return False, f"Error: {e}"