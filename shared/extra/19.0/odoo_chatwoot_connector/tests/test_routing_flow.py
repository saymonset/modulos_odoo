from odoo.tests import TransactionCase, tagged
import logging

_logger = logging.getLogger(__name__)


@tagged('odoo_chatwoot_connector', 'routing_mapping')
class TestRoutingFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Mapping = cls.env['chatwoot.mapping']
        cls.team_a = cls.env['crm.team'].create({'name': 'Test Equipo A'})
        cls.team_b = cls.env['crm.team'].create({'name': 'Test Equipo B'})
        cls.flow_medios = cls.env['chatbot.flujo'].create({
            'name': 'flujo_citas_medios_propios',
            'company_id': cls.env.company.id,
        })
        cls._clean_params()

    @classmethod
    def _clean_params(cls):
        cls.env['ir.config_parameter'].sudo().search(
            [('key', 'like', 'odoo_chatwoot_connector_last_mapping_%')]
        ).unlink()

    def test_routing_key_codigo_generico(self):
        self._clean_params()
        m = self.Mapping.create({
            'name': 'Mapeo por routing_key',
            'routing_key': 'Cotizacion_Personalizada',
            'team_id': self.team_a.id,
        })
        rec = self.Mapping.select_round_robin_mapping(
            team=self.team_a, equipo_asignado='Cotizacion_Personalizada',
        )
        self.assertEqual(rec.id, m.id)

    def test_equipo_asignado_legacy_sigue_funcionando(self):
        self._clean_params()
        m = self.Mapping.create({
            'name': 'Mapeo legacy',
            'equipo_asignado': 'flujo_citas_medios_propios',
            'team_id': self.team_a.id,
        })
        rec = self.Mapping.select_round_robin_mapping(
            team=self.team_a, equipo_asignado='flujo_citas_medios_propios',
        )
        self.assertEqual(rec.id, m.id)

    def test_flow_name_fallback_sin_equipo(self):
        self._clean_params()
        m = self.Mapping.create({
            'name': 'Mapeo por flow',
            'flow_id': self.flow_medios.id,
            'team_id': self.team_b.id,
        })
        rec = self.Mapping.select_round_robin_mapping(
            team=self.team_b, equipo_asignado='', flow_name='flujo_citas_medios_propios',
        )
        self.assertEqual(rec.id, m.id)

    def test_flow_name_fallback_cuando_equipo_no_coincide(self):
        self._clean_params()
        m = self.Mapping.create({
            'name': 'Mapeo por flow',
            'flow_id': self.flow_medios.id,
            'team_id': self.team_b.id,
        })
        rec = self.Mapping.select_round_robin_mapping(
            team=self.team_b, equipo_asignado='otro_codigo', flow_name='flujo_citas_medios_propios',
        )
        self.assertEqual(rec.id, m.id)

    def test_round_robin_por_equipo(self):
        self._clean_params()
        m1 = self.Mapping.create({
            'name': 'M1', 'routing_key': 'Cotizacion_Simple', 'team_id': self.team_a.id,
        })
        m2 = self.Mapping.create({
            'name': 'M2', 'routing_key': 'Cotizacion_Simple', 'team_id': self.team_a.id,
        })
        r1 = self.Mapping.select_round_robin_mapping(
            team=self.team_a, equipo_asignado='Cotizacion_Simple',
        )
        r2 = self.Mapping.select_round_robin_mapping(
            team=self.team_a, equipo_asignado='Cotizacion_Simple',
        )
        self.assertEqual(r1.id, m1.id)
        self.assertEqual(r2.id, m2.id)