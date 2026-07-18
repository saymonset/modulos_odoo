import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def get_bcv_rate_json(self, company_id):
        company = self.env['res.company'].browse(company_id)
        return self._get_bcv_rate(company)

    @api.model
    def get_cop_rate_json(self, company_id):
        company = self.env['res.company'].browse(company_id)
        return self._get_cop_rate(company)

    @api.model
    def get_cop_enabled_json(self, company_id):
        company = self.env['res.company'].browse(company_id)
        return company.cop_show_fields
