/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class PaymentScreenDueUsd extends Component {
    static template = "pos_venezuela_dual_currency.PaymentScreenDueUsd";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({
            rate: 1,
            orderTotalBs: 0,
        });

        onMounted(() => {
            this.loadRate();
            this._interval = setInterval(() => {
                const order = this.pos.getOrder();
                if (!order) return;
                const total = order.remainingDue || 0;
                if (total !== this.state.orderTotalBs) {
                    this.state.orderTotalBs = total;
                }
            }, 500);
            this._rateInterval = setInterval(() => {
                this.loadRate();
            }, 60000);
        });

        onWillUnmount(() => {
            if (this._interval) {
                clearInterval(this._interval);
            }
            if (this._rateInterval) {
                clearInterval(this._rateInterval);
            }
        });
    }

    get usdTotal() {
        if (!this.state.rate || this.state.rate <= 0) return 0;
        return this.state.orderTotalBs / this.state.rate;
    }

    formatDecimal(value) {
        if (value == null || isNaN(value)) return "0.00";
        return Number(value).toFixed(2);
    }

    async loadRate() {
        try {
            const rate = await this.orm.call(
                "product.template",
                "get_bcv_rate_json",
                [this.pos.company.id]
            );
            this.state.rate = rate || 1;
        } catch (e) {
            console.error("Error al obtener tasa BCV:", e);
        }
    }
}
