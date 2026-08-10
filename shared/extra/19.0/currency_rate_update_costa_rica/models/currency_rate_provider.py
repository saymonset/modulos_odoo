import re
import logging
import requests
from bs4 import BeautifulSoup
from odoo import models, fields, _

_logger = logging.getLogger(__name__)

class CurrencyRateProvider(models.Model):
    _inherit = 'currency.rate.provider'

    provider_type = fields.Selection(selection_add=[
        ('bccr', 'Banco Central de Costa Rica')
    ], ondelete={'bccr': 'set default'})

    def _fetch_rate_bccr(self):
        """Extracts the official USD rate from the BCCR website."""
        try:
            url = 'https://www.bccr.fi.cr/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for "Venta USD"
            # In the markdown view we saw: "Venta USD₡ 457,33"
            # We search for text that contains "Venta USD" followed by numbers
            text = soup.get_text(separator=' ', strip=True)
            match = re.search(r'Venta USD\s*[₡]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
            
            if not match:
                # Try searching in specific spans/divs if text search fails
                # BCCR often uses specific IDs or classes for these values
                # But a regex on the full text is usually robust for simple scraping
                match = re.search(r'Venta\s*USD\s*(\d{3,4}[\.,]\d{2})', text)

            if match:
                tasa_str = match.group(1)
                # Costa Rica uses dot as decimal and comma as thousands usually, or vice versa?
                # Based on markdown: 457,33 (comma as decimal)
                # Wait, let's look closer at line 335: "Venta USD₡ 457,33"
                # So comma is decimal.
                cleaned = tasa_str.replace('.', '').replace(',', '.')
                try:
                    tasa = float(cleaned)
                    if 300 < tasa < 1000:
                        _logger.info(f"BCCR Rate detected: {tasa}")
                        return tasa
                except ValueError:
                    pass

            _logger.warning("Could not extract USD rate from BCCR")
            return False

        except Exception as e:
            _logger.error(f"Error fetching BCCR rate: {e}")
            return False
