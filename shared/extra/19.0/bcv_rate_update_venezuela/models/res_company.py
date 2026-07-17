from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    schedule_info = fields.Char(string="Horario de Atención", default="Abierto - Cierra a las 7:00 p.m.")

    bcv_manual_rate_active = fields.Boolean(
        string='Usar Tasa Manual',
        default=False,
        help='Activar para usar una tasa de cambio manual en lugar de la tasa oficial del BCV.'
    )
    bcv_manual_rate = fields.Float(
        string='Tasa Manual (1 USD = X VES)',
        digits=(12, 2),
        default=0.0,
        help='Tasa de cambio manual. Solo se usa si "Usar Tasa Manual" está activo.'
    )

    cop_show_fields = fields.Boolean(
        string='Mostrar precios en COP',
        default=False,
        help='Activar para mostrar columnas y precios en Pesos Colombianos (COP) en todo el sistema.'
    )
    cop_manual_rate_active = fields.Boolean(
        string='Usar Tasa COP Manual',
        default=False,
        help='Activar para usar una tasa COP manual en lugar de la TRM automática.'
    )
    cop_manual_rate = fields.Float(
        string='Tasa COP Manual (1 USD = X COP)',
        digits=(12, 2),
        default=0.0,
        help='Tasa de cambio manual para COP. Solo se usa si "Usar Tasa COP Manual" está activo.'
    )

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {'bcv_manual_rate_active', 'bcv_manual_rate'}
        if trigger_fields & set(vals.keys()):
            for company in self:
                if company.bcv_manual_rate_active and company.bcv_manual_rate > 0:
                    self.env['product.template']._recalculate_ves_prices_from_usd()
                    break
        trigger_cop = {'cop_manual_rate_active', 'cop_manual_rate'}
        if trigger_cop & set(vals.keys()):
            for company in self:
                if company.cop_manual_rate_active and company.cop_manual_rate > 0:
                    self.env['product.template']._recalculate_cop_prices_from_usd()
                    break
        return res