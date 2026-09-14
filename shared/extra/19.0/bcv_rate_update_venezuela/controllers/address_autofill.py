import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AddressAutofill(http.Controller):

    @http.route('/shop/get_company_address_data', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def get_company_address_data(self):
        """Retorna datos por defecto de la compañía (Venezuela fallback)."""
        company = request.env.company
        venezuela = request.env['res.country'].search([('code', '=', 'VE')], limit=1)
        default_country_id = venezuela.id if venezuela else False

        return {
            'country_id': company.country_id.id if company.country_id else default_country_id,
            'city': company.city or '',
            'zip': company.zip or '',
        }

    @http.route('/shop/find_partner_by_phone', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def find_partner_by_phone(self, phone='', **kwargs):
        """Busca un partner por teléfono usando comparación de dígitos."""
        partner = self.find_partner_by_phone_digits(request.env, phone)
        if not partner:
            return {'found': False}

        return {
            'found': True,
            'partner': {
                'name': partner.name or '',
                'phone': partner.phone or '',
                'email': partner.email or '',
                'company_name': partner.commercial_company_name or '',
                'street': partner.street or '',
                'street2': partner.street2 or '',
                'city': partner.city or '',
                'zip': partner.zip or '',
                'vat': partner.vat or '',
                'country_id': partner.country_id.id if partner.country_id else False,
                'state_id': partner.state_id.id if partner.state_id else False,
            },
        }

    @staticmethod
    def find_partner_by_phone_digits(env, phone):
        """Busca un partner por teléfono comparando solo dígitos.

        Copia las estrategias de ChatBotUtils.find_partner_by_phone
        (ai_chatbot_1_portal) para no acoplar el checkout al chatbot.
        """
        if not phone:
            return None

        phone_digits = ''.join(filter(str.isdigit, str(phone)))
        if not phone_digits or len(phone_digits) < 7:
            _logger.warning('Teléfono inválido o muy corto: %s', phone)
            return None

        partner = None

        # Estrategia 1: buscar por últimos 10 dígitos
        search_term = phone_digits[-10:] if len(phone_digits) >= 10 else phone_digits
        if len(search_term) >= 7:
            partner = env['res.partner'].sudo().search([
                ('phone', '=like', f'%{search_term}'),
                ('active', '=', True),
            ], limit=1)
            if partner:
                return partner

        # Estrategia 2: buscar por dígitos completos
        partner = env['res.partner'].sudo().search([
            ('phone', 'ilike', phone_digits),
            ('active', '=', True),
        ], limit=1)
        if partner:
            return partner

        # Estrategia 3: buscar por últimos 8 dígitos
        if len(phone_digits) >= 8:
            search_term_8 = phone_digits[-8:]
            partner = env['res.partner'].sudo().search([
                ('phone', '=like', f'%{search_term_8}'),
                ('active', '=', True),
            ], limit=1)
            if partner:
                return partner

        # Estrategia 4: comparación manual por dígitos
        all_partners = env['res.partner'].sudo().search([
            ('phone', '!=', False),
            ('active', '=', True),
        ], limit=100)

        for p in all_partners:
            if p.phone:
                p_digits = ''.join(filter(str.isdigit, p.phone))
                if p_digits.endswith(phone_digits) or phone_digits.endswith(p_digits[-8:]):
                    return p

        _logger.warning('No se encontró partner para teléfono: %s', phone)
        return None