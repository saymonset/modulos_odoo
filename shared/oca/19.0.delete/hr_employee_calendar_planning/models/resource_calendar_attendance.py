from odoo import fields, models


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    date_from = fields.Date(string="Starting Date")
    date_to = fields.Date(string="End Date")
