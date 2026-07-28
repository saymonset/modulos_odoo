from odoo import fields, models


class HrEmployeeSecondLastnameMixin(models.AbstractModel):
    _name = "hr.employee.second.lastname.mixin"
    _description = "Employee Second Lastname Mixin"

    firstname = fields.Char("First name")
    lastname = fields.Char("Last name")
    lastname2 = fields.Char("Second last name")

class HrEmployee(models.Model):
    _inherit = ["hr.employee", "hr.employee.second.lastname.mixin"]

class HrEmployeePublic(models.Model):
    _inherit = ["hr.employee.public", "hr.employee.second.lastname.mixin"]
