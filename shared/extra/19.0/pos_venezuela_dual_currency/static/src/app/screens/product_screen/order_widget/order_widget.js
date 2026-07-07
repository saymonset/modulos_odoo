/** @odoo-module */

import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const _origSetup = OrderDisplay.prototype.setup;

patch(OrderDisplay.prototype, {
    setup() {
        if (_origSetup) {
            _origSetup.call(this, ...arguments);
        }
        this.orm = useService("orm");
        this._usdState = useState({ rate: 1 });
        this._loadRate();
    },
    _getRefTotal() {
        const order = this.props.order;
        if (!order || !this._usdState?.rate) return 0;
        return (order.total || order.currencyDisplayPriceIncl || 0) / this._usdState.rate;
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
        return Number(value).toFixed(2);
    },
});
