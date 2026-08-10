/** @odoo-module */

import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { patch } from "@web/core/utils/patch";
import { useState, onMounted, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

const _origSetup = OrderDisplay.prototype.setup;

patch(OrderDisplay.prototype, {
    setup() {
        if (_origSetup) {
            _origSetup.call(this, ...arguments);
        }
        this.pos = usePos();
        this.orm = useService("orm");
        this._usdState = useState({ rate: 1, orderTotal: 0, copRate: 1, copEnabled: false });
        this._loadRate();

        onMounted(() => {
            this._interval = setInterval(() => {
                this._syncOrderTotal();
            }, 500);
        });

        onWillUnmount(() => {
            if (this._interval) {
                clearInterval(this._interval);
            }
        });
    },

    _syncOrderTotal() {
        const order = this.pos.getOrder();
        if (!order) return;
        const total = order.getTotalDue
            ? order.getTotalDue()
            : (order.totalDue || order.total || 0);
        if (total !== this._usdState.orderTotal) {
            this._usdState.orderTotal = total;
        }
    },

    _getRefTotal() {
        if (!this._usdState?.rate || this._usdState.rate <= 0) return 0;
        return this._usdState.orderTotal / this._usdState.rate;
    },

    _getRefCopTotal() {
        if (!this._usdState?.copEnabled || !this._usdState?.copRate) return 0;
        return this._getRefTotal() * this._usdState.copRate;
    },

    async _loadRate() {
        try {
            const rate = await this.orm.call(
                'product.template', 'get_bcv_rate_json',
                [this.pos.company.id]
            );
            this._usdState.rate = rate || 1;
        } catch (e) {
            console.error("Error al obtener tasa BCV:", e);
        }
        try {
            const [copRate, copEnabled] = await Promise.all([
                this.orm.call('product.template', 'get_cop_rate_json', [this.pos.company.id]),
                this.orm.call('product.template', 'get_cop_enabled_json', [this.pos.company.id]),
            ]);
            this._usdState.copRate = copRate || 1;
            this._usdState.copEnabled = !!copEnabled;
        } catch (_) {}
    },

    formatDecimal(value) {
        if (value == null || isNaN(value)) return "0,00";
        return Number(value).toLocaleString("es-VE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    },
});
