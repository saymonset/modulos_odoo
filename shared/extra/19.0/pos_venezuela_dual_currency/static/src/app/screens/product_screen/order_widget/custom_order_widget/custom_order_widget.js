/** @odoo-module **/

import { Component, useState, onRendered, onWillUpdateProps } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";

export class CustomOrderWidget extends Component {
    static template = "pos_venezuela_dual_currency.CustomOrderWidget";
    static props = {
        lines: { type: Array, element: Object, optional: true },
        taxTotals: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ ref: 1, taxTotals: this.props.taxTotals });

        this.loadRate().then(rate => {
            this.state.ref = rate || 1;
        });

        onRendered(() => {
            this.state.taxTotals = this.props.taxTotals;
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.taxTotals !== this.props.taxTotals) {
                this.state.taxTotals = nextProps.taxTotals;
            }
        });
    }

    formatMonetary(value, options) {
        return formatMonetary(value, options);
    }

    getRefTotal() {
        const tt = this.state.taxTotals;
        if (!tt) return 0;
        const total = (tt.order_sign || 0) * (tt.order_total || 0);
        return this.state.ref > 0 ? total / this.state.ref : 0;
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
