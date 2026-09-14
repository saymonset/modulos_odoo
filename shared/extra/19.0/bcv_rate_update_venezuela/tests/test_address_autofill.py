from odoo.tests import tagged

from odoo.addons.bcv_rate_update_venezuela.controllers.address_autofill import AddressAutofill

from .common import BaseBcvTestCase


@tagged("-at_install", "post_install")
class TestAddressAutofill(BaseBcvTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Cliente',
            'phone': '+584141234567',
            'email': 'cliente@test.com',
            'vat': 'V-12345678',
            'street': 'Av Principal 123',
            'city': 'Porlamar',
            'zip': '6301',
        })

    def test_01_matching_ignora_formato(self):
        """Formatos distintos encuentran al mismo partner."""
        for phone in ('0414-123.45.67', '+584141234567', '04141234567'):
            partner = AddressAutofill.find_partner_by_phone_digits(self.env, phone)
            self.assertEqual(partner.id, self.partner.id, f"Fallo con formato: {phone}")

    def test_02_telefono_invalido_no_busca(self):
        """Menos de 7 dígitos no devuelve nada."""
        for phone in ('', '123', '12345'):
            self.assertIsNone(
                AddressAutofill.find_partner_by_phone_digits(self.env, phone),
                f"Debía devolver None con: {phone!r}",
            )

    def test_03_sin_match_devuelve_none(self):
        """Un teléfono que no está en BD devuelve None."""
        partner = AddressAutofill.find_partner_by_phone_digits(self.env, '04129999999')
        self.assertIsNone(partner)

    def test_04_no_coincide_con_otro_formato_distinto(self):
        """No confunde un teléfono de otro cliente."""
        otro = self.env['res.partner'].create({'name': 'Otro Cliente', 'phone': '04127654321'})
        partner = AddressAutofill.find_partner_by_phone_digits(self.env, '04127654321')
        self.assertEqual(partner.id, otro.id)