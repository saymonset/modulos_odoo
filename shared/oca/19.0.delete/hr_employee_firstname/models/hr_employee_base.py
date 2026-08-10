from odoo import fields, models


class HrEmployeeFirstnameMixin(models.AbstractModel):
    _name = "hr.employee.firstname.mixin"
    _description = "Employee Firstname Mixin"

    firstname = fields.Char()
    lastname = fields.Char()

class HrEmployee(models.Model):
    _inherit = ["hr.employee", "hr.employee.firstname.mixin"]

class HrEmployeePublic(models.Model):
    _inherit = ["hr.employee.public", "hr.employee.firstname.mixin"]
