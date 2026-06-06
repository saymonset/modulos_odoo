import logging

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


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

    @api.model
    def select_round_robin_mapping(self, team=None, equipo_asignado=None, flow_name=None):
        """Return the next active mapping for the given context.

        Priority:
        1. exact equipo_asignado
        2. flow_name
        3. team_id
        Then rotate among the candidate mappings in ascending id order.
        """
        candidates = self.sudo().search([('active', '=', True)]).sorted('id')

        if equipo_asignado:
            filtered = candidates.filtered(lambda m: m.equipo_asignado == equipo_asignado)
            if filtered:
                candidates = filtered

        if not candidates and flow_name:
            filtered = self.sudo().search([('active', '=', True)]).filtered(
                lambda m: m.flow_id and m.flow_id.name == flow_name
            )
            if filtered:
                candidates = filtered.sorted('id')

        if not candidates and team:
            team_id = team.id if hasattr(team, 'id') else int(team)
            filtered = self.sudo().search([('active', '=', True), ('team_id', '=', team_id)]).sorted('id')
            if filtered:
                candidates = filtered

        if not candidates:
            return self.browse()

        rr_key_parts = [
            str(team.id if hasattr(team, 'id') and team else team or ''),
            equipo_asignado or '',
        ]
        rr_key = 'odoo_chatwoot_connector_last_mapping_' + '_'.join([p for p in rr_key_parts if p])
        params = self.env['ir.config_parameter'].sudo()
        last_id = params.get_param(rr_key)

        next_rec = candidates[0]
        if last_id:
            try:
                last_id = int(last_id)
                ids = candidates.ids
                if last_id in ids:
                    idx = ids.index(last_id)
                    next_rec = candidates[(idx + 1) % len(candidates)]
            except Exception:
                next_rec = candidates[0]

        params.set_param(rr_key, next_rec.id)
        return next_rec
