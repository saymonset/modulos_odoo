/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

let _rate = 1;
let _rateLoaded = false;
let _copRate = 1;
let _copEnabled = false;
let _copRateLoaded = false;

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

    get totalCop() {
        return _copRate > 0 ? this.totalUsd * _copRate : 0;
    }

    get remainingCop() {
        return _copRate > 0 ? this.remainingUsd * _copRate : 0;
    }

    get showCop() {
        return _copEnabled && _copRate > 0 && _copRateLoaded;
    }

    formatAmount(value) {
        if (value == null || isNaN(value)) return "0,00";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    async _ensureRate() {
        if (!_rateLoaded) {
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
        if (!_copRateLoaded) {
            try {
                const [copRate, copEnabled] = await Promise.all([
                    this.orm.call('product.template', 'get_cop_rate_json', [this.pos.company.id]),
                    this.orm.call('product.template', 'get_cop_enabled_json', [this.pos.company.id]),
                ]);
                _copRate = copRate || 1;
                _copEnabled = !!copEnabled;
                _copRateLoaded = true;
                this.render();
            } catch (_) {
                _copRateLoaded = true;
            }
        }
    }
}
