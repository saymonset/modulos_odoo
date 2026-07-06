/** @odoo-module **/
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";
import { CustomPaymentStatus } from "./custom_payment_status/custom_payment_status";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PaymentScreenStatus.prototype, {
    components: {
        ...PaymentScreenStatus.components,
        CustomPaymentStatus,
    },
    setup() {
        this.pos = usePos();
        super.setup(...arguments);
    },
});
