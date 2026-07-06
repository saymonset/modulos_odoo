/** @odoo-module **/
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { CustomPaymentLines } from "./custom_payment_lines/custom_payment_lines";

patch(PaymentScreenPaymentLines, {
    components: {
        ...PaymentScreenPaymentLines.components,
        CustomPaymentLines,
    },
});
