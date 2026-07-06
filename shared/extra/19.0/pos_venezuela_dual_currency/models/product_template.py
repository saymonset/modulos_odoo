from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def get_bcv_rate_json(self, company_id):
        """Wrapper para _get_bcv_rate accesible desde JS vía orm.call.
        Acepta company_id (int) desde el frontend y retorna la tasa (float).
        """
        company = self.env['res.company'].browse(company_id)
        return self._get_bcv_rate(company)
