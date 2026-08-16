from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class BaseWhatsappTestCase(TransactionCase):

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
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'phone': '+584121234567',
        })
        cls.waba_account = cls.env['waba.account'].create({
            'name': 'Test WABA',
            'phone_number_id': '123456789',
            'access_token': 'test_token',
            'verify_token': 'test_verify',
            'active': True,
        })