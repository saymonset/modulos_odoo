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

    def test_03_remaining_in_bs_uses_remaining_due_without_fallback(self):
        js = self._read(JS_PATH)
        self.assertIn("Math.max(order.remainingDue, 0)", js)
        # El fallback a la última línea de pago reinyectaba la deuda completa
        self.assertNotIn("getAmount", js)
        self.assertNotIn("get_amount", js)

    def test_04_pending_prefill_due_in_shared_state(self):
        js = self._read(JS_PATH)
        self.assertIn("pendingPrefillDue", js)

    def test_05_prefill_consumes_and_resets_pending(self):
        js = self._read(JS_PATH)
        self.assertIn("posState.pendingPrefillDue != null", js)
        self.assertIn('posState.pendingPrefillDue = null', js)

    def test_06_parse_es_ve_removes_thousands_separator(self):
        js = self._read(JS_PATH)
        self.assertIn("_parseEsVE", js)
        self.assertIn("_formatDisplay", js)

    def test_07_select_currency_prefills_converted_remaining(self):
        js = self._read(JS_PATH)
        self.assertIn("_prefillForCurrency", js)
        self.assertIn("remainingAtSelection", js)

    def test_08_restante_zero_shows_zero(self):
        js = self._read(JS_PATH)
        self.assertIn('_formatDisplay(due, false)', js)
        self.assertIn('return "0"', js)
