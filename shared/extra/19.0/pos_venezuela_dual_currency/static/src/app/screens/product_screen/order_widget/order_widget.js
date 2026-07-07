/** @odoo-module */

import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { patch } from "@web/core/utils/patch";
import { useState, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const _origSetup = OrderDisplay.prototype.setup;

patch(OrderDisplay.prototype, {
    setup() {
        if (_origSetup) {
            _origSetup.call(this, ...arguments);
        }
        this.orm = useService("orm");
        this._usdState = useState({ rate: 1, orderTotal: 0 });
        this._updateOrderTotal();
        this._loadRate();

        onWillUpdateProps(() => {
            this._updateOrderTotal();
        });
    },

    _updateOrderTotal() {
        const order = this.props.order;
        if (!order) return;
        const total = order.total
            || order.currencyDisplayPriceIncl
            || (typeof order.getTotalDue === 'function' ? order.getTotalDue() : 0)
            || 0;
        this._usdState.orderTotal = total;
    },

    _getRefTotal() {
        if (!this._usdState?.rate || this._usdState.rate <= 0) return 0;
        const total = this._usdState.orderTotal || 0;
        return total ? total / this._usdState.rate : 0;
    },

    async _loadRate() {
        try {
            const order = this.props.order;
            if (!order) return;
            const company = order.company_id || this.env.services?.pos?.company;
            if (!company) return;
            const rate = await this.orm.call(
                'product.template', 'get_bcv_rate_json', [company.id]
            );
            this._usdState.rate = rate || 1;
        } catch (e) {
            console.error("Error al obtener tasa BCV:", e);
        }
    },

    formatDecimal(value) {
        if (value == null || isNaN(value)) return "0.00";
        return Number(value).toFixed(2);
    },
});
