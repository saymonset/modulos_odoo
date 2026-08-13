from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class BaseBcvTestCase(TransactionCase):
    """Base class for bcv_rate_update_venezuela tests."""

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