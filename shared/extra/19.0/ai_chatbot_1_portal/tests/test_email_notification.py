from odoo.tests import TransactionCase, tagged
import logging

_logger = logging.getLogger(__name__)


@tagged('ai_chatbot_1_portal', 'email_notification')
class TestEmailNotification(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.team = cls.env['crm.team'].create({
            'name': 'Test Grupo Citas',
            'alias_name': 'test-citas-unisa',
        })

        cls.user = cls.env['res.users'].create({
            'name': 'Test Agent',
            'login': 'test_agent@test.com',
            'email': 'saymon_set@hotmail.com',
            'password': 'test123',
        })
        cls.team.write({'member_ids': [(6, 0, [cls.user.id])]})

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Patient',
            'vat': '12345678',
            'phone': '+584141234567',
            'email': 'patient@test.com',
            'type': 'contact',
            'company_type': 'person',
        })

        cls.tag = cls.env['crm.tag'].create({
            'name': 'Test Bot Tag',
            'color': 10,
        })

        cls.utm_medium = cls.env['utm.medium'].create({'name': 'Test WhatsApp'})
        cls.utm_source = cls.env['utm.source'].create({'name': 'Test WhatsApp Bot UNISA'})
        cls.utm_campaign = cls.env['utm.campaign'].create({'name': 'Test Campaña WhatsApp UNISA'})

        cls.env['ir.config_parameter'].sudo().set_param('unisa_bot_last_user_test', False)

    def _create_test_lead(self):
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils
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
            'name': 'Juan Pérez',
            'phone': '+584161234567',
            'email': 'juan@test.com',
        }
        lead = ChatBotUtils.create_lead(
            self.env, data, self.partner, self.team,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        return lead

    def test_01_email_template_exists(self):
        template = self.env.ref('ai_chatbot_1_portal.email_template_lead_asignado', raise_if_not_found=False)
        self.assertTrue(template, "Template de email debe existir")
        self.assertEqual(template.model_id.model, 'crm.lead')

    def test_02_email_sent_on_assignment(self):
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        lead = self._create_test_lead()

        mail_count_before = self.env['mail.mail'].search_count([])
        ChatBotUtils.assign_lead_round_robin(self.env, lead, self.team)

        self.assertTrue(lead.user_id.id, "Lead debe tener usuario asignado")
        self.assertEqual(lead.user_id.email, 'saymon_set@hotmail.com')

        mail_count_after = self.env['mail.mail'].search_count([])
        self.assertEqual(mail_count_after, mail_count_before + 1, "Debe haberse creado 1 mail.mail")

        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(mail.email_to, 'saymon_set@hotmail.com')
        self.assertIn('Juan Pérez', mail.body_html or '')
        self.assertIn('4161234567', mail.body_html or '')
        self.assertIn('Consulta General', mail.body_html or '')
        self.assertEqual(mail.model, 'crm.lead')
        self.assertEqual(mail.res_id, lead.id)

    def test_03_no_email_if_user_no_email(self):
        from odoo.addons.ai_chatbot_1_portal.controllers.chatbot_utils import ChatBotUtils

        user_sin_email = self.env['res.users'].create({
            'name': 'No Email Agent',
            'login': 'noemail_agent@test.com',
            'email': '',
            'password': 'test123',
        })
        team_tmp = self.env['crm.team'].create({
            'name': 'Test Team No Email',
            'member_ids': [(6, 0, [user_sin_email.id])],
        })

        data = {
            'solicitar_name': 'Test',
            'solicitar_vat': '11111111',
            'solicitar_phone': '+584241234567',
            'solicitar_birthdate': '01/01/2000',
            'solicitar_email': 'test@test.com',
            'servicio_solicitado': 'Consulta',
            'consentimiento': True,
            'plataforma': 'whatsapp',
            'equipo_asignado': 'Agendamiento_Directo',
            'name': 'Test',
            'phone': '+584241234567',
            'email': 'test@test.com',
        }
        lead = ChatBotUtils.create_lead(
            self.env, data, self.partner, team_tmp,
            self.utm_medium, self.utm_source, self.utm_campaign, self.tag
        )
        lead.write({'user_id': False})

        try:
            ChatBotUtils.assign_lead_round_robin(self.env, lead, team_tmp)
            self.assertTrue(lead.user_id.id)
        except Exception as e:
            self.fail(f"No debe fallar si usuario no tiene email: {e}")
