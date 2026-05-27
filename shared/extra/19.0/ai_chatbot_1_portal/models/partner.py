# models/partner.py
from odoo import models, fields, api
from datetime import datetime

class ResPartner(models.Model):
    _inherit = 'res.partner'

    birthdate = fields.Date(string='Fecha de Nacimiento')
    age = fields.Integer(string='Edad', compute='_compute_age', store=False)
    consentimiento_whatsapp = fields.Boolean(string='Consentimiento WhatsApp', default=False)

    @api.depends('birthdate')
    def _compute_age(self):
        for partner in self:
            if partner.birthdate:
                today = datetime.now().date()
                birthdate = fields.Date.from_string(partner.birthdate)
                age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                partner.age = age
            else:
                partner.age = 0