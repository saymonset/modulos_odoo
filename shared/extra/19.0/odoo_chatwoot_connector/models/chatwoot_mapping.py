from odoo import models, fields


class ChatwootMapping(models.Model):
    _name = 'chatwoot.mapping'
    _description = 'Mapeo Chatwoot para flujos/equipos'

    name = fields.Char(required=True, help="Etiqueta interna (p.ej. CITAS_MP o flujo_agendamiento)")
    flow_id = fields.Many2one('chatbot.flujo', string='Flujo (opcional)')
    team_id = fields.Many2one('crm.team', string='Equipo CRM', help='Equipo CRM al que se asocia este mapping')
    equipo_asignado = fields.Char(string="Equipo Asignado (valor esperado desde n8n/AI)")
    chatwoot_inbox_id = fields.Integer(string='Chatwoot inbox id', help='Inbox id en Chatwoot (fallback)')
    chatwoot_agent_id = fields.Integer(string='Chatwoot agent id (User id)', help='ID de agente en Chatwoot (opcional)')
    chatwoot_agent_email = fields.Char(string='Chatwoot agent email', help='Email del agente para resolver dinámicamente si cambia el id')
    prefer_assign_to_agent = fields.Boolean(string='Intentar asignar a agente primero', default=True)
    chatwoot_tags = fields.Char(string='Tags (CSV)', help='Tags separados por comas')
    active = fields.Boolean(default=True)
