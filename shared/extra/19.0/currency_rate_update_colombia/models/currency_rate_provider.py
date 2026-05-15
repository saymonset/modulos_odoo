import re
import logging
import requests
from bs4 import BeautifulSoup
from odoo import models, fields, _

_logger = logging.getLogger(__name__)

class CurrencyRateProvider(models.Model):
    _inherit = 'currency.rate.provider'

    provider_type = fields.Selection(selection_add=[
        ('bogota', 'TRM Colombia (Bogotá)')
    ], ondelete={'bogota': 'set default'})

    def _fetch_rate_bogota(self):
        """Extracts the official TRM rate for Colombia from a reliable source."""
        try:
            # Using dolar-colombia.com as it's very scrape-friendly
            url = 'https://www.dolar-colombia.com/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for 1 USD = X.XXX,XX COP
            text = soup.get_text(separator=' ', strip=True)
            # Markdown: "## 1 USD = 3,794.91 COP"
            match = re.search(r'1 USD\s*=\s*([\d\.,]+)\s*COP', text)
            
            if match:
                tasa_str = match.group(1)
                # Colombia format: thousands with comma, decimal with dot (usually)
                # Based on markdown: 3,794.91
                cleaned = tasa_str.replace(',', '')
                try:
                    tasa = float(cleaned)
                    if 2000 < tasa < 6000:
                        _logger.info(f"Colombia TRM detected: {tasa}")
                        return tasa
                except ValueError:
                    pass

            _logger.warning("Could not extract TRM rate for Colombia")
            return False

        except Exception as e:
            _logger.error(f"Error fetching Colombia rate: {e}")
            return False
