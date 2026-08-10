import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_igtf = fields.Boolean(
        string='¿Este pago incluye IGTF?',
        default=False,
        help="Marca este método de pago para aplicar automáticamente el IGTF"
    )
    igtf_percentage = fields.Float(
        string='Porcentaje IGTF',
        default=0.0,
        help='Porcentaje del IGTF que se aplica a esta transacción'
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['is_igtf', 'igtf_percentage']
        return params
