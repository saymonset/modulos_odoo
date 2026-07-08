/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { posState } from "../../../../shared_state";

export class CustomPaymentLines extends Component {
    static template = "pos_venezuela_dual_currency.CustomPaymentLines";
    static props = {
        paymentLines: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.inputRef = useRef("bsInput");
        this._userEdited = false;
        this.state = useState({
            rate: 1,
            inputBs: 0,
            resultUsd: 0,
        });

        this.loadRate().then(r => {
            this.state.rate = r || 1;
            this._autoFill();
        });

        onMounted(() => {
            this._autoFill();
            this._interval = setInterval(() => {
                this._syncRateAndUpdateResult();
            }, 500);
        });

        onWillUnmount(() => {
            if (this._interval) {
                clearInterval(this._interval);
            }
        });
    }

    _autoFill() {
        if (this._userEdited) return;
        const order = this.pos.getOrder();
        if (!order) return;
        const totalBs = order.getTotalDue
            ? order.getTotalDue()
            : (order.totalDue || 0);
        this.state.inputBs = totalBs;
        this.state.resultUsd = this.state.rate > 0 ? totalBs / this.state.rate : 0;
    }

    _syncRateAndUpdateResult() {
        // If user hasn't edited, auto-fill with current total
        if (!this._userEdited) {
            const order = this.pos.getOrder();
            if (!order) return;
            const totalBs = order.getTotalDue
                ? order.getTotalDue()
                : (order.totalDue || 0);
            if (Math.abs(this.state.inputBs - totalBs) > 0.001) {
                this.state.inputBs = totalBs;
            }
        }
        this.state.resultUsd = this.state.rate > 0 ? this.state.inputBs / this.state.rate : 0;
    }

    onInputChange(event) {
        this._userEdited = true;
        const val = parseFloat(event.target.value) || 0;
        this.state.inputBs = val;
        this.state.resultUsd = this.state.rate > 0 ? val / this.state.rate : 0;
        this.updateLastPaymentLine(this.state.resultUsd);
    }

    onBlur() {
        if (this.inputRef.el) {
            this.updateLastPaymentLine(this.state.resultUsd);
        }
    }

    updateLastPaymentLine(newValue) {
        const lines = this.props.paymentLines || [];
        if (lines.length > 0) {
            const lastLine = lines[lines.length - 1];
            if (!posState.is_igtf) {
                lastLine.setAmount(newValue);
            }
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
        if (value == null || isNaN(value)) return "0.00";
        return Number(value).toFixed(2);
    }
}
