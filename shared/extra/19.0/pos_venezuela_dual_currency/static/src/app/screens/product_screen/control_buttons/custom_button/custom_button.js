/** @odoo-module **/

import { Component, useState, onWillUpdateProps } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CustomButton extends Component {
    static template = "pos_venezuela_dual_currency.CustomButton";
    static props = {
        line: Object,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.state = useState({ rate: 1 });

        this.loadRate().then(rate => {
            this.state.rate = rate || 1;
        });

        onWillUpdateProps(() => {
            // force re-render to recompute getter
            this.render();
        });
    }

    get priceInUSD() {
        const line = this.props.line;
        if (!line || !this.state.rate) return 0;
        try {
            const unitPrice = line.prices?.total_excluded_currency || line.price_unit || 0;
            return this.state.rate > 0 ? unitPrice / this.state.rate : 0;
        } catch (_e) {
            return 0;
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
        if (value == null || isNaN(value)) return "0,00";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}
