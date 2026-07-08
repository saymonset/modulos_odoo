/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    get orderIsRounded() {
        if (!this.paymentlines) return false;
        return this.paymentlines.some(
            (p) => p.payment_method?.is_cash_count && p.amount > 0
        );
    },
});
