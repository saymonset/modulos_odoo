/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomPaymentStatus extends Component {
    static template = "pos_venezuela_dual_currency.CustomPaymentStatus";
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ rate: 1, orderTotalBs: 0 });

        this.loadRate().then(r => {
            this.state.rate = r || 1;
        });

        onMounted(() => {
            this._interval = setInterval(() => {
                const order = this.pos.getOrder();
                if (!order) return;
                const total = order.remainingDue || 0;
                if (total !== this.state.orderTotalBs) {
                    this.state.orderTotalBs = total;
                }
            }, 500);
        });

        onWillUnmount(() => {
            if (this._interval) {
                clearInterval(this._interval);
            }
        });
    }

    get usdTotal() {
        if (!this.state.rate || this.state.rate <= 0) return 0;
        return this.state.orderTotalBs / this.state.rate;
    }

    async loadRate() {
        try {
            const rate = await this.orm.call(
                'product.template', 'get_bcv_rate_json',
                [this.pos.company.id]
            );
            return rate;
        } catch (e) {
            console.error("Error al obtener tasa BCV:", e);
            return 1;
        }
    }

    formatDecimal(value) {
        if (value == null || isNaN(value)) return "0.00";
        return Number(value).toFixed(2);
    }
}
