from odoo import models, fields, api

class Website(models.Model):
    _inherit = 'website'

    def get_bcv_rate(self):
        """Retorna la tasa USD/VES actual (cuántos bolívares por 1 USD)"""
        company = self.company_id
        if company.bcv_manual_rate_active and company.bcv_manual_rate > 0:
            return company.bcv_manual_rate
        rate_info = self.get_rate_info(currency_name='USD')
        return rate_info.get('rate', 1.0)

    def get_conversion_factor_ves_to_usd(self):
        """
        Retorna el factor para convertir VES a USD (precio_VES * factor = precio_USD).
        """
        if self.company_id.currency_id.name == 'USD':
            return 1.0

        rate = self.get_bcv_rate()
        if rate and rate > 1.0:
            return 1.0 / rate
        return 0.0

    def get_bcv_rate_info(self):
        """
        Retorna un dict con la tasa BCV (1 USD = X VES).
        Mantenido por compatibilidad con plantillas existentes.
        """
        info = self.get_rate_info(currency_name='USD')
        if info.get('rate') == 1.0 and info.get('date') is None:
             info = self.get_rate_info()
        return info

    def get_cop_rate(self):
        """Retorna la tasa COP actual (cuántos pesos colombianos por 1 USD)"""
        company = self.company_id
        if company.cop_manual_rate_active and company.cop_manual_rate > 0:
            return company.cop_manual_rate
        # Buscar directamente por provider_type='bogota' ya que el provider
        # tiene currency_id=USD (1 USD = X COP), no COP.
        rate = self.env['res.currency.rate'].search([
            ('currency_id.name', '=', 'USD'),
            ('company_id', '=', company.id),
            ('provider_id.provider_type', '=', 'bogota'),
        ], order='name desc', limit=1)
        if rate and rate.original_value:
            return rate.original_value
        provider = self.env['currency.rate.provider'].sudo().search([
            ('company_id', '=', company.id),
            ('provider_type', '=', 'bogota'),
            ('active', '=', True),
        ], limit=1)
        if provider and provider.last_rate:
            return provider.last_rate
        return 1.0

    def get_cop_rate_info(self):
        """
        Retorna un dict con la tasa COP (1 USD = X COP).
        """
        company = self.company_id
        rate_val = self.get_cop_rate()
        provider = self.env['currency.rate.provider'].sudo().search([
            ('company_id', '=', company.id),
            ('provider_type', '=', 'bogota'),
            ('active', '=', True),
        ], limit=1)
        date_formatted = ''
        if provider and provider.last_update:
            date_formatted = provider.last_update.strftime('%d/%m/%Y')
        return {
            'rate': rate_val,
            'currency_name': 'COP',
            'date_formatted': date_formatted,
        }
