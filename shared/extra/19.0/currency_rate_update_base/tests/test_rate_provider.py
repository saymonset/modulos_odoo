from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestCurrencyRateProvider(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context,
            mail_create_nolog=True,
            mail_create_nosubscribe=True,
            mail_notrack=True,
            tracking_disable=True,
        ))
        cls.USD = cls.env.ref('base.USD')
        cls.EUR = cls.env.ref('base.EUR')
        cls.VES = cls.env.ref('base.VES', raise_if_not_found=False)
        cls.COP = cls.env.ref('base.COP', raise_if_not_found=False)
        cls.company = cls.env.company
        cls.Provider = cls.env['currency.rate.provider']

    def _create_provider(self, name, target_currency, provider_type='manual'):
        return self.Provider.create({
            'name': name,
            'provider_type': provider_type,
            'currency_id': target_currency.id,
            'company_id': self.company.id,
        })

    def test_01_compute_rate_currency_id_venezuela(self):
        if not self.VES:
            self.skipTest("VES currency not found")
        provider = self._create_provider('BCV Venezuela', self.USD, 'bcv')
        self.assertEqual(provider.rate_currency_id, self.VES)

    def test_02_compute_rate_currency_id_colombia(self):
        if not self.COP:
            self.skipTest("COP currency not found")
        provider = self._create_provider('Bogota Colombia', self.USD, 'bogota')
        self.assertEqual(provider.rate_currency_id, self.COP)

    def test_03_compute_rate_currency_id_costa_rica(self):
        crc = self.env.ref('base.CRC', raise_if_not_found=False)
        if not crc:
            self.skipTest("CRC currency not found")
        provider = self._create_provider('Costa Rica BCCR', self.USD, 'bccr')
        self.assertEqual(provider.rate_currency_id, crc)

    def test_04_compute_rate_currency_id_fallback_company(self):
        provider = self._create_provider('Generic Provider', self.USD)
        self.assertEqual(provider.rate_currency_id, self.company.currency_id)

    def test_05_onchange_is_main_rate_uniqueness(self):
        p1 = self._create_provider('Provider 1', self.USD)
        p2 = self._create_provider('Provider 2', self.USD)
        p1.is_main_rate = True
        p2._onchange_is_main_rate()
        self.assertTrue(p1.is_main_rate)
        p2.is_main_rate = True
        p2._onchange_is_main_rate()
        self.assertFalse(p1.is_main_rate)
        self.assertTrue(p2.is_main_rate)

    def test_06_dispatch_fetch_no_method(self):
        provider = self._create_provider('Manual Provider', self.USD, 'manual')
        result = provider._dispatch_fetch()
        self.assertFalse(result)

    def test_07_dispatch_fetch_calls_method(self):
        provider = self._create_provider('Test Fetch', self.USD, 'manual')
        def _fetch_rate_manual(self):
            return 42.0
        provider._fetch_rate_manual = lambda: 42.0
        import types
        provider._fetch_rate_manual = types.MethodType(
            lambda inst: 42.0, provider
        )
        result = provider._dispatch_fetch()
        self.assertEqual(result, 42.0)

    def test_08_update_odoo_rate_base_usd(self):
        if self.company.currency_id != self.USD:
            self.company.currency_id = self.USD
        ves = self.VES or self.env['res.currency'].search([('name', '=', 'VES')], limit=1)
        if not ves:
            self.skipTest("VES currency not found")
        provider = self._create_provider('BCV Test', ves)
        provider._update_odoo_rate(36.5)
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', ves.id),
            ('company_id', '=', self.company.id),
        ], order='name desc', limit=1)
        self.assertTrue(rate)
        self.assertAlmostEqual(rate.rate, 36.5, places=2)
        self.assertAlmostEqual(rate.original_value, 36.5, places=2)

    def test_09_update_odoo_rate_target_usd(self):
        if self.company.currency_id == self.USD:
            self.company.currency_id = self.EUR
        provider = self._create_provider('USD Rate', self.USD)
        provider._update_odoo_rate(36.5)
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.USD.id),
            ('company_id', '=', self.company.id),
        ], order='name desc', limit=1)
        self.assertTrue(rate)
        self.assertAlmostEqual(rate.rate, 1.0 / 36.5, places=4)

    def test_10_update_odoo_rate_zero(self):
        if self.company.currency_id == self.USD:
            self.company.currency_id = self.EUR
        provider = self._create_provider('Zero Test', self.USD)
        provider._update_odoo_rate(0.0)
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.USD.id),
            ('company_id', '=', self.company.id),
        ], order='name desc', limit=1)
        self.assertTrue(rate)
        self.assertEqual(rate.rate, 0.0)

    def test_11_action_update_rate_error_sets_state(self):
        provider = self._create_provider('Error Provider', self.USD)
        def _dispatch_fetch_bad(self):
            raise ValueError("Connection failed")
        import types
        provider._dispatch_fetch = types.MethodType(_dispatch_fetch_bad, provider)
        with self.assertRaises(UserError):
            provider.action_update_rate()
        self.assertEqual(provider.state, 'error')

    def test_12_action_update_rate_success(self):
        if self.company.currency_id != self.USD:
            self.company.currency_id = self.USD
        ves = self.VES or self.env['res.currency'].search([('name', '=', 'VES')], limit=1)
        if not ves:
            self.skipTest("VES currency not found")
        provider = self._create_provider('Good Provider', ves, 'manual')
        import types
        provider._dispatch_fetch = types.MethodType(lambda inst: 35.0, provider)
        provider.action_update_rate()
        self.assertEqual(provider.state, 'active')
        self.assertAlmostEqual(provider.last_rate, 35.0, places=2)