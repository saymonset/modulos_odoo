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

        // Capture remainingDue BEFORE super creates the payment line,
        // because addPaymentline() sets the line amount to remainingDue
        // and then remainingDue becomes 0.
        const dueBefore = this.currentOrder?.remainingDue || 0;

        const result = await super.addNewPaymentLine(paymentMethod);

        if (paymentMethod.is_igtf) {
            const lines = this.paymentLines;
            if (lines.length > 0) {
                const lastLine = lines[lines.length - 1];
                if (lastLine) {
                    const igtfAmount = ((paymentMethod.igtf_percentage / 100) * dueBefore) * -1;
                    try {
                        lastLine.setAmount(igtfAmount);
                    } catch (_) {
                        console.warn("pos_venezuela_dual_currency: IGTF setAmount failed", _);
                    }

                    let rate = 0;
                    try {
                        rate = await this.env.services.orm.call(
                            "product.template",
                            "get_bcv_rate_json",
                            [this.pos.company.id]
                        );
                    } catch (_) {}

                    lastLine.currency_type = 'bs';
                    lastLine.rate_applied = rate || 0;
                    lastLine.amount_foreign = rate > 0
                        ? Math.round((igtfAmount / rate) * 100) / 100
                        : 0;
                }
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
