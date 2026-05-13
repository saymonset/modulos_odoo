from odoo import models, fields, api
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

_logger.warning("!!!!!!!!! ARCHIVO saymons sale_order.py CARGADO !!!!!!!!!")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    payment_proof = fields.Binary('Comprobante de pago', attachment=True)
    payment_proof_filename = fields.Char('Nombre del archivo')

    payment_date = fields.Date('Fecha de pago')
    payment_method = fields.Selection([
        ('transfer', 'Transferencia'),
        ('movil', 'Pago móvil'),
        ('other', 'Otro'),
    ], string='Forma de pago', default='movil')
    bank_origin = fields.Char('Banco origen')
    bank_destination = fields.Char('Banco destino', default='N/A')
    reference = fields.Char('Referencia')
    amount_vef = fields.Float('Monto en bolívares')
    exchange_rate = fields.Float('Tasa de cambio')
    amount_usd = fields.Float('Monto USD')

    currency_aux = fields.Many2one(
        'res.currency',
        string='Moneda Auxiliar USD',
        compute='_compute_currency_aux',
        store=True
    )

    amount_total_usd = fields.Monetary(
        string='Total USD (BCV)',
        currency_field='currency_aux',
        compute='_compute_amount_total_usd',
        store=True
    )

    whatsapp_sent = fields.Boolean(string="WhatsApp enviado", default=False)

    @api.depends('order_line.price_subtotal_usd_bcv')
    def _compute_amount_total_usd(self):
        for order in self:
            order.amount_total_usd = sum(line.price_subtotal_usd_bcv for line in order.order_line)

    @api.depends('currency_id')
    def _compute_currency_aux(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for order in self:
            order.currency_aux = usd

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Copia automáticamente el comprobante de pago de la orden de venta a la factura"""
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        for order in self:
            attachments = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
            ])

            for invoice in invoices:
                for att in attachments:
                    self.env['ir.attachment'].sudo().create({
                        'name': att.name,
                        'type': att.type,
                        'datas': att.datas,
                        'mimetype': att.mimetype,
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'description': 'Comprobante de pago - Transferencia / Pago Móvil',
                    })
                    _logger.info(f"Comprobante copiado a factura {invoice.name} desde orden {order.name}")

        return invoices

    def action_confirm(self):
        _logger.warning(f"=== INICIO action_confirm: self = {self}, ids = {self.ids}, len = {len(self)} ===")

        # ------------------------------------------------------------
        # Caso 1: self está vacío -> intentar recuperar orden desde transacción de pago
        # ------------------------------------------------------------
        if not self:
            _logger.warning("self está VACÍO. Intentando recuperar orden desde payment.transaction...")

            # Intentamos buscar la transacción (sin el campo inexistente 'is_processed')
            try:
                _logger.info("Buscando payment.transaction con referencia like 'S%' y estado pending/authorized...")
                transaction = self.env['payment.transaction'].sudo().search([
                    ('reference', 'like', 'S%'),
                    ('state', 'in', ['pending', 'authorized']),
                ], order='id desc', limit=1)
                _logger.info(f"Búsqueda finalizada. transaction encontrada: {transaction.id if transaction else 'Ninguna'}")
            except Exception as e:
                _logger.exception(f"ERROR en la búsqueda de payment.transaction: {e}")
                # Si hay error, devolvemos un recordset vacío (no podemos continuar)
                return self.env['sale.order']

            # Si encontramos transacción y tiene sale_order_ids asociados
            if transaction and transaction.sale_order_ids:
                order = transaction.sale_order_ids[0]
                _logger.warning(f"Orden recuperada desde transacción: {order.name} (ID {order.id})")
                _logger.info(f"Se llamará a order.action_confirm() sobre esa orden...")
                # Llamamos recursivamente a action_confirm sobre la orden encontrada
                result = order.action_confirm()
                _logger.info(f"La llamada recursiva a action_confirm ha retornado: {result}")
                return result
            else:
                _logger.error("No se pudo recuperar la orden. No hay transacción válida o no tiene sale_order_ids.")
                _logger.error("Devolviendo recordset vacío de sale.order")
                return self.env['sale.order']  # recordset vacío

        # ------------------------------------------------------------
        # Caso 2: self tiene registros (una o más órdenes)
        # ------------------------------------------------------------
        _logger.warning(f"self NO está vacío. Procesando {len(self)} orden(es) normalmente.")
        for idx, order in enumerate(self):
            _logger.info(f"Orden #{idx+1}: name={order.name}, id={order.id}, state={order.state}")

        # Confirmamos la(s) orden(es) llamando al método original
        _logger.info("Llamando a super().action_confirm() para confirmar las órdenes...")
        res = super().action_confirm()
        _logger.info(f"super().action_confirm() ha retornado: {res}")

        # Ahora, para cada orden, guardamos datos de pago desde la sesión (si existen) y enviamos WhatsApp
        for order in self:
            _logger.info(f"Procesando orden {order.name} (ID {order.id}) después de confirmación.")

            # --------------------------------------------------------
            # Guardar datos de pago desde la sesión (si aplica)
            # --------------------------------------------------------
            try:
                # Verificar si estamos en un contexto HTTP con sesión activa
                if request and hasattr(request, 'session') and 'payment_data' in request.session:
                    payment_data = request.session.pop('payment_data')
                    _logger.info(f"Datos de pago encontrados en sesión para orden {order.name}: {payment_data}")
                    order.sudo().write({
                        'payment_date': payment_data.get('payment_date'),
                        'payment_method': payment_data.get('payment_method'),
                        'bank_origin': payment_data.get('bank_origin'),
                        'bank_destination': payment_data.get('bank_destination', 'N/A'),
                        'reference': payment_data.get('reference'),
                        'amount_vef': payment_data.get('amount_vef', 0),
                        'exchange_rate': payment_data.get('exchange_rate', 0),
                        'amount_usd': payment_data.get('amount_usd', 0),
                    })
                    _logger.warning(f"✅ Datos de pago guardados correctamente para orden {order.name}")
                else:
                    _logger.info(f"No hay datos de pago en sesión (request={request}, session tiene payment_data? = {hasattr(request, 'session') and 'payment_data' in request.session if request else False})")
            except Exception as e:
                _logger.exception(f"❌ Error guardando datos de pago para orden {order.name}: {e}")

            # --------------------------------------------------------
            # Enviar WhatsApp si cumple condiciones
            # --------------------------------------------------------
            if order.whatsapp_sent:
                _logger.info(f"La orden {order.name} ya tiene whatsapp_sent = True, se omite envío.")
                continue

            if order.state == 'sale' and order.partner_id.phone:
                _logger.info(f"Orden {order.name}: state='sale', partner phone={order.partner_id.phone}. Buscando comprobante...")
                attachments = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'sale.order'),
                    ('res_id', '=', order.id),
                    ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
                ], limit=1)
                if attachments:
                    _logger.info(f"Comprobante encontrado para orden {order.name}. Llamando a _send_whatsapp_confirmation...")
                    self._send_whatsapp_confirmation(order)
                else:
                    _logger.warning(f"No se encontró comprobante para orden {order.name}. WhatsApp NO enviado.")
            else:
                _logger.warning(f"Condiciones NO cumplidas para orden {order.name}: state={order.state}, phone={order.partner_id.phone}")

        _logger.warning(f"=== FIN action_confirm para {len(self)} orden(es). Retornando: {res} ===")
        return res

    def _send_whatsapp_confirmation(self, order):
        """Envía mensaje WhatsApp usando la plantilla registrada."""
        # Buscar la plantilla por su nombre técnico (cambia si es diferente)
        template = self.env['whatsapp.template'].sudo().search([
            ('name', '=', 'pedido_confirmado_con_ubicacion'),
            ('active', '=', True)
        ], limit=1)

        if not template:
            _logger.error(f"No se encontró la plantilla 'pedido_confirmado_con_ubicacion' para la orden {order.name}")
            return

        # Preparar los parámetros según tu plantilla (ajusta el orden y cantidad)
        parameter_values = [
            order.partner_id.name,                      # {{1}}
            order.name,                                 # {{2}}
            order.company_id.phone or '',               # {{3}}
            order.company_id.name,                      # {{4}}
        ]

        try:
            template.send_to_partner(order.partner_id, parameter_values)
            order.write({'whatsapp_sent': True})
            _logger.info(f"WhatsApp enviado correctamente para orden {order.name}")
        except Exception as e:
            _logger.exception(f"Error al enviar WhatsApp para orden {order.name}: {e}")