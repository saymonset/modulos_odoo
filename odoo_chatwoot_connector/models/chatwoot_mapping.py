from odoo import models, fields


class ChatwootMapping(models.Model):
    _name = 'chatwoot.mapping'
    _description = 'Mapeo Chatwoot para flujos/equipos'

    name = fields.Char(required=True, help="Etiqueta interna (p.ej. CITAS_MP o flujo_agendamiento)")
    flow_id = fields.Many2one('chatbot.flujo', string='Flujo (opcional)')
    equipo_asignado = fields.Char(string="Equipo Asignado (valor esperado desde n8n/AI)")
    chatwoot_inbox_id = fields.Integer(string='Chatwoot inbox id')
    chatwoot_agent_id = fields.Integer(string='Chatwoot agent id (User id)')
    chatwoot_tags = fields.Char(string='Tags (CSV)', help='Tags separados por comas')
    active = fields.Boolean(default=True)
