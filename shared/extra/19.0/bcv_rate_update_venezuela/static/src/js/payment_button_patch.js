/** @odoo-module **/
import { patch } from '@web/core/utils/patch';
import { PaymentButton } from '@payment/interactions/payment_button';

patch(PaymentButton.prototype, {
    _canSubmit() {
        const proofRoot = document.getElementById('payment_proof_form_container');
        if (!proofRoot) {
            return super._canSubmit();
        }
        return super._canSubmit() && document.body.dataset.bcvPaymentProofValid === '1';
    },
});
