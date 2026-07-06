/** @odoo-module **/

import { Component, useState, onWillUpdateProps, onRendered } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomButton extends Component {
    static template = "pos_venezuela_dual_currency.CustomButton";
    static props = {
        line: Object,
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ price: 0, rate: 1 });

        this.loadRate().then(rate => {
            this.state.rate = rate || 1;
        });

        onRendered(() => {
            this.updateRef();
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.line.price !== this.props.line.price) {
                this.updateRef();
            }
        });
    }

    updateRef() {
        const price = this.extractNumericPrice(this.props.line.price);
        this.state.price = this.state.rate > 0 ? price / this.state.rate : 0;
    }

    extractNumericPrice(price) {
        if (typeof price === 'number') return price;
        if (typeof price === 'string') {
            const match = price.match(/[\d.]+/);
            return match ? parseFloat(match[0]) : 0;
        }
        return 0;
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
