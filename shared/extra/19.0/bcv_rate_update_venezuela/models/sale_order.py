from odoo import models, fields, api, _
from odoo.exceptions import UserError
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
        """Copia automáticamente el comprobante de pago de la orden de venta a la factura y lo publica en el chatter"""
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        for order in self:
            attachments = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
            ])

            for invoice in invoices:
                for att in attachments:
                    new_att = self.env['ir.attachment'].sudo().create({
                        'name': att.name,
                        'type': att.type,
                        'datas': att.datas,
                        'mimetype': att.mimetype,
                        'res_model': 'account.move',
                        'res_id': invoice.id,
                        'description': 'Comprobante de pago - Transferencia / Pago Móvil',
                    })
                    invoice.sudo().message_post(
                        body=f"🧾 Comprobante de pago adjunto desde la orden {order.name}",
                        attachment_ids=[new_att.id]
                    )
                    _logger.info(f"Comprobante copiado a factura {invoice.name} desde orden {order.name}")

        return invoices

    @api.constrains('state', 'payment_method', 'reference', 'bank_origin', 'bank_destination', 'amount_vef')
    def _check_payment_required_fields(self):
        for order in self:
            # Solo validar cuando la orden se está confirmando (state = 'sale')
            # y el método de pago es transferencia o pago móvil
            if order.state == 'sale' and order.payment_method in ['transfer', 'movil']:
                if not order.reference:
                    raise UserError(_('La referencia es obligatoria para pagos por transferencia bancaria.'))
                if not order.bank_origin:
                    raise UserError(_('Debe seleccionar el banco origen.'))
                if not order.bank_destination or order.bank_destination == 'N/A':
                    raise UserError(_('Debe seleccionar el banco destino.'))
                attachment = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'sale.order'),
                    ('res_id', '=', order.id),
                    ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
                ], limit=1)
                if not attachment:
                    raise UserError(_('Debe adjuntar el comprobante de pago.'))
                if order.amount_vef < (order.amount_total - 0.01):
                    raise UserError(_('El monto pagado (%.2f Bs.) es menor al total de la orden (%.2f Bs.).') 
                                    % (order.amount_vef, order.amount_total))

    def action_confirm(self):
        _logger.warning(f"=== INICIO action_confirm: self = {self}, ids = {self.ids}, len = {len(self)} ===")

        if not self:
            _logger.warning("self está VACÍO. Intentando recuperar orden desde payment.transaction...")
            try:
                _logger.info("Buscando payment.transaction con referencia like 'S%' y estado pending/authorized...")
                transaction = self.env['payment.transaction'].sudo().search([
                    ('reference', 'like', 'S%'),
                    ('state', 'in', ['pending', 'authorized']),
                ], order='id desc', limit=1)
                _logger.info(f"Búsqueda finalizada. transaction encontrada: {transaction.id if transaction else 'Ninguna'}")
            except Exception as e:
                _logger.exception(f"ERROR en la búsqueda de payment.transaction: {e}")
                return self.env['sale.order']

            if transaction and transaction.sale_order_ids:
                order = transaction.sale_order_ids[0]
                _logger.warning(f"Orden recuperada desde transacción: {order.name} (ID {order.id})")

                if order.state == 'sale':
                    _logger.info(f"La orden {order.name} ya está confirmada. Ejecutando post-procesamiento...")
                    self._process_order_post_confirm(order)
                    return self.env['sale.order']
                else:
                    _logger.info(f"Orden en estado {order.state}. Llamando a order.action_confirm()...")
                    result = order.action_confirm()
                    _logger.info(f"La llamada recursiva a action_confirm ha retornado: {result}")
                    return result
            else:
                _logger.error("No se pudo recuperar la orden. No hay transacción válida o no tiene sale_order_ids.")
                return self.env['sale.order']

        _logger.warning(f"self NO está vacío. Procesando {len(self)} orden(es) normalmente.")
        for idx, order in enumerate(self):
            _logger.info(f"Orden #{idx+1}: name={order.name}, id={order.id}, state={order.state}")

        _logger.info("Llamando a super().action_confirm() para confirmar las órdenes...")
        res = super().action_confirm()
        _logger.info(f"super().action_confirm() ha retornado: {res}")

        for order in self:
            self._process_order_post_confirm(order)

        _logger.warning(f"=== FIN action_confirm para {len(self)} orden(es). Retornando: {res} ===")
        return res

    @staticmethod
    def _process_order_post_confirm(order):
        """Procesa una orden ya confirmada: guarda datos de pago y envía WhatsApp si corresponde."""
        _logger.info(f"Procesando orden {order.name} (ID {order.id}) después de confirmación.")

        try:
            if request and hasattr(request, 'session') and 'payment_data' in request.session:
                payment_data = request.session.pop('payment_data')
                _logger.info(f"Datos de pago encontrados en sesión para orden {order.name}: {payment_data}")
                if not order.payment_date:
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
                    _logger.info(f"Los datos de pago ya existían en la orden, se omite escritura desde sesión.")
            else:
                _logger.info(f"No hay datos de pago en sesión o ya fueron consumidos.")
        except Exception as e:
            _logger.exception(f"❌ Error guardando datos de pago para orden {order.name}: {e}")

        if order.whatsapp_sent:
            _logger.info(f"La orden {order.name} ya tiene whatsapp_sent = True, se omite envío.")
            return

        if order.state == 'sale' and order.partner_id.phone:
            _logger.info(f"Orden {order.name}: state='sale', partner phone={order.partner_id.phone}. Buscando comprobante...")
            attachments = order.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
            ], limit=1)
            if attachments:
                service = order.env['whatsapp.service']
                result = service.sendWhatsappConfirmation(order)
                if not result.get('success'):
                    _logger.error(f"Fallo en WhatsApp para {order.name}: {result.get('message')}")
            else:
                _logger.warning(f"No se encontró comprobante para orden {order.name}. WhatsApp NO enviado.")
        else:
            _logger.warning(f"Condiciones NO cumplidas para orden {order.name}: state={order.state}, phone={order.partner_id.phone}")