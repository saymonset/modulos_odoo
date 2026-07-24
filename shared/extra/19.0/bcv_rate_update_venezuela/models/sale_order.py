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
    amount_vef = fields.Float('Monto en bolívares', digits=(12, 2))
    exchange_rate = fields.Float('Tasa VES/USD', digits=(12, 2))
    amount_usd = fields.Float('Monto USD', digits=(12, 2))
    amount_cop = fields.Float('Monto COP', digits=(12, 2))

    currency_aux = fields.Many2one('res.currency', string='Moneda Auxiliar USD', compute='_compute_currency_aux', store=True)
    amount_total_usd = fields.Monetary(string='Total USD (BCV)', currency_field='currency_aux', compute='_compute_amount_total_usd', store=True)
    currency_aux_cop = fields.Many2one('res.currency', string='Moneda Auxiliar COP', compute='_compute_currency_aux_cop', store=True)
    amount_total_cop = fields.Monetary(string='Total COP', currency_field='currency_aux_cop', compute='_compute_amount_total_usd', store=True)
    bcv_rate_value = fields.Float(
        string='Tasa BCV (USD/VES)',
        digits=(12, 2),
        compute='_compute_bcv_rate_value',
        store=True,
    )
    amount_total_ves_from_usd = fields.Monetary(
        string='Total Bolívares (VES)',
        currency_field='currency_id',
        compute='_compute_bcv_rate_value',
        store=True,
    )
    partner_phone = fields.Char(string='Teléfono', related='partner_id.phone', readonly=True)
    whatsapp_sent = fields.Boolean(string="WhatsApp enviado", default=False)

    price_tier_type = fields.Selection([
        ('retail', 'Menudeo'),
        ('wholesale', 'Mayoreo'),
        ('mercadolibre', 'MercadoLibre'),
    ], string='Nivel de precio', default='retail')

    @api.depends('order_line.price_subtotal_usd_bcv', 'order_line.price_subtotal_cop')
    def _compute_amount_total_usd(self):
        for order in self:
            order.amount_total_usd = sum(line.price_subtotal_usd_bcv for line in order.order_line)
            order.amount_total_cop = sum(line.price_subtotal_cop for line in order.order_line)

    @api.depends('company_id', 'amount_total_usd')
    def _compute_bcv_rate_value(self):
        for order in self:
            rate = self.env['product.template']._get_bcv_rate(order.company_id)
            order.bcv_rate_value = rate if rate else 1.0
            order.amount_total_ves_from_usd = order.amount_total_usd * order.bcv_rate_value if order.amount_total_usd else 0.0

    @api.onchange('price_tier_type')
    def _onchange_price_tier_type(self):
        for order in self:
            if order.price_tier_type and order.order_line:
                for line in order.order_line:
                    if line.product_id:
                        tmpl = line.product_id.product_tmpl_id
                        tier = tmpl.price_tier_ids.filtered(
                            lambda t: t.tier_type == order.price_tier_type)
                        if tier and tier.price_ves:
                            line.price_unit = tier.price_ves

    @api.depends('currency_id')
    def _compute_currency_aux(self):
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        for order in self:
            order.currency_aux = usd if usd else order.company_id.currency_id

    @api.depends('currency_id')
    def _compute_currency_aux_cop(self):
        cop = self.env.ref('base.COP', raise_if_not_found=False)
        for order in self:
            order.currency_aux_cop = cop if cop else order.company_id.currency_id

    # ------------------------------------------------------------
    # GUARDAR DATOS DEL COMPROBANTE (desde frontend)
    # ------------------------------------------------------------
    def action_save_payment_data(self, payment_data):
        _logger.info(f"*** SALVANDO: Datos de pago para orden {self.name}")
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
    # VALIDACIÓN DE CAMPOS OBLIGATORIOS
    # ------------------------------------------------------------
    def validate_payment_required_fields(self):
        _logger.info(f"*** VALIDANDO: {len(self)} orden(es)")
        for order in self:
            if order.payment_method in ['transfer', 'movil']:
                if not order.reference:
                    raise UserError(_('✏️ Falta la referencia del pago. Por favor, indique el número de referencia de su transferencia.'))
                if not order.bank_origin:
                    raise UserError(_('🏦 Falta el banco origen. Seleccione desde qué banco realiza la transferencia.'))
                if not order.bank_destination or order.bank_destination == 'N/A':
                    raise UserError(_('🏦 Falta el banco destino. Seleccione el banco al que depositará.'))
                attachment = self.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'sale.order'),
                    ('res_id', '=', order.id),
                    ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
                ], limit=1)
                if not attachment:
                    raise UserError(_('📎 Falta adjuntar el comprobante de pago. Por favor, suba la imagen o PDF del comprobante.'))
                if order.amount_vef < (order.amount_total - 0.01):
                    raise UserError(_('💰 El monto pagado (%.2f Bs.) es menor al total de la orden (%.2f Bs.). Por favor, verifique el monto.'))
                _logger.info(f"*** VALIDACIÓN EXITOSA para orden {order.name}")

    # ------------------------------------------------------------
    # CONFIRMACIÓN DE LA ORDEN (con procesamiento posterior)
    # ------------------------------------------------------------
    def action_confirm(self):
        _logger.info(f"*** CONFIRMANDO: action_confirm llamado con órdenes {self.ids}")
        if not self:
            return self.env['sale.order']
        for order in self:
            if request and hasattr(request, 'session') and 'payment_data' in request.session:
                payment_data = request.session.pop('payment_data')
                order.action_save_payment_data(payment_data)
        res = super().action_confirm()
        for order in self:
            self._process_order_post_confirm(order)
        return res

    # ------------------------------------------------------------
    # PROCESAMIENTO POST-CONFIRMACIÓN (WhatsApp y otros)
    # ------------------------------------------------------------
    @staticmethod
    def _process_order_post_confirm(order):
        """Procesa una orden ya confirmada: guarda datos de pago (si no se hicieron antes) y envía WhatsApp."""
        _logger.info(f"*** POST-CONFIRMACIÓN: Procesando orden {order.name}")

        # Si aún no se guardaron los datos de pago (por ejemplo, porque no vinieron en la sesión),
        # intentamos recuperarlos nuevamente (esto es un respaldo).
        if not order.payment_date and request and hasattr(request, 'session') and 'payment_data' in request.session:
            payment_data = request.session.pop('payment_data')
            if payment_data.get('sale_order_id') == order.id:
                order.action_save_payment_data(payment_data)
                _logger.info(f"*** POST-CONFIRMACIÓN: Datos de pago guardados desde sesión para {order.name}")

        # Enviar WhatsApp solo si no se ha enviado antes y la orden está confirmada y el cliente tiene teléfono
        if not order.whatsapp_sent and order.state == 'sale' and order.partner_id.phone:
            _logger.info(f"*** POST-CONFIRMACIÓN: Intentando enviar WhatsApp para orden {order.name}")
            # Buscar el comprobante adjunto (para enviarlo como imagen si existe)
            attachment = order.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('description', '=', 'Comprobante de pago - Transferencia / Pago Móvil'),
            ], limit=1)
            if attachment:
                if 'whatsapp.service' in order.env.registry:
                    service = order.env['whatsapp.service']
                    result = service.sendWhatsappConfirmation(order)
                    if not result.get('success'):
                        _logger.error(f"*** POST-CONFIRMACIÓN: Fallo en WhatsApp para {order.name}: {result.get('message')}")
                    else:
                        order.write({'whatsapp_sent': True})
                        _logger.info(f"*** POST-CONFIRMACIÓN: WhatsApp enviado correctamente para {order.name}")
                else:
                    _logger.info(f"*** POST-CONFIRMACIÓN: Módulo WhatsApp no instalado, saltando notificación para {order.name}")
            else:
                _logger.warning(f"*** POST-CONFIRMACIÓN: No se encontró comprobante para orden {order.name}. WhatsApp NO enviado.")
        else:
            _logger.info(f"*** POST-CONFIRMACIÓN: No se cumplen condiciones para enviar WhatsApp a {order.name} (whatsapp_sent={order.whatsapp_sent}, state={order.state}, phone={order.partner_id.phone})")


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
                if not sale_order.reference and request and hasattr(request, 'session') and 'payment_data' in request.session:
                    payment_data = request.session.get('payment_data')
                    if payment_data and payment_data.get('sale_order_id') == sale_order_id:
                        sale_order.action_save_payment_data(payment_data)
        return super()._get_processing_values(values)
