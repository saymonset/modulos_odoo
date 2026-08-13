from unittest.mock import patch, MagicMock
import os

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def _load_fixture(filename):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


@tagged("-at_install", "post_install", "bccr_scraping")
class TestFetchRateBccr(TransactionCase):

    def _create_provider(self):
        return self.env['currency.rate.provider'].create({
            'name': 'Costa Rica BCCR Test',
            'provider_type': 'bccr',
            'currency_id': self.env.ref('base.CRC', raise_if_not_found=False).id
                or self.env.ref('base.USD').id,
            'company_id': self.env.company.id,
        })

    def _mock_response(self, html_text):
        resp = MagicMock()
        resp.text = html_text
        resp.raise_for_status.return_value = None
        resp.status_code = 200
        return resp

    def test_01_happy_path(self):
        provider = self._create_provider()
        html = _load_fixture('bccr_sample.html')
        with patch('requests.get', return_value=self._mock_response(html)):
            rate = provider._fetch_rate_bccr()
        self.assertTrue(rate)
        self.assertAlmostEqual(rate, 457.33, places=2)

    def test_02_invalid_html_returns_false(self):
        provider = self._create_provider()
        with patch('requests.get', return_value=self._mock_response("<html><body>No rates</body></html>")):
            rate = provider._fetch_rate_bccr()
        self.assertFalse(rate)

    def test_03_out_of_bounds_returns_false(self):
        provider = self._create_provider()
        html = "<html><body><p>Venta USD 50,00</p></body></html>"
        with patch('requests.get', return_value=self._mock_response(html)):
            rate = provider._fetch_rate_bccr()
        self.assertFalse(rate)

    def test_04_connection_error_returns_false(self):
        provider = self._create_provider()
        import requests
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("No internet")):
            rate = provider._fetch_rate_bccr()
        self.assertFalse(rate)