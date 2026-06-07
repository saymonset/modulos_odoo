from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError
from unittest.mock import patch
import logging

_logger = logging.getLogger(__name__)


@tagged('ai_chatbot_1_portal', 'lead_creation')
class TestLeadCreation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.team = cls.env['crm.team'].create({
            'name': 'Test Grupo Citas',
            'alias_name': 'test-citas-unisa',
        })

        cls.user_1 = cls.env['res.users'].create({
            'name': 'Test Agent 1',
            'login': 'test_agent1@test.com',
            'email': 'test_agent1@test.com',
            'password': 'test123',
        })
        cls.user_2 = cls.env['res.users'].create({
            'name': 'Test Agent 2',
            'login': 'test_agent2@test.com',
            'email': 'test_agent2@test.com',
            'password': 'test123',
        })
        cls.team.write({'member_ids': [(6, 0, [cls.user_1.id, cls.user_2.id])]})

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Patient',
            'vat': '12345678',
            'phone': '+584141234567',
            'email': 'patient@test.com',
            'type': 'contact',
            'company_type': 'person',
        })

        cls.stage = cls.env['crm.stage'].search([('name', 'ilike', 'nuevo')], limit=1)
        if not cls.stage:
            cls.stage = cls.env['crm.stage'].search([], limit=1)

        cls.tag = cls.env['crm.tag'].create({
            'name': 'Test Bot Tag',
            'color': 10,
        })

        cls.utm_medium = cls.env['utm.medium'].create({'name': 'Test WhatsApp'})
        cls.utm_source = cls.env['utm.source'].create({'name': 'Test WhatsApp Bot UNISA'})
        cls.utm_campaign = cls.env['utm.campaign'].create({'name': 'Test Campaña WhatsApp UNISA'})

        cls.env['ir.config_parameter'].sudo().set_param('unisa_bot_last_user_test', False)

    def _make_lead_data(self, overrides=None):
        data = {
            'solicitar_name': 'Juan Pérez',
            'solicitar_vat': '87654321',
            'solicitar_phone': '+584161234567',
            'solicitar_birthdate': '15/05/1990',
            'solicitar_email': 'juan@test.com',
            'servicio_solicitado': 'Consulta General',
            'consentimiento': True,
            'plataforma': 'whatsapp',
            'equipo_asignado': 'Agendamiento_Directo',
            'solicitar_fecha_preferida': '01/07/2026',
            'solicitar_consulta_deseada': 'Medicina General',
            'name': 'Juan Pérez',
            'phone': '+584161234567',
            'email': 'juan@test.com',
        }
        if overrides:
            data.update(overrides)
        return data

    def test_01_create_lead_basic(self):
        """Crear lead básico con datos mínimos"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        data = self._make_lead_data()
        lead = ChatBotUtils.create_lead(
            self.env, data, self.partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )

        self.assertTrue(lead.id, "Lead debe tener ID")
        self.assertIn('Consulta General', lead.name)
        self.assertIn(f'ID {lead.id}', lead.name)
        self.assertEqual(lead.partner_id.id, self.partner.id)
        self.assertEqual(lead.contact_name, 'Juan Pérez')
        self.assertEqual(lead.email_from, 'juan@test.com')
        self.assertEqual(lead.team_id.id, self.team.id)
        self.assertEqual(lead.type, 'opportunity')
        self.assertEqual(lead.stage_id.id, self.stage.id)
        self.assertTrue(self.tag in lead.tag_ids, "Tag debe estar asignado")
        self.assertIn('Cédula', lead.description)
        self.assertIn('Consentimiento WhatsApp', lead.description)

    def test_02_create_lead_without_email(self):
        """Crear lead sin email (debe funcionar)"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        data = self._make_lead_data({'solicitar_email': '', 'email': ''})
        lead = ChatBotUtils.create_lead(
            self.env, data, self.partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        self.assertTrue(lead.id)
        self.assertEqual(lead.email_from, self.partner.email)

    def test_03_create_resultados_lead_lab(self):
        """Crear lead de resultados de laboratorio"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        data = self._make_lead_data({
            'equipo_asignado': 'RESULTADOS_LAB',
            'estudio_solicitado': 'Hemograma Completo',
            'identificacion_paciente': 'Juan Pérez',
        })
        lead = ChatBotUtils.create_resultados_lead(
            self.env, data, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        self.assertTrue(lead.id)
        self.assertIn('Resultados LABORATORIO', lead.name)
        self.assertIn('Hemograma Completo', lead.name)
        self.assertIn('SOLICITUD DE RESULTADOS', lead.description)
        self.assertIn('LABORATORIO', lead.description)

    def test_04_create_resultados_lead_imagenes(self):
        """Crear lead de resultados de imágenes"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        data = self._make_lead_data({
            'equipo_asignado': 'RESULTADOS_IMAGENES',
            'estudio_solicitado': 'Resonancia Magnética',
            'identificacion_paciente': 'María García',
        })
        lead = ChatBotUtils.create_resultados_lead(
            self.env, data, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        self.assertTrue(lead.id)
        self.assertIn('Resultados IMAGENOLOGÍA', lead.name)
        self.assertIn('IMAGENOLOGÍA', lead.description)

    def test_05_round_robin_assignment(self):
        """Round-robin asigna usuarios secuencialmente"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        data = self._make_lead_data()
        lead_1 = ChatBotUtils.create_lead(
            self.env, data, self.partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        ChatBotUtils.assign_lead_round_robin(self.env, lead_1, self.team)
        self.assertTrue(lead_1.user_id.id, "Lead debe tener usuario asignado")
        first_user = lead_1.user_id.id

        lead_2 = ChatBotUtils.create_lead(
            self.env, data, self.partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        ChatBotUtils.assign_lead_round_robin(self.env, lead_2, self.team)
        second_user = lead_2.user_id.id
        self.assertNotEqual(first_user, second_user, "Round-robin debe asignar usuarios diferentes")

        lead_3 = ChatBotUtils.create_lead(
            self.env, data, self.partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        ChatBotUtils.assign_lead_round_robin(self.env, lead_3, self.team)
        third_user = lead_3.user_id.id
        self.assertEqual(first_user, third_user,
                         "Round-robin debe ciclar: 3ra asignación = 1er usuario")

    def test_06_round_robin_sin_miembros(self):
        """Round-robin sin miembros del equipo no debe fallar"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        team_sin_miembros = self.env['crm.team'].create({
            'name': 'Test Sin Miembros',
        })
        data = self._make_lead_data()
        lead = ChatBotUtils.create_lead(
            self.env, data, self.partner, team_sin_miembros,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        # Limpiar user_id asignado automáticamente por CRM
        lead.write({'user_id': False})
        ChatBotUtils.assign_lead_round_robin(self.env, lead, team_sin_miembros)
        self.assertFalse(lead.user_id, "Lead no debe tener usuario asignado sin miembros")

    def test_07_generate_description(self):
        """Generar descripción del lead incluye todos los campos"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        data = self._make_lead_data()
        description = ChatBotUtils.generate_description(data)
        self.assertIn('Juan Pérez', description)
        self.assertIn('87654321', description)
        self.assertIn('juan@test.com', description)
        self.assertIn('Consulta General', description)
        self.assertIn('Medicina General', description)
        self.assertIn('WhatsApp', description)

    def test_08_create_partner_lead_integration(self):
        """Crear partner y lead en flujo completo"""
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        partner = ChatBotUtils.update_create_contact(self.env, {
            'solicitar_name': 'Nuevo Paciente',
            'solicitar_vat': '99999999',
            'solicitar_phone': '+584241234567',
            'solicitar_birthdate': '10/10/1985',
            'solicitar_email': 'nuevo@test.com',
            'consentimiento': True,
        })
        self.assertTrue(partner.id, "Partner debe crearse")
        self.assertEqual(partner.name, 'Nuevo Paciente')
        self.assertEqual(partner.vat, '99999999')
        self.assertEqual(partner.email, 'nuevo@test.com')

        data = self._make_lead_data({
            'solicitar_name': 'Nuevo Paciente',
            'solicitar_vat': '99999999',
            'solicitar_phone': '+584241234567',
            'solicitar_email': 'nuevo@test.com',
        })
        lead = ChatBotUtils.create_lead(
            self.env, data, partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        self.assertTrue(lead.id)
        ChatBotUtils.assign_lead_round_robin(self.env, lead, self.team)
        self.assertTrue(lead.user_id.id, "Lead debe tener usuario asignado")
