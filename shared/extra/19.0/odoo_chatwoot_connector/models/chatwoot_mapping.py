from odoo import models, fields


EQUIPO_ASIGNADO_SELECTION = [
    ('Agendamiento_Directo', 'Agendamiento Directo'),
    ('Agendamiento_Precios', 'Agendamiento Precios'),
    ('Agendamiento_Servicios', 'Agendamiento Servicios'),
    ('Agendamiento_Otra_Consulta', 'Agendamiento Otra Consulta'),
    ('Ventas_UNISA', 'Ventas UNISA'),
    ('CITAS_MP', 'Citas Medios Propios'),
    ('CITAS_SEGUROS', 'Citas Seguros'),
    ('RESULTADOS_LAB', 'Resultados Laboratorio'),
    ('RESULTADOS_IMAGENES', 'Resultados Imágenes'),
    # Aliases de compatibilidad durante migración y cargas antiguas
    ('flujo_agendamiento_directo', 'Legacy: flujo_agendamiento_directo'),
    ('flujo_agendamiento_precios', 'Legacy: flujo_agendamiento_precios'),
    ('flujo_agendamiento_servicios', 'Legacy: flujo_agendamiento_servicios'),
    ('flujo_agendamiento_otra_consulta', 'Legacy: flujo_agendamiento_otra_consulta'),
    ('flujo_ventas_unisa', 'Legacy: flujo_ventas_unisa'),
    ('flujo_citas_medios_propios', 'Legacy: flujo_citas_medios_propios'),
    ('flujo_citas_seguro', 'Legacy: flujo_citas_seguro'),
    ('flujo_resultados_laboratorio', 'Legacy: flujo_resultados_laboratorio'),
    ('flujo_resultados_imagenes', 'Legacy: flujo_resultados_imagenes'),
]


class ChatwootMapping(models.Model):
    _name = 'chatwoot.mapping'
    _description = 'Mapeo Chatwoot para flujos/equipos'

    name = fields.Char(required=True, help="Nombre corto para reconocer el mapping en la lista.")
    flow_id = fields.Many2one(
        'chatbot.flujo',
        string='Flujo (opcional)',
        help='Elige el flujo interno si quieres dejarlo ligado a un flujo de chatbot.'
    )
    team_id = fields.Many2one(
        'crm.team',
        string='Equipo CRM',
        help='Equipo de Odoo que recibirá el lead cuando llegue este equipo asignado.'
    )
    equipo_asignado = fields.Selection(
        EQUIPO_ASIGNADO_SELECTION,
        string="Equipo Asignado",
        help="Selecciona un valor exacto del workflow n8n. No se debe escribir a mano.")
    chatwoot_inbox_id = fields.Integer(
        string='Chatwoot inbox id',
        help='ID de la bandeja de entrada en Chatwoot. Se usa como respaldo si no se asigna a un agente.'
    )
    chatwoot_agent_id = fields.Integer(
        string='Chatwoot agent id (User id)',
        help='ID numérico del agente en Chatwoot. Si lo sabes, puedes usarlo para asignar directo.'
    )
    chatwoot_agent_email = fields.Char(
        string='Chatwoot agent email',
        help='Email del agente en Chatwoot. Úsalo si no quieres depender del ID.'
    )
    prefer_assign_to_agent = fields.Boolean(
        string='Intentar asignar a agente primero',
        default=True,
        help='Si está activo, primero intenta asignar al agente y luego usa la inbox como respaldo.'
    )
    chatwoot_tags = fields.Char(
        string='Tags (CSV)',
        help='Escribe los tags separados por coma. Ejemplo: Citas,WhatsApp'
    )
    active = fields.Boolean(
        default=True,
        help='Desactiva este mapping si ya no quieres que se use, sin borrarlo.'
    )
