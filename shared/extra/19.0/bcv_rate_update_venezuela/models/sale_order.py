from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Campos del comprobante
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

    currency_aux = fields.Many2one('res.currency', string='Moneda Auxiliar USD', compute='_compute_currency_aux', store=True)
    amount_total_usd = fields.Monetary(string='Total USD (BCV)', currency_field='currency_aux', compute='_compute_amount_total_usd', store=True)
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

    # ------------------------------------------------------------
    # VALIDACIÓN REUTILIZABLE
    # ------------------------------------------------------------
    def validate_payment_required_fields(self):
        """Lanza UserError si falta algún campo obligatorio para transferencia/pago móvil."""
        for order in self:
            if order.payment_method in ['transfer', 'movil']:
                if not order.reference:
                    raise UserError(_('❌ La referencia es obligatoria para pagos por transferencia.'))
                if not order.bank_origin:
                    raise UserError(_('❌ Debe seleccionar el banco origen.'))
                if not order.bank_destination or order.bank_destination == 'N/A':
                    raise UserError(_('❌ Debe seleccionar el banco destino.'))
                attachment = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'sale.order'),
                    ('res_id', '=', order.id),
                    ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
                ], limit=1)
                if not attachment:
                    raise UserError(_('❌ Debe adjuntar el comprobante de pago.'))
                if order.amount_vef < (order.amount_total - 0.01):
                    raise UserError(_('❌ El monto pagado (%.2f Bs.) es menor al total (%.2f Bs.)')
                                    % (order.amount_vef, order.amount_total))

    @api.constrains('state', 'payment_method', 'reference', 'bank_origin', 'bank_destination', 'amount_vef')
    def _check_payment_required_fields(self):
        for order in self:
            if order.state == 'sale' and order.payment_method in ['transfer', 'movil']:
                order.validate_payment_required_fields()

    # ------------------------------------------------------------
    # GUARDAR DATOS DEL COMPROBANTE DESDE EL FRONTEND
    # ------------------------------------------------------------
    def action_save_payment_data(self, payment_data):
        """Guarda los datos del comprobante en la orden."""
        self.sudo().write({
            'payment_date': payment_data.get('payment_date'),
            'payment_method': payment_data.get('payment_method'),
            'bank_origin': payment_data.get('bank_origin'),
            'bank_destination': payment_data.get('bank_destination', 'N/A'),
            'reference': payment_data.get('reference'),
            'amount_vef': float(payment_data.get('amount_vef', 0)),
            'exchange_rate': float(payment_data.get('exchange_rate', 0)),
            'amount_usd': float(payment_data.get('amount_usd', 0)),
        })
        return True

    # ------------------------------------------------------------
    # FACTURACIÓN Y POST-CONFIRMACIÓN
    # ------------------------------------------------------------
    def _create_invoices(self, grouped=False, final=False, date=None):
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
                    _logger.info(f"Comprobante copiado a factura {invoice.name}")
        return invoices

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            self._process_order_post_confirm(order)
        return res

    @staticmethod
    def _process_order_post_confirm(order):
        try:
            if request and hasattr(request, 'session') and 'payment_data' in request.session:
                payment_data = request.session.pop('payment_data')
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
        except Exception as e:
            _logger.exception(f"Error guardando datos de pago: {e}")

        if not order.whatsapp_sent and order.state == 'sale' and order.partner_id.phone:
            attachments = order.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
            ], limit=1)
            if attachments:
                service = order.env['whatsapp.service']
                result = service.sendWhatsappConfirmation(order)
                if not result.get('success'):
                    _logger.error(f"Fallo en WhatsApp: {result.get('message')}")


# ------------------------------------------------------------
# HERENCIA DEL PROVEEDOR DE PAGO (VALIDACIÓN ANTES DE CREAR TRANSACCIÓN)
# ------------------------------------------------------------
class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _get_processing_values(self, values):
        sale_order_id = values.get('sale_order_id')
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)
            if sale_order:
                sale_order.validate_payment_required_fields()
        return super()._get_processing_values(values)