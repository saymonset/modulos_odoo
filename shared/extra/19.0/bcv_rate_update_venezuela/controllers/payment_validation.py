from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)


class PaymentDataController(http.Controller):

    @http.route('/payment/validate_and_save', type='json', auth='public', methods=['POST'])
    def validate_and_save_payment_data(self, **post):
        _logger.info(">>> PAYMENT: /payment/validate_and_save called")
        data = json.loads(request.httprequest.data) if request.httprequest.data else post
        sale_order_id = data.get('sale_order_id')
        if not sale_order_id:
            return {'error': 'No se encontró la orden'}
        sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
        if not sale_order:
            return {'error': 'Orden no válida'}
        _logger.info(f">>> PAYMENT: Saving data for order {sale_order.name}")
        sale_order.action_save_payment_data(data)
        try:
            sale_order.validate_payment_required_fields()
            _logger.info(">>> PAYMENT: Validation passed")
        except UserError as e:
            _logger.info(f">>> PAYMENT: Validation failed: {str(e)}")
            return {'error': str(e)}
        return {'success': True}