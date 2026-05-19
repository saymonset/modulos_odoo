from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


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
    # GUARDAR DATOS DEL COMPROBANTE (desde frontend)
    # ------------------------------------------------------------
    def action_save_payment_data(self, payment_data):
        _logger.info(f"*** SALVANDO: Datos de pago para orden {self.name}: {payment_data}")
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
    # VALIDACIÓN DE CAMPOS OBLIGATORIOS (lanza UserError)
    # ------------------------------------------------------------
    def validate_payment_required_fields(self):
        _logger.info(f"*** VALIDANDO: {len(self)} orden(es)")
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
                _logger.info(f"*** VALIDACIÓN EXITOSA para orden {order.name}")

    # ------------------------------------------------------------
    # CONFIRMACIÓN DE LA ORDEN (con recuperación de sesión y validación)
    # ------------------------------------------------------------
    def action_confirm(self):
        _logger.info(f"*** CONFIRMANDO: action_confirm llamado con órdenes {self.ids}")
        # Si no tenemos órdenes (caso típico desde el flujo de pago)
        if not self:
            # Buscar la última transacción pendiente
            tx = self.env['payment.transaction'].sudo().search([
                ('reference', 'like', 'S%'),
                ('state', 'in', ['pending', 'authorized']),
            ], order='id desc', limit=1)
            if tx and tx.sale_order_ids:
                order = tx.sale_order_ids[0]
                _logger.info(f"*** CONFIRMANDO: Orden recuperada desde transacción: {order.name}")
                # Recuperar datos de sesión si existen
                if request and hasattr(request, 'session') and 'payment_data' in request.session:
                    payment_data = request.session.pop('payment_data')
                    if payment_data.get('sale_order_id') == order.id:
                        order.action_save_payment_data(payment_data)
                # Validar campos obligatorios
                order.validate_payment_required_fields()
                # Confirmar la orden
                return super(SaleOrder, order).action_confirm()
            else:
                _logger.warning("*** CONFIRMANDO: No se encontró transacción para recuperar orden")
                return self.env['sale.order']
        else:
            # Confirmación normal (desde botón)
            for order in self:
                if request and hasattr(request, 'session') and 'payment_data' in request.session:
                    payment_data = request.session.pop('payment_data')
                    order.action_save_payment_data(payment_data)
                order.validate_payment_required_fields()
            return super().action_confirm()


# ------------------------------------------------------------
# HERENCIA DEL PROVEEDOR DE PAGO (validación extra)
# ------------------------------------------------------------
class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    def _get_processing_values(self, values):
        _logger.info(f"*** PAYMENT: _get_processing_values llamado para proveedor {self.code}")
        sale_order_id = values.get('sale_order_id')
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)
            if sale_order and sale_order.payment_method in ['transfer', 'movil']:
                # Intentar recuperar datos de sesión si aún no están guardados
                if not sale_order.reference and request and hasattr(request, 'session') and 'payment_data' in request.session:
                    payment_data = request.session.get('payment_data')
                    if payment_data and payment_data.get('sale_order_id') == sale_order_id:
                        sale_order.action_save_payment_data(payment_data)
                sale_order.validate_payment_required_fields()
        return super()._get_processing_values(values)