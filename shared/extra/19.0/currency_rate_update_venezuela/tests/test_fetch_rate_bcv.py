from unittest.mock import patch, MagicMock
import os

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def _load_fixture(filename):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


@tagged("-at_install", "post_install", "bcv_scraping")
class TestFetchRateBcv(TransactionCase):

    def _create_provider(self):
        return self.env['currency.rate.provider'].create({
            'name': 'BCV Venezuela Test',
            'provider_type': 'bcv',
            'currency_id': self.env.ref('base.VES', raise_if_not_found=False).id
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
        html = _load_fixture('bcv_sample.html')
        with patch('requests.get', return_value=self._mock_response(html)):
            rate = provider._fetch_rate_bcv()
        self.assertTrue(rate)
        self.assertAlmostEqual(rate, 36.50, places=2)

    def test_02_invalid_html_returns_false(self):
        provider = self._create_provider()
        with patch('requests.get', return_value=self._mock_response("<html><body>No rates here</body></html>")):
            rate = provider._fetch_rate_bcv()
        self.assertFalse(rate)

    def test_03_out_of_bounds_returns_false(self):
        provider = self._create_provider()
        html = "<html><body><p>USD 5,00</p></body></html>"
        with patch('requests.get', return_value=self._mock_response(html)):
            rate = provider._fetch_rate_bcv()
        self.assertFalse(rate)

    def test_04_connection_error_returns_false(self):
        provider = self._create_provider()
        import requests
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("No internet")):
            rate = provider._fetch_rate_bcv()
        self.assertFalse(rate)

    def test_05_large_rate_with_thousands_sep(self):
        provider = self._create_provider()
        html = "<html><body><p>USD 1.234,56</p></body></html>"
        with patch('requests.get', return_value=self._mock_response(html)):
            rate = provider._fetch_rate_bcv()
        self.assertTrue(rate)
        self.assertAlmostEqual(rate, 1234.56, places=2)