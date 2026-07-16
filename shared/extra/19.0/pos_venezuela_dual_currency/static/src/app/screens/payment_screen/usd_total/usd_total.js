/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

let _rate = 1;
let _rateLoaded = false;

export class PaymentScreenDueUsd extends Component {
    static template = "pos_venezuela_dual_currency.PaymentScreenDueUsd";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        onMounted(() => this._ensureRate());
    }

    get totalBs() {
        const order = this.pos.getOrder();
        return order ? (order.priceIncl || 0) : 0;
    }

    get remainingBs() {
        const order = this.pos.getOrder();
        return order ? (order.remainingDue || 0) : 0;
    }

    get totalUsd() {
        return _rate > 0 ? this.totalBs / _rate : 0;
    }

    get remainingUsd() {
        return _rate > 0 ? this.remainingBs / _rate : 0;
    }

    formatAmount(value) {
        if (value == null || isNaN(value)) return "0,00";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    async _ensureRate() {
        if (_rateLoaded) return;
        try {
            const rate = await this.orm.call(
                "product.template", "get_bcv_rate_json",
                [this.pos.company.id]
            );
            _rate = rate || 1;
            _rateLoaded = true;
            this.render();
        } catch (e) {
            _rateLoaded = true;
        }
    }
}
