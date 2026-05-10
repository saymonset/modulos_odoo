# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models


class HrContractRenewWizard(models.TransientModel):
    _name = "hr.contract.renew.wizard"
    _description = "HR Contract Renew Wizard"

    contract_id = fields.Many2one("hr.version", string="Record", required=True)
    date_end = fields.Date(
        string="End Date", required=True, default=fields.Date.context_today
    )

    def action_renew_contract(self):
        self.ensure_one()
        new_contract = self.contract_id.copy(
            {
                "contract_date_start": self.date_end,
                "date_version": self.date_end,
                "resource_calendar_id": self.contract_id.resource_calendar_id.id,
            }
        )
        self.contract_id.contract_date_end = self.date_end - relativedelta(days=1)
        return {
            "name": _("New Record"),
            "view_mode": "list",
            "res_model": "hr.version",
            "res_id": new_contract.id,
            "type": "ir.actions.act_window",
        }
