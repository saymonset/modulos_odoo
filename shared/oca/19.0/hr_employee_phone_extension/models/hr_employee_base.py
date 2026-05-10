# copyright 2013 Savoir-faire Linux (<http://www.savoirfairelinux.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrEmployeePhoneExtensionMixin(models.AbstractModel):
    """Enhance the features of the employee using Number details."""
    _name = "hr.employee.phone.extension.mixin"
    _description = "Employee Phone Extension Mixin"

    internal_number = fields.Char(help="Internal phone number.")
    short_number = fields.Char(help="Short phone number.")

class HrEmployee(models.Model):
    _inherit = ["hr.employee", "hr.employee.phone.extension.mixin"]

class HrEmployeePublic(models.Model):
    _inherit = ["hr.employee.public", "hr.employee.phone.extension.mixin"]
