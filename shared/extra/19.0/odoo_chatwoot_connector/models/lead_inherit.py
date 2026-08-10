import json
import logging

from html import escape as html_escape

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    chatwoot_conversation_id = fields.Char(string='Chatwoot Conversation ID')
    chatwoot_account_id = fields.Char(string='Chatwoot Account ID')
    chatwoot_assign_log = fields.Text(string='Chatwoot Assign Log')
    chatwoot_assign_failed = fields.Boolean(string='Chatwoot Assign Failed', default=False)
    chatwoot_processing_status = fields.Selection(
        [
            ('new', 'Nuevo'),
            ('assigned', 'Asignado'),
            ('error', 'Error'),
        ],
        string='Estado de Procesamiento Chatwoot',
        default='new',
        index=True,
    )
    chatwoot_processed_at = fields.Datetime(string='Procesado en Chatwoot')
    chatwoot_assigned_agent_name = fields.Char(string='Agente Asignado Chatwoot')

    # -- Auditoría legible del flujo (derivada del JSON de chatwoot_assign_log) --
    chatwoot_flow_name = fields.Char(
        string='Flujo',
        compute='_compute_flow_audit_fields',
    )
    chatwoot_flow_status = fields.Selection(
        [
            ('ok', 'Completado'),
            ('partial', 'Incompleto'),
            ('unknown', 'Sin información'),
        ],
        string='Estado del Flujo',
        compute='_compute_flow_audit_fields',
        store=True,
        index=True,
    )
    chatwoot_flow_steps_total = fields.Integer(
        string='Pasos Esperados',
        compute='_compute_flow_audit_fields',
    )
    chatwoot_flow_steps_completed = fields.Integer(
        string='Pasos Completados',
        compute='_compute_flow_audit_fields',
    )
    chatwoot_flow_steps_required_total = fields.Integer(
        string='Pasos Requeridos',
        compute='_compute_flow_audit_fields',
    )
    chatwoot_flow_steps_required_ok = fields.Integer(
        string='Requeridos Cumplidos',
        compute='_compute_flow_audit_fields',
    )
    chatwoot_flow_summary_html = fields.Html(
        string='Auditoría de Flujo',
        compute='_compute_flow_audit_fields',
        sanitize=False,
    )

    @api.depends('chatwoot_assign_log')
    def _compute_flow_audit_fields(self):
        for record in self:
            data = {}
            if record.chatwoot_assign_log:
                try:
                    data = json.loads(record.chatwoot_assign_log)
                except (ValueError, TypeError):
                    data = {}

            flow_name = data.get('flow_name') or ''
            steps_expected = data.get('steps_expected') or []
            steps_completed = data.get('steps_completed') or []
            steps_missing = data.get('steps_missing') or []
            flow_ok = data.get('flow_ok')
            errors = data.get('errors') or []
            warnings = data.get('warnings') or []

            record.chatwoot_flow_name = flow_name
            if flow_ok is None or not steps_expected:
                record.chatwoot_flow_status = 'unknown'
            elif flow_ok:
                record.chatwoot_flow_status = 'ok'
            else:
                record.chatwoot_flow_status = 'partial'

            record.chatwoot_flow_steps_total = len(steps_expected)
            record.chatwoot_flow_steps_completed = len(steps_completed)

            required_expected = [s for s in steps_expected if s.get('es_requerido')]
            missing_destinos = {s.get('campo_destino') for s in steps_missing}
            record.chatwoot_flow_steps_required_total = len(required_expected)
            record.chatwoot_flow_steps_required_ok = sum(
                1 for s in required_expected if s.get('campo_destino') not in missing_destinos
            )

            # -- Resumen HTML legible para personal funcional --
            status_txt = {
                'ok': '✅ Completado',
                'partial': '⚠️ Incompleto',
                'unknown': '— Sin información',
            }.get(record.chatwoot_flow_status, '—')

            estados_paso = {}
            for s in steps_expected:
                estado = 'sí' if s.get('campo_destino') in steps_completed else 'no'
                estados_paso[s.get('campo_destino')] = estado

            lineas = [f"<b>Flujo:</b> {html_escape(flow_name or 'sin información')}"]
            lineas.append(f"<b>Estado:</b> {status_txt}")
            lineas.append(
                f"<b>Pasos requeridos:</b> {record.chatwoot_flow_steps_required_ok}/"
                f"{record.chatwoot_flow_steps_required_total} cumplidos"
            )
            lineas.append(
                f"<b>Pasos completados:</b> {record.chatwoot_flow_steps_completed}/"
                f"{record.chatwoot_flow_steps_total}"
            )

            if steps_expected:
                lineas.append("<ul>")
                for s in steps_expected:
                    nombre = html_escape(s.get('nombre') or s.get('campo_destino') or '?')
                    campo = s.get('campo_destino')
                    req = 'requerido' if s.get('es_requerido') else 'opcional'
                    marca = '✅' if estados_paso.get(campo) == 'sí' else '❌'
                    lineas.append(f"<li>{marca} <b>{nombre}</b> <i>({req})</i></li>")
                lineas.append("</ul>")

            if errors:
                lineas.append(f"<b>Errores:</b> {html_escape('; '.join(map(str, errors)))}")
            else:
                lineas.append("<b>Errores:</b> ninguno")
            if warnings:
                lineas.append(f"<b>Advertencias:</b> {html_escape('; '.join(map(str, warnings)))}")
            else:
                lineas.append("<b>Advertencias:</b> ninguna")

            if record.chatwoot_flow_status == 'unknown':
                lineas.append(
                    "<i>Sin auditoría registrada. Verifica que el flujo llegó a "
                    "capturar_lead y que n8n envía el name_flow correcto.</i>"
                )

            record.chatwoot_flow_summary_html = "<br/>".join(lineas)