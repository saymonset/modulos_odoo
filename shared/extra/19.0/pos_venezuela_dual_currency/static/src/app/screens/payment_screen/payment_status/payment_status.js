/** @odoo-module **/
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";
import { CustomPaymentStatus } from "./custom_payment_status/custom_payment_status";

patch(PaymentScreenStatus, {
    components: {
        ...PaymentScreenStatus.components,
        CustomPaymentStatus,
    },
});
