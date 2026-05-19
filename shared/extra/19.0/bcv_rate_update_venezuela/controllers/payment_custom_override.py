from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class PaymentCustomOverride(http.Controller):

    @http.route('/payment/custom/process', type='http', auth='public', methods=['POST'], csrf=False)
    def custom_process(self, **post):
        """Intercepta el procesamiento del pago personalizado y valida los campos de la orden."""
        _logger.info("*** PAYMENT: Interceptando /payment/custom/process")
        reference = post.get('reference')
        if not reference:
            return request.redirect('/shop/payment?error=missing_reference')

        # Buscar la orden de venta por la referencia (ej. 'S00110')
        sale_order = request.env['sale.order'].sudo().search([('name', '=', reference)], limit=1)
        if not sale_order:
            _logger.warning(f"No se encontró orden con referencia {reference}")
            return request.redirect('/shop/payment?error=order_not_found')

        _logger.info(f"*** PAYMENT: Orden encontrada: {sale_order.name} (ID {sale_order.id})")

        # Recuperar datos de pago desde la sesión (si existen)
        if 'payment_data' in request.session:
            payment_data = request.session.pop('payment_data')
            if payment_data.get('sale_order_id') == sale_order.id:
                _logger.info(f"*** PAYMENT: Datos de pago recuperados de sesión: {payment_data}")
                try:
                    sale_order.action_save_payment_data(payment_data)
                except Exception as e:
                    _logger.error(f"Error guardando datos: {e}")

        # Validar campos obligatorios (si el método es transferencia o pago móvil)
        try:
            sale_order.validate_payment_required_fields()
        except UserError as e:
            # Redirigir a la página de pago con el mensaje de error
            error_msg = str(e).replace(' ', '+')
            _logger.warning(f"*** PAYMENT: Validación falló: {str(e)}")
            return request.redirect(f'/shop/payment?error={error_msg}')

        # Si pasa la validación, continuar con el flujo normal del módulo payment_custom
        _logger.info("*** PAYMENT: Validación exitosa, continuando con el procesamiento original")
        # Llamar al controlador original (necesitamos importarlo dinámicamente)
        # Para evitar conflictos, podemos simplemente crear la transacción manualmente
        # o usar el método estándar. Como conocemos la estructura, haremos:
        tx = request.env['payment.transaction'].sudo().create({
            'reference': reference,
            'amount': sale_order.amount_total,
            'currency_id': sale_order.currency_id.id,
            'partner_id': sale_order.partner_id.id,
            'state': 'pending',
            'provider_id': sale_order._get_payment_provider_id(),  # método auxiliar que debes implementar
        })
        # Redirigir a la página de estado de pago (estándar)
        return request.redirect('/payment/status')