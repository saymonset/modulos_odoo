/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomPaymentStatus extends Component {
    static template = "pos_venezuela_dual_currency.CustomPaymentStatus";
    static props = {};

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ rate: 1 });

        this.loadRate().then(r => {
            this.state.rate = r || 1;
        });
    }

    getRefTotal() {
        const order = this.pos?.getOrder();
        if (!order || !this.state.rate) return 0;
        return (order.totalDue || 0) / this.state.rate;
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
