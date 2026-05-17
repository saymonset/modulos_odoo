from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
import base64
import logging
import re

_logger = logging.getLogger(__name__)

class WebsiteSaleAttachment(WebsiteSale):

    # -------------------------------------------------------------------------
    # Búsqueda de partner por email o teléfono (para auto-llenado y evitar duplicados)
    # -------------------------------------------------------------------------
    @http.route('/shop/get_partner_data', type='json', auth='public', website=True)
    def get_partner_data(self, email=None, phone=None):
        """
        Busca un partner por email o teléfono y devuelve sus datos de contacto.
        Solo devuelve datos si el partner NO tiene un usuario asociado (seguridad).
        """
        if not email and not phone:
            return {}
            
        domain = []
        if email:
            domain.append(('email', '=', email))
        if phone:
            domain.append(('phone', '=', phone))
            
        if not domain:
            return {}
            
        # Buscar el partner. Si ambos están presentes, buscar por email O teléfono.
        search_domain = ['|'] * (len(domain) - 1) + domain if len(domain) > 1 else domain
        
        partner = request.env['res.partner'].sudo().search(search_domain, limit=1)
        
        if partner:
            # Seguridad: No devolver datos si el partner tiene un usuario de portal/interno
            # o si es el usuario público.
            if partner.user_ids or partner.id == request.website.partner_id.id:
                _logger.info(f"Partner found but has users or is public. Skipping auto-fill for security.")
                return {'has_user': True}
                
            return {
                'name': partner.name,
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'zip': partner.zip,
                'country_id': partner.country_id.id,
                'state_id': partner.state_id.id,
                'phone': partner.phone,
                'email': partner.email,
                'vat': partner.vat,
            }
        return {}

    @http.route(['/shop/address/submit'], type='http', methods=['POST'], auth='public', website=True, sitemap=False)
    def shop_address_submit(self, partner_id=None, **form_data):
        """
        Sobrescribe la subida de dirección para intentar vincular a un partner existente
        si el cliente es un invitado y proporciona un email/teléfono ya registrado.
        """
        _logger.info(f"=== shop_address_submit override (partner_id: {partner_id}) ===")
        
        # Solo intentar vincular si no viene un partner_id explícito y el carrito es anónimo
        if not partner_id and request.cart and request.cart._is_anonymous_cart():
            email = form_data.get('email')
            phone = form_data.get('phone')
            
            domain = []
            if email:
                domain.append(('email', '=', email))
            if phone:
                domain.append(('phone', '=', phone))
            
            if domain:
                search_domain = ['|'] * (len(domain) - 1) + domain if len(domain) > 1 else domain
                # Solo vincular si el partner encontrado NO tiene usuarios (evitar hijacking de cuentas)
                existing_partner = request.env['res.partner'].sudo().search(search_domain + [('user_ids', '=', False)], limit=1)
                
                if existing_partner:
                    _logger.info(f"Vínculando orden a partner existente ID {existing_partner.id} ({existing_partner.name})")
                    partner_id = existing_partner.id
                    
        return super().shop_address_submit(partner_id=partner_id, **form_data)

    # -------------------------------------------------------------------------
    # Endpoint JSON: obtener total de orden + tasa BCV + equivalente USD
    # -------------------------------------------------------------------------
    @http.route('/payment_proof/get_order_total_and_rate', type='json', auth='public', csrf=False)
    def get_order_total_and_rate(self):
        """Devuelve el total de la orden actual en VES, la tasa BCV y el equivalente en USD"""
        _logger.info("=== get_order_total_and_rate called ===")
        try:
            sale_order_id = request.session.get('sale_order_id') or request.session.get('sale_last_order_id')
            if not sale_order_id:
                _logger.warning("No hay sale_order_id en sesión")
                return {'error': 'No hay orden activa'}

            order = request.env['sale.order'].sudo().browse(int(sale_order_id)).exists()
            if not order:
                _logger.warning(f"No se encontró la orden con ID {sale_order_id}")
                return {'error': 'No se encontró la orden'}

            amount_vef = order.amount_total
            _logger.info(f"Monto en VES: {amount_vef}")

            rate_info = request.website.get_rate_info()
            exchange_rate = rate_info.get('rate', 0.0)

            if exchange_rate and exchange_rate > 1.0:
                amount_usd = amount_vef / exchange_rate
                _logger.info(f"Tasa encontrada: {exchange_rate}, USD: {amount_usd}")
                return {
                    'amount_vef': amount_vef,
                    'exchange_rate': exchange_rate,
                    'rate_date': rate_info.get('date_formatted', ''),
                    'amount_usd': amount_usd,
                }
            else:
                _logger.warning("No se encontró tasa válida a través de get_rate_info()")
                return {
                    'amount_vef': amount_vef,
                    'exchange_rate': 0.0,
                    'rate_date': '',
                    'amount_usd': 0.0,
                    'error': 'Tasa de cambio no disponible temporalmente'
                }
        except Exception as e:
            _logger.error(f"Error en get_order_total_and_rate: {str(e)}", exc_info=True)
            return {'error': f'Error interno: {str(e)}'}
        
    # -------------------------------------------------------------------------
    # Ruta para subir comprobante (POST)
    # -------------------------------------------------------------------------
    @http.route(['/shop/upload_payment_proof'], type='http', methods=['POST'], auth='public', website=True, csrf=False)
    def upload_payment_proof(self, **post):
        file = request.httprequest.files.get('payment_proof_file')
        if not file or not file.filename:
            return request.make_response('ERROR', status=400)

        sale_order_id = request.session.get('sale_order_id') or request.session.get('sale_last_order_id')
        order = None
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(int(sale_order_id)).exists()

        file_data = file.read()
        file_base64 = base64.b64encode(file_data).decode('utf-8')
        filename = file.filename
        
        # ---- MEJORA: Detectar correctamente el mimetype para que la imagen se vea en el chatter ----
        mimetype = file.content_type
        if not mimetype or mimetype == 'application/octet-stream':
            ext = filename.split('.')[-1].lower()
            if ext in ('jpg', 'jpeg'):
                mimetype = 'image/jpeg'
            elif ext == 'png':
                mimetype = 'image/png'
            elif ext == 'gif':
                mimetype = 'image/gif'
            elif ext == 'pdf':
                mimetype = 'application/pdf'
            else:
                mimetype = 'application/octet-stream'
        # ---------------------------------------------------------------------------------------

        payment_data = {
            'payment_date': post.get('payment_date'),
            'payment_method': post.get('payment_method'),
            'bank_origin': post.get('bank_origin'),
            'bank_destination': post.get('bank_destination', 'N/A'),
            'reference': post.get('reference'),
            'amount_vef': float(post.get('amount_vef', 0)),
            'exchange_rate': float(post.get('exchange_rate', 0)),
            'amount_usd': float(post.get('amount_usd', 0)),
        }
        _logger.info(f"📝 Datos de pago recibidos: {payment_data}")

        # Guardar en sesión por si se necesita después
        request.session['payment_data'] = payment_data

        if order:
            try:
                # 1. Crear attachment
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'type': 'binary',
                    'datas': file_base64,
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'mimetype': mimetype,
                    'description': 'Comprobante de pago - Transferencia / Pago Móvil',
                })
                
                # 2. Escribir campos binarios y metadata directamente en la orden
                order.sudo().write({
                    'payment_proof': file_base64,
                    'payment_proof_filename': filename,
                    'payment_date': payment_data['payment_date'],
                    'payment_method': payment_data['payment_method'],
                    'bank_origin': payment_data['bank_origin'],
                    'bank_destination': payment_data['bank_destination'],
                    'reference': payment_data['reference'],
                    'amount_vef': payment_data['amount_vef'],
                    'exchange_rate': payment_data['exchange_rate'],
                    'amount_usd': payment_data['amount_usd'],
                })
                
                # 3. Publicar en el chatter con la imagen en línea (si es imagen)
                # Construir URL del attachment para mostrarla en línea
                # Usar un timestamp para evitar caché, si no hay write_date se omite
                timestamp = int(attachment.write_date.timestamp()) if attachment.write_date else ''
                attachment_url = f"/web/image/{attachment.id}" + (f"?unique={timestamp}" if timestamp else "")
                
                # Generar cuerpo HTML
                if mimetype.startswith('image/'):
                    img_tag = f'<div style="margin-top: 10px;"><img src="{attachment_url}" style="max-width: 100%; max-height: 300px; border: 1px solid #ccc; padding: 5px;" /></div>'
                else:
                    img_tag = f'<div style="margin-top: 10px;"><a href="{attachment_url}" target="_blank">📄 Ver archivo adjunto</a></div>'
                
                body_html = f"""
                <p>🧾 <strong>Comprobante de pago adjunto</strong></p>
                <ul>
                    <li>📅 Fecha: {payment_data.get('payment_date', 'No especificada')}</li>
                    <li>💳 Método: {payment_data.get('payment_method', 'No especificado')}</li>
                    <li>🔢 Referencia: {payment_data.get('reference', 'No especificada')}</li>
                    <li>₿ Monto Bs: {payment_data.get('amount_vef', 0):,.2f}</li>
                    <li>💱 Tasa BCV: {payment_data.get('exchange_rate', 0):,.4f}</li>
                    <li>💵 Monto USD: {payment_data.get('amount_usd', 0):,.2f}</li>
                </ul>
                {img_tag}
                <p><em>Adjunto: {filename}</em></p>
                """
                
                order.sudo().message_post(
                    body=body_html,
                    attachment_ids=[attachment.id],
                    message_type='comment',
                    subtype_id=request.env.ref('mail.mt_comment').id
                )
                _logger.info(f"✅ Comprobante guardado y publicado en orden {order.name}")
                return request.make_response('OK')
            except Exception as e:
                _logger.error(f"Error guardando comprobante: {e}", exc_info=True)
                return request.make_response('ERROR', status=500)

        # Si no hay orden, guardar en sesión (fallback para cuando aún no se ha creado)
        request.session['payment_proof'] = {
            'data': file_base64,
            'filename': filename,
            'mimetype': mimetype,
        }
        _logger.info(f"📤 Comprobante guardado en sesión: {filename}")
        return request.make_response('OK')

    # -------------------------------------------------------------------------
    # Endpoint JSON: ID del proveedor de transferencia bancaria
    # -------------------------------------------------------------------------
    @http.route('/payment_proof/get_transfer_provider_id', type='json', auth='public', csrf=False)
    def get_transfer_provider_id(self):
        provider = request.env['payment.provider'].sudo().search([('is_wire_transfer', '=', True)], limit=1)
        _logger.info(f"Transfer provider ID: {provider.id if provider else 0}")
        return provider.id if provider else 0

    # -------------------------------------------------------------------------
    # Endpoint JSON: lista de bancos venezolanos
    # -------------------------------------------------------------------------
    @http.route('/payment_proof/get_bank_list', type='json', auth='public', csrf=False)
    def get_bank_list(self):
        try:
            banks = request.env['res.bank'].sudo().search([('active', '=', True)], order='name ASC')
            bank_list = []
            for bank in banks:
                bank_list.append({
                    'id': bank.bic,
                    'name': bank.name,
                    'bic': bank.bic,
                })
            _logger.info(f"Devolviendo {len(bank_list)} bancos desde res.bank")
            return bank_list
        except Exception as e:
            _logger.error(f"Error al obtener lista de bancos: {str(e)}")
            return [
                {'id': '0102', 'name': 'Banco de Venezuela', 'bic': '0102'},
                {'id': '0134', 'name': 'Banesco Banco Universal', 'bic': '0134'},
                {'id': '0105', 'name': 'Banco Mercantil', 'bic': '0105'},
            ]

    # -------------------------------------------------------------------------
    # Endpoint JSON: lista de bancos desde diarios contables (para banco destino)
    # -------------------------------------------------------------------------
    @http.route('/payment_proof/get_bank_journal_list', type='json', auth='public', csrf=False)
    def get_bank_journal_list(self):
        try:
            bank_journals = request.env['account.journal'].sudo().search([
                ('type', '=', 'bank'),
                ('active', '=', True),
            ], order='name ASC')
            bank_list = []
            for journal in bank_journals:
                bank_name = journal.bank_id.name if journal.bank_id else journal.name
                bank_list.append({
                    'id': journal.id,
                    'name': bank_name,
                    'journal_id': journal.id,
                    'bic': journal.bank_id.bic if journal.bank_id else '',
                })
            _logger.info(f"Devolviendo {len(bank_list)} bancos desde los diarios contables")
            return bank_list
        except Exception as e:
            _logger.error(f"Error al obtener lista de bancos: {str(e)}")
            return []

    # -------------------------------------------------------------------------
    # Endpoint JSON: obtener datos del banco destino (para instrucciones de pago)
    # -------------------------------------------------------------------------
    @http.route('/payment_proof/get_bank_details', type='json', auth='public', csrf=False)
    def get_bank_details(self, journal_id):
        try:
            if not journal_id:
                return {'error': 'No se especificó banco destino'}
            try:
                journal_id = int(journal_id)
            except (ValueError, TypeError):
                return {'error': f'ID de banco inválido: {journal_id}'}
            journal = request.env['account.journal'].sudo().browse(journal_id).exists()
            if not journal:
                return {'error': f'Banco destino no encontrado con ID: {journal_id}'}
            bank_details = {
                'bank_name': journal.bank_id.name if journal.bank_id else journal.name,
                'account_number': journal.bank_acc_number or 'No especificado',
                'account_holder': journal.bank_id and journal.bank_id.name or request.env.company.name,
                'phone': journal.bank_id and journal.bank_id.phone or '',
                'email': journal.bank_id and journal.bank_id.email or '',
                'routing_number': journal.bank_id and journal.bank_id.bic or '',
                'instructions': 'Transferencia bancaria - Por favor use su número de orden como referencia',
            }
            company = request.env.company
            bank_details['company_name'] = company.name
            bank_details['company_rif'] = company.vat or ''
            _logger.info(f"Detalles del banco destino para journal {journal_id}: {bank_details}")
            return bank_details
        except Exception as e:
            _logger.error(f"Error al obtener detalles del banco: {str(e)}", exc_info=True)
            return {'error': str(e)}

    # -------------------------------------------------------------------------
    # Hook _process_payment (recupera datos de sesión si no se guardaron antes)
    # -------------------------------------------------------------------------
    def _process_payment(self, **kwargs):
        """Procesa el pago y recupera los datos de sesión si aún no se han guardado"""
        _logger.info("🔄 Entrando en _process_payment (Payment Custom)")
        sale_order_id = request.session.get('sale_order_id') or request.session.get('sale_last_order_id')
        order = None
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(int(sale_order_id)).exists()

        # Si existe el comprobante en sesión y no se ha guardado aún (fallback)
        if order and 'payment_proof' in request.session:
            proof = request.session.pop('payment_proof')
            try:
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': proof['filename'],
                    'type': 'binary',
                    'datas': proof['data'],
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'mimetype': proof.get('mimetype', 'application/octet-stream'),
                    'description': 'Comprobante de pago - Transferencia / Pago Móvil',
                })
                _logger.info(f"✅ Attachment creado en Sale Order {order.name} desde sesión")
                order.sudo().write({
                    'payment_proof': proof['data'],
                    'payment_proof_filename': proof['filename'],
                })
                # Publicar en chatter con vista previa de imagen (similar al método anterior)
                timestamp = int(attachment.write_date.timestamp()) if attachment.write_date else ''
                attachment_url = f"/web/image/{attachment.id}" + (f"?unique={timestamp}" if timestamp else "")
                mimetype = proof.get('mimetype', '')
                if mimetype.startswith('image/'):
                    img_tag = f'<div style="margin-top: 10px;"><img src="{attachment_url}" style="max-width: 100%; max-height: 300px; border: 1px solid #ccc; padding: 5px;" /></div>'
                else:
                    img_tag = f'<div style="margin-top: 10px;"><a href="{attachment_url}" target="_blank">📄 Ver archivo adjunto</a></div>'
                body_html = f"<p>🧾 <strong>Comprobante de pago adjunto</strong> (recuperado desde sesión)</p>{img_tag}<p><em>Adjunto: {proof['filename']}</em></p>"
                order.sudo().message_post(
                    body=body_html,
                    attachment_ids=[attachment.id],
                    message_type='comment',
                    subtype_id=request.env.ref('mail.mt_comment').id
                )
            except Exception as e:
                _logger.error(f"Error creando attachment desde sesión: {e}", exc_info=True)

        # También recuperar datos de pago adicionales si existen y aún no se han escrito
        if order and 'payment_data' in request.session:
            payment_data = request.session.pop('payment_data')
            try:
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
                _logger.info(f"✅ Datos de pago adicionales guardados en orden {order.name}")
            except Exception as e:
                _logger.error(f"Error guardando datos de pago adicionales: {e}", exc_info=True)

        return super()._process_payment(**kwargs)