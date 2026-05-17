from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    schedule_info = fields.Char(string="Horario de Atención", default="Abierto - Cierra a las 7:00 p.m.")