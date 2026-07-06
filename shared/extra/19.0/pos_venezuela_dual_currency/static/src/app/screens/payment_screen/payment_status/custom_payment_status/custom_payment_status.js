/** @odoo-module **/

import { Component, useState, onRendered } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { posState } from "../../../../shared_state";

export class CustomPaymentStatus extends Component {
    static template = "pos_venezuela_dual_currency.CustomPaymentStatus";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ rate: 1, usdTotal: 0 });

        this.loadRate().then(r => {
            this.state.rate = r || 1;
            this.updateUsdTotal();
        });

        onRendered(() => {
            this.updateUsdTotal();
        });
    }

    updateUsdTotal() {
        const order = posState.getCurrentOrder();
        if (order && this.state.rate > 0) {
            this.state.usdTotal = (order.getTotalDue() || 0) / this.state.rate;
        }
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
        return Number(value).toFixed(2);
    }
}
