from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import json

class PaymentDataController(http.Controller):

    @http.route('/payment/validate_and_save', type='json', auth='public', methods=['POST'])
    def validate_and_save_payment_data(self, **post):
        data = json.loads(request.httprequest.data) if request.httprequest.data else post
        sale_order_id = data.get('sale_order_id')
        if not sale_order_id:
            return {'error': 'No se encontró la orden'}
        sale_order = request.env['sale.order'].sudo().browse(sale_order_id)
        if not sale_order:
            return {'error': 'Orden no válida'}
        try:
            sale_order.action_save_payment_data(data)
            sale_order.validate_payment_required_fields()
        except UserError as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': f'Error: {str(e)}'}
        return {'success': True}