/** @odoo-module **/
import { patch } from '@web/core/utils/patch';
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { onWillStart, onWillUpdateProps } from "@odoo/owl";
import { posState } from "../../../shared_state";

const originalAddNewPaymentLine = PaymentScreen.prototype.addNewPaymentLine;

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

        await originalAddNewPaymentLine.call(this, paymentMethod);

        if (paymentMethod.is_igtf) {
            const lines = this.paymentLines;
            if (lines.length > 0) {
                const pctStr = ` (${paymentMethod.igtf_percentage}%)`;
                if (!paymentMethod.name.includes(pctStr)) {
                    paymentMethod.name += pctStr;
                }
                const lastLine = lines[lines.length - 1];
                const totalDue = this.currentOrder ? this.currentOrder.getTotalDue() : 0;
                lastLine.amount = ((paymentMethod.igtf_percentage / 100) * totalDue) * -1;
            }
        }
    },

    async deletePaymentLine(uuid) {
        const line = this.paymentLines.find(l => l.uuid === uuid);
        if (line) {
            if (line.payment_method_id.payment_method_type === "qr_code") {
                this.currentOrder.remove_paymentline(line);
                this.numberBuffer.reset();
                return;
            }
            if (["waiting", "waitingCard", "timeout"].includes(line.get_payment_status())) {
                line.set_payment_status("waitingCancel");
                await line.payment_method_id.payment_terminal.send_payment_cancel(this.currentOrder, uuid);
            }
            this.currentOrder.remove_paymentline(line);
            this.numberBuffer.reset();
            posState.setPaymentMethodName("");
            posState.is_igtf = false;
        }
    },
});
