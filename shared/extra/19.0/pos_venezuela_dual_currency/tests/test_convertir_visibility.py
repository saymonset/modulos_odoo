from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import file_open

TEMPLATE_PATH = (
    "pos_venezuela_dual_currency/static/src/app/screens/payment_screen/"
    "payment_lines/custom_payment_lines/custom_payment_lines.xml"
)
JS_PATH = (
    "pos_venezuela_dual_currency/static/src/app/screens/payment_screen/"
    "payment_lines/custom_payment_lines/custom_payment_lines.js"
)


@tagged("-at_install", "post_install", "pos_dual_currency")
class TestConvertirVisibility(TransactionCase):

    def _read(self, path):
        with file_open(path, "r") as fh:
            return fh.read()

    def test_01_template_hides_converter_without_payment_lines(self):
        xml = self._read(TEMPLATE_PATH)
        self.assertIn('t-if="props.paymentLines and props.paymentLines.length > 0"', xml)
        self.assertNotIn("Selecciona un m\xe9todo de pago", xml)

    def test_02_js_prefills_remaining_in_bs(self):
        js = self._read(JS_PATH)
        self.assertIn("prefillFromRemaining()", js)
        self.assertIn('selectedCurrency = "bs"', js)
        self.assertIn("remainingInBs", js)
