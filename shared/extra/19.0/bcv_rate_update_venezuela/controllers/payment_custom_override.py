from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import logging
import re

_logger = logging.getLogger(__name__)


class PaymentCustomOverride(http.Controller):

    @http.route('/payment/custom/process', type='http', auth='public', methods=['POST'], csrf=False)
    def custom_process(self, **post):
        _logger.info("=" * 80)
        _logger.info("*** PAYMENT: INICIO - Interceptando /payment/custom/process")
        reference = post.get('reference')
        if not reference:
            _logger.warning("*** PAYMENT: No se recibió referencia")
            return request.redirect('/shop/payment?error=Falta+la+referencia+del+pago')

        # Limpiar sufijo numérico (ej: "S00118-3" -> "S00118")
        clean_reference = re.sub(r'-\d+$', '', reference)
        _logger.info(f"*** PAYMENT: Referencia original: {reference}, limpia: {clean_reference}")

        # Buscar la orden de venta
        sale_order = request.env['sale.order'].sudo().search([('name', '=', clean_reference)], limit=1)
        if not sale_order:
            _logger.warning(f"No se encontró orden con referencia {clean_reference}")
            return request.redirect('/shop/payment?error=No+se+encontró+la+orden+de+pago')

        _logger.info(f"*** PAYMENT: Orden encontrada: {sale_order.name} (ID {sale_order.id})")

        # Recuperar datos de sesión (guardados durante la subida del comprobante)
        if 'payment_data' in request.session:
            payment_data = request.session.pop('payment_data')
            _logger.info(f"*** PAYMENT: Datos de sesión recuperados: {payment_data}")
            if payment_data.get('sale_order_id') == sale_order.id:
                sale_order.action_save_payment_data(payment_data)
                _logger.info(f"*** PAYMENT: Datos guardados en la orden")
            else:
                _logger.warning(f"El sale_order_id de la sesión no coincide")
        else:
            _logger.warning("*** PAYMENT: No hay datos de pago en la sesión")

        # Validar campos obligatorios
        try:
            sale_order.validate_payment_required_fields()
            _logger.info("*** PAYMENT: Validación exitosa")
        except UserError as e:
            error_msg = str(e).strip()
            error_msg_url = error_msg.replace(' ', '+')
            _logger.warning(f"*** PAYMENT: Validación falló: {error_msg}")
            return request.redirect(f'/shop/payment?error={error_msg_url}')

        # ================================================================
        # 1. VERIFICAR Y LIMPIAR TRANSACCIONES EXISTENTES
        # ================================================================
        existing_tx = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference)
        ], limit=1)
        if existing_tx:
            _logger.info(f"*** PAYMENT: Ya existe una transacción con referencia {reference}. Estado actual: {existing_tx.state}")
            if existing_tx.state in ['pending', 'authorized', 'done']:
                # Estado válido, redirigir a la página de estado de pago
                return request.redirect('/payment/status')
            else:
                # Estado 'draft' o 'cancel' - eliminar para crear una nueva
                _logger.info(f"*** PAYMENT: Eliminando transacción en estado {existing_tx.state} para crear una nueva")
                existing_tx.sudo().unlink()
                _logger.info("*** PAYMENT: Transacción eliminada correctamente")

        # ================================================================
        # 2. OBTENER PROVEEDOR Y MÉTODO DE PAGO
        # ================================================================
        provider = request.env['payment.provider'].sudo().search([
            ('code', '=', 'custom')
        ], limit=1)
        if not provider:
            provider = request.env['payment.provider'].sudo().search([
                ('is_wire_transfer', '=', True)
            ], limit=1)
        if not provider:
            _logger.error("No se encontró proveedor de pago")
            return request.redirect('/shop/payment?error=Error+en+la+configuración+de+pago')
        _logger.info(f"*** PAYMENT: Proveedor encontrado: ID={provider.id}, code={provider.code}")

        # Obtener método de pago asociado al proveedor (campo many2many 'provider_ids')
        payment_method = request.env['payment.method'].sudo().search([
            ('provider_ids', 'in', provider.id)
        ], limit=1)
        if not payment_method:
            # Fallback: tomar cualquier método de pago activo
            payment_method = request.env['payment.method'].sudo().search([], limit=1)
        if not payment_method:
            _logger.error("No se encontró método de pago")
            return request.redirect('/shop/payment?error=Error+en+el+método+de+pago')
        _logger.info(f"*** PAYMENT: Método de pago: ID={payment_method.id}, name={payment_method.name}")

        # ================================================================
        # 3. CREAR NUEVA TRANSACCIÓN
        # ================================================================
        tx_values = {
            'reference': reference,
            'amount': sale_order.amount_total,
            'currency_id': sale_order.currency_id.id,
            'partner_id': sale_order.partner_id.id,
            'provider_id': provider.id,
            'payment_method_id': payment_method.id,
            'state': 'pending',
            'is_live': True,
        }
        _logger.info(f"*** PAYMENT: Creando transacción con valores: {tx_values}")
        try:
            tx = request.env['payment.transaction'].sudo().create(tx_values)
            _logger.info(f"*** PAYMENT: Transacción creada con ID {tx.id}")
            return request.redirect('/payment/status')
        except Exception as e:
            _logger.exception("*** PAYMENT: Error al crear la transacción")
            return request.redirect(f'/shop/payment?error=Error+al+procesar+el+pago:+{str(e)}')