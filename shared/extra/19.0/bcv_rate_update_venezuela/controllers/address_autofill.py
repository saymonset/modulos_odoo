from odoo import http
from odoo.http import request


class AddressAutofill(http.Controller):

    @http.route('/shop/get_company_address_data', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def get_company_address_data(self):
        """Retorna datos por defecto de la compañía (Venezuela fallback)"""
        company = request.env.company
        venezuela = request.env['res.country'].search([('code', '=', 'VE')], limit=1)
        default_country_id = venezuela.id if venezuela else False

        return {
            'country_id': company.country_id.id if company.country_id else default_country_id,
            'city': company.city or '',
            'zip': company.zip or '',
        }

    @http.route('/shop/search_partner_by_email_or_phone', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def search_partner_by_email_or_phone(self, email='', phone='', **kwargs):
        """
        Busca contacto por email o teléfono.
        """
        Partner = request.env['res.partner'].sudo()
        domain = []

        email = (email or '').strip()
        phone = (phone or '').strip()

        if email and '@' in email and len(email) >= 5:
            domain.append(('email', 'ilike', email))

        if phone and len(phone) >= 5:
            phone_clean = ''.join(filter(str.isdigit, phone))
            if phone_clean:
                domain.append(('phone', 'ilike', phone_clean))

        if not domain:
            return {}

        # Buscar primero por email (más preciso), luego por teléfono
        partner = Partner.search(domain, limit=1, order='email desc')  
        
        if not partner:
            return {}

        return {
            'name': partner.name or '',
            'phone': partner.phone or '',
            'email': partner.email or '',
            'street': partner.street or '',
            'street2': partner.street2 or '',
            'city': partner.city or '',
            'zip': partner.zip or '',
            'country_id': partner.country_id.id if partner.country_id else False,
            'state_id': partner.state_id.id if partner.state_id else False,
            'vat': partner.vat or '',
        }