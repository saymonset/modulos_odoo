/** @odoo-module **/
import { patch } from '@web/core/utils/patch';
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { posState } from "../../../shared_state";

const _origSetup = PaymentScreen.prototype.setup;
const _origAddNewPaymentLine = PaymentScreen.prototype.addNewPaymentLine;
const _origDeletePaymentLine = PaymentScreen.prototype.deletePaymentLine;

patch(PaymentScreen.prototype, {
    setup() {
        if (_origSetup) {
            _origSetup.call(this, ...arguments);
        }

        onWillStart(() => {
            posState.setCurrentOrder(this.currentOrder);
        });
        onWillUpdateProps((nextProps) => {
            posState.setCurrentOrder(nextProps.currentOrder);
        });
    },

    async addNewPaymentLine(paymentMethod) {
        posState.setPaymentMethodName(paymentMethod.name);
        posState.is_igtf = paymentMethod.is_igtf;

        const result = await _origAddNewPaymentLine.call(this, paymentMethod);

        if (paymentMethod.is_igtf) {
            const lines = this.paymentLines;
            if (lines.length > 0) {
                const lastLine = lines[lines.length - 1];
                const totalDue = this.currentOrder?.remainingDue || 0;
                const igtfAmount = ((paymentMethod.igtf_percentage / 100) * totalDue) * -1;
                lastLine.setAmount(igtfAmount);
            }
        }

        return result;
    },

    async deletePaymentLine(uuid) {
        posState.setPaymentMethodName("");
        posState.is_igtf = false;
        return _origDeletePaymentLine.call(this, uuid);
    },
});
