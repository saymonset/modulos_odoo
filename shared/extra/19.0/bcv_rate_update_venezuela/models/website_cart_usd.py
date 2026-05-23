from odoo import models, fields, api

class Website(models.Model):
    _inherit = 'website'

    def get_bcv_rate(self):
        """Retorna la tasa USD/VES actual (cuántos bolívares por 1 USD)"""
        # get_rate_info returns the 'rate' as display_val (original_value or rate)
        rate_info = self.get_rate_info(currency_name='USD')
        return rate_info.get('rate', 1.0)

    def get_conversion_factor_ves_to_usd(self):
        """
        Retorna el factor para convertir VES a USD (precio_VES * factor = precio_USD).
        """
        # Si la moneda base ya es USD, no hay factor de conversión (es 1.0)
        if self.company_id.currency_id.name == 'USD':
            return 1.0
            
        rate = self.get_bcv_rate()
        # Si la tasa es 1.0 o 0.0 y la moneda base no es USD, la tasa no es válida
        if rate and rate > 1.0:
            return 1.0 / rate
        return 0.0
    
    def get_bcv_rate_info(self):
        """
        Retorna un dict con la tasa BCV (1 USD = X VES).
        Mantenido por compatibilidad con plantillas existentes.
        """
        # Priorizar el proveedor marcado como "Main" o buscar USD
        info = self.get_rate_info(currency_name='USD')
        
        # Si no hay tasa de USD específica, intentamos obtener cualquier tasa activa (para otros países)
        if info.get('rate') == 1.0 and info.get('date') is None:
             info = self.get_rate_info()

        return info