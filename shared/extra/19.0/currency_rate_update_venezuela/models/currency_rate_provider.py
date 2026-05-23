import re
import logging
import requests
import urllib3
from bs4 import BeautifulSoup
from odoo import models, fields, _

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_logger = logging.getLogger(__name__)

class CurrencyRateProvider(models.Model):
    _inherit = 'currency.rate.provider'

    provider_type = fields.Selection(selection_add=[
        ('bcv', 'Banco Central de Venezuela')
    ], ondelete={'bcv': 'set default'})

    def _fetch_rate_bcv(self):
        """Extracts the official USD rate from the BCV website."""
        try:
            url = 'https://www.bcv.org.ve'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            response = requests.get(url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Search for blocks containing "USD"
            text_blocks = soup.find_all(string=re.compile(r'(?i)USD', re.DOTALL | re.IGNORECASE))

            for block in text_blocks:
                # BCV format: thousands with dot, decimal with comma
                match = re.search(r'(\d{1,3}(?:\.\d{3})*,\d{2,8})', block)
                if match:
                    tasa_str = match.group(1)
                    cleaned = tasa_str.replace('.', '').replace(',', '.')
                    try:
                        tasa = float(cleaned)
                        if 10 < tasa < 2000000:
                            _logger.info(f"BCV Rate detected: {tasa}")
                            return tasa
                    except ValueError:
                        continue

            # Fallback
            full_text = soup.get_text(separator=' ', strip=True)
            match = re.search(r'(?i)USD\s*[^0-9]*?(\d{1,3}(?:\.\d{3})*,\d{2,8})', full_text)
            if match:
                tasa_str = match.group(1)
                cleaned = tasa_str.replace('.', '').replace(',', '.')
                tasa = float(cleaned)
                if 10 < tasa < 2000000:
                    return tasa

            _logger.warning("Could not extract USD rate from BCV")
            return False

        except Exception as e:
            _logger.error(f"Error fetching BCV rate: {e}")
            return False
