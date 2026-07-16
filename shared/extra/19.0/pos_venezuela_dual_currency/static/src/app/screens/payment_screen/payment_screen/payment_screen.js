/** @odoo-module **/
import { patch } from '@web/core/utils/patch';
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { posState } from "../../../shared_state";
import { PaymentScreenDueUsd } from "../usd_total/usd_total";

patch(PaymentScreen, {
    components: {
        ...PaymentScreen.components,
        PaymentScreenDueUsd,
    },
});

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(() => posState.setCurrentOrder(this.currentOrder));
        onWillUpdateProps((np) => posState.setCurrentOrder(np.currentOrder));
    },

    async addNewPaymentLine(paymentMethod) {
        posState.setPaymentMethodName(paymentMethod.name);
        posState.is_igtf = !!paymentMethod.is_igtf;

        const dueBefore = this.currentOrder?.remainingDue || 0;

        const result = await super.addNewPaymentLine(paymentMethod);

        if (paymentMethod.is_igtf && dueBefore > 0) {
            const line = this.paymentLines[this.paymentLines.length - 1];
            if (line) {
                const igtf = (paymentMethod.igtf_percentage / 100) * dueBefore;
                line.setAmount(-igtf);
            }
        }

        return result;
    },

    async deletePaymentLine(uuid) {
        posState.setPaymentMethodName("");
        posState.is_igtf = false;
        return super.deletePaymentLine(uuid);
    },
});
