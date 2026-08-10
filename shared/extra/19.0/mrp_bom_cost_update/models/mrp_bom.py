from odoo import api, fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    bom_cost = fields.Monetary(
        string='BOM Cost',
        compute='_compute_bom_cost',
        currency_field='currency_id',
        store=False,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='product_tmpl_id.currency_id',
        string="Currency",
    )

    @api.depends(
        'bom_line_ids.product_qty',
        'bom_line_ids.product_id.standard_price',
        'operation_ids.time_cycle',
        'operation_ids.workcenter_id.costs_hour',
        'product_qty',
    )
    def _compute_bom_cost(self):
        for bom in self:
            total = 0.0
            # Material costs
            for line in bom.bom_line_ids:
                qty = line.product_qty
                price = line.product_id.standard_price
                total += qty * price
            # Operation costs
            for operation in bom.operation_ids:
                duration_hours = operation.time_cycle / 60.0
                hourly_cost = operation.workcenter_id.costs_hour
                total += duration_hours * hourly_cost
            bom.bom_cost = total

    def action_update_bom_cost(self):
        self._compute_bom_cost()
        for bom in self:
            if bom.bom_cost:
                product = bom.product_tmpl_id
                product.standard_price = bom.bom_cost
