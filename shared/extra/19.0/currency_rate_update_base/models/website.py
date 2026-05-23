from odoo import models, fields, api, _

class Website(models.Model):
    _inherit = 'website'

    def get_rate_info(self, currency_name=None):
        """
        Generic method to get rate information for a specific currency 
        or the first active provider of the company.
        """
        domain = [('company_id', '=', self.company_id.id), ('active', '=', True)]
        
        # If currency_name is provided (e.g. 'USD'), we look for that specific provider
        if currency_name:
            domain.append(('currency_id.name', '=', currency_name))
        
        # 1. Look for providers marked as "Main"
        main_domain = domain + [('is_main_rate', '=', True)]
        
        # 2. Try to find one that matches the company's local currency first
        # (e.g. if company is VES, pick BCV instead of Colombia even if both are main)
        company_currency_id = self.company_id.currency_id.id
        provider = self.env['currency.rate.provider'].sudo().search(
            main_domain + [('rate_currency_id', '=', company_currency_id)],
            limit=1
        )
        
        # 3. Fallback to any main rate if no local match found
        if not provider:
            provider = self.env['currency.rate.provider'].sudo().search(main_domain, limit=1)
            
        # 4. Final fallback to any active provider
        if not provider:
            provider = self.env['currency.rate.provider'].sudo().search(domain, limit=1)
        
        if not provider:
            return {
                'rate': 0.0,
                'date': None,
                'date_formatted': '',
                'rate_display': _('Tasa no configurada'),
                'currency_name': currency_name or '',
            }

        display_val = provider.last_rate
        if not display_val or display_val == 0:
            return {
                'rate': 1.0,
                'date': None,
                'date_formatted': '',
                'rate_display': _('Tasa no disponible'),
                'currency_name': provider.currency_id.name,
            }

        fecha = provider.last_update
        fecha_formateada = fecha.strftime('%d/%m/%Y') if fecha else ''
        
        base_currency = self.company_id.currency_id
        target_currency = provider.currency_id
        
        # Format with symbol from rate_currency_id (e.g. COP, CRC, VES)
        rate_currency = provider.rate_currency_id or base_currency
        rate_symbol = rate_currency.symbol or rate_currency.name
        target_symbol = target_currency.symbol or target_currency.name

        # Smart display: Show "1 USD = Symbol X.XX"
        if target_currency.name == 'USD':
            rate_text = f"1 USD = {rate_symbol} {display_val:,.2f}"
        else:
            rate_text = f"1 {rate_symbol} = {target_symbol} {display_val:,.2f}"

        return {
            'rate': display_val,
            'date': fecha,
            'date_formatted': fecha_formateada,
            'rate_display': rate_text,
            'currency_name': target_currency.name,
        }
