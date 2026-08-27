from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "odoo_chatwoot_connector", "business_config_notice")
class TestBusinessConfigNotice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            no_reset_password=True,
            tracking_disable=True,
        ))

    def test_01_aviso_true_con_config_activa(self):
        self.env['chatbot.config'].create({'name': 'Clínica Notice'})

        setting = self.env['res.config.settings'].create({})

        self.assertTrue(setting.has_active_business_config)

    def test_02_aviso_false_sin_config_activa(self):
        self.env['chatbot.config'].with_context(active_test=False).search([]).write(
            {'active': False})

        setting = self.env['res.config.settings'].create({})

        self.assertFalse(setting.has_active_business_config)