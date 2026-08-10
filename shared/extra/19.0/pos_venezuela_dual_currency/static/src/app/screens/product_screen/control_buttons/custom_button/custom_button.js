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
        this.state = useState({
            rate: 1,
            copRate: 1,
            copEnabled: false,
            copLoaded: false,
        });

        this.loadRate().then(rate => {
            this.state.rate = rate || 1;
        });
        this.loadCopData();

        onWillUpdateProps(() => {
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

    get priceInCOP() {
        if (!this.state.copEnabled || !this.state.copRate) return 0;
        return this.priceInUSD * this.state.copRate;
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

    async loadCopData() {
        try {
            const [copRate, copEnabled] = await Promise.all([
                this.orm.call('product.template', 'get_cop_rate_json', [this.pos.company.id]),
                this.orm.call('product.template', 'get_cop_enabled_json', [this.pos.company.id]),
            ]);
            this.state.copRate = copRate || 1;
            this.state.copEnabled = !!copEnabled;
            this.state.copLoaded = true;
            this.render();
        } catch (e) {
            this.state.copLoaded = true;
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
