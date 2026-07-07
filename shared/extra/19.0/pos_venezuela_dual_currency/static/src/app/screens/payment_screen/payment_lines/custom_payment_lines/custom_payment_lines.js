/** @odoo-module **/

import { Component, useState, onMounted, onWillUpdateProps, useRef } from "@odoo/owl";
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
        this.state = useState({
            result: 0,
            hasData: false,
            rate: 1,
        });

        this.loadRate().then(r => {
            this.state.rate = r || 1;
        });

        onMounted(() => {
            this.updateHasData();
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.paymentLines) {
                this.updateHasData(nextProps.paymentLines);
            }
        });
    }

    updateHasData(paymentLines) {
        const lines = paymentLines || this.props.paymentLines || [];
        this.state.hasData = lines.length > 0;
        if (!this.state.hasData) {
            this.state.result = 0;
        }
    }

    async onInputChange(event) {
        const val = parseFloat(event.target.value) || 0;
        this.state.result = this.state.rate > 0 ? val / this.state.rate : 0;
        this.updateLastPaymentLine(this.state.result);
    }

    onBlur() {
        if (this.inputRef.el) {
            this.inputRef.el.value = '';
        }
        this.state.result = 0;
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
        return Number(value).toFixed(2);
    }
}
